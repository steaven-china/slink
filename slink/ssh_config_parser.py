"""
Parse ~/.ssh/config and extract host entries.
"""
import os
import re


def parse_ssh_config(path: str = None) -> dict:
    """Parse SSH config file and return dict of {alias: info_dict}."""
    if path is None:
        path = os.path.expanduser("~/.ssh/config")

    if not os.path.exists(path):
        return {}

    hosts = {}
    current_host = None

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            # Host definition
            match = re.match(r"^Host\s+(.+)$", stripped, re.IGNORECASE)
            if match:
                names = match.group(1).split()
                # Skip wildcards
                real_names = [n for n in names if "*" not in n and "?" not in n]
                if real_names:
                    current_host = real_names[0]
                    current_aliases = real_names
                    base = {
                        "hostname": current_host,
                        "port": 22,
                        "username": os.environ.get("USER", os.environ.get("USERNAME", "")),
                    }
                    for name in real_names:
                        hosts[name] = dict(base)
                else:
                    current_host = None
                    current_aliases = []
                continue

            if current_host is None:
                continue

            # Config entries (apply to all aliases in this Host block)
            key_val_match = re.match(r"^(\w+)\s+(.+)$", stripped)
            if not key_val_match:
                continue

            key, val = key_val_match.group(1).lower(), key_val_match.group(2).strip()

            for name in current_aliases:
                if key == "hostname":
                    hosts[name]["hostname"] = val
                elif key == "user":
                    hosts[name]["username"] = val
                elif key == "port":
                    try:
                        hosts[name]["port"] = int(val)
                    except ValueError:
                        pass
                elif key == "identityfile":
                    hosts[name]["key_file"] = os.path.expanduser(val)
            # Other keys can be added here as needed

    return hosts
