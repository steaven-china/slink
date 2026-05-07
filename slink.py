#!/usr/bin/env python3
"""Direct runner: python slink.py <command> ..."""
import sys
from pathlib import Path

# Ensure the local package is importable
sys.path.insert(0, str(Path(__file__).parent))

from slink.cli import main

if __name__ == "__main__":
    main()
