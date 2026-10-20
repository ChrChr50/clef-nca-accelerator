#!/usr/bin/env python3
"""Generate deterministic synthetic and upstream-checkpoint golden hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from reference.original_nca.core import (  # noqa: E402
    CHANNELS,
    GRID_SIZE,
    CanonicalNCA,
    NCAWeights,
    load_tfjs_weights,
    seeded_initial_grid,
    seeded_masks,
)
from reference.original_nca.experiment import run_episode  # noqa: E402


def digest(array: np.ndarray) -> str:
    value = np.asarray(array, dtype="<f4")
    return hashlib.sha256(value.tobytes(order="C")).hexdigest()


def synthetic_weights() -> NCAWeights:
    sizes = (1080, 20, 600, 30, 180, 6)
    shapes = ((3, 3, 6, 20), (20,), (1, 1, 20, 30), (30,), (1, 1, 30, 6), (6,))
    tensors = []
    for index, (size, shape) in enumerate(zip(sizes, shapes, strict=True)):
        values = np.sin(np.arange(size, dtype=np.float32) * np.float32(0.013 + index * 0.001))
        tensors.append((values * np.float32(0.025)).reshape(shape).astype(np.float32))
    return NCAWeights(*tensors)


def case(weights: NCAWeights, checkpoint: str) -> dict[str, object]:
    nca = CanonicalNCA(weights)
    grid = seeded_initial_grid(1701)
    observations = np.asarray([[0.01, -0.02, 0.03, -0.04]], dtype=np.float32)
    masks = seeded_masks(2701, 4)
    delta = nca.local_delta(grid)
    step = nca.step(grid, observations, masks[0])
    rollout = grid
    readouts = []
    for index in range(4):
        rollout = nca.step(rollout, observations, masks[index])
        readouts.append(nca.readout(rollout)[0].tolist())
    cartpole = run_episode(nca, seed=31415, max_steps=8)
    return {
        "checkpoint": checkpoint,
        "initial_grid_seed": 1701,
        "mask_seed": 2701,
        "steps": 4,
        "observations": observations[0].tolist(),
        "local_delta_sha256_f32le": digest(delta),
        "complete_step_sha256_f32le": digest(step),
        "complete_step_readout": nca.readout(step)[0].tolist(),
        "rollout_sha256_f32le": digest(rollout),
        "rollout_readouts": readouts,
        "fixed_cartpole_rollout": {
            "seed": 31415,
            "environment_step_cap": 8,
            "steps": cartpole.steps,
            "reward_sum": cartpole.reward_sum,
            "actions_sha256": cartpole.actions_sha256,
        },
    }


def synthetic_array_case() -> dict[str, np.ndarray]:
    """Full arrays used for cross-platform elementwise golden comparison."""

    nca = CanonicalNCA(synthetic_weights())
    grid = seeded_initial_grid(1701)
    observations = np.asarray([[0.01, -0.02, 0.03, -0.04]], dtype=np.float32)
    masks = seeded_masks(2701, 4)
    delta = nca.local_delta(grid)
    step = nca.step(grid, observations, masks[0])
    rollout = grid
    for mask in masks:
        rollout = nca.step(rollout, observations, mask)
    return {
        "local_delta": np.asarray(delta, dtype="<f4"),
        "complete_step": np.asarray(step, dtype="<f4"),
        "four_step_rollout": np.asarray(rollout, dtype="<f4"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", type=Path)
    parser.add_argument("--write", type=Path)
    parser.add_argument("--write-arrays", type=Path)
    args = parser.parse_args()
    cases = [case(synthetic_weights(), "synthetic-v1")]
    if args.upstream:
        for model in ("model1", "model2", "model3"):
            base = args.upstream / "demo" / "models" / model
            weights = load_tfjs_weights(base / "model.json", base / "group1-shard1of1.bin")
            cases.append(case(weights, model))
    output = {
        "schema_version": 1,
        "byte_contract": "C-order little-endian IEEE-754 binary32",
        "cases": cases,
    }
    rendered = json.dumps(output, indent=2, sort_keys=True) + "\n"
    if args.write:
        args.write.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    if args.write_arrays:
        np.savez_compressed(args.write_arrays, **synthetic_array_case())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
