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
