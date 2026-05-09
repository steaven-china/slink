# File Permissions

All directories are created with `0o700` and files with `0o600`.

## Permission Matrix

| File | Unix | Windows |
|------|------|---------|
| `hosts.enc` | `0o600` | Read-only (`S_IREAD`) |
| `salt` | `0o600` | Read-only |
| `.show_direct` | `0o600` | Read-only |
| `.lock` | `0o600` | Read-only |
| `groups.yml` | `0o600` | Read-only |
| Workspaces | `0o600` | Read-only |

## Cross-Platform Locking

Advisory file locking prevents concurrent writes on shared filesystems:

- **Windows**: `msvcrt.locking`
- **Unix**: `fcntl.flock`

## Read-Only File Handling

On Windows, read-only files cannot be deleted or overwritten without first clearing the read-only flag. All write operations in slink handle this automatically:

- `save_hosts()`
- `save_groups()`
- `save_workspace()`
- `rotate_password()`
