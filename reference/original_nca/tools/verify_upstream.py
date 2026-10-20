#!/usr/bin/env python3
"""Verify the local authoritative clone and fixed-checkpoint golden vectors."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from reference.original_nca.tools.generate_golden import case  # noqa: E402
from reference.original_nca.core import load_tfjs_weights  # noqa: E402


EXPECTED_REVISION = "8c85be11b0838ea14ac51a11dac3098db43afed2"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", type=Path, required=True)
    args = parser.parse_args()
    provenance = json.loads((ROOT / "reference/original_nca/provenance.json").read_text())
    golden = json.loads((ROOT / "reference/original_nca/golden/golden_vectors.json").read_text())
    expected_cases = {item["checkpoint"]: item for item in golden["cases"]}
    revision = subprocess.check_output(
        ["git", "-C", str(args.upstream), "rev-parse", "HEAD"], text=True
    ).strip()
    errors: list[str] = []
    if revision != EXPECTED_REVISION:
        errors.append(f"revision {revision} != {EXPECTED_REVISION}")
    for artifact in provenance["artifacts"]:
        path = args.upstream / artifact["path"]
        if not path.is_file():
            errors.append(f"missing {artifact['path']}")
        elif sha256(path) != artifact["sha256"]:
            errors.append(f"hash mismatch {artifact['path']}")
    for model in ("model1", "model2", "model3"):
        base = args.upstream / "demo" / "models" / model
        observed = case(
            load_tfjs_weights(base / "model.json", base / "group1-shard1of1.bin"), model
        )
        if observed != expected_cases[model]:
            errors.append(f"golden mismatch {model}")
    if errors:
        print("upstream verification: FAIL")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(
        "upstream verification: PASS "
        "(revision, 13 artifact hashes, 3 checkpoint operator/CartPole rollouts)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
