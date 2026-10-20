#!/usr/bin/env python3
"""Check the pinned Python execution contract and published configuration."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
def main() -> int:
    errors: list[str] = []

    for relative in ("pyproject.toml", "config/toolchains.toml"):
        try:
            with (ROOT / relative).open("rb") as stream:
                tomllib.load(stream)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            errors.append(f"invalid TOML in {relative}: {exc}")

    lock_lines = [
        line.strip()
        for line in (ROOT / "requirements/ci.lock").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    lock_text = " ".join(lock_lines)
    required_lock_tokens = (
        "numpy==2.3.5",
        "sha256:0d8163f43acde9a73c2a33605353a4f1bc4798745a8b1d73183b28e5b435ae28",
        "sha256:86945f2ee6d10cdfd67bcb4069c1662dd711f7e2a4343db5cecec06b87cf31aa",
    )
    if not all(token in lock_text for token in required_lock_tokens):
        errors.append("CI lock is missing the pinned NumPy version or wheel hashes")

    workflow = (ROOT / ".github/workflows/smoke.yml").read_text(encoding="utf-8")
    if "python scripts/run_smoke.py" not in workflow:
        errors.append("CI does not invoke the repository smoke entry point")

    if sys.version_info[:2] != (3, 12):
        errors.append(
            f"expected Python 3.12, found {sys.version_info.major}.{sys.version_info.minor}"
        )

    if errors:
        print("reproducibility check: FAIL")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(
        "reproducibility check: PASS ("
        "NumPy 2.3.5 locked, Python 3.12)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
