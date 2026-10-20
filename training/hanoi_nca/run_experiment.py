#!/usr/bin/env python3
"""Run the bounded P05 learnability experiment and emit reproducible evidence."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import platform
from pathlib import Path
import random
import sys
import time
import copy

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.hanoi.environment import HanoiEnv, HanoiState, encode_observation, transition
from reference.hanoi.oracle import encode_locations, optimal_actions, reverse_graph_distances
from training.hanoi_nca.control import build_control, save_control
from training.hanoi_nca.dataset import Sample, build_corpus, manifest, supervised_arrays
from training.hanoi_nca.layout import layout_statistics, load_layout
from training.hanoi_nca.model import build_model, require_torch, save_checkpoint
from training.hanoi_nca.runtime import TorchNCARuntime


@dataclass(frozen=True)
class EpisodeSpec:
    disk_count: int
    goal_peg: int
    reset_mode: str
    seed: int
    locations: tuple[int, ...] | None = None
    standard_source: int | None = None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def target_loss(logits, targets):
    torch = require_torch()
    return -(targets * torch.log_softmax(logits, dim=1)).sum(dim=1).mean()


def classification_metrics(model, corpus: list[Sample]) -> dict[str, dict[str, float | int]]:
    torch = require_torch()
    model.eval()
    by_split: dict[str, list[Sample]] = defaultdict(list)
    for sample in corpus:
        if sample.actions:
            by_split[sample.split].append(sample)
    results: dict[str, dict[str, float | int]] = {}
    with torch.no_grad():
        for split, samples in sorted(by_split.items()):
            observations = torch.tensor([sample.observation for sample in samples], dtype=torch.float32)
            predictions = model(observations).argmax(dim=1).cpu().numpy()
            correct = sum(int(prediction in sample.actions) for prediction, sample in zip(predictions, samples, strict=True))
            results[split] = {"cases": len(samples), "accuracy": correct / len(samples)}
    return results


def nca_classification_metrics(
    runtime: TorchNCARuntime,
    corpus: list[Sample],
    step_min: int,
    step_max: int,
    seed: int,
    fire_rate: float,
    maximum_cases_per_split: int = 512,
) -> dict[str, dict[str, float | int | bool]]:
    """Measure open-loop action accuracy on deterministic hash-selected cases."""
    torch = require_torch()
    rng = np.random.RandomState(seed)
    generator = torch.Generator().manual_seed(seed)
    by_split: dict[str, list[Sample]] = defaultdict(list)
    for sample in corpus:
        if sample.actions:
            by_split[sample.split].append(sample)
    output: dict[str, dict[str, float | int | bool]] = {}
    runtime.model.eval()
    with torch.no_grad():
        for split, all_samples in sorted(by_split.items()):
            samples = sorted(all_samples, key=lambda sample: sample.state_hash)[:maximum_cases_per_split]
            correct = 0
            for start in range(0, len(samples), 16):
                batch = samples[start : start + 16]
                observations = torch.tensor([sample.observation for sample in batch], dtype=torch.float32)
                state = runtime.initial_state(len(batch), seed * 100000 + start)
                steps = int(rng.randint(step_min, step_max + 1))
                state = runtime.run(state, observations, steps, fire_rate, generator)
                predictions = runtime.readout(state).argmax(dim=1).cpu().numpy()
                correct += sum(
                    int(prediction in sample.actions)
                    for prediction, sample in zip(predictions, batch, strict=True)
                )
            output[split] = {
                "cases": len(samples),
                "available_cases": len(all_samples),
                "hash_selected_subset": len(samples) < len(all_samples),
                "accuracy": correct / len(samples),
            }
    return output


def train_control(corpus: list[Sample], seed: int, epochs: int) -> tuple[object, dict[str, object]]:
    torch = require_torch()
    torch.manual_seed(seed)
    np.random.seed(seed)
    model = build_control(seed)
    observations, targets, _ = supervised_arrays(corpus, "train")
    x = torch.from_numpy(observations)
    y = torch.from_numpy(targets)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.002)
    generator = torch.Generator().manual_seed(seed)
    curve: list[dict[str, float | int]] = []
    batch_size = 256
    for epoch in range(epochs):
        permutation = torch.randperm(len(x), generator=generator)
        total = 0.0
        for start in range(0, len(x), batch_size):
            indices = permutation[start : start + batch_size]
            optimizer.zero_grad(set_to_none=True)
            loss = target_loss(model(x[indices]), y[indices])
            loss.backward()
            optimizer.step()
            total += float(loss.detach()) * len(indices)
        curve.append({"epoch": epoch, "loss": total / len(x)})
    return model, {"curve": curve, "classification": classification_metrics(model, corpus)}


def curriculum_projection() -> np.ndarray:
    rng = np.random.RandomState(3105)
    projection = rng.choice((-1.0, 1.0), size=(36, 6)).astype(np.float32)
    projection /= np.sqrt(np.float32(36.0))
    return projection


def train_nca(
    corpus: list[Sample],
    seed: int,
    curriculum_iterations: int,
    imitation_iterations: int,
    step_min: int,
    step_max: int,
    batch_size: int,
    output_hidden_policy: str,
    fire_rate: float = 0.5,
    progressive_n: bool = True,
) -> tuple[object, TorchNCARuntime, dict[str, object]]:
    torch = require_torch()
    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)
    model = build_model(seed)
    runtime = TorchNCARuntime(model, output_hidden_policy)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    rng = np.random.RandomState(seed)
    generator = torch.Generator().manual_seed(seed)
    projection_np = curriculum_projection()
    projection = torch.from_numpy(projection_np)
    curves: dict[str, list[dict[str, float | int]]] = {"signal_curriculum": [], "supervised_imitation": []}

    for iteration in range(curriculum_iterations):
        observations = torch.from_numpy(rng.uniform(-1.0, 1.0, (batch_size, 36)).astype(np.float32))
        target = torch.tanh(observations @ projection)
        state = runtime.initial_state(batch_size, seed * 100000 + iteration)
        steps = int(rng.randint(step_min, step_max + 1))
        optimizer.zero_grad(set_to_none=True)
        state = runtime.run(state, observations, steps, fire_rate=fire_rate, generator=generator)
        scores = runtime.readout(state)
        loss = torch.mean((scores - target) ** 2)
        loss.backward()
        gradient_norm = float(torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0))
        optimizer.step()
        curves["signal_curriculum"].append(
            {"iteration": iteration, "loss": float(loss.detach()), "steps": steps, "gradient_norm": gradient_norm}
        )

    train_samples = [sample for sample in corpus if sample.split == "train" and sample.actions]
    train_by_n = {
        disk_count: [sample for sample in train_samples if sample.state.disk_count == disk_count]
        for disk_count in sorted({sample.state.disk_count for sample in train_samples})
    }
    for iteration in range(imitation_iterations):
        maximum_n = min(6, 1 + (6 * iteration // max(1, imitation_iterations))) if progressive_n else 6
        eligible_n = [disk_count for disk_count in train_by_n if disk_count <= maximum_n]
        chosen = []
        for _ in range(batch_size):
            disk_count = eligible_n[int(rng.randint(0, len(eligible_n)))]
            bucket = train_by_n[disk_count]
            chosen.append(bucket[int(rng.randint(0, len(bucket)))])
        observations = torch.tensor([sample.observation for sample in chosen], dtype=torch.float32)
        targets = torch.zeros((batch_size, 6), dtype=torch.float32)
        for row, sample in enumerate(chosen):
            targets[row, list(sample.actions)] = 1.0 / len(sample.actions)
        state = runtime.initial_state(batch_size, seed * 200000 + iteration)
        steps = int(rng.randint(step_min, step_max + 1))
        optimizer.zero_grad(set_to_none=True)
        state = runtime.run(state, observations, steps, fire_rate=fire_rate, generator=generator)
        scores = runtime.readout(state)
        loss = target_loss(scores, targets)
        loss.backward()
        gradient_norm = float(torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0))
        optimizer.step()
        curves["supervised_imitation"].append(
            {
                "iteration": iteration,
                "loss": float(loss.detach()),
                "steps": steps,
                "gradient_norm": gradient_norm,
                "maximum_n": maximum_n,
            }
        )

    return model, runtime, {
        "curves": curves,
        "projection_sha256": hashlib.sha256(projection_np.tobytes()).hexdigest(),
        "pooling": "fresh independently sampled grid per supervised batch",
        "fire_rate": fire_rate,
        "disk_count_curriculum": (
            "progressive n<=1 through n<=6 with disk-count-balanced sampling"
            if progressive_n
            else "all available n with disk-count-balanced sampling"
        ),
    }


def episode_specs() -> list[EpisodeSpec]:
    specs: list[EpisodeSpec] = []
    for disk_count in range(1, 9):
        for goal in range(3):
            specs.append(EpisodeSpec(disk_count, goal, "seeded", seed=5000 + 100 * disk_count + goal))
            source = (goal + 1) % 3
            specs.append(EpisodeSpec(disk_count, goal, "standard", seed=0, standard_source=source))
            locations = tuple((disk + goal + disk_count) % 3 for disk in range(disk_count))
            specs.append(EpisodeSpec(disk_count, goal, "explicit", seed=0, locations=locations))
    return specs


def reset_episode(env: HanoiEnv, spec: EpisodeSpec) -> HanoiState:
    if spec.reset_mode == "seeded":
        return env.reset(seed=spec.seed)
    if spec.reset_mode == "standard":
        return env.reset(seed=spec.seed, standard_source=spec.standard_source)
    return env.reset(seed=spec.seed, initial_locations=spec.locations)


def budget_for(disk_count: int, multiplier: float = 2.0) -> int:
    return math.ceil(multiplier * ((1 << disk_count) - 1))


def evaluate_control(model, specs: list[EpisodeSpec]) -> list[dict[str, object]]:
    torch = require_torch()
    model.eval()
    records = []
    with torch.no_grad():
        for spec in specs:
            env = HanoiEnv(spec.disk_count, spec.goal_peg, budget_for(spec.disk_count))
            initial = reset_episode(env, spec)
            initial_snapshot_hash = env.snapshot_hash
            initial_distance = reverse_graph_distances(spec.disk_count, spec.goal_peg)[encode_locations(initial.locations)]
            illegal = 0
            margins: list[float] = []
            while not env.terminated and not env.truncated:
                observation = torch.tensor([encode_observation(env.state)], dtype=torch.float32)
                scores = model(observation)[0]
                top = torch.topk(scores, 2).values
                margins.append(float(top[0] - top[1]))
                result = env.step(int(scores.argmax()))
                illegal += int(not result.legal)
            records.append(
                episode_record(spec, env, initial, initial_snapshot_hash, initial_distance, illegal, margins, "conventional", "none")
            )
    return records


def evaluate_nca(
    runtime: TorchNCARuntime,
    specs: list[EpisodeSpec],
    step_min: int,
    step_max: int,
    seed: int,
    persistent: bool,
) -> list[dict[str, object]]:
    torch = require_torch()
    runtime.model.eval()
    rng = np.random.RandomState(seed)
    generator = torch.Generator().manual_seed(seed)
    records = []
    with torch.no_grad():
        for episode_index, spec in enumerate(specs):
            env = HanoiEnv(spec.disk_count, spec.goal_peg, budget_for(spec.disk_count))
            initial = reset_episode(env, spec)
            initial_snapshot_hash = env.snapshot_hash
            initial_distance = reverse_graph_distances(spec.disk_count, spec.goal_peg)[encode_locations(initial.locations)]
            state = runtime.initial_state(1, seed * 1000 + episode_index)
            illegal = 0
            margins: list[float] = []
            while not env.terminated and not env.truncated:
                if not persistent:
                    state = runtime.initial_state(1, seed * 100000 + episode_index * 1000 + env.moves_taken)
                observations = torch.tensor([encode_observation(env.state)], dtype=torch.float32)
                steps = int(rng.randint(step_min, step_max + 1))
                state = runtime.run(state, observations, steps, fire_rate=0.5, generator=generator)
                scores = runtime.readout(state)[0]
                top = torch.topk(scores, 2).values
                margins.append(float(top[0] - top[1]))
                result = env.step(int(scores.argmax()))
                illegal += int(not result.legal)
            records.append(
                episode_record(
                    spec,
                    env,
                    initial,
                    initial_snapshot_hash,
                    initial_distance,
                    illegal,
                    margins,
                    "nca",
                    "coherent_persistent" if persistent else "independent_grid_per_move",
                )
            )
    return records


def episode_record(
    spec: EpisodeSpec,
    env: HanoiEnv,
    initial: HanoiState,
    initial_snapshot_hash: str,
    initial_distance: int,
    illegal: int,
    margins: list[float],
    controller: str,
    pairing: str,
) -> dict[str, object]:
    return {
        "controller": controller,
        "pairing": pairing,
        "n": spec.disk_count,
        "goal": spec.goal_peg,
        "reset_mode": spec.reset_mode,
        "seed": spec.seed,
        "initial_state_hash": initial.state_hash,
        "initial_snapshot_hash": initial_snapshot_hash,
        "initial_distance": initial_distance,
        "budget": env.move_budget,
        "moves": env.moves_taken,
        "illegal_attempts": illegal,
        "legal_attempts": env.moves_taken - illegal,
        "terminated": env.terminated,
        "truncated": env.truncated,
        "failure_class": "none" if env.terminated else ("illegal_action_budget_exhaustion" if illegal == env.move_budget else "move_budget_truncation"),
        "excess_moves": env.moves_taken - initial_distance if env.terminated else None,
        "mean_action_margin": sum(margins) / len(margins) if margins else None,
        "final_snapshot_hash": env.snapshot_hash,
    }


def dagger(
    runtime: TorchNCARuntime,
    corpus: list[Sample],
    specs: list[EpisodeSpec],
    seed: int,
    step_min: int,
    step_max: int,
    iterations: int,
    batch_size: int,
) -> dict[str, object]:
    torch = require_torch()
    rng = np.random.RandomState(seed)
    generator = torch.Generator().manual_seed(seed)
    visited: list[tuple[tuple[float, ...], tuple[int, ...], str, object]] = []
    numerical_failures: list[dict[str, object]] = []
    finite_model_state = copy.deepcopy(runtime.model.state_dict())
    runtime.model.eval()
    with torch.no_grad():
        for episode_index, spec in enumerate(specs):
            env = HanoiEnv(spec.disk_count, spec.goal_peg, budget_for(spec.disk_count))
            reset_episode(env, spec)
            state = runtime.initial_state(1, seed * 1000 + episode_index)
            while not env.terminated and not env.truncated:
                observation_tuple = encode_observation(env.state)
                pre_observation_state = state.detach().clone()
                observations = torch.tensor([observation_tuple], dtype=torch.float32)
                steps = int(rng.randint(step_min, step_max + 1))
                state = runtime.run(state, observations, steps, fire_rate=0.5, generator=generator)
                if not bool(torch.isfinite(state).all()):
                    numerical_failures.append(
                        {
                            "phase": "trajectory_collection",
                            "episode_index": episode_index,
                            "moves_taken": env.moves_taken,
                            "state_hash": env.state.state_hash,
                        }
                    )
                    break
                visited.append(
                    (observation_tuple, optimal_actions(env.state), env.state.state_hash, pre_observation_state)
                )
                env.step(int(runtime.readout(state)[0].argmax()))

    optimizer = torch.optim.Adam(runtime.model.parameters(), lr=0.0005)
    curve = []
    aborted = False
    runtime.model.train()
    for iteration in range(iterations):
        chosen = [visited[index] for index in rng.randint(0, len(visited), size=batch_size)]
        observations = torch.tensor([item[0] for item in chosen], dtype=torch.float32)
        targets = torch.zeros((batch_size, 6), dtype=torch.float32)
        for row, (_, actions, _, _) in enumerate(chosen):
            targets[row, list(actions)] = 1.0 / len(actions)
        state = torch.cat([item[3] for item in chosen], dim=0)
        steps = int(rng.randint(step_min, step_max + 1))
        optimizer.zero_grad(set_to_none=True)
        state = runtime.run(state, observations, steps, fire_rate=0.5, generator=generator)
        loss = target_loss(runtime.readout(state), targets)
        if not bool(torch.isfinite(loss)):
            numerical_failures.append(
                {"phase": "optimization", "iteration": iteration, "reason": "non-finite loss"}
            )
            aborted = True
            runtime.model.load_state_dict(finite_model_state)
            break
        loss.backward()
        gradient_norm = float(torch.nn.utils.clip_grad_norm_(runtime.model.parameters(), 1.0))
        if not math.isfinite(gradient_norm):
            numerical_failures.append(
                {"phase": "optimization", "iteration": iteration, "reason": "non-finite gradient"}
            )
            aborted = True
            runtime.model.load_state_dict(finite_model_state)
            break
        optimizer.step()
        finite_model_state = copy.deepcopy(runtime.model.state_dict())
        curve.append({"iteration": iteration, "loss": float(loss.detach()), "steps": steps, "gradient_norm": gradient_norm})
    return {
        "curve": curve,
        "visited_samples": len(visited),
        "unique_state_hashes": len({item[2] for item in visited}),
        "pairing": "coherent (Hanoi snapshot, persistent NCA grid)",
        "optimization_initial_state": "captured persistent pre-observation NCA grid from the paired trajectory",
        "status": "aborted_and_rolled_back" if aborted else "completed",
        "numerical_failures": numerical_failures,
    }


def summarize_episodes(records: list[dict[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {
        "episodes": len(records),
        "completed": sum(bool(record["terminated"]) for record in records),
        "truncated": sum(bool(record["truncated"]) for record in records),
        "legal_attempts": sum(int(record["legal_attempts"]) for record in records),
        "illegal_attempts": sum(int(record["illegal_attempts"]) for record in records),
    }
    by_stratum: dict[str, Counter] = defaultdict(Counter)
    for record in records:
        key = f"n={record['n']}|goal={record['goal']}|distance={record['initial_distance']}|reset={record['reset_mode']}"
        by_stratum[key]["episodes"] += 1
        by_stratum[key]["completed"] += int(bool(record["terminated"]))
        by_stratum[key]["truncated"] += int(bool(record["truncated"]))
        by_stratum[key]["illegal_attempts"] += int(record["illegal_attempts"])
    result["by_stratum"] = {key: dict(value) for key, value in sorted(by_stratum.items())}
    return result


def budget_analysis(corpus: list[Sample]) -> dict[str, object]:
    policies = {
        "n": lambda n: n,
        "half_standard": lambda n: 1 << (n - 1),
        "standard_max": lambda n: (1 << n) - 1,
        "double_standard": lambda n: 2 * ((1 << n) - 1),
    }
    output: dict[str, object] = {}
    for name, function in policies.items():
        by_n = {}
        for n in range(1, 9):
            cases = [sample for sample in corpus if sample.state.disk_count == n]
            budget = function(n)
            unsolvable = sum(sample.distance > budget for sample in cases)
            by_n[str(n)] = {"budget": budget, "cases": len(cases), "distance_exceeds_budget": unsolvable}
        output[name] = by_n
    return output


def marker_range_probe(seed: int, steps: int = 59) -> dict[str, object]:
    torch = require_torch()
    observations = torch.zeros((1, 36), dtype=torch.float32)
    output = {}
    for policy in ("accumulate", "clamp_one"):
        model = build_model(seed)
        runtime = TorchNCARuntime(model, policy)
        state = runtime.initial_state(1, seed)
        generator = torch.Generator().manual_seed(seed)
        with torch.no_grad():
            state = runtime.run(state, observations, steps, 0.5, generator)
        layout = load_layout()
        hidden = torch.stack([state[0, 4:6, row, column] for row, column in layout.output_coordinates])
        output[policy] = {
            "output_hidden_min": float(hidden.min()),
            "output_hidden_max": float(hidden.max()),
            "whole_state_max_abs": float(state.abs().max()),
        }
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "experiments/p05")
    parser.add_argument("--seed", type=int, default=105)
    parser.add_argument("--control-epochs", type=int, default=30)
    parser.add_argument("--curriculum-iterations", type=int, default=30)
    parser.add_argument("--imitation-iterations", type=int, default=100)
    parser.add_argument("--dagger-iterations", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--step-min", type=int, default=8)
    parser.add_argument("--step-max", type=int, default=12)
    parser.add_argument("--output-hidden-policy", choices=("accumulate", "clamp_one"), default="accumulate")
    parser.add_argument("--supervised-fire-rate", type=float, default=0.5)
    args = parser.parse_args()
    torch = require_torch()
    torch.set_num_threads(min(8, torch.get_num_threads()))
    start = time.perf_counter()
    args.output.mkdir(parents=True, exist_ok=True)

    corpus = build_corpus()
    dataset_manifest = manifest(corpus)
    dataset_path = args.output / "dataset_manifest.json"
    dataset_path.write_text(json.dumps(dataset_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    control, control_training = train_control(corpus, args.seed, args.control_epochs)
    control_path = args.output / "conventional_control.npz"
    save_control(control, control_path)

    nca, runtime, nca_training = train_nca(
        corpus,
        args.seed,
        args.curriculum_iterations,
        args.imitation_iterations,
        args.step_min,
        args.step_max,
        args.batch_size,
        args.output_hidden_policy,
        args.supervised_fire_rate,
        True,
    )
    specs = episode_specs()
    dagger_specs = [spec for spec in specs if spec.disk_count <= 6 and spec.reset_mode == "seeded"]
    dagger_result = dagger(
        runtime,
        corpus,
        dagger_specs,
        args.seed + 1,
        args.step_min,
        args.step_max,
        args.dagger_iterations,
        args.batch_size,
    )

    control_records = evaluate_control(control, specs)
    coherent_records = evaluate_nca(runtime, specs, args.step_min, args.step_max, args.seed + 2, True)
    independent_records = evaluate_nca(runtime, specs, args.step_min, args.step_max, args.seed + 2, False)
    episode_path = args.output / "episode_records.json"
    episode_path.write_text(
        json.dumps(
            {
                "specs": [asdict(spec) for spec in specs],
                "conventional": control_records,
                "nca_coherent": coherent_records,
                "nca_independent": independent_records,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    candidate_path = args.output / "g3_candidate_nca.npz"
    save_checkpoint(
        nca,
        candidate_path,
        {
            "status": "candidate_not_frozen",
            "seed": args.seed,
            "steps": [args.step_min, args.step_max],
            "supervised_fire_rate": args.supervised_fire_rate,
            "dagger_and_evaluation_fire_rate": 0.5,
            "output_hidden_policy": args.output_hidden_policy,
        },
    )
    environment = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
        "torch": torch.__version__,
        "torch_threads": torch.get_num_threads(),
    }
    results = {
        "schema": "clef.p05.experiment.v1",
        "status": "measured_g3_candidate_not_frozen",
        "config": vars(args) | {"output": str(args.output.resolve().relative_to(ROOT))},
        "environment": environment,
        "runtime_seconds": time.perf_counter() - start,
        "dataset_manifest_sha256": sha256(dataset_path),
        "layout_statistics": layout_statistics(load_layout()),
        "budget_analysis": budget_analysis(corpus),
        "marker_policy_probe_59_steps": marker_range_probe(args.seed),
        "conventional_training": control_training,
        "nca_training": nca_training,
        "nca_open_loop_classification": nca_classification_metrics(
            runtime,
            corpus,
            args.step_min,
            args.step_max,
            args.seed + 3,
            0.5,
        ),
        "dagger": dagger_result,
        "episode_summaries": {
            "conventional": summarize_episodes(control_records),
            "nca_coherent": summarize_episodes(coherent_records),
            "nca_independent": summarize_episodes(independent_records),
        },
        "artifacts": {
            "candidate_nca": {"path": str(candidate_path.resolve().relative_to(ROOT)), "sha256": sha256(candidate_path)},
            "conventional_control": {"path": str(control_path.resolve().relative_to(ROOT)), "sha256": sha256(control_path)},
            "episode_records": {"path": str(episode_path.resolve().relative_to(ROOT)), "sha256": sha256(episode_path)},
        },
        "rl_fine_tuning": {"attempted": False, "reason": "optional; reward policy is intentionally deferred to G3"},
    }
    result_path = args.output / "results.json"
    result_path.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"result": str(result_path), "runtime_seconds": results["runtime_seconds"], "summaries": results["episode_summaries"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
