"""
Simple store layer on top of the encrypted file.
"""
from .crypto import load_hosts, save_hosts


def list_hosts(password: str = None) -> dict:
    return load_hosts(password)


def get_host(name: str, password: str = None) -> dict:
    hosts = load_hosts(password)
    return hosts.get(name)


def add_host(name: str, host_info: dict, password: str = None):
    hosts = load_hosts(password)
    if name in hosts:
        raise ValueError(f"Host '{name}' already exists. Use 'update' or remove it first.")
    hosts[name] = host_info
    save_hosts(hosts, password)


def update_host(name: str, host_info: dict, password: str = None):
    hosts = load_hosts(password)
    if name not in hosts:
        raise ValueError(f"Host '{name}' does not exist.")
    hosts[name] = host_info
    save_hosts(hosts, password)


def remove_host(name: str, password: str = None):
    hosts = load_hosts(password)
    if name not in hosts:
        raise ValueError(f"Host '{name}' does not exist.")
    del hosts[name]
    save_hosts(hosts, password)


def upsert_host(name: str, host_info: dict, password: str = None):
    hosts = load_hosts(password)
    hosts[name] = host_info
    save_hosts(hosts, password)
