"""
slink - Secure SSH Connection Manager
A lightweight CLI tool to store and manage encrypted SSH connection info.
"""
import os
import subprocess


__version__ = "0.1.0"


def _get_build_id() -> str:
    try:
        base = os.path.dirname(os.path.abspath(__file__))
        day = subprocess.check_output(
            ["git", "log", "-1", "--format=%cd", "--date=format:%Y%m%d"],
            cwd=base,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        short_hash = subprocess.check_output(
            ["git", "log", "-1", "--format=%h"],
            cwd=base,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return f"0.1.0+{day}+{short_hash}"
    except Exception:
        return __version__


__version__ = _get_build_id()
