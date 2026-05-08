"""
Command-line interface for slink.
"""
import json
import os
import subprocess
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
    """Try to load a host file (plain text, JSON, or encrypted .enc)."""
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

    if file_path.lower().endswith(".json"):
        with open(file_path, "r", encoding="utf-8-sig") as f:
            return json.load(f)

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    info = parse_config(text)
    if info.get("hostname"):
        return info

    # Try JSON as fallback for files without recognized extension
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    password = os.environ.get("SLINK_PASSWORD")
    if password is None:
        password = getpass("Master password (trying encrypted): ")
    try:
        plain_text = decrypt_file_to_text(file_path, password)
        return parse_config(plain_text)
    except DecryptError:
        click.echo("Could not parse file as plain text, JSON, or decrypt it.", err=True)
        sys.exit(1)


@click.group()
@click.version_option(version=__version__, prog_name="sli")
def cli():
    """slink - Secure SSH Connection Manager"""
    pass


def _complete_host_names(ctx, param, incomplete):
    """Shell completion for host names (reads .show_direct first, no password needed)."""
    from .store import get_show_direct_names
    try:
        names = get_show_direct_names()
        if names:
            return [k for k in names if k.startswith(incomplete)]
    except Exception:
        pass
    # fallback to encrypted store
    password = os.environ.get("SLINK_PASSWORD")
    if not password:
        return []
    try:
        from .crypto import load_hosts
        hosts = load_hosts(password=password)
        return [k for k in hosts if k.startswith(incomplete)]
    except Exception:
        return []


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
    try:
        save_hosts({}, password=pw1)
    except OSError as exc:
        click.echo(f"Failed to initialize slink: {exc}", err=True)
        sys.exit(1)
    click.echo("slink initialized successfully.")


@cli.command(name="passwd")
@click.option("--old-password", envvar="SLINK_PASSWORD", default=None, help="Current master password")
def passwd_cmd(old_password):
    """Change the master password."""
    if old_password is None:
        old_password = getpass("Current master password: ")
    new_pw1 = getpass("New master password: ")
    new_pw2 = getpass("Confirm new master password: ")
    if new_pw1 != new_pw2:
        click.echo("Passwords do not match.", err=True)
        sys.exit(1)
    if not new_pw1:
        click.echo("Password cannot be empty.", err=True)
        sys.exit(1)
    try:
        from .store import rotate_password
        rotate_password(old_password, new_pw1)
        click.echo("Master password changed successfully.")
    except DecryptError:
        click.echo("Invalid current master password.", err=True)
        sys.exit(1)


@cli.command(name="add")
@click.argument("name")
@click.option("--hostname", "-h", prompt="Hostname/IP", help="Remote host address")
@click.option("--port", "-p", default=22, show_default=True, help="SSH port")
@click.option("--username", "-u", prompt="Username", help="SSH username")
@click.option("--ask-password", is_flag=True, help="Prompt for SSH password interactively")
@click.option("--key-file", "-i", default=None, help="Path to SSH private key file")
@click.option("--key-text", default=None, help="Paste private key text directly")
@click.option("--alias", "-a", multiple=True, help="Alias names for this host (repeatable)")
@click.option("--jump-host", "-J", multiple=True, help="Jump host alias or spec (repeatable for chaining)")
@click.option("--extra-args", "-X", multiple=True, help="Extra SSH arguments (repeatable)")
@click.option("--master-password", envvar="SLINK_PASSWORD", default=None, help="Master password")
def add_cmd(name, hostname, port, username, ask_password, key_file, key_text, alias, jump_host, extra_args, master_password):
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
    if alias:
        info["aliases"] = list(alias)
    if jump_host:
        info["jump_host"] = list(jump_host)
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


@cli.command(name="names")
def names_cmd():
    """List all stored host names (no password required)."""
    from .store import get_show_direct_names
    names = get_show_direct_names()
    if not names:
        click.echo("No hosts stored yet.")
        return
    for name in names:
        click.echo(name)


@cli.command(name="list")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON")
@click.option("--master-password", envvar="SLINK_PASSWORD", default=None, help="Master password")
def list_cmd(use_json, master_password):
    """List all stored hosts."""
    if master_password is None:
        master_password = getpass("Master password: ")
    hosts = list_hosts(password=master_password)
    if not hosts:
        if use_json:
            click.echo("{}")
        else:
            click.echo("No hosts stored yet.")
        return
    if use_json:
        click.echo(json.dumps(hosts, ensure_ascii=False, indent=2))
        return
    click.echo(f"{'Name':<20} {'Hostname':<25} {'Port':<6} {'User':<15}")
    click.echo("-" * 70)
    for name, info in hosts.items():
        click.echo(
            f"{name:<20} {info.get('hostname',''):<25} {info.get('port',22):<6} {info.get('username',''):<15}"
        )


@cli.command(name="show")
@click.argument("name", shell_complete=_complete_host_names)
@click.option("--json", "use_json", is_flag=True, help="Output as JSON")
@click.option("--master-password", envvar="SLINK_PASSWORD", default=None, help="Master password")
def show_cmd(name, use_json, master_password):
    """Show details for a single host (passwords hidden)."""
    if master_password is None:
        master_password = getpass("Master password: ")
    info = get_host(name, password=master_password)
    if not info:
        click.echo(f"Host '{name}' not found.", err=True)
        sys.exit(1)
    if use_json:
        click.echo(json.dumps({name: info}, ensure_ascii=False, indent=2))
        return
    click.echo(f"Name:     {name}")
    click.echo(f"Hostname: {info.get('hostname')}")
    click.echo(f"Port:     {info.get('port', 22)}")
    click.echo(f"Username: {info.get('username')}")
    aliases = info.get('aliases', [])
    aliases = info.get('aliases', [])
    click.echo(f"Aliases:  {', '.join(aliases) if aliases else 'None'}")
    jump_hosts = info.get('jump_host', [])
    if isinstance(jump_hosts, str):
        jump_hosts = [jump_hosts]
    click.echo(f"Jump host: {', '.join(jump_hosts) if jump_hosts else 'None'}")
    click.echo(f"Key file: {info.get('key_file') or ('<inline key>' if info.get('key') else 'None')}")
    click.echo(f"Password: {'<set>' if info.get('password') else 'None'}")
    extra = info.get('extra_args')
    click.echo(f"Extra args: {' '.join(extra) if extra else 'None'}")


@cli.command(name="rm")
@click.argument("name", shell_complete=_complete_host_names)
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
    try:
        hosts = parse_ssh_config(config)
    except PermissionError as exc:
        click.echo(f"Permission denied reading SSH config: {exc}", err=True)
        sys.exit(1)
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


def _resolve_jump_chain(info: dict, password: str):
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


@cli.command(name="connect")
@click.argument("name", shell_complete=_complete_host_names)
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
    _resolve_jump_chain(info, master_password)
    if extra_args:
        stored = info.get("extra_args", [])
        info["extra_args"] = stored + list(extra_args)
    try:
        ssh_connect(info)
    except ValueError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)


@cli.command(name="edit")
@click.argument("name", shell_complete=_complete_host_names)
@click.option("--hostname", "-h", default=None, help="Remote host address")
@click.option("--port", "-p", default=None, type=int, help="SSH port")
@click.option("--username", "-u", default=None, help="SSH username")
@click.option("--ask-password", is_flag=True, help="Prompt for SSH password interactively")
@click.option("--key-file", "-i", default=None, help="Path to SSH private key file")
@click.option("--key-text", default=None, help="Paste private key text directly")
@click.option("--alias", "-a", multiple=True, help="Set alias names (repeatable, replaces existing)")
@click.option("--jump-host", "-J", multiple=True, help="Set jump hosts (repeatable, replaces existing)")
@click.option("--extra-args", "-X", multiple=True, help="Extra SSH arguments (repeatable)")
@click.option("--master-password", envvar="SLINK_PASSWORD", default=None, help="Master password")
def edit_cmd(name, hostname, port, username, ask_password, key_file, key_text, alias, jump_host, extra_args, master_password):
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
    if key_text:
        info["key"] = key_text
        info.pop("key_file", None)
    elif key_file is not None:
        info["key_file"] = key_file
        info.pop("key", None)
    if alias:
        info["aliases"] = list(alias)
    if jump_host:
        info["jump_host"] = list(jump_host)
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


@cli.command(name="export")
@click.option("--output", "-o", required=True, type=click.Path(), help="Output JSON file path")
@click.option("--with-secrets", is_flag=True, help="Include passwords and keys in export")
@click.option("--master-password", envvar="SLINK_PASSWORD", default=None, help="Master password")
def export_cmd(output, with_secrets, master_password):
    """Export all hosts to a JSON file."""
    if master_password is None:
        master_password = getpass("Master password: ")
    hosts = list_hosts(password=master_password)
    if not hosts:
        click.echo("No hosts to export.", err=True)
        sys.exit(1)
    data = {}
    for name, info in hosts.items():
        data[name] = dict(info)
        if not with_secrets:
            data[name].pop("password", None)
            data[name].pop("key", None)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    click.echo(f"Exported {len(data)} host(s) to {output}")


@cli.command(name="import-json")
@click.argument("file", type=click.Path(exists=True))
@click.option("--master-password", envvar="SLINK_PASSWORD", default=None, help="Master password")
def import_json_cmd(file, master_password):
    """Import hosts from a JSON file into slink encrypted store."""
    if master_password is None:
        master_password = getpass("Master password: ")
    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        data = {item.get("name", f"host_{i}"): item for i, item in enumerate(data)}
    if not isinstance(data, dict):
        click.echo("Invalid JSON format: expected a dict or list.", err=True)
        sys.exit(1)
    imported = 0
    skipped = 0
    for name, info in data.items():
        if not isinstance(info, dict):
            continue
        try:
            add_host(str(name), info, password=master_password)
            imported += 1
            click.echo(f"  Imported: {name}")
        except ValueError:
            if click.confirm(f"  Host '{name}' already exists. Overwrite?"):
                upsert_host(str(name), info, password=master_password)
                imported += 1
                click.echo(f"  Overwritten: {name}")
            else:
                skipped += 1
    click.echo(f"\nDone: {imported} imported, {skipped} skipped.")


@cli.command(name="agent-pass")
@click.option("--ttl", "-t", default=300, help="Time-to-live in seconds (default: 300)")
@click.option("--master-password", envvar="SLINK_PASSWORD", default=None, help="Master password")
def agent_pass_cmd(ttl, master_password):
    """Generate a temporary agent password for read-only access."""
    import secrets
    if master_password is None:
        master_password = getpass("Master password: ")
    try:
        hosts = load_hosts(master_password)
    except DecryptError:
        click.echo("Invalid master password.", err=True)
        sys.exit(1)
    temp_password = secrets.token_urlsafe(16)[:16]
    from .crypto import save_agent_hosts
    save_agent_hosts(hosts, temp_password, ttl=ttl)
    click.echo(f"Agent password: {temp_password}")
    click.echo(f"Expires in: {ttl} seconds")
    click.echo(f"Usage: SLINK_PASSWORD={temp_password} sli list")


@cli.command(name="jump-list")
@click.argument("jump_host", shell_complete=_complete_host_names)
@click.option("--master-password", envvar="SLINK_PASSWORD", default=None, help="Master password")
def jump_list_cmd(jump_host, master_password):
    """SSH into a jump host and list its downstream targets."""
    if master_password is None:
        master_password = getpass("Master password: ")
    info = get_host(jump_host, password=master_password)
    if not info:
        click.echo(f"Host '{jump_host}' not found.", err=True)
        sys.exit(1)

    ssh_cmd = ["ssh", "-o", "StrictHostKeyChecking=accept-new"]
    user = info.get("username")
    host = info.get("hostname", jump_host)
    port = info.get("port", 22)
    target = f"{user}@{host}" if user else host
    if port != 22:
        ssh_cmd.extend(["-p", str(port)])

    ssh_cmd.extend([target, "cat", "~/.slink/.show_direct"])
    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            click.echo(f"SSH failed: {result.stderr.strip()}", err=True)
            sys.exit(1)
        click.echo(result.stdout)
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


def _complete_ml_targets(ctx, param, incomplete):
    """Complete host names and @group references for sli ml."""
    names = _get_show_direct_names()
    try:
        from .group import load_groups
        groups = load_groups()
        group_names = [f"@{name}" for name in groups.keys()]
    except Exception:
        group_names = []
    all_names = names + group_names
    return [n for n in all_names if n.startswith(incomplete)]


@cli.command(name="ml")
@click.argument("targets", nargs=-1, required=False, shell_complete=_complete_ml_targets)
@click.option("--workspace", "-w", help="Load workspace by name")
@click.option("--list-groups", is_flag=True, help="List all defined groups")
@click.option("--list-workspaces", is_flag=True, help="List all saved workspaces")
@click.option("--user", "-u", help="Override username")
@click.option("--port", "-p", type=int, help="Override port")
@click.option("--dry-run", is_flag=True, help="Show what would be connected")
@click.option("--master-password", envvar="SLINK_PASSWORD", default=None, help="Master password")
def ml_cmd(targets, workspace, list_groups, list_workspaces, user, port, dry_run, master_password):
    """Multi-login: connect to multiple hosts in a unified interactive session."""
    if list_groups:
        from .group import load_groups
        groups = load_groups()
        if not groups:
            click.echo("No groups defined.")
            return
        for name, info in sorted(groups.items()):
            hosts = ", ".join(info.get("hosts", []))
            subgroups = ", ".join(info.get("groups", []))
            click.echo(f"{name}: hosts=[{hosts}] groups=[{subgroups}]")
        return

    if list_workspaces:
        from .workspace import list_workspaces
        names = list_workspaces()
        if not names:
            click.echo("No workspaces saved.")
            return
        for n in names:
            click.echo(f"  {n}")
        return

    if master_password is None:
        master_password = getpass("Master password: ")

    hosts_to_connect = []
    ws = None

    # Auto-load workspace from current directory
    if not targets and not workspace:
        from .workspace import find_workspace_file
        ws_file = find_workspace_file()
        if ws_file:
            with open(ws_file, "r", encoding="utf-8") as f:
                ws = json.load(f)
            hosts_to_connect = ws.get("hosts", [])
            click.echo(f"[Auto-loaded workspace: {ws.get('name', 'unknown')}]")
        else:
            click.echo("No targets specified and no .sli-workspace.json found.", err=True)
            sys.exit(1)

    if workspace:
        from .workspace import load_workspace
        ws = load_workspace(workspace)
        hosts_to_connect = ws.get("hosts", [])

    if targets:
        from .group import expand_targets, load_groups
        all_hosts = list_hosts(password=master_password)
        groups = load_groups()
        hosts_to_connect = expand_targets(list(targets), groups, all_hosts)

    if not hosts_to_connect:
        click.echo("No hosts to connect.", err=True)
        sys.exit(1)

    from .store import get_host
    from .ml_engine import Session, MLEngine

    sessions = []
    for name in hosts_to_connect:
        info = get_host(name, password=master_password)
        if not info:
            click.echo(f"Host '{name}' not found.", err=True)
            continue
        if user:
            info = dict(info)
            info["username"] = user
        if port:
            info = dict(info)
            info["port"] = port

        if dry_run:
            click.echo(f"[dry-run] {name}: {info.get('username')}@{info.get('hostname')}:{info.get('port', 22)}")
            continue

        s = Session(name, info)
        try:
            s.connect()
            sessions.append(s)
            click.echo(f"[Connected to {name}]")
        except Exception as exc:
            click.echo(f"[Failed {name}]: {exc}", err=True)

    if dry_run or not sessions:
        return

    engine = MLEngine(sessions)

    # Restore workspace state
    if ws:
        for name in ws.get("blocked", []):
            engine.cmd_block([name])
        if ws.get("mode") == "focus" and ws.get("focused"):
            engine.cmd_focus([ws["focused"]])

    try:
        engine.run()
    except KeyboardInterrupt:
        click.echo("\n[Interrupted]")
    finally:
        engine._cleanup()


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
                                        "show", "rm", "connect", "edit", "init",
                                        "names", "export", "import-json", "import",
                                        "jump-list", "agent-pass", "ml"):
        info = _try_load_file(file_path)
        if info.get("hostname"):
            if info.get("key_file"):
                info["key_file"] = os.path.expanduser(info["key_file"])
            ssh_connect(info)
            return
    cli()


if __name__ == "__main__":
    main()
