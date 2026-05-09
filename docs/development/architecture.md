# Architecture

## Module Overview

| Module | Responsibility |
|--------|---------------|
| `cli.py` | Click-based CLI, command routing, quick-connect |
| `gui.py` | tkinter GUI (`sli-ui`) |
| `api.py` | Public API surface (chain unpack, file load, jump resolution) |
| `crypto.py` | Encryption/decryption, key derivation, salt management |
| `store.py` | Encrypted host CRUD, alias resolution, `.show_direct` sync |
| `ssh_wrapper.py` | System `ssh` invocation, temp key files, process cleanup |
| `ml_engine.py` | Multi-login PTY engine (broadcast/focus/block/unblock) |
| `group.py` | YAML group parser, `@group` expansion, cycle detection |
| `workspace.py` | JSON workspace save/load |
| `parser.py` | Plain-text config parser |
| `ssh_config_parser.py` | `~/.ssh/config` importer |
| `lock.py` | Cross-platform advisory file locking |

## Data Flow

```
User Input
    |
    v
+-----------+     +--------+     +----------+
|  CLI/GUI  | --> | store  | --> | crypto   |
+-----------+     +--------+     +----------+
    |                  |               |
    v                  v               v
+-----------+     +--------+     +----------+
| ssh_wrapper|    | .show  |     | hosts.enc|
+-----------+     |_direct |     +----------+
```

## Threading Model

- **GUI**: SSH connections run in daemon threads to keep UI responsive.
- **ML Engine**: Unix uses `select+termios`; Windows uses `threading+msvcrt` with `RLock`.
- **SSH Wrapper**: `ACTIVE_PROCS` registry protected by `threading.Lock`.
