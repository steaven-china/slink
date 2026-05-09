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
import threading


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


ACTIVE_PROCS = []
_ACTIVE_LOCK = threading.Lock()


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
    proc = None
    try:
        if key:
            tmp_path = _write_temp_key(key)
            ssh_cmd.extend(["-i", tmp_path])
        elif key_file:
            ssh_cmd.extend(["-i", key_file])

        env = os.environ.copy()
        if use_sshpass:
            env["SSHPASS"] = password
        proc = subprocess.Popen(ssh_cmd, env=env)
        with _ACTIVE_LOCK:
            ACTIVE_PROCS.append(proc)
        proc.wait()
    finally:
        if proc:
            with _ACTIVE_LOCK:
                if proc in ACTIVE_PROCS:
                    ACTIVE_PROCS.remove(proc)
        if tmp_path:
            try:
                if sys.platform == "win32":
                    os.chmod(tmp_path, stat.S_IWRITE)
                os.remove(tmp_path)
            except OSError:
                pass


def _escape_config_val(val: str) -> str:
    """Quote values that contain spaces for ssh_config."""
    if " " in val or '"' in val:
        return '"' + val.replace('"', '\\"') + '"'
    return val


def _build_chain_config(jumps: list[dict], temp_keys: dict) -> str:
    """Build OpenSSH config text for jump hosts."""
    lines = []
    for i, hop in enumerate(jumps):
        lines.append(f"Host slk_jump_{i}")
        lines.append(f"    HostName {hop['hostname']}")
        if hop.get("username"):
            lines.append(f"    User {hop['username']}")
        port = int(hop.get("port", 22))
        if port != 22:
            lines.append(f"    Port {port}")
        key_file = temp_keys.get(f"jump_{i}") or hop.get("key_file")
        if key_file:
            key_file = key_file.replace("\\", "/")
            lines.append(f"    IdentityFile {_escape_config_val(key_file)}")
        lines.append("    StrictHostKeyChecking accept-new")
        lines.append("")
    return "\n".join(lines)


def connect_chain(jumps: list[dict], endpoint: dict):
    """
    Connect through a chain of jumps to an endpoint.

    Generates a temporary SSH config file so each jump can have its own
    IdentityFile.  Jumps with password-based auth are not supported by
    OpenSSH ProxyJump; keys or agent are required for intermediate hops.
    """
    import atexit

    temp_keys = {}
    config_path = None

    def _cleanup():
        for p in list(temp_keys.values()):
            try:
                if sys.platform == "win32":
                    os.chmod(p, stat.S_IWRITE)
                os.remove(p)
            except OSError:
                pass
        nonlocal config_path
        if config_path:
            try:
                if sys.platform == "win32":
                    os.chmod(config_path, stat.S_IWRITE)
                os.remove(config_path)
            except OSError:
                pass

    atexit.register(_cleanup)

    try:
        # Write temp inline keys
        for i, hop in enumerate(jumps):
            if hop.get("key"):
                temp_keys[f"jump_{i}"] = _write_temp_key(hop["key"])
        if endpoint.get("key"):
            temp_keys["endpoint"] = _write_temp_key(endpoint["key"])

        config_text = _build_chain_config(jumps, temp_keys)
        fd, config_path = tempfile.mkstemp(prefix="slink_cfg_", suffix=".conf")
        try:
            os.write(fd, config_text.encode("utf-8"))
            os.close(fd)
        except Exception:
            try:
                os.close(fd)
            except OSError:
                pass
            raise

        # Build ssh command
        password = endpoint.get("password")
        use_sshpass = False
        if password and shutil.which("sshpass"):
            use_sshpass = True
        elif password:
            print("Warning: 'sshpass' not found. Install it to use password-based login.", file=sys.stderr)

        ssh_cmd = []
        if use_sshpass:
            ssh_cmd = ["sshpass", "-e", "ssh"]
        else:
            ssh_cmd = ["ssh"]

        ssh_cmd.extend(["-F", config_path])

        jump_specs = [f"slk_jump_{i}" for i in range(len(jumps))]
        ssh_cmd.extend(["-J", ",".join(jump_specs)])

        if temp_keys.get("endpoint"):
            ssh_cmd.extend(["-i", temp_keys["endpoint"]])
        elif endpoint.get("key_file"):
            ssh_cmd.extend(["-i", endpoint["key_file"]])

        ssh_cmd.extend(["-o", "StrictHostKeyChecking=accept-new"])

        extra_args = endpoint.get("extra_args", [])
        if isinstance(extra_args, str):
            extra_args = extra_args.split()
        if extra_args:
            ssh_cmd.extend(extra_args)

        target = endpoint.get("hostname", "")
        if endpoint.get("username"):
            target = f"{endpoint['username']}@{target}"

        print(f"Connecting via {len(jumps)} jump(s) to {target} ...")

        env = os.environ.copy()
        if use_sshpass:
            env["SSHPASS"] = password

        proc = subprocess.Popen(ssh_cmd, env=env)
        with _ACTIVE_LOCK:
            ACTIVE_PROCS.append(proc)
        proc.wait()
    finally:
        if "proc" in locals() and proc:
            with _ACTIVE_LOCK:
                if proc in ACTIVE_PROCS:
                    ACTIVE_PROCS.remove(proc)
        _cleanup()
        atexit.unregister(_cleanup)


def terminate_all():
    """Terminate all active SSH processes."""
    with _ACTIVE_LOCK:
        procs = list(ACTIVE_PROCS)
        ACTIVE_PROCS.clear()
    for proc in procs:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
