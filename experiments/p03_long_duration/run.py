"""Resumable, explicitly reconstructed long-horizon CartPole checkpoint study.

This lives outside the immutable original-paper reference. The only intentional
environment change is an opt-in episode horizon above released HEAD's 10,000.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from reference.original_nca.cartpole import CartPole  # noqa: E402
from reference.original_nca.core import (  # noqa: E402
    CHANNELS,
    GRID_SIZE,
    CanonicalNCA,
    damage_with_trace,
    load_tfjs_weights,
    seeded_initial_grid,
)
from reference.original_nca.experiment import _random_damage  # noqa: E402

CONDITIONS = {
    "baseline": {},
    "noisy_update": {"noisy_updates": True},
    "damage_after_input": {"damage_after_input_probability": 0.5},
    "noisy_damage_after_input": {
        "noisy_updates": True,
        "damage_after_input_probability": 0.5,
    },
    "uniform_damage": {"continuous_damage_probability": 1 / 220},
    "noisy_uniform_damage": {
        "noisy_updates": True,
        "continuous_damage_probability": 1 / 220,
    },
    "delete_cart_position": {"deleted_inputs": (0, 1)},
}


def evaluate(
    nca: CanonicalNCA, seed: int, condition: str, cap: int, progress: Path,
    reinit_probability: float = 0.0,
) -> dict:
    config = {"seed": seed, "condition": condition, "cap": cap,
              "reinit_probability": reinit_probability}
    fingerprint = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    rng = np.random.RandomState(seed)
    env = CartPole.reset(rng)
    env.max_steps = cap - 1  # Released default is 10,000; termination uses >.
    grid = seeded_initial_grid(seed ^ 0x5A17)
    reward_sum = 0.0
    actions = bytearray()
    if progress.exists():
        with np.load(progress, allow_pickle=False) as saved:
            if str(saved["fingerprint"]) != fingerprint:
                raise ValueError("progress belongs to a different episode configuration")
            env.state = saved["env_state"]
            env.step_count = int(saved["step_count"])
            grid = saved["grid"]
            reward_sum = float(saved["reward_sum"])
            actions = bytearray(saved["actions"].tobytes())
            rng.set_state(("MT19937", saved["rng_keys"], int(saved["rng_pos"]),
                           int(saved["rng_gauss_flag"]), float(saved["rng_gauss"])))
        print(f"resumed {config} at {env.step_count}", flush=True)
    options = CONDITIONS[condition]
    active = tuple(i not in options.get("deleted_inputs", ()) for i in range(8))
    while env.step_count < cap:
        observation = env.state.astype(np.float32)[None, :]
        steps = int(rng.randint(50, 60))
        if reinit_probability and rng.random_sample() < reinit_probability:
            grid = ((rng.random_sample((1, GRID_SIZE, GRID_SIZE, CHANNELS)) - 0.5) * 0.2).astype(np.float32)
        if options.get("damage_after_input_probability", 0) and rng.random_sample() < 0.5:
            grid = _random_damage(grid, rng, damage_with_trace)
        for _ in range(steps):
            mask = rng.random_sample((1, GRID_SIZE, GRID_SIZE, 1)) <= 0.5
            noise = None
            if options.get("noisy_updates", False):
                noise = (np.float32(0.01) * rng.uniform(
                    -1.0, 1.0, size=(1, GRID_SIZE, GRID_SIZE, CHANNELS)
                )).astype(np.float32)
            grid = nca.step(grid, observation, mask, update_noise=noise, active_inputs=active)
            if options.get("continuous_damage_probability", 0) and rng.random_sample() < 1 / 220:
                grid = _random_damage(grid, rng, damage_with_trace)
        action = int(nca.action(grid)[0])
        actions.append(action)
        _, reward, done = env.step(action)
        reward_sum += reward
        if env.step_count % 1000 == 0 and not done:
            state = rng.get_state()
            np.savez_compressed(
                progress, fingerprint=fingerprint, env_state=env.state,
                step_count=env.step_count, grid=grid, reward_sum=reward_sum,
                actions=np.frombuffer(actions, dtype=np.uint8), rng_keys=state[1],
                rng_pos=state[2], rng_gauss_flag=state[3], rng_gauss=state[4],
            )
            print(f"{config}: {env.step_count} steps", flush=True)
        if done:
            break
    progress.unlink(missing_ok=True)
    return {
        **config, "steps": len(actions), "reward_sum": reward_sum,
        "actions_sha256": hashlib.sha256(actions).hexdigest(),
        "right_censored": len(actions) == cap,
        "python": platform.python_version(), "numpy": np.__version__,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=("model1", "model2", "model3"), default="model2")
    parser.add_argument("--conditions", nargs="+", choices=tuple(CONDITIONS), default=["baseline"])
    parser.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2])
    parser.add_argument("--cap", type=int, default=30_000)
    parser.add_argument("--reinit-probability", type=float, default=0.0)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("results.jsonl"))
    args = parser.parse_args()
    if args.cap < 1:
        raise ValueError("cap must be positive")
    if not 0 <= args.reinit_probability <= 1:
        raise ValueError("reinit probability must be in [0, 1]")
    source = ROOT / "self-organized-control" / "demo" / "models" / args.model
    nca = CanonicalNCA(load_tfjs_weights(source / "model.json", source / "group1-shard1of1.bin"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    existing = [] if not args.output.exists() else [json.loads(line) for line in args.output.read_text().splitlines()]
    for condition in args.conditions:
        for seed in args.seeds:
            key = (args.model, condition, seed, args.cap, args.reinit_probability)
            if any((x["model"], x["condition"], x["seed"], x["cap"],
                    x.get("reinit_probability", 0.0)) == key for x in existing):
                continue
            progress = args.output.with_name(
                f"progress_{args.model}_{condition}_{seed}_{args.cap}_{args.reinit_probability}.npz"
            )
            result = evaluate(nca, seed, condition, args.cap, progress, args.reinit_probability)
            result["model"] = args.model
            with args.output.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(result, sort_keys=True) + "\n")
            existing.append(result)
            print(json.dumps(result, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
