# GUI Mode

## Launch

```bash
sli-ui
```

A tkinter-based desktop interface for users who prefer a graphical workflow.

## Features

- **Password Dialog** — Modal input for the master password on startup.
- **Host CRUD** — Add, edit, and delete hosts through forms instead of CLI flags.
- **Search Filter** — Real-time filtering of the host list.
- **Keyboard Navigation**
  - `↑/↓` — Navigate list
  - `Enter` — Connect
  - `Delete` — Delete host
  - `F2` — Edit host
  - `Ctrl+F` — Focus search box
  - `Ctrl+N` — Add host
  - `J` — Jump list
- **Connection** — Double-click a host to open an SSH session in a background thread.
- **Status Bar** — Shows connection state and host count.

## Dependencies

tkinter is usually bundled with Python. If missing:

```bash
# Debian / Ubuntu
sudo apt-get install python3-tk

# Arch
sudo pacman -S tk

# macOS (Homebrew Python)
brew install python-tk
```

## When to Use GUI vs CLI

| Scenario | Recommended |
|----------|-------------|
| Quick connect | CLI (`sli connect`) |
| Batch operations / scripting | CLI |
| Visual host management | GUI (`sli-ui`) |
| Shell completion & aliases | CLI |
| Jump host discovery | CLI (`sli jump-list`) |
