#!/usr/bin/env python3
"""Run and checkpoint the P05 Hypothesis-A stabilization experiment."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import platform
from pathlib import Path
import random
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.hanoi.environment import HanoiEnv, HanoiState, encode_observation
from reference.hanoi.oracle import optimal_actions
from training.hanoi_nca.dataset import build_corpus
from training.hanoi_nca.hypothesis_a import (
    AUX_SCHEMA,
    MixedStepSchedule,
    auxiliary_loss,
    auxiliary_metrics,
    auxiliary_targets,
    build_auxiliary_heads,
    make_environment,
    permute_state,
    representation,
    standard_states,
    state_stability_penalty,
    state_statistics,
)
from training.hanoi_nca.model import build_model, require_torch
from training.hanoi_nca.runtime import TorchNCARuntime
from training.hanoi_nca.run_experiment import episode_specs, evaluate_nca, summarize_episodes, target_loss


SCHEMA = "clef.p05.hypothesis-a.v1"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def save_resume(path: Path, model, heads, optimizer, phase: str, config: dict[str, object], curves: dict[str, object]) -> None:
    torch = require_torch()
    payload = {
        "schema": SCHEMA,
        "phase": phase,
        "config": config,
        "model": model.state_dict(),
        "heads": heads.state_dict(),
        "optimizer": optimizer.state_dict(),
        "torch_rng": torch.get_rng_state(),
        "numpy_rng": np.random.get_state(),
        "python_rng": random.getstate(),
        "curves": curves,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(payload, path)


def load_resume(path: Path, model, heads, optimizer):
    torch = require_torch()
    payload = torch.load(path, map_location="cpu", weights_only=False)
    if payload["schema"] != SCHEMA:
        raise ValueError("resume schema mismatch")
    model.load_state_dict(payload["model"])
    heads.load_state_dict(payload["heads"])
    optimizer.load_state_dict(payload["optimizer"])
    torch.set_rng_state(payload["torch_rng"])
    np.random.set_state(payload["numpy_rng"])
    random.setstate(payload["python_rng"])
    return payload


class CoherentPool:
    def __init__(self, runtime, states: list[HanoiState], size: int, seed: int) -> None:
        self.runtime = runtime
        self.states = states
        self.rng = np.random.RandomState(seed)
        self.cursor = 0
        self.envs: list[HanoiEnv] = []
        self.grids = runtime.initial_state(size, seed)
        self.resets = 0
        for slot in range(size):
            self.envs.append(self._new_env(slot))

    def _new_env(self, slot: int) -> HanoiEnv:
        source = self.states[self.cursor % len(self.states)]
        self.cursor += 1
        permutation = tuple(int(x) for x in self.rng.permutation(3))
        state = permute_state(source, permutation)
        budget = 2 * ((1 << state.disk_count) - 1)
        if hasattr(self, "grids"):
            self.grids[slot : slot + 1] = self.runtime.initial_state(1, 900000 + self.resets)
        self.resets += 1
        return make_environment(state, budget)

    def batch(self):
        states = [env.state for env in self.envs]
        observations = np.asarray([encode_observation(state) for state in states], dtype=np.float32)
        targets = np.zeros((len(states), 6), dtype=np.float32)
        for row, state in enumerate(states):
            actions = optimal_actions(state)
            targets[row, list(actions)] = 1.0 / len(actions)
        return states, observations, targets

    def advance(self, actions: list[int]) -> None:
        for slot, action in enumerate(actions):
            env = self.envs[slot]
            env.step(action)
            if env.terminated or env.truncated:
                self.envs[slot] = self._new_env(slot)


def train_phase(
    name: str,
    runtime,
    heads,
    optimizer,
    states: list[HanoiState],
    iterations: int,
    batch_size: int,
    schedule: MixedStepSchedule,
    fire_rate: float,
    seed: int,
    on_policy: bool,
    overflow_weight: float,
    stability_limit: float,
) -> dict[str, object]:
    torch = require_torch()
    pool = CoherentPool(runtime, states, batch_size, seed)
    rng = np.random.RandomState(seed + 1)
    generator = torch.Generator().manual_seed(seed + 2)
    curve = []
    finite_snapshot = (copy.deepcopy(runtime.model.state_dict()), copy.deepcopy(heads.state_dict()))
    abort_reason = None
    stability_rejections = 0
    for iteration in range(iterations):
        logical_states, observations_np, targets_np = pool.batch()
        observations = torch.from_numpy(observations_np)
        targets = torch.from_numpy(targets_np)
        steps, schedule_class = schedule.draw(iteration, rng)
        optimizer.zero_grad(set_to_none=True)
        evolved = runtime.run(pool.grids, observations, steps, fire_rate, generator)
        stats = state_statistics(evolved)
        if not stats["finite"]:
            abort_reason = f"non-finite state at iteration {iteration}"
            runtime.model.load_state_dict(finite_snapshot[0])
            heads.load_state_dict(finite_snapshot[1])
            break
        if float(stats["max_abs"]) > stability_limit:
            # The state is used only to compute a corrective overflow gradient;
            # it is never accepted as the persistent state or used for action.
            stability = state_stability_penalty(evolved)
            corrective_loss = overflow_weight * stability
            corrective_loss.backward()
            gradient_norm = float(torch.nn.utils.clip_grad_norm_(runtime.model.parameters(), 1.0))
            if not math.isfinite(gradient_norm):
                abort_reason = f"non-finite corrective gradient at iteration {iteration}"
                runtime.model.load_state_dict(finite_snapshot[0])
                heads.load_state_dict(finite_snapshot[1])
                break
            optimizer.step()
            finite_snapshot = (copy.deepcopy(runtime.model.state_dict()), copy.deepcopy(heads.state_dict()))
            stability_rejections += 1
            pool.grids = runtime.initial_state(len(pool.envs), seed * 100000 + iteration)
            entry = {
                "iteration": iteration,
                "stability_rejected": True,
                "overflow_penalty": float(stability.detach()),
                "gradient_norm": gradient_norm,
                "steps": steps,
                "schedule_class": schedule_class,
                **stats,
            }
            curve.append(entry)
            print(json.dumps({"phase": name, **entry}), flush=True)
            continue
        scores = runtime.readout(evolved)
        action_loss = target_loss(scores, targets)
        aux_loss, aux_parts = auxiliary_loss(heads, representation(runtime, evolved), auxiliary_targets(logical_states))
        stability = state_stability_penalty(evolved)
        loss = action_loss + 0.25 * aux_loss + overflow_weight * stability
        if not bool(torch.isfinite(loss)):
            abort_reason = f"non-finite loss at iteration {iteration}"
            break
        loss.backward()
        gradient_norm = float(torch.nn.utils.clip_grad_norm_(
            list(runtime.model.parameters()) + list(heads.parameters()), 1.0
        ))
        if not math.isfinite(gradient_norm):
            abort_reason = f"non-finite gradient at iteration {iteration}"
            runtime.model.load_state_dict(finite_snapshot[0])
            heads.load_state_dict(finite_snapshot[1])
            break
        optimizer.step()
        finite_snapshot = (copy.deepcopy(runtime.model.state_dict()), copy.deepcopy(heads.state_dict()))
        pool.grids = evolved.detach()
        if on_policy:
            actions = scores.detach().argmax(1).tolist()
        else:
            actions = [int(np.flatnonzero(row)[0]) for row in targets_np]
        pool.advance(actions)
        if iteration % max(1, iterations // 20) == 0 or iteration == iterations - 1:
            entry = {
                "iteration": iteration,
                "loss": float(loss.detach()),
                "action_loss": float(action_loss.detach()),
                "auxiliary_loss": float(aux_loss.detach()),
                "overflow_penalty": float(stability.detach()),
                "gradient_norm": gradient_norm,
                "steps": steps,
                "schedule_class": schedule_class,
                "stability_rejected": False,
                **stats,
                **{f"aux_{key}": float(value.detach()) for key, value in aux_parts.items()},
            }
            curve.append(entry)
            print(json.dumps({"phase": name, **entry}), flush=True)
    return {
        "name": name,
        "iterations_requested": iterations,
        "iterations_completed": iteration + 1 if iterations else 0,
        "on_policy": on_policy,
        "pool_resets": pool.resets,
        "stability_limit": stability_limit,
        "stability_rejections": stability_rejections,
        "abort_reason": abort_reason,
        "curve": curve,
    }


def collect_representations(runtime, states: list[HanoiState], schedule: MixedStepSchedule, fire_rate: float, seed: int):
    torch = require_torch()
    runtime.model.eval()
    rng = np.random.RandomState(seed)
    generator = torch.Generator().manual_seed(seed + 1)
    features = []
    with torch.no_grad():
        for start in range(0, len(states), 32):
            batch = states[start : start + 32]
            observations = torch.tensor([encode_observation(state) for state in batch], dtype=torch.float32)
            grid = runtime.initial_state(len(batch), seed * 1000 + start)
            steps, _ = schedule.draw(start // 32, rng)
            grid = runtime.run(grid, observations, steps, fire_rate, generator)
            features.append(representation(runtime, grid).cpu())
    return torch.cat(features), auxiliary_targets(states)


def independent_probe(runtime, train_states: list[HanoiState], test_states: list[HanoiState], schedule, fire_rate, seed, epochs=100):
    torch = require_torch()
    train_x, train_y = collect_representations(runtime, train_states, schedule, fire_rate, seed)
    test_x, test_y = collect_representations(runtime, test_states, schedule, fire_rate, seed + 100)
    heads = build_auxiliary_heads(seed + 200)
    optimizer = torch.optim.Adam(heads.parameters(), lr=0.01)
    for _ in range(epochs):
        optimizer.zero_grad(set_to_none=True)
        loss, _ = auxiliary_loss(heads, train_x, train_y)
        loss.backward()
        optimizer.step()
    def majority_baselines(train_targets, test_targets):
        legality_choice = (train_targets["legality"].mean(axis=0) >= 0.5).astype(np.float32)
        legality = float((test_targets["legality"] == legality_choice[None, :]).mean())
        top = np.stack([
            np.bincount(train_targets["top_disks"][:, peg], minlength=9).argmax()
            == test_targets["top_disks"][:, peg]
            for peg in range(3)
        ], axis=1).mean()
        roles = np.stack([
            np.bincount(train_targets["peg_roles"][:, peg], minlength=3).argmax()
            == test_targets["peg_roles"][:, peg]
            for peg in range(3)
        ], axis=1).mean()
        subgoal_choice = np.bincount(train_targets["subgoal_disk"], minlength=9).argmax()
        subgoal = float((test_targets["subgoal_disk"] == subgoal_choice).mean())
        return {
            "legality_bit_accuracy": legality,
            "top_disk_accuracy": float(top),
            "peg_role_accuracy": float(roles),
            "subgoal_disk_accuracy": subgoal,
        }

    return {
        "feature_boundary": "all six channels at the six output cells only",
        "train_cases": len(train_states),
        "test_cases": len(test_states),
        "train": auxiliary_metrics(heads, train_x, train_y),
        "test": auxiliary_metrics(heads, test_x, test_y),
        "test_majority_baseline": majority_baselines(train_y, test_y),
    }


def diagnostic_episode_specs(max_n: int = 8):
    """All standard transfers through n=6 plus one standard n=7 and n=8."""
    return [
        spec for spec in episode_specs()
        if spec.reset_mode == "standard"
        and spec.disk_count <= max_n
        and (spec.disk_count <= 6 or spec.goal_peg == 0)
    ]


def worst_case_stability_soak(runtime, schedule, fire_rate: float, seed: int, moves: int = 510, bound: float = 10.0):
    """Persist one grid for the double-standard n=8 budget without clipping."""
    torch = require_torch()
    rng = np.random.RandomState(seed)
    generator = torch.Generator().manual_seed(seed + 1)
    observations = [
        encode_observation(HanoiState(tuple((disk + offset) % 3 for disk in range(8)), offset % 3))
        for offset in range(3)
    ]
    grid = runtime.initial_state(1, seed)
    maximum = 0.0
    first_bound_exceedance = None
    checkpoints = []
    runtime.model.eval()
    with torch.no_grad():
        for move in range(moves):
            observation = torch.tensor([observations[move % len(observations)]], dtype=torch.float32)
            steps, schedule_class = schedule.draw(move, rng)
            grid = runtime.run(grid, observation, steps, fire_rate, generator)
            stats = state_statistics(grid)
            maximum = max(maximum, float(stats["max_abs"]))
            if float(stats["max_abs"]) > bound and first_bound_exceedance is None:
                first_bound_exceedance = move + 1
            if not stats["finite"]:
                return {"moves_requested": moves, "moves_completed": move + 1, "finite": False, "bounded": False, "bound": bound, "maximum_abs": maximum, "failure_move": move + 1}
            if move % 50 == 49 or move == moves - 1:
                checkpoints.append({"move": move + 1, "steps": steps, "schedule_class": schedule_class, **stats})
    return {"moves_requested": moves, "moves_completed": moves, "finite": True, "bounded": first_bound_exceedance is None, "bound": bound, "first_bound_exceedance": first_bound_exceedance, "maximum_abs": maximum, "checkpoints": checkpoints}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "experiments/p05_hypothesis_a")
    parser.add_argument("--seed", type=int, default=205)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--standard-iterations", type=int, default=160)
    parser.add_argument("--arbitrary-iterations", type=int, default=320)
    parser.add_argument("--dagger-iterations", type=int, default=80)
    parser.add_argument("--fire-rate", type=float, default=0.5)
    parser.add_argument("--overflow-weight", type=float, default=1.0)
    parser.add_argument("--stability-limit", type=float, default=10.0)
    parser.add_argument("--probe-epochs", type=int, default=100)
    parser.add_argument("--soak-moves", type=int, default=510)
    parser.add_argument("--evaluation-max-n", type=int, default=8)
    parser.add_argument("--resume", type=Path)
    args = parser.parse_args()
    torch = require_torch()
    torch.set_num_threads(min(8, torch.get_num_threads()))
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    random.seed(args.seed)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    config = vars(args).copy()
    config["output"] = str(output.resolve().relative_to(ROOT))
    config["resume"] = str(args.resume) if args.resume else None
    config["schedule"] = {"short": [20, 24], "long": [50, 59], "long_every": 4}
    config["auxiliary_schema"] = AUX_SCHEMA
    config["graph_parameter_count"] = 1916
    json_write(output / "config.json", config)

    model = build_model(args.seed)
    runtime = TorchNCARuntime(model, "clamp_one")
    heads = build_auxiliary_heads(args.seed + 1)
    optimizer = torch.optim.Adam(list(model.parameters()) + list(heads.parameters()), lr=0.0002)
    curves: dict[str, object] = {}
    completed_phase = "none"
    if args.resume:
        payload = load_resume(args.resume, model, heads, optimizer)
        curves = payload["curves"]
        completed_phase = payload["phase"]

    schedule = MixedStepSchedule()
    corpus = build_corpus()
    train_samples = [sample for sample in corpus if sample.split == "train" and sample.actions]
    arbitrary_states = [sample.state for sample in train_samples]
    started = time.perf_counter()
    phases = [
        ("standard", standard_states(6), args.standard_iterations, False),
        ("arbitrary", arbitrary_states, args.arbitrary_iterations, False),
        ("dagger", arbitrary_states, args.dagger_iterations, True),
    ]
    order = [item[0] for item in phases]
    start_index = order.index(completed_phase) + 1 if completed_phase in order else 0
    for index, (name, states, iterations, on_policy) in enumerate(phases):
        if index < start_index:
            continue
        result = train_phase(
            name, runtime, heads, optimizer, states, iterations, args.batch_size,
            schedule, args.fire_rate, args.seed + 1000 * (index + 1), on_policy,
            args.overflow_weight,
            args.stability_limit,
        )
        curves[name] = result
        save_resume(output / f"resume_after_{name}.pt", model, heads, optimizer, name, config, curves)
        json_write(output / "progress.json", {
            "schema": SCHEMA, "last_completed_phase": name,
            "resume_checkpoint": f"resume_after_{name}.pt",
            "checkpoint_sha256": digest(output / f"resume_after_{name}.pt"),
            "curves": curves,
        })
        if result["abort_reason"]:
            break

    specs = diagnostic_episode_specs(args.evaluation_max_n)
    evaluations = {}
    for label, step_min, step_max in (("short_20_24", 20, 24), ("long_50_59", 50, 59)):
        records = evaluate_nca(runtime, specs, step_min, step_max, args.seed + 7000, True)
        evaluations[label] = summarize_episodes(records)

    train_probe_states = [sample.state for sample in train_samples[:512]]
    test_probe_states = [sample.state for sample in corpus if sample.split == "test_seen_n" and sample.actions][:512]
    probes = independent_probe(
        runtime, train_probe_states, test_probe_states, schedule,
        args.fire_rate, args.seed + 8000, args.probe_epochs,
    )
    soak = worst_case_stability_soak(
        runtime, schedule, args.fire_rate, args.seed + 9000,
        args.soak_moves, args.stability_limit,
    )
    acceptance = {
        "bounded_510_move_soak": bool(soak["finite"] and soak["bounded"] and soak["moves_completed"] == args.soak_moves),
        "short_schedule_standard_completion": evaluations["short_20_24"]["completed"] == len(specs),
        "long_schedule_standard_completion": evaluations["long_50_59"]["completed"] == len(specs),
        "held_out_legality_probe_at_least_0_90": probes["test"]["legality_bit_accuracy"] >= 0.90,
        "held_out_top_disk_probe_at_least_0_80": probes["test"]["top_disk_accuracy"] >= 0.80,
        "held_out_peg_role_probe_at_least_0_80": probes["test"]["peg_role_accuracy"] >= 0.80,
        "held_out_subgoal_probe_at_least_0_80": probes["test"]["subgoal_disk_accuracy"] >= 0.80,
    }
    acceptance["hypothesis_a_passed"] = all(acceptance.values())
    final_checkpoint = output / "final_resume.pt"
    save_resume(final_checkpoint, model, heads, optimizer, "complete", config, curves)
    result = {
        "schema": SCHEMA,
        "status": "completed" if all(not value["abort_reason"] for value in curves.values()) else "stability_abort",
        "config": config,
        "environment": {"python": platform.python_version(), "numpy": np.__version__, "torch": torch.__version__},
        "runtime_seconds": time.perf_counter() - started,
        "phases": curves,
        "closed_loop": evaluations,
        "evaluation_set": "all standard transfers n=1..6 plus goal-0 standard transfers n=7,8",
        "worst_case_persistent_stability_soak": soak,
        "acceptance": acceptance,
        "functional_freeze_eligible": bool(acceptance["hypothesis_a_passed"]),
        "independent_hidden_state_probe": probes,
        "final_checkpoint": {"path": str(final_checkpoint.relative_to(ROOT)), "sha256": digest(final_checkpoint)},
        "deployment_boundary": "only locked 1,916-parameter NCA; auxiliary heads and oracle labels are training-only",
    }
    json_write(output / "results.json", result)
    print(json.dumps({"result": str(output / "results.json"), "status": result["status"], "closed_loop": evaluations}, indent=2))
    return 0 if result["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
