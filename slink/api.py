"""
Public API surface for slink.

This module holds core logic that was previously scattered in cli.py.
CLI and GUI are thin consumers of these functions.
"""
import json
import os
import sys
from getpass import getpass

import click

from .crypto import DecryptError, decrypt_file_to_text
from .parser import parse_config
from .store import get_host


def unpack_chain(data: dict) -> dict:
    """Unpack a chain payload into a _chain dict for connect_chain()."""
    topology = data.get("topology", data)
    secrets = data.get("secrets", {"jumps": [], "endpoint": {}})

    # Support both 'endpoint' (new) and 'target' (legacy/compat)
    endpoint = dict(topology.get("endpoint", topology.get("target", {})))
    endpoint_secret = secrets.get("endpoint", secrets.get("target", {}))
    if endpoint_secret.get("password"):
        endpoint["password"] = endpoint_secret["password"]
    if endpoint_secret.get("key_file"):
        endpoint["key_file"] = os.path.expanduser(endpoint_secret["key_file"])
    if endpoint_secret.get("key"):
        endpoint["key"] = endpoint_secret["key"]

    jumps = []
    for i, hop in enumerate(topology.get("jumps", [])):
        hop = dict(hop)
        secret = secrets.get("jumps", [])[i] if i < len(secrets.get("jumps", [])) else {}
        if secret.get("password"):
            hop["password"] = secret["password"]
        if secret.get("key_file"):
            hop["key_file"] = os.path.expanduser(secret["key_file"])
        if secret.get("key"):
            hop["key"] = secret["key"]
        jumps.append(hop)

    return {"_chain": {"jumps": jumps, "endpoint": endpoint}}


def load_file(file_path: str) -> dict:
    """Load a host file, chain file, or encrypted .enc."""
    lower = file_path.lower()
    is_chain = lower.endswith(".chain") or lower.endswith(".chain.enc")

    if lower.endswith(".enc"):
        password = os.environ.get("SLINK_PASSWORD")
        if password is None:
            password = getpass("Master password: ")
        try:
            plain_text = decrypt_file_to_text(file_path, password)
        except DecryptError:
            click.echo("Invalid master password or corrupted file.", err=True)
            sys.exit(1)
        if is_chain:
            return unpack_chain(json.loads(plain_text))
        return parse_config(plain_text)

    if lower.endswith(".json") or lower.endswith(".chain"):
        with open(file_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        if is_chain:
            return unpack_chain({"topology": data, "secrets": {"jumps": [], "target": {}}})
        return data

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    info = parse_config(text)
    if info.get("hostname"):
        return info

    # Try JSON as fallback for files without recognized extension
    try:
        data = json.loads(text)
        if isinstance(data, dict) and ("jumps" in data or "topology" in data):
            return unpack_chain({"topology": data, "secrets": {"jumps": [], "target": {}}})
        return data
    except json.JSONDecodeError:
        pass

    password = os.environ.get("SLINK_PASSWORD")
    if password is None:
        password = getpass("Master password (trying encrypted): ")
    try:
        plain_text = decrypt_file_to_text(file_path, password)
        try:
            data = json.loads(plain_text)
            if isinstance(data, dict) and ("topology" in data or "jumps" in data):
                return unpack_chain(data)
            return data
        except json.JSONDecodeError:
            return parse_config(plain_text)
    except DecryptError:
        click.echo("Could not parse file as plain text, JSON, or decrypt it.", err=True)
        sys.exit(1)


def collect_chain_secrets(chain_data: dict) -> dict:
    """Interactively collect passwords/keys for each node in a chain."""
    secrets = {"jumps": [], "endpoint": {}}

    for i, hop in enumerate(chain_data.get("jumps", [])):
        click.echo(f"\n--- Jump {i + 1}: {hop.get('hostname')} ---")
        secret = {}
        if click.confirm("Add password?", default=False):
            secret["password"] = getpass("Password: ")
        if click.confirm("Add key file?", default=False):
            secret["key_file"] = click.prompt("Key file path")
        if click.confirm("Paste inline key?", default=False):
            secret["key"] = click.prompt("Key content", hide_input=False)
        secrets["jumps"].append(secret)

    endpoint = chain_data.get("endpoint", chain_data.get("target", {}))
    click.echo(f"\n--- Endpoint: {endpoint.get('hostname')} ---")
    secret = {}
    if click.confirm("Add password?", default=False):
        secret["password"] = getpass("Password: ")
    if click.confirm("Add key file?", default=False):
        secret["key_file"] = click.prompt("Key file path")
    if click.confirm("Paste inline key?", default=False):
        secret["key"] = click.prompt("Key content", hide_input=False)
    secrets["endpoint"] = secret
    return secrets


def resolve_jump_chain(info: dict, password: str):
    """Resolve jump host aliases into ssh -J compatible specs."""
    jump_hosts = info.get("jump_host")
    if not jump_hosts:
        return
    if isinstance(jump_hosts, str):
        jump_hosts = [jump_hosts]
    resolved = []
    for jh in jump_hosts:
        jh = jh.strip()
        if not jh:
            continue
        jump_info = get_host(jh, password=password)
        if jump_info:
            jh_host = jump_info.get("hostname", jh)
            jh_port = jump_info.get("port", 22)
            jh_user = jump_info.get("username")
            spec = jh_host
            if jh_user:
                spec = f"{jh_user}@{spec}"
            if jh_port != 22:
                spec = f"{spec}:{jh_port}"
            resolved.append(spec)
        else:
            resolved.append(jh)
    info["jump_host"] = resolved


def parse_jump_spec(spec: str) -> dict:
    """Parse an ssh jump spec like user@host:port into a dict."""
    username = None
    port = 22
    if "@" in spec:
        username, spec = spec.split("@", 1)
    if ":" in spec:
        spec, port_str = spec.rsplit(":", 1)
        try:
            port = int(port_str)
        except ValueError:
            pass
    return {"hostname": spec, "username": username, "port": port}
