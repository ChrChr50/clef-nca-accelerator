#!/usr/bin/env python3
"""Reject oracle imports/data from deployable and synthesis artifact trees."""

from __future__ import annotations

import ast
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
DEPLOYABLE_TREES = ("model_export", "rtl", "boards", "flows")
SCANNED_SUFFIXES = {".py", ".sv", ".svh", ".v", ".vh", ".tcl", ".qsf", ".f", ".json", ".toml", ".mem", ".hex", ".mif", ".coe"}
FORBIDDEN_TOKENS = (
    "reference.hanoi.oracle",
    "hanoi.oracle",
    "import oracle",
    "oracle import",
    "reverse_graph_distances",
    "optimal_actions",
    "distance_table_hash",
    "oracle_distance",
    "oracle_trace",
)


def violations(root: Path) -> list[str]:
    failures: list[str] = []
    protected = [
        root / "reference" / "hanoi" / "environment.py",
        root / "reference" / "hanoi" / "__init__.py",
        root / "training" / "hanoi_nca" / "adapter.py",
        root / "training" / "hanoi_nca" / "model.py",
        root / "training" / "hanoi_nca" / "runtime.py",
        root / "training" / "hanoi_nca" / "control.py",
    ]
    candidates = list(protected)
    for tree in DEPLOYABLE_TREES:
        directory = root / tree
        if directory.exists():
            candidates.extend(path for path in directory.rglob("*") if path.is_file() and path.suffix.lower() in SCANNED_SUFFIXES)
    for path in candidates:
        if not path.exists():
            failures.append(f"missing protected contract file: {path.relative_to(root)}")
            continue
        relative = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        lowered_name = path.name.lower()
        if path.parts[-1] not in {"environment.py", "__init__.py", "adapter.py", "model.py", "runtime.py", "control.py"} and any(
            marker in lowered_name for marker in ("oracle", "optimal_action", "distance_table", "distances")
        ):
            failures.append(f"forbidden artifact name: {relative}")
        for token in FORBIDDEN_TOKENS:
            if token in text:
                failures.append(f"forbidden token {token!r}: {relative}")
        if path.suffix == ".py":
            try:
                ast.parse(text, filename=str(path))
            except SyntaxError as error:
                failures.append(f"unparseable Python file {relative}: {error}")
    return failures


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT
    failures = violations(root)
    if failures:
        print("oracle import/build firewall: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("oracle import/build firewall: PASS")
    print("scanned deployable trees: " + ", ".join(DEPLOYABLE_TREES))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
