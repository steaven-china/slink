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
                    hosts[current_host] = {
                        "hostname": current_host,
                        "port": 22,
                        "username": os.environ.get("USER", os.environ.get("USERNAME", "")),
                    }
                else:
                    current_host = None
                continue

            if current_host is None:
                continue

            # Config entries
            key_val_match = re.match(r"^(\w+)\s+(.+)$", stripped)
            if not key_val_match:
                continue

            key, val = key_val_match.group(1).lower(), key_val_match.group(2).strip()

            if key == "hostname":
                hosts[current_host]["hostname"] = val
            elif key == "user":
                hosts[current_host]["username"] = val
            elif key == "port":
                try:
                    hosts[current_host]["port"] = int(val)
                except ValueError:
                    pass
            elif key == "identityfile":
                hosts[current_host]["key_file"] = os.path.expanduser(val)
            elif key == "addkeystoagent":
                pass
            elif key == "serveraliveinterval":
                pass
            # Other keys can be added here as needed

    return hosts
