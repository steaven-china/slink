"""Host group management for sli ml."""
import os
import stat
import sys
import tempfile

from .crypto import DEFAULT_CONFIG_DIR

GROUPS_FILE = os.path.join(DEFAULT_CONFIG_DIR, "groups.yml")


def load_groups() -> dict:
    """Load groups from ~/.slink/groups.yml. Returns {name: {"hosts": [...], "groups": [...]}}."""
    if not os.path.exists(GROUPS_FILE):
        return {}
    try:
        import yaml
    except ImportError:
        raise ImportError("PyYAML is required for group support. Install: pip install pyyaml")
    with open(GROUPS_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not data:
        return {}
    return {k: _normalize_group(v) for k, v in data.items()}


def _normalize_group(value):
    """Normalize group value to dict with hosts and groups lists."""
    if isinstance(value, list):
        return {"hosts": value, "groups": []}
    if isinstance(value, dict):
        return {
            "hosts": value.get("hosts", []),
            "groups": value.get("groups", []),
        }
    return {"hosts": [], "groups": []}


def resolve_group(name: str, groups: dict, _resolved: set = None) -> list:
    """Expand a group name to a flat list of host names (no duplicates, preserves order)."""
    if _resolved is None:
        _resolved = set()
    if name in _resolved:
        raise ValueError(f"Circular group reference detected: {' -> '.join(_resolved)} -> {name}")
    _resolved.add(name)

    group = groups.get(name)
    if not group:
        raise ValueError(f"Group '{name}' not found.")

    result = []
    for host in group.get("hosts", []):
        if host not in result:
            result.append(host)

    for sub_name in group.get("groups", []):
        sub_name = sub_name.lstrip("@")
        for h in resolve_group(sub_name, groups, _resolved.copy()):
            if h not in result:
                result.append(h)

    return result


def expand_targets(targets: list, groups: dict, all_hosts: dict) -> list:
    """Expand a list of targets (hosts and @groups) to unique host names."""
    result = []
    for t in targets:
        if t.startswith("@"):
            for h in resolve_group(t[1:], groups):
                if h not in result:
                    result.append(h)
        else:
            if t not in all_hosts:
                raise ValueError(f"Host '{t}' not found in encrypted store.")
            if t not in result:
                result.append(t)
    return result


def save_groups(groups: dict):
    """Save groups to ~/.slink/groups.yml atomically."""
    import yaml
    os.makedirs(DEFAULT_CONFIG_DIR, mode=0o700, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(
        dir=DEFAULT_CONFIG_DIR,
        prefix=".groups.yml.",
        suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            yaml.dump(groups, f, default_flow_style=False, allow_unicode=True, sort_keys=True)
        if sys.platform == "win32" and os.path.exists(GROUPS_FILE):
            os.chmod(GROUPS_FILE, stat.S_IWRITE)
        os.replace(tmp_path, GROUPS_FILE)
        if sys.platform != "win32":
            os.chmod(GROUPS_FILE, 0o600)
    except Exception:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise
