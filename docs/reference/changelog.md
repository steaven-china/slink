# Changelog

## Unreleased

### Added
- **Chain connections** — `.chain` / `.chain.enc` multi-hop SSH with per-hop keys (`sli chain-create`, `connect_chain`)
- **Tunnel command** — `sli tunnel` for local/remote port forwarding and SOCKS5 proxies
- **GUI chain support** — Open Chain file dialog and Export Chain from selected host
- **Public API** — `slink.api` module exposing core logic for programmatic use
- **CI/CD** — GitHub Actions workflows for cross-platform testing and Nuitka release builds

### Changed
- License switched from GPL-3.0 to LGPL-3.0
- Documentation migrated to standalone CSS (no Tailwind CDN)
- Refactored docs into structured tree (`getting-started/`, `user-guide/`, etc.)

### Fixed
- `ACTIVE_PROCS` race condition in `ssh_wrapper.py`
- Quick-connect exception handling in `cli.py`
- `_refresh_list` selection sync in `gui.py`
- `save_workspace` fd leak on Windows
- SSH config import to support multiple aliases per Host block
- `sli file.txt --help` incorrectly triggering quick-connect
- `group.py` missing `import sys` on Windows

## 0.1.0

- Initial release
- Encrypted host storage (Fernet + PBKDF2)
- Aliases, jump hosts, JSON import/export
- Multi-user isolation (`SLINK_USER`)
- Password rotation
- Shell completion
- tkinter GUI
- Agent temporary password
- Multi-login engine (`sli ml`) with broadcast/focus modes
- Group support (`@group`)
- Workspace save/load
- Cross-platform locking
