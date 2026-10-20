"""Regenerate model2 weights only into the ignored local artifacts area.

No restricted tensor, literal, memory image or derived checkpoint is tracked.
This is not a quantized RTL export; P07/G4 owns numerical conversion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from reference.original_nca.core import NCAWeights, load_tfjs_weights  # noqa: E402
from sw.cartpole.qualification import load_config  # noqa: E402
from model_export.cartpole.freeze import FREEZE_PATH, load_frozen  # noqa: E402


TENSOR_NAMES = (
    "conv0_kernel", "conv0_bias", "conv1_kernel", "conv1_bias",
    "conv2_kernel", "conv2_bias",
)


def serialize_f32le(weights: NCAWeights) -> bytes:
    if weights.parameter_count != 1916:
        raise ValueError("expected original 1,916-parameter graph")
    return b"".join(
        np.asarray(getattr(weights, name), dtype="<f4").tobytes(order="C")
        for name in TENSOR_NAMES
    )


def validate_round_trip(weights: NCAWeights, raw: bytes) -> None:
    if len(raw) != 1916 * 4:
        raise ValueError("wrong byte count")
    offset = 0
    for name in TENSOR_NAMES:
        original = np.asarray(getattr(weights, name), dtype="<f4")
        count = original.size
        reconstructed = np.frombuffer(raw, dtype="<f4", count=count, offset=offset).reshape(original.shape)
        if not np.array_equal(reconstructed.view("<u4"), original.view("<u4")):
            raise ValueError(f"round-trip mismatch: {name}")
        offset += count * 4


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", type=Path, default=ROOT / "self-organized-control")
    parser.add_argument("--summary", type=Path, default=ROOT / "experiments/p06_cartpole/summary.json")
    parser.add_argument("--out", type=Path, default=ROOT / "artifacts/p06_cartpole/restricted/model2_weights_f32le.bin")
    parser.add_argument("--accepted-freeze", action="store_true",
                        help="Use accepted ADR-0011 resolved freeze; preserve original qualification result")
    args = parser.parse_args()
    config, digest = load_config()
    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    expected = config["authority"]["tfjs_weight_blob_sha256"]
    frozen = load_frozen(FREEZE_PATH) if args.accepted_freeze else None
    if ((not summary.get("qualification_pass") and frozen is None) or summary["config_sha256"] != digest
            or summary["tfjs_weight_blob_sha256"] != expected
            or summary["completed_episodes"] != 10 or not summary["checkpoint_golden_pass"]):
        raise ValueError("accepted qualification has not passed; refusing export")
    allowed = (ROOT / "artifacts").resolve()
    target = args.out.resolve()
    if not target.is_relative_to(allowed) or target.suffix != ".bin":
        raise ValueError("restricted export must be a .bin under ignored artifacts/")
    verifier = subprocess.run(
        [sys.executable, str(ROOT / "reference/original_nca/tools/verify_upstream.py"),
         "--upstream", str(args.upstream)], cwd=ROOT, check=False,
    )
    if verifier.returncode:
        return verifier.returncode
    model = args.upstream / "demo/models/model2"
    weights = load_tfjs_weights(model / "model.json", model / "group1-shard1of1.bin")
    raw = serialize_f32le(weights)
    validate_round_trip(weights, raw)
    observed = hashlib.sha256(raw).hexdigest()
    if observed != expected:
        raise ValueError("export hash differs from pinned model2 blob")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
        raise ValueError("written export failed hash check")
    print(json.dumps({
        "local_restricted_export": str(target), "bytes": len(raw),
        "sha256": observed, "round_trip": "bitwise equal across all six tensors",
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
