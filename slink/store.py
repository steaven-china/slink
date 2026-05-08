"""
Simple store layer on top of the encrypted file.
"""
import os
import sys

from .crypto import DEFAULT_CONFIG_DIR, load_hosts, save_hosts
from .lock import FileLock


_LOCK_FILE = os.path.join(DEFAULT_CONFIG_DIR, ".lock")
SHOW_DIRECT_FILE = os.path.join(DEFAULT_CONFIG_DIR, ".show_direct")


def _resolve_host_name(name: str, hosts: dict) -> str:
    """Resolve a host name or alias to the canonical host name."""
    if name in hosts:
        return name
    for host_name, info in hosts.items():
        aliases = info.get("aliases", [])
        if name in aliases:
            return host_name
    return None


def _check_alias_conflicts(name: str, aliases: list, hosts: dict, exclude_name: str = None):
    """Check if name or aliases conflict with existing hosts or their aliases."""
    new_names = [name] + list(aliases or [])
    for existing_name, existing_info in hosts.items():
        if existing_name == exclude_name:
            continue
        existing_names = [existing_name] + list(existing_info.get("aliases", []))
        for new_name in new_names:
            if new_name in existing_names:
                raise ValueError(
                    f"Name or alias '{new_name}' already used by host '{existing_name}'."
                )


def _update_show_direct(hosts: dict):
    with open(SHOW_DIRECT_FILE, "w", encoding="utf-8") as f:
        f.write("showlist:\n")
        for name in sorted(hosts):
            f.write(f"    {name}\n")
            for alias in sorted(hosts[name].get("aliases", [])):
                f.write(f"    {alias}\n")
    if sys.platform != "win32":
        os.chmod(SHOW_DIRECT_FILE, 0o600)


def get_show_direct_names() -> list:
    if not os.path.exists(SHOW_DIRECT_FILE):
        return []
    with open(SHOW_DIRECT_FILE, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    names = []
    for line in lines[1:]:
        stripped = line.strip()
        if stripped:
            names.append(stripped)
    return names


def list_hosts(password: str = None) -> dict:
    with FileLock(_LOCK_FILE):
        return load_hosts(password)


def get_host(name: str, password: str = None) -> dict:
    with FileLock(_LOCK_FILE):
        hosts = load_hosts(password)
        resolved = _resolve_host_name(name, hosts)
        return hosts.get(resolved) if resolved else None


def add_host(name: str, host_info: dict, password: str = None):
    with FileLock(_LOCK_FILE):
        hosts = load_hosts(password)
        if name in hosts:
            raise ValueError(f"Host '{name}' already exists. Use 'update' or remove it first.")
        _check_alias_conflicts(name, host_info.get("aliases"), hosts)
        hosts[name] = host_info
        save_hosts(hosts, password)
        _update_show_direct(hosts)


def update_host(name: str, host_info: dict, password: str = None):
    with FileLock(_LOCK_FILE):
        hosts = load_hosts(password)
        resolved = _resolve_host_name(name, hosts)
        if resolved is None:
            raise ValueError(f"Host '{name}' does not exist.")
        _check_alias_conflicts(name, host_info.get("aliases"), hosts, exclude_name=resolved)
        hosts[resolved] = host_info
        save_hosts(hosts, password)
        _update_show_direct(hosts)


def remove_host(name: str, password: str = None):
    with FileLock(_LOCK_FILE):
        hosts = load_hosts(password)
        resolved = _resolve_host_name(name, hosts)
        if resolved is None:
            raise ValueError(f"Host '{name}' does not exist.")
        del hosts[resolved]
        save_hosts(hosts, password)
        _update_show_direct(hosts)


def upsert_host(name: str, host_info: dict, password: str = None):
    with FileLock(_LOCK_FILE):
        hosts = load_hosts(password)
        resolved = _resolve_host_name(name, hosts)
        target = resolved if resolved is not None else name
        _check_alias_conflicts(name, host_info.get("aliases"), hosts, exclude_name=target)
        hosts[target] = host_info
        save_hosts(hosts, password)
        _update_show_direct(hosts)


def rotate_password(old_password: str, new_password: str):
    """Decrypt hosts with old password and re-encrypt with new password using a new salt."""
    import stat
    with FileLock(_LOCK_FILE):
        hosts = load_hosts(password=old_password)
        salt_path = os.path.join(DEFAULT_CONFIG_DIR, "salt")
        if os.path.exists(salt_path):
            if sys.platform == "win32":
                os.chmod(salt_path, stat.S_IWRITE)
            os.remove(salt_path)
        save_hosts(hosts, password=new_password)
        _update_show_direct(hosts)
