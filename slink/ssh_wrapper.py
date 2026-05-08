"""
SSH connection wrapper.
Uses the system `ssh` command so the user gets their normal shell experience
(Pty, shell rc files, agent forwarding, etc.).
"""
import os
import shutil
import stat
import subprocess
import sys
import tempfile


# Mapping for common key types in case users paste raw keys
KEY_HEADERS = {
    "OPENSSH PRIVATE KEY": "id_ed25519",
    "RSA PRIVATE KEY": "id_rsa",
    "EC PRIVATE KEY": "id_ecdsa",
    "DSA PRIVATE KEY": "id_dsa",
}


def _get_key_filename(key_data: str) -> str:
    key_data = key_data.strip()
    for header, filename in KEY_HEADERS.items():
        if header in key_data:
            return filename
    return "id_key"


def _write_temp_key(key_data: str) -> str:
    """Write a private key to a temp file with safe permissions."""
    key_data = key_data.strip()
    fname = _get_key_filename(key_data)
    fd, path = tempfile.mkstemp(prefix=fname + "_", suffix=".tmp")
    try:
        os.write(fd, key_data.encode("utf-8"))
        os.close(fd)
        if sys.platform == "win32":
            os.chmod(path, stat.S_IREAD)
        else:
            os.chmod(path, 0o600)
        return path
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.remove(path)
        except OSError:
            pass
        raise


def connect(host_info: dict):
    """
    Build and execute an ssh command based on host_info.
    Supported fields:
      - hostname (required)
      - port     (default 22)
      - username (default current user)
      - password (optional; only used for non-interactive modes or expect)
      - key      (optional; PEM private key content string)
      - key_file (optional; path to private key file)
      - jump_host (optional; str or list of jump host spec like user@ip:port)
      - extra_args (optional; list of extra ssh flags)
    """
    hostname = host_info.get("hostname")
    if not hostname:
        raise ValueError("hostname is required")

    port = host_info.get("port", 22)
    username = host_info.get("username")
    password = host_info.get("password")
    key = host_info.get("key")
    key_file = host_info.get("key_file")
    jump_host = host_info.get("jump_host")
    if key_file and not os.path.isfile(key_file):
        raise ValueError(f"Key file not found: {key_file}")
    extra_args = host_info.get("extra_args", [])
    if isinstance(extra_args, str):
        extra_args = extra_args.split()

    use_sshpass = False
    if password and shutil.which("sshpass"):
        use_sshpass = True
    elif password:
        print("Warning: 'sshpass' not found. Install it to use password-based login.", file=sys.stderr)

    ssh_cmd = []
    if use_sshpass:
        ssh_cmd = ["sshpass", "-e", "ssh"]

    if not ssh_cmd:
        ssh_cmd = ["ssh"]

    # Handle jump host chain
    if jump_host:
        if isinstance(jump_host, list):
            jump_str = ",".join(str(j) for j in jump_host)
        else:
            jump_str = str(jump_host)
        ssh_cmd.extend(["-J", jump_str])

    ssh_cmd.extend(["-p", str(port)])
    ssh_cmd.extend(["-o", "StrictHostKeyChecking=accept-new"])

    if extra_args:
        ssh_cmd.extend(extra_args)

    target = hostname
    if username:
        target = f"{username}@{hostname}"
    ssh_cmd.append(target)

    print(f"Connecting to {target} ...")
    tmp_path = None
    try:
        if key:
            tmp_path = _write_temp_key(key)
            ssh_cmd.extend(["-i", tmp_path])
        elif key_file:
            ssh_cmd.extend(["-i", key_file])

        env = os.environ.copy()
        if use_sshpass:
            env["SSHPASS"] = password
        subprocess.run(ssh_cmd, check=False, env=env)
    finally:
        if tmp_path:
            try:
                if sys.platform == "win32":
                    os.chmod(tmp_path, stat.S_IWRITE)
                os.remove(tmp_path)
            except OSError:
                pass
