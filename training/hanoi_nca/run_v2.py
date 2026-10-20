#!/usr/bin/env python3
"""Reproducible P05 v2 routing, legality, action, and multi-move experiment."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.hanoi.environment import ACTIONS, HanoiEnv, encode_observation, transition
from reference.hanoi.oracle import optimal_actions
from training.hanoi_nca.dataset import Sample, build_corpus, identity_bucket
from training.hanoi_nca.layout import layout_statistics, load_layout
from training.hanoi_nca.model import require_torch, save_checkpoint
from training.hanoi_nca.run_experiment import episode_specs, evaluate_nca, summarize_episodes
from training.hanoi_nca.v2_adapter import LAYOUT_PATH
from training.hanoi_nca.v2_model import PARAMETER_COUNT, build_v2_model
from training.hanoi_nca.v2_runtime import TorchNCAV2Runtime


SCHEMA = "clef.p05.hanoi-v2-experiment.v1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def v2_split(sample: Sample) -> str:
    bucket = identity_bucket(sample.state_hash)
    return "train" if bucket < 80 else ("validation" if bucket < 90 else "test")


def partition_manifest(corpus: list[Sample]) -> dict[str, object]:
    counts = Counter()
    identities = defaultdict(hashlib.sha256)
    for sample in corpus:
        split = v2_split(sample)
        counts[
            f"{split}|n={sample.state.disk_count}|goal={sample.state.goal_peg}|"
            f"distance={sample.distance}|terminal={not sample.actions}|reset={sample.reset_mode}"
        ] += 1
        identities[split].update((sample.state_hash + "\n").encode("ascii"))
    return {
        "rule": "first 32 state-hash bits modulo 100: <80 train, 80-89 validation, 90-99 test for each n=1..8",
        "counts": dict(sorted(counts.items())),
        "identity_digests": {key: value.hexdigest() for key, value in sorted(identities.items())},
        "training_trajectory_rule": "stop before consuming any state outside the training identity partition",
    }


def training_strata(corpus: list[Sample]) -> dict[tuple[int, int], list[Sample]]:
    strata = defaultdict(list)
    for sample in corpus:
        if sample.actions and v2_split(sample) == "train":
            strata[(sample.state.disk_count, sample.state.goal_peg)].append(sample)
    if len(strata) != 24:
        raise AssertionError("every disk-count/goal training stratum must be nonempty")
    return dict(strata)


def draw_batch(strata: dict[tuple[int, int], list[Sample]], rng: np.random.RandomState, count: int) -> list[Sample]:
    samples = []
    for _ in range(count):
        key = (int(rng.randint(1, 9)), int(rng.randint(0, 3)))
        cases = strata[key]
        samples.append(cases[int(rng.randint(len(cases)))])
    return samples


def routing_targets(samples: list[Sample]) -> np.ndarray:
    """Simple spatial-transport target, not a Hanoi solution signal."""
    targets = np.zeros((len(samples), 6), dtype=np.float32)
    for row, sample in enumerate(samples):
        n = sample.state.disk_count
        for action, (source, destination) in enumerate(ACTIONS):
            occupancy = sum(peg == source for peg in sample.state.locations) / n
            targets[row, action] = occupancy + 0.5 * (sample.state.goal_peg == destination)
    return targets


def legality_targets(samples: list[Sample]) -> np.ndarray:
    return np.asarray(
        [[float(transition(sample.state, action)[1]) for action in range(6)] for sample in samples],
        dtype=np.float32,
    )


def action_targets(samples: list[Sample]) -> np.ndarray:
    targets = np.zeros((len(samples), 6), dtype=np.float32)
    for row, sample in enumerate(samples):
        targets[row, list(sample.actions)] = 1.0 / len(sample.actions)
    return targets


def soft_target_loss(scores, targets):
    torch = require_torch()
    return -(targets * torch.log_softmax(scores, dim=1)).sum(dim=1).mean()


def train_single_decision(
    phase: str,
    runtime,
    optimizer,
    strata,
    iterations: int,
    batch_size: int,
    step_min: int,
    step_max: int,
    seed: int,
) -> list[dict[str, object]]:
    torch = require_torch()
    rng = np.random.RandomState(seed)
    mask_rng = torch.Generator().manual_seed(seed + 1)
    curve = []
    runtime.model.train()
    for iteration in range(iterations):
        samples = draw_batch(strata, rng, batch_size)
        observations = torch.tensor([sample.observation for sample in samples], dtype=torch.float32)
        if phase == "routing":
            target = torch.from_numpy(routing_targets(samples))
        elif phase == "legality":
            target = torch.from_numpy(legality_targets(samples))
        elif phase == "imitation":
            target = torch.from_numpy(action_targets(samples))
        else:
            raise ValueError("unknown single-decision phase")
        steps = int(rng.randint(step_min, step_max + 1))
        state = runtime.initial_state(batch_size, seed * 100000 + iteration)
        optimizer.zero_grad(set_to_none=True)
        evolved = runtime.run(state, observations, steps, 0.5, mask_rng)
        scores = runtime.readout(evolved)
        if phase == "routing":
            loss = torch.mean((scores - target) ** 2)
        elif phase == "legality":
            loss = torch.nn.functional.binary_cross_entropy_with_logits(scores, target)
        else:
            loss = soft_target_loss(scores, target)
        if not bool(torch.isfinite(loss)):
            raise FloatingPointError(f"{phase}: non-finite loss at iteration {iteration}")
        loss.backward()
        norm = float(torch.nn.utils.clip_grad_norm_(runtime.model.parameters(), 1.0))
        if not np.isfinite(norm):
            raise FloatingPointError(f"{phase}: non-finite gradient at iteration {iteration}")
        optimizer.step()
        if iteration % max(1, iterations // 20) == 0 or iteration == iterations - 1:
            curve.append({
                "iteration": iteration,
                "steps": steps,
                "loss": float(loss.detach()),
                "gradient_norm": norm,
                "max_abs_state": float(evolved.detach().abs().max()),
            })
    return curve


def train_multi_decision(
    phase: str,
    runtime,
    optimizer,
    strata,
    iterations: int,
    batch_size: int,
    decisions: int,
    step_min: int,
    step_max: int,
    seed: int,
) -> list[dict[str, object]]:
    torch = require_torch()
    rng = np.random.RandomState(seed)
    mask_rng = torch.Generator().manual_seed(seed + 1)
    curve = []
    runtime.model.train()
    for iteration in range(iterations):
        samples = draw_batch(strata, rng, batch_size)
        envs = []
        for sample in samples:
            env = HanoiEnv(sample.state.disk_count, sample.state.goal_peg, 2 * ((1 << sample.state.disk_count) - 1))
            env.reset(initial_locations=sample.state.locations)
            envs.append(env)
        state = runtime.initial_state(batch_size, seed * 100000 + iteration)
        optimizer.zero_grad(set_to_none=True)
        losses = []
        oracle_labels = 0
        active_counts = []
        illegal_attempts = 0
        for decision in range(decisions):
            active = [
                index for index, env in enumerate(envs)
                if not env.terminated and not env.truncated and identity_bucket(env.state.state_hash) < 80
            ]
            if not active:
                break
            active_set = set(active)
            # Inactive rows receive zeros, so held-out identities are never presented.
            obs = np.zeros((batch_size, 36), dtype=np.float32)
            targets = np.zeros((batch_size, 6), dtype=np.float32)
            for index in active:
                current = envs[index].state
                obs[index] = encode_observation(current)
                actions = optimal_actions(current)
                targets[index, list(actions)] = 1.0 / len(actions)
                oracle_labels += 1
            observations = torch.from_numpy(obs)
            target_tensor = torch.from_numpy(targets)
            steps = int(rng.randint(step_min, step_max + 1))
            state = runtime.run(state, observations, steps, 0.5, mask_rng)
            scores = runtime.readout(state)
            losses.append(soft_target_loss(scores[active], target_tensor[active]))
            active_counts.append(len(active))
            chosen = scores.detach().argmax(1).tolist()
            for index in active:
                if phase == "teacher_sequence":
                    action = optimal_actions(envs[index].state)[0]
                elif phase == "dagger_sequence":
                    action = int(chosen[index])
                else:
                    raise ValueError("unknown multi-decision phase")
                result = envs[index].step(action)
                illegal_attempts += int(not result.legal)
            # Do not continue any trajectory that crossed into the held-out partition.
            for index in range(batch_size):
                if index not in active_set:
                    continue
                if identity_bucket(envs[index].state.state_hash) >= 80:
                    active_counts.append(-1)
        if not losses:
            continue
        loss = torch.stack(losses).mean()
        if not bool(torch.isfinite(loss)):
            raise FloatingPointError(f"{phase}: non-finite loss at iteration {iteration}")
        loss.backward()
        norm = float(torch.nn.utils.clip_grad_norm_(runtime.model.parameters(), 1.0))
        if not np.isfinite(norm):
            raise FloatingPointError(f"{phase}: non-finite gradient at iteration {iteration}")
        optimizer.step()
        if iteration % max(1, iterations // 20) == 0 or iteration == iterations - 1:
            curve.append({
                "iteration": iteration,
                "loss": float(loss.detach()),
                "gradient_norm": norm,
                "decisions_with_loss": len(losses),
                "oracle_labels": oracle_labels,
                "active_batch_counts": [value for value in active_counts if value >= 0],
                "held_out_trajectory_stops": active_counts.count(-1),
                "illegal_attempts": illegal_attempts,
                "max_abs_state": float(state.detach().abs().max()),
            })
    return curve


def open_loop_metrics(runtime, samples: list[Sample], seed: int, limit: int, steps: int) -> dict[str, object]:
    torch = require_torch()
    rng = np.random.RandomState(seed)
    mask_rng = torch.Generator().manual_seed(seed + 1)
    groups = defaultdict(list)
    for sample in samples:
        if sample.actions:
            groups[(sample.state.disk_count, sample.state.goal_peg)].append(sample)
    selected = []
    keys = sorted(groups)
    for position, key in enumerate(keys):
        quota = limit // len(keys) + int(position < limit % len(keys))
        cases = groups[key]
        indices = rng.choice(len(cases), size=min(quota, len(cases)), replace=False)
        selected.extend(cases[int(index)] for index in indices)
    correct = 0
    by_n = defaultdict(lambda: [0, 0])
    maximum = 0.0
    runtime.model.eval()
    with torch.no_grad():
        for start in range(0, len(selected), 16):
            batch = selected[start : start + 16]
            observations = torch.tensor([sample.observation for sample in batch], dtype=torch.float32)
            state = runtime.initial_state(len(batch), seed * 100000 + start)
            evolved = runtime.run(state, observations, steps, 0.5, mask_rng)
            maximum = max(maximum, float(evolved.abs().max()))
            predictions = runtime.readout(evolved).argmax(1).tolist()
            for sample, predicted in zip(batch, predictions):
                hit = int(predicted in sample.actions)
                correct += hit
                cell = by_n[sample.state.disk_count]
                cell[0] += hit
                cell[1] += 1
    return {
        "cases": len(selected),
        "correct": correct,
        "accuracy": correct / len(selected) if selected else None,
        "by_n": {str(n): {"correct": pair[0], "cases": pair[1], "accuracy": pair[0] / pair[1]} for n, pair in sorted(by_n.items())},
        "maximum_abs_state": maximum,
        "fresh_grid": True,
        "steps": steps,
        "fire_rate": 0.5,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "experiments/p05_v2")
    parser.add_argument("--seed", type=int, default=305)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--step-min", type=int, default=20)
    parser.add_argument("--step-max", type=int, default=24)
    parser.add_argument("--routing-iterations", type=int, default=80)
    parser.add_argument("--legality-iterations", type=int, default=80)
    parser.add_argument("--imitation-iterations", type=int, default=320)
    parser.add_argument("--teacher-sequence-iterations", type=int, default=80)
    parser.add_argument("--dagger-sequence-iterations", type=int, default=80)
    parser.add_argument("--sequence-decisions", type=int, default=3)
    parser.add_argument("--eval-cases-per-split", type=int, default=256)
    parser.add_argument("--eval-max-n", type=int, default=4)
    parser.add_argument("--soak-moves", type=int, default=510)
    args = parser.parse_args()
    if args.batch_size < 1 or args.step_min < 1 or args.step_max < args.step_min or args.sequence_decisions < 1:
        parser.error("batch size, step bounds, and sequence length must be positive")
    if not 1 <= args.eval_max_n <= 8:
        parser.error("eval-max-n must be in [1,8]")
    torch = require_torch()
    torch.set_num_threads(min(8, torch.get_num_threads()))
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    started = time.perf_counter()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    config = vars(args).copy()
    config["output"] = str(output.relative_to(ROOT))
    config["architecture"] = {
        "layout": str(LAYOUT_PATH.relative_to(ROOT)),
        "layout_sha256": sha256(LAYOUT_PATH),
        "channels": 8,
        "parameters": PARAMETER_COUNT,
        "state_bound": 5.0,
        "fire_rate": 0.5,
        "mask_predicate": "uniform <= fire_rate",
        "observation_injected_before_first_epoch": True,
    }
    write_json(output / "config.json", config)
    corpus = build_corpus()
    write_json(output / "partition_manifest.json", partition_manifest(corpus))
    strata = training_strata(corpus)
    model = build_v2_model(args.seed)
    runtime = TorchNCAV2Runtime(model)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.0005)
    curves = {}
    phases = (
        ("routing", args.routing_iterations),
        ("legality", args.legality_iterations),
        ("imitation", args.imitation_iterations),
        ("teacher_sequence", args.teacher_sequence_iterations),
        ("dagger_sequence", args.dagger_sequence_iterations),
    )
    for index, (phase, iterations) in enumerate(phases):
        if phase.endswith("_sequence"):
            curve = train_multi_decision(
                phase, runtime, optimizer, strata, iterations, args.batch_size,
                args.sequence_decisions, args.step_min, args.step_max,
                args.seed + 1000 * (index + 1),
            )
        else:
            curve = train_single_decision(
                phase, runtime, optimizer, strata, iterations, args.batch_size,
                args.step_min, args.step_max, args.seed + 1000 * (index + 1),
            )
        curves[phase] = curve
        checkpoint = output / f"after_{phase}.npz"
        save_checkpoint(model, checkpoint, {"schema": SCHEMA, "phase": phase, "config": config})
        print(json.dumps({"phase": phase, "iterations": iterations, "last": curve[-1] if curve else None}), flush=True)
    partitions = {name: [sample for sample in corpus if v2_split(sample) == name] for name in ("train", "validation", "test")}
    open_loop = {
        name: open_loop_metrics(runtime, samples, args.seed + 7000 + index, args.eval_cases_per_split, args.step_max)
        for index, (name, samples) in enumerate(partitions.items())
    }
    specs = [spec for spec in episode_specs() if spec.reset_mode == "standard" and spec.disk_count <= args.eval_max_n]
    records = evaluate_nca(runtime, specs, args.step_min, args.step_max, args.seed + 8000, True)
    write_json(output / "episode_records.json", records)
    # The soak varies legal observations while retaining one NCA grid; it measures
    # state range, not policy competence or Hanoi environment outcomes.
    from training.hanoi_nca.hypothesis_a import MixedStepSchedule
    from training.hanoi_nca.run_hypothesis_a import worst_case_stability_soak
    soak = worst_case_stability_soak(
        runtime, MixedStepSchedule(args.step_min, args.step_max, args.step_min, args.step_max, 1),
        0.5, args.seed + 9000, moves=args.soak_moves, bound=5.0,
    )
    result = {
        "schema": SCHEMA,
        "status": "completed_experiment_not_model_freeze",
        "config": config,
        "environment": {"python": platform.python_version(), "numpy": np.__version__, "torch": torch.__version__},
        "runtime_seconds": time.perf_counter() - started,
        "curves": curves,
        "open_loop": open_loop,
        "closed_loop": summarize_episodes(records),
        "stability_soak": soak,
        "checkpoints": {
            phase: {
                "path": str((output / f"after_{phase}.npz").relative_to(ROOT)),
                "sha256": sha256(output / f"after_{phase}.npz"),
            }
            for phase, _ in phases
        },
        "functional_freeze_eligible": False,
        "claim": "bounded P05 v2 experimental candidate only; no shortest-path or robust-control claim",
    }
    write_json(output / "results.json", result)
    print(json.dumps({"result": str(output / "results.json"), "closed_loop": result["closed_loop"], "open_loop": open_loop}, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
