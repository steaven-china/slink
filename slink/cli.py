"""
Command-line interface for slink.
"""
import os
import sys
from getpass import getpass

import click

from . import __version__
from .crypto import DecryptError, decrypt_file_to_text, encrypt_file, save_hosts
from .parser import parse_config
from .ssh_config_parser import parse_ssh_config
from .ssh_wrapper import connect as ssh_connect
from .store import add_host, get_host, list_hosts, remove_host, upsert_host


def _try_load_file(file_path: str) -> dict:
    """Try to load a host file (plain text or encrypted .enc)."""
    if file_path.lower().endswith(".enc"):
        password = os.environ.get("SLINK_PASSWORD")
        if password is None:
            password = getpass("Master password: ")
        try:
            plain_text = decrypt_file_to_text(file_path, password)
        except DecryptError:
            click.echo("Invalid master password or corrupted file.", err=True)
            sys.exit(1)
        return parse_config(plain_text)

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    info = parse_config(text)
    if info.get("hostname"):
        return info

    password = os.environ.get("SLINK_PASSWORD")
    if password is None:
        password = getpass("Master password (trying encrypted): ")
    try:
        plain_text = decrypt_file_to_text(file_path, password)
        return parse_config(plain_text)
    except DecryptError:
        click.echo("Could not parse file as plain text or decrypt it.", err=True)
        sys.exit(1)


@click.group()
@click.version_option(version=__version__, prog_name="slink")
def cli():
    """slink - Secure SSH Connection Manager"""
    pass


@cli.command()
def init():
    """Initialize slink by setting a master password."""
    click.echo("Welcome to slink! Let's set up your master password.")
    pw1 = getpass("Enter master password: ")
    pw2 = getpass("Confirm master password: ")
    if pw1 != pw2:
        click.echo("Passwords do not match.", err=True)
        sys.exit(1)
    if not pw1:
        click.echo("Password cannot be empty.", err=True)
        sys.exit(1)
    # Create an empty encrypted store to validate the password works
    save_hosts({}, password=pw1)
    click.echo("slink initialized successfully.")


@cli.command(name="add")
@click.argument("name")
@click.option("--hostname", "-h", prompt="Hostname/IP", help="Remote host address")
@click.option("--port", "-p", default=22, show_default=True, help="SSH port")
@click.option("--username", "-u", prompt="Username", help="SSH username")
@click.option("--ask-password", is_flag=True, help="Prompt for SSH password interactively")
@click.option("--key-file", "-i", default=None, help="Path to SSH private key file")
@click.option("--key-text", default=None, help="Paste private key text directly")
@click.option("--extra-args", "-X", multiple=True, help="Extra SSH arguments (repeatable)")
@click.option("--master-password", envvar="SLINK_PASSWORD", default=None, help="Master password")
def add_cmd(name, hostname, port, username, ask_password, key_file, key_text, extra_args, master_password):
    """Add a new host configuration."""
    if master_password is None:
        master_password = getpass("Master password: ")

    info = {
        "hostname": hostname,
        "port": port,
        "username": username,
    }
    if ask_password:
        ssh_password = getpass("SSH password: ")
        if ssh_password:
            info["password"] = ssh_password
    if key_text:
        info["key"] = key_text
    elif key_file:
        info["key_file"] = key_file
    if extra_args:
        info["extra_args"] = list(extra_args)

    try:
        add_host(name, info, password=master_password)
        click.echo(f"Host '{name}' added.")
    except ValueError as e:
        click.echo(str(e), err=True)
        if click.confirm("Overwrite existing entry?"):
            upsert_host(name, info, password=master_password)
            click.echo(f"Host '{name}' updated.")


@cli.command(name="list")
@click.option("--master-password", envvar="SLINK_PASSWORD", default=None, help="Master password")
def list_cmd(master_password):
    """List all stored hosts."""
    if master_password is None:
        master_password = getpass("Master password: ")
    hosts = list_hosts(password=master_password)
    if not hosts:
        click.echo("No hosts stored yet.")
        return
    click.echo(f"{'Name':<20} {'Hostname':<25} {'Port':<6} {'User':<15}")
    click.echo("-" * 70)
    for name, info in hosts.items():
        click.echo(
            f"{name:<20} {info.get('hostname',''):<25} {info.get('port',22):<6} {info.get('username',''):<15}"
        )


@cli.command(name="show")
@click.argument("name")
@click.option("--master-password", envvar="SLINK_PASSWORD", default=None, help="Master password")
def show_cmd(name, master_password):
    """Show details for a single host (passwords hidden)."""
    if master_password is None:
        master_password = getpass("Master password: ")
    info = get_host(name, password=master_password)
    if not info:
        click.echo(f"Host '{name}' not found.", err=True)
        sys.exit(1)
    click.echo(f"Name:     {name}")
    click.echo(f"Hostname: {info.get('hostname')}")
    click.echo(f"Port:     {info.get('port', 22)}")
    click.echo(f"Username: {info.get('username')}")
    click.echo(f"Key file: {info.get('key_file') or ('<inline key>' if info.get('key') else 'None')}")
    click.echo(f"Password: {'<set>' if info.get('password') else 'None'}")
    extra = info.get('extra_args')
    click.echo(f"Extra args: {' '.join(extra) if extra else 'None'}")


@cli.command(name="rm")
@click.argument("name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@click.option("--master-password", envvar="SLINK_PASSWORD", default=None, help="Master password")
def rm_cmd(name, yes, master_password):
    """Remove a stored host."""
    if master_password is None:
        master_password = getpass("Master password: ")
    if not yes and not click.confirm(f"Remove host '{name}'?"):
        return
    try:
        remove_host(name, password=master_password)
        click.echo(f"Host '{name}' removed.")
    except ValueError as e:
        click.echo(str(e), err=True)
        sys.exit(1)


@cli.command(name="import")
@click.option("--config", "-c", default=None, type=click.Path(exists=True), help="Path to SSH config file (default: ~/.ssh/config)")
@click.option("--host", "-h", default=None, help="Import a specific host only")
@click.option("--master-password", envvar="SLINK_PASSWORD", default=None, help="Master password")
def import_cmd(config, host, master_password):
    """Import hosts from ~/.ssh/config into slink encrypted store."""
    if master_password is None:
        master_password = getpass("Master password: ")
    hosts = parse_ssh_config(config)
    if not hosts:
        click.echo("No hosts found in SSH config.", err=True)
        sys.exit(1)

    if host:
        if host not in hosts:
            click.echo(f"Host '{host}' not found in SSH config.", err=True)
            sys.exit(1)
        hosts = {host: hosts[host]}

    imported = 0
    skipped = 0
    for name, info in hosts.items():
        try:
            add_host(name, info, password=master_password)
            imported += 1
            click.echo(f"  Imported: {name}")
        except ValueError:
            if click.confirm(f"  Host '{name}' already exists. Overwrite?"):
                upsert_host(name, info, password=master_password)
                imported += 1
                click.echo(f"  Overwritten: {name}")
            else:
                skipped += 1

    click.echo(f"\nDone: {imported} imported, {skipped} skipped.")


@cli.command(name="connect")
@click.argument("name")
@click.option("--extra-args", "-X", multiple=True, help="Extra SSH arguments (repeatable)")
@click.option("--master-password", envvar="SLINK_PASSWORD", default=None, help="Master password")
def connect_cmd(name, extra_args, master_password):
    """Connect to a stored host via SSH."""
    if master_password is None:
        master_password = getpass("Master password: ")
    info = get_host(name, password=master_password)
    if not info:
        click.echo(f"Host '{name}' not found.", err=True)
        sys.exit(1)
    if extra_args:
        stored = info.get("extra_args", [])
        info["extra_args"] = stored + list(extra_args)
    ssh_connect(info)


@cli.command(name="edit")
@click.argument("name")
@click.option("--hostname", "-h", default=None, help="Remote host address")
@click.option("--port", "-p", default=None, type=int, help="SSH port")
@click.option("--username", "-u", default=None, help="SSH username")
@click.option("--ask-password", is_flag=True, help="Prompt for SSH password interactively")
@click.option("--key-file", "-i", default=None, help="Path to SSH private key file")
@click.option("--extra-args", "-X", multiple=True, help="Extra SSH arguments (repeatable)")
@click.option("--master-password", envvar="SLINK_PASSWORD", default=None, help="Master password")
def edit_cmd(name, hostname, port, username, ask_password, key_file, extra_args, master_password):
    """Edit an existing host (only provided fields are updated)."""
    if master_password is None:
        master_password = getpass("Master password: ")
    info = get_host(name, password=master_password)
    if not info:
        click.echo(f"Host '{name}' not found.", err=True)
        sys.exit(1)
    if hostname is not None:
        info["hostname"] = hostname
    if port is not None:
        info["port"] = port
    if username is not None:
        info["username"] = username
    if ask_password:
        ssh_password = getpass("SSH password: ")
        info["password"] = ssh_password
    if key_file is not None:
        info["key_file"] = key_file
        info.pop("key", None)
    if extra_args:
        info["extra_args"] = list(extra_args)
    upsert_host(name, info, password=master_password)
    click.echo(f"Host '{name}' updated.")


@cli.command(name="encrypt")
@click.argument("file", type=click.Path(exists=True))
@click.option("--output", "-o", default=None, help="Output encrypted file path")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing file without prompting")
@click.option("--master-password", envvar="SLINK_PASSWORD", default=None, help="Master password")
def encrypt_cmd(file, output, force, master_password):
    """Encrypt a plain-text host file."""
    if master_password is None:
        master_password = getpass("Master password: ")
    if output is None:
        output = file + ".enc"
    if os.path.exists(output) and not force:
        if not click.confirm(f"File '{output}' already exists. Overwrite?"):
            return
    encrypt_file(file, output, master_password)
    click.echo(f"Encrypted: {file} -> {output}")


@cli.command(name="decrypt")
@click.argument("file", type=click.Path(exists=True))
@click.option("--output", "-o", default=None, help="Output plain text file path")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing file without prompting")
@click.option("--master-password", envvar="SLINK_PASSWORD", default=None, help="Master password")
def decrypt_cmd(file, output, force, master_password):
    """Decrypt an encrypted host file to plain text."""
    if master_password is None:
        master_password = getpass("Master password: ")
    if output is None:
        if file.lower().endswith(".enc"):
            output = file[:-4]
        else:
            output = file + ".txt"
    if os.path.exists(output) and not force:
        if not click.confirm(f"File '{output}' already exists. Overwrite?"):
            return
    from .crypto import decrypt_file
    decrypt_file(file, output, master_password)
    click.echo(f"Decrypted: {file} -> {output}")


def _resolve_argv_file(argv):
    """Detect if the first non-option arg is a file path for quick connect."""
    commands = set(cli.commands.keys())
    for arg in argv[1:]:
        if arg.startswith("-"):
            continue
        if arg in commands:
            return None
        if os.path.isfile(arg):
            return arg
        break
    return None


def main():
    # Quick-connect: slink host.txt / slink host.enc
    file_path = _resolve_argv_file(sys.argv)
    if file_path and file_path not in ("encrypt", "decrypt", "add", "list",
                                        "show", "rm", "connect", "edit", "init"):
        info = _try_load_file(file_path)
        if info.get("hostname"):
            if info.get("key_file"):
                info["key_file"] = os.path.expanduser(info["key_file"])
            ssh_connect(info)
            return
    cli()


if __name__ == "__main__":
    main()
