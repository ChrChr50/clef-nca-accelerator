#!/usr/bin/env python3
"""Compare the clean-room NumPy reference with TensorFlow.js 3.7.0."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from reference.original_nca.core import CanonicalNCA, load_tfjs_weights  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--node", default="node")
    args = parser.parse_args()
    output = ROOT / "tmp/p03-tfjs-oracle/output"
    script = ROOT / "reference/original_nca/tools/tfjs_oracle.cjs"
    result = subprocess.run(
        [args.node, str(script), str(args.upstream), str(output)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    weights = load_tfjs_weights(
        args.upstream / "demo/models/model1/model.json",
        args.upstream / "demo/models/model1/group1-shard1of1.bin",
    )
    nca = CanonicalNCA(weights)
    indices = np.arange(32 * 32 * 6, dtype=np.float32)
    grid = (np.sin(indices * np.float32(0.017)) * np.float32(0.1)).reshape(1, 32, 32, 6)
    mask = (np.arange(32 * 32).reshape(1, 32, 32, 1) % 3) != 0
    observation = np.asarray([[0.01, -0.02, 0.03, -0.04]], dtype=np.float32)
    expected_delta = np.fromfile(output / "local_delta.bin", dtype="<f4").reshape(1,32,32,6)
    expected_step = np.fromfile(output / "complete_step.bin", dtype="<f4").reshape(1,32,32,6)
    observed_delta = nca.local_delta(grid)
    observed_step = nca.step(grid, observation, mask)
    delta_error = float(np.max(np.abs(observed_delta - expected_delta)))
    step_error = float(np.max(np.abs(observed_step - expected_step)))
    if delta_error > 2e-5 or step_error > 2e-5:
        print(f"TensorFlow.js comparison: FAIL (delta={delta_error}, step={step_error})")
        return 1
    print(
        "TensorFlow.js comparison: PASS "
        f"(delta max_abs={delta_error:.9g}, step max_abs={step_error:.9g}; {result.stdout.strip()})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

