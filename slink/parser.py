"""
Plain-text config parser.
Format: one key per line,  key: value
Supports # comments, blank lines, and multiline values via | block.
"""

MULTILINE_START = "|"
MULTILINE_END = "|end"
# Keys that should be parsed as space-separated lists
LIST_KEYS = {"extra_args"}


def parse_config(text: str) -> dict:
    """Parse plain text config into dict."""
    config = {}
    key = None
    value_lines = []
    in_multiline = False

    for raw_line in text.splitlines():
        line = raw_line.rstrip("\n\r")
        stripped = line.strip()

        if in_multiline:
            if stripped == MULTILINE_END:
                config[key] = "\n".join(value_lines)
                in_multiline = False
                key = None
                value_lines = []
            else:
                # Preserve relative indentation inside block
                value_lines.append(line)
            continue

        # Skip comments and blank lines ONLY when not in multiline
        if not stripped or stripped.startswith("#"):
            continue

        if ":" in stripped:
            k, v = stripped.split(":", 1)
            k = k.strip()
            v = v.strip()
            if v == MULTILINE_START:
                in_multiline = True
                key = k
                value_lines = []
            else:
                # Try int conversion for port etc.
                if v.isdigit():
                    v = int(v)
                elif k in LIST_KEYS and v:
                    v = v.split()
                config[k] = v
        elif "=" in stripped:
            k, v = stripped.split("=", 1)
            k = k.strip()
            v = v.strip()
            if v.isdigit():
                v = int(v)
            elif k in LIST_KEYS and v:
                v = v.split()
            config[k] = v

    if in_multiline:
        raise ValueError(
            f"Multiline block for key '{key}' was not closed with '{MULTILINE_END}'"
        )
    return config


def dump_config(config: dict) -> str:
    """Serialize dict to plain text config."""
    lines = []
    order = ["hostname", "port", "username", "password", "key_file", "key", "extra_args"]
    done = set()

    for k in order:
        if k in config:
            lines.extend(_dump_entry(k, config[k]))
            done.add(k)

    for k, v in config.items():
        if k not in done:
            lines.extend(_dump_entry(k, v))

    return "\n".join(lines) + "\n"


def _dump_entry(key: str, value) -> list:
    if isinstance(value, list):
        return [f"{key}: {' '.join(str(v) for v in value)}"]
    if isinstance(value, str) and ("\n" in value or value.strip() == ""):
        return [f"{key}: |", value, "|end"]
    return [f"{key}: {value}"]
