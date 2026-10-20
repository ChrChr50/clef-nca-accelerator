#!/usr/bin/env python3
"""Evaluate shipped checkpoints under named, reproducible perturbation conditions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from reference.original_nca.core import CanonicalNCA, load_tfjs_weights  # noqa: E402
from reference.original_nca.experiment import run_episode  # noqa: E402


def summarize(results, seeds: list[int], cap: int) -> dict[str, object]:
    data = np.asarray([item.steps for item in results], dtype=np.float64)
    episodes = [
        {
            "seed": seed,
            "steps": item.steps,
            "reward_sum": item.reward_sum,
            "actions_sha256": item.actions_sha256,
            "right_censored": item.steps == cap,
        }
        for seed, item in zip(seeds, results, strict=True)
    ]
    return {
        "n": int(data.size),
        "mean_steps": float(data.mean()),
        "sample_std_steps": float(data.std(ddof=1)) if data.size > 1 else 0.0,
        "min_steps": int(data.min()),
        "max_steps": int(data.max()),
        "censored_episodes": sum(item["right_censored"] for item in episodes),
        "episodes": episodes,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--model", choices=("model1", "model2", "model3"), default="model1")
    parser.add_argument("--episodes", type=int, default=10)
    parser.add_argument("--max-steps", type=int, default=10_001)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    base = args.upstream / "demo" / "models" / args.model
    nca = CanonicalNCA(load_tfjs_weights(base / "model.json", base / "group1-shard1of1.bin"))
    conditions = {
        "baseline": {},
        "noisy_update": {"noisy_updates": True},
        "damage_after_input": {"damage_after_input_probability": 0.5},
        "noisy_damage_after_input": {
            "noisy_updates": True,
            "damage_after_input_probability": 0.5,
        },
        "uniform_damage": {"continuous_damage_probability": 1.0 / 220.0},
        "noisy_uniform_damage": {
            "noisy_updates": True,
            "continuous_damage_probability": 1.0 / 220.0,
        },
        "delete_cart_position": {"deleted_inputs": (0, 1)},
    }
    for input_index in range(8):
        conditions[f"delete_input_{input_index}_with_noise_and_damage"] = {
            "deleted_inputs": (input_index,),
            "noisy_updates": True,
            "damage_after_input_probability": 0.5,
        }
    seeds = list(range(args.episodes))
    report = {
        "schema_version": 1,
        "model": args.model,
        "seeds": seeds,
        "runtime": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "dependency_lock": "requirements/original_nca.lock",
        },
        "conditions": {},
        "qualification": "clean-room empirical attempt; not historical bitwise replay",
        "comparison_rule": (
            "uncensored 95% confidence interval for reproduced mean must overlap "
            "paper mean plus/minus one reported standard deviation"
        ),
    }
    for name, options in conditions.items():
        results = [
            run_episode(nca, seed, max_steps=args.max_steps, **options)
            for seed in seeds
        ]
        report["conditions"][name] = summarize(results, seeds, args.max_steps)
    report["evaluation_cap_steps"] = args.max_steps
    report["conditions_with_censoring"] = sum(
        value["censored_episodes"] > 0 for value in report["conditions"].values()
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
