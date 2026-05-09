# Command Reference

## Core Commands

### `sli init`
Set or change the master password. Creates `~/.slink/` if it does not exist.

### `sli add <name> [OPTIONS]`
Add a new SSH host.

| Option | Description |
|--------|-------------|
| `-h, --host` | IP or hostname (required) |
| `-p, --port` | SSH port (default: 22) |
| `-u, --user` | SSH username (required) |
| `-a, --alias` | Alias name (repeatable) |
| `--jump-host` | Jump host name (repeatable) |
| `-i, --identity` | Private key path |
| `-d, --description` | Free-text note |

### `sli connect <name>`
SSH into the host. Aliases, jump hosts, and key files are resolved automatically.

### `sli list [--json]`
List all stored hosts. `--json` outputs machine-readable format.

### `sli show <name> [--json]`
Show detailed host information (password is never displayed).

### `sli edit <name> [OPTIONS]`
Modify an existing host. Same options as `add`.

### `sli rm <name>`
Remove a host and its aliases.

## Import / Export

### `sli import [--file PATH]`
Import hosts from `~/.ssh/config` or a custom file.

### `sli export [--with-secrets] [--json]`
Export config. `--with-secrets` includes passwords (plaintext). `--json` for JSON output.

### `sli import-json <file>`
Import hosts from a JSON file previously exported.

## Utility

### `sli passwd`
Rotate the master password. Regenerates salt and re-encrypts all data.

### `sli jump-list <jump-host>`
SSH into a jump host and read its `.show_direct` to discover downstream targets.

### `sli names`
List host names without requiring a password (reads `.show_direct`).

### `sli gui`
Launch the tkinter GUI (same as `sli-ui`).

### `sli ml <targets...>`
Multi-login PTY-based session engine. Supports broadcast/focus modes, groups (`@group`), and workspaces.

### `sli agent-pass --ttl <seconds>`
Generate a temporary read-only password for agent access.
