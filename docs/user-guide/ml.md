# Multi-Login Engine (`sli ml`)

`sli ml` opens PTY-based SSH sessions to multiple hosts simultaneously, with a unified input prompt.

## Basic Usage

```bash
sli ml web1 web2 db1
```

## Group Expansion

Use `@group` to expand predefined groups:

```bash
sli ml @production
```

Define groups in `~/.slink/groups.yml`:

```yaml
production:
  hosts: [web1, web2, db1]
  groups: [staging]
```

## Internal Commands

While in `sli ml`, commands prefixed with `>` are intercepted:

| Command | Action |
|---------|--------|
| `>broadcast` | Send input to all unblocked sessions (default) |
| `>focus <name>` | Send input only to named session |
| `>block [name…]` | Block sessions from receiving input |
| `>unblock [name…]` | Resume blocked sessions |
| `>list` | Show session status |
| `>save <name>` | Save current state as workspace |
| `>exit` | Disconnect all and quit |

## Dangerous Command Confirmation

Commands matching dangerous patterns (`rm -rf /`, `dd`, `mkfs`, `reboot`, `shutdown`, `init 0`) trigger a `yes` confirmation before being broadcast.

## Workspaces

Auto-load workspace from `.sli-workspace.json` in the current directory:

```bash
cd my-project
sli ml          # auto-loads workspace
```

Save/load named workspaces:

```bash
sli ml -w prod       # load workspace "prod"
sli ml --list-workspaces
```
