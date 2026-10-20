#!/usr/bin/env python3
"""Validate the P02 repository scaffold without third-party dependencies."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    "README.md",
    "LICENSE",
    ".gitignore",
    ".gitattributes",
    ".editorconfig",
    ".verible-verilog-format",
    "pyproject.toml",
    "requirements/ci.lock",
    "config/toolchains.toml",
    ".github/workflows/smoke.yml",
    "docs/STATUS.md",
    "docs/requirements/REQUIREMENTS_TRACEABILITY.md",
    "docs/decisions/ADR-0001-platform-toolchain-and-repository-policy.md",
    "docs/artifacts/RETENTION_POLICY.md",
)

REQUIRED_DIRECTORIES = (
    "reference",
    "training",
    "model_export",
    "rtl",
    "tb",
    "sw",
    "boards",
    "flows",
    "experiments",
    "docs",
    "tests",
    "rtl/core",
    "rtl/wrappers/fpga",
    "rtl/wrappers/asic",
    "boards/de1_soc",
    "flows/fpga/quartus/de1_soc",
    "flows/asic/openroad",
    "artifacts",
    "third_party",
)


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []
    for relative in REQUIRED_FILES:
        require((ROOT / relative).is_file(), f"missing file: {relative}", errors)
    for relative in REQUIRED_DIRECTORIES:
        require((ROOT / relative).is_dir(), f"missing directory: {relative}", errors)

    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8").lower()
    require(
        "all rights reserved" in license_text,
        "LICENSE does not preserve the accepted all-rights-reserved posture",
        errors,
    )

    toolchains = (ROOT / "config/toolchains.toml").read_text(encoding="utf-8")
    for token in ("DE1-SoC", "5CSEMA5F31C6N", "Quartus Prime Lite", "Yosys", "OpenROAD"):
        require(token in toolchains, f"toolchain policy is missing {token!r}", errors)

    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for token in ("/tmp/", "*.lic", "/artifacts/**", "pdks/"):
        require(token in gitignore, f".gitignore is missing required rule {token!r}", errors)

    if errors:
        print("scaffold check: FAIL")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(
        f"scaffold check: PASS ({len(REQUIRED_FILES)} files, "
        f"{len(REQUIRED_DIRECTORIES)} directories)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
