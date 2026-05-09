# Changelog

## Unreleased

- Added search filter and keyboard navigation to GUI
- Removed Tailwind CDN dependency from documentation site
- Fixed `ACTIVE_PROCS` race condition in `ssh_wrapper.py`
- Fixed quick-connect exception handling in `cli.py`
- Fixed `_refresh_list` selection sync in `gui.py`
- Fixed `save_workspace` fd leak on Windows
- Fixed SSH config import to support multiple aliases per Host block
- Fixed `sli file.txt --help` incorrectly triggering quick-connect

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
