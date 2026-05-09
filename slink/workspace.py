"""Workspace (session snapshot) management for sli ml."""
import json
import os
import stat
import sys
import tempfile
from datetime import datetime, timezone

from .crypto import DEFAULT_CONFIG_DIR

WORKSPACES_DIR = os.path.join(DEFAULT_CONFIG_DIR, "workspaces")


def _ensure_dir():
    os.makedirs(WORKSPACES_DIR, mode=0o700, exist_ok=True)


def _workspace_path(name: str) -> str:
    _ensure_dir()
    return os.path.join(WORKSPACES_DIR, f"{name}.json")


def list_workspaces() -> list:
    """Return sorted list of workspace names."""
    if not os.path.exists(WORKSPACES_DIR):
        return []
    names = []
    for f in os.listdir(WORKSPACES_DIR):
        if f.endswith(".json"):
            names.append(f[:-5])
    return sorted(names)


def load_workspace(name: str) -> dict:
    """Load workspace by name."""
    path = _workspace_path(name)
    if not os.path.exists(path):
        raise ValueError(f"Workspace '{name}' not found.")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_workspace(data: dict, name: str):
    """Save workspace dict atomically."""
    path = _workspace_path(name)
    fd, tmp_path = tempfile.mkstemp(
        dir=WORKSPACES_DIR,
        prefix=f".{name}.json.",
        suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        if sys.platform == "win32" and os.path.exists(path):
            os.chmod(path, stat.S_IWRITE)
        os.replace(tmp_path, path)
        if sys.platform != "win32":
            os.chmod(path, 0o600)
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


def delete_workspace(name: str):
    """Delete workspace by name."""
    path = _workspace_path(name)
    if os.path.exists(path):
        if sys.platform == "win32":
            os.chmod(path, stat.S_IWRITE)
        os.remove(path)


def build_workspace(name: str, hosts: list, blocked: list = None,
                    focused: str = None, mode: str = "broadcast") -> dict:
    """Build a workspace dict from current session state."""
    return {
        "name": name,
        "hosts": list(hosts),
        "blocked": list(blocked or []),
        "focused": focused,
        "mode": mode,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def find_workspace_file(start_dir: str = None) -> str:
    """Look for .sli-workspace.json in current or parent directories."""
    if start_dir is None:
        start_dir = os.getcwd()
    current = os.path.abspath(start_dir)
    root = os.path.dirname(current)
    while current and current != root:
        path = os.path.join(current, ".sli-workspace.json")
        if os.path.exists(path):
            return path
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return None
