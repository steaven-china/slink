# Groups & Workspaces

## Groups

Groups let you refer to multiple hosts by a single name (`@group`).

### Configuration File

`~/.slink/groups.yml`:

```yaml
web:
  hosts: [web1, web2, web3]

db:
  hosts: [db-master, db-replica]

production:
  hosts: []
  groups: [web, db]
```

### Usage

```bash
sli ml @web
sli ml @production
```

### Validation

- Circular references are detected and rejected.
- Unknown groups raise an error.

## Workspaces

Workspaces save the state of an `sli ml` session (blocked hosts, focus, mode).

### Auto-Discovery

`sli ml` looks for `.sli-workspace.json` in the current directory and parent directories.

### Manual Save / Load

```bash
# Inside sli ml
>save prod

# From CLI
sli ml -w prod
sli ml --list-workspaces
```

### Workspace File Format

```json
{
  "name": "prod",
  "hosts": ["web1", "web2", "db1"],
  "blocked": ["db1"],
  "focused": "web1",
  "mode": "focus",
  "created_at": "2024-01-15T08:30:00+00:00"
}
```

Workspaces are stored in `~/.slink/workspaces/`.
