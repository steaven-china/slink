"""
Encryption utilities using Fernet (AES-128-CBC + HMAC via cryptography).
Master password is derived using PBKDF2-HMAC-SHA256 with a random salt.
"""
import base64
import json
import os
import stat
import sys
import tempfile
from getpass import getpass

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class DecryptError(ValueError):
    """Raised when decryption fails due to wrong password or corrupted data."""
    pass


def _get_default_config_dir() -> str:
    """Return config dir, supports SLINK_USER for multi-user isolation."""
    user = os.environ.get("SLINK_USER")
    if user:
        return os.path.expanduser(f"~/.slink/users/{user}")
    return os.path.expanduser("~/.slink")


DEFAULT_CONFIG_DIR = _get_default_config_dir()
SALT_FILE = os.path.join(DEFAULT_CONFIG_DIR, "salt")
HOSTS_FILE = os.path.join(DEFAULT_CONFIG_DIR, "hosts.enc")


def _secure_chmod(path: str):
    if sys.platform == "win32":
        os.chmod(path, stat.S_IREAD)
    else:
        os.chmod(path, 0o600)


def _ensure_dir():
    dir_path = DEFAULT_CONFIG_DIR
    os.makedirs(dir_path, mode=0o700, exist_ok=True)
    if sys.platform != "win32":
        os.chmod(dir_path, 0o700)
        # Ensure parent dirs down to ~/.slink are also secure
        parent = os.path.dirname(dir_path)
        root = os.path.expanduser("~/.slink")
        while parent and os.path.exists(parent) and parent.startswith(root):
            os.chmod(parent, 0o700)
            parent = os.path.dirname(parent)


def _get_or_create_salt() -> bytes:
    _ensure_dir()
    if os.path.exists(SALT_FILE):
        with open(SALT_FILE, "rb") as f:
            return f.read()

    salt = os.urandom(16)
    # Atomic creation: O_EXCL fails if another process already created it
    try:
        fd = os.open(SALT_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.write(fd, salt)
        finally:
            os.close(fd)
        _secure_chmod(SALT_FILE)
        return salt
    except FileExistsError:
        with open(SALT_FILE, "rb") as f:
            return f.read()


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def _get_key_from_user(prompt: str = "Master password: ") -> bytes:
    password = getpass(prompt)
    salt = _get_or_create_salt()
    return _derive_key(password, salt)


def _get_key(password: str = None) -> bytes:
    if password is None:
        return _get_key_from_user("Master password: ")
    salt = _get_or_create_salt()
    return _derive_key(password, salt)


def encrypt_text(plain_text: str, password: str = None) -> bytes:
    """Encrypt plain text string to encrypted bytes."""
    key = _get_key(password)
    payload = plain_text.encode("utf-8")
    return Fernet(key).encrypt(payload)


def decrypt_text(token: bytes, password: str = None) -> str:
    """Decrypt bytes back to plain text string."""
    key = _get_key(password)
    try:
        payload = Fernet(key).decrypt(token)
        return payload.decode("utf-8")
    except InvalidToken:
        raise DecryptError("Invalid master password or corrupted data.")


def encrypt_file(plain_path: str, enc_path: str, password: str = None):
    """Encrypt a plain text file to an encrypted file."""
    with open(plain_path, "r", encoding="utf-8") as f:
        plain = f.read()
    token = encrypt_text(plain, password)
    # On Windows, must make writable before overwriting a read-only file
    if sys.platform == "win32" and os.path.exists(enc_path):
        os.chmod(enc_path, stat.S_IWRITE)
    with open(enc_path, "wb") as f:
        f.write(token)
    _secure_chmod(enc_path)


def decrypt_file(enc_path: str, plain_path: str, password: str = None):
    """Decrypt an encrypted file to a plain text file."""
    with open(enc_path, "rb") as f:
        token = f.read()
    plain = decrypt_text(token, password)
    with open(plain_path, "w", encoding="utf-8") as f:
        f.write(plain)


def decrypt_file_to_text(enc_path: str, password: str = None) -> str:
    """Decrypt an encrypted file to plain text string."""
    with open(enc_path, "rb") as f:
        token = f.read()
    return decrypt_text(token, password)


# --- Legacy dict-based helpers (for the local encrypted store) ---


def encrypt_data(data: dict, password: str = None) -> bytes:
    """Encrypt a dictionary to bytes."""
    key = _get_key(password)
    payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
    return Fernet(key).encrypt(payload)


def decrypt_data(token: bytes, password: str = None) -> dict:
    """Decrypt bytes back to a dictionary."""
    key = _get_key(password)
    try:
        payload = Fernet(key).decrypt(token)
        return json.loads(payload.decode("utf-8"))
    except InvalidToken:
        raise DecryptError("Invalid master password or corrupted data.")
    except json.JSONDecodeError as exc:
        raise DecryptError(f"Corrupted data: not valid JSON ({exc})")


def save_hosts(hosts: dict, password: str = None):
    """Save hosts dictionary to encrypted file atomically."""
    _ensure_dir()
    token = encrypt_data(hosts, password)

    fd, tmp_path = tempfile.mkstemp(
        dir=DEFAULT_CONFIG_DIR,
        prefix=".hosts.enc.",
        suffix=".tmp"
    )
    try:
        os.write(fd, token)
        os.close(fd)
        _secure_chmod(tmp_path)
        # On Windows, os.replace can't overwrite read-only files
        if sys.platform == "win32" and os.path.exists(HOSTS_FILE):
            os.chmod(HOSTS_FILE, stat.S_IWRITE)
        os.replace(tmp_path, HOSTS_FILE)
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


def load_hosts(password: str = None) -> dict:
    """Load hosts dictionary from encrypted file."""
    if not os.path.exists(HOSTS_FILE):
        return {}
    with open(HOSTS_FILE, "rb") as f:
        token = f.read()
    return decrypt_data(token, password)
