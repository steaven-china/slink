# Config Files

## Config Directory

Default location: `~/.slink/`

On Windows: `%USERPROFILE%\.slink\`

## File Layout

```
~/.slink/
├── hosts.enc          # Encrypted host database
├── salt               # PBKDF2 salt (0o600)
├── .show_direct       # Plaintext name index (0o600)
├── .lock              # Advisory lock file
├── groups.yml         # Host groups definition
└── workspaces/        # Saved ml workspaces
    └── <name>.json
```

## Chain Files

Chain files describe multi-hop SSH topologies. They come in two flavors:

### `.chain` — Plain topology (safe to share, no secrets)

```json
{
  "jumps": [
    {"hostname": "bastion.example.com", "username": "ops", "port": 2222},
    {"hostname": "10.0.0.1", "username": "root"}
  ],
  "endpoint": {
    "hostname": "10.0.0.5",
    "username": "dbadmin"
  }
}
```

### `.chain.enc` — Encrypted bundle (one password unlocks everything)

Internally stores `topology` + `secrets` and auto-merges on load:

```json
{
  "topology": {
    "jumps": [...],
    "endpoint": {...}
  },
  "secrets": {
    "jumps": [
      {"password": "...", "key_file": "..."},
      ...
    ],
    "endpoint": {"password": "...", "key": "..."}
  }
}
```

Use `sli chain-create` to build these interactively, or export a stored host
with jumps from the GUI.

## Multi-User Isolation

Set the environment variable to switch config directories:

```bash
export SLINK_USER=alice
sli list   # reads ~/.slink/users/alice/
```

Useful on shared bastion hosts where multiple operators need separate encrypted stores.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SLINK_USER` | Switch to per-user config directory |
| `SLINK_PASSWORD` | Skip interactive password prompt |
