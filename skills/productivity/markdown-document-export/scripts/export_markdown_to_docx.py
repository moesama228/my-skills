#!/usr/bin/env python3
"""Backward-compatible wrapper for explicit Word export."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    command = [
        sys.executable,
        str(script_dir / "export_markdown.py"),
        *sys.argv[1:],
        "--output-format",
        "word",
    ]
    completed = subprocess.run(command, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
