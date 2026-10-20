#!/usr/bin/env python3
"""Run the repository scaffold and reproducibility smoke gate."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKS = (
    "scripts/check_scaffold.py",
    "scripts/check_reproducibility.py",
    "scripts/check_oracle_firewall.py",
)


def main() -> int:
    for check in CHECKS:
        result = subprocess.run([sys.executable, check], cwd=ROOT, check=False)
        if result.returncode:
            return result.returncode
    print("repository smoke gate: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
