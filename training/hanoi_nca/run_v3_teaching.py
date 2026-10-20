#!/usr/bin/env python3
"""Gated, resumable P05 Hanoi NCA teaching experiment.

This is a distinct experimental operator, not the accepted v2 model freeze.
The training-only oracle never enters the runtime or saved weight tensors.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.hanoi_nca.dataset import build_corpus
from training.hanoi_nca.layout import load_layout
from training.hanoi_nca.model import require_torch, save_checkpoint
from training.hanoi_nca.run_experiment import episode_specs, evaluate_nca, summarize_episodes
from training.hanoi_nca.run_v2 import (
    action_targets, legality_targets, open_loop_metrics, partition_manifest,
    routing_targets, training_strata, v2_split, write_json,
)
from training.hanoi_nca.v2_model import build_v2_model
from training.hanoi_nca.v3_runtime import TorchNCAV3Runtime, overflow_penalty
from training.hanoi_nca.v4_runtime import TorchNCAV4Runtime, boundary_margin_penalty

SCHEMA = "clef.p05.hanoi-v6-gated-teaching.v1"
LAYOUT_PATH = Path(__file__).with_name("layout_v6.json")
LAYOUT = load_layout(LAYOUT_PATH)

STAGES = (
    # kind, number of active synthetic inputs or maximum disk count,
    # supervised outputs, step range, maximum iterations, normalized goal
    ("local_relay", 1, 1, 8, 12, 1500, 0.15),
    ("relay_r3", 1, 1, 12, 20, 2000, 0.15),
    ("relay_r4", 1, 1, 16, 26, 2000, 0.15),
    ("relay_r5", 1, 1, 22, 34, 2000, 0.15),
    ("relay_r6", 1, 1, 30, 42, 2500, 0.15),
    ("relay_r8", 1, 1, 40, 50, 3000, 0.15),
    ("broadcast", 1, 6, 40, 50, 3000, 0.15),
    ("combine", 8, 6, 50, 59, 4000, 0.15),
    ("combine", 36, 6, 50, 59, 6000, 0.15),
    ("routing", 8, 6, 50, 59, 2500, 0.10),
    ("legality", 8, 6, 50, 59, 2500, 0.90),
    ("imitation", 2, 6, 50, 59, 4000, 0.85),
    ("imitation", 4, 6, 50, 59, 4000, 0.80),
    ("imitation", 6, 6, 50, 59, 5000, 0.80),
    ("imitation", 8, 6, 50, 59, 6000, 0.80),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stage_name(index: int) -> str:
    kind, width, outputs, *_ = STAGES[index]
    return f"{index:02d}_{kind}_{width}_{outputs}"


def source_indices(kind: str):
    if kind == "local_relay":
        return (23,)
    if kind.startswith("relay_r"):
        radius = int(kind.removeprefix("relay_r"))
        row, column = LAYOUT.output_coordinates[0]
        return tuple(i for i, (r, c) in enumerate(LAYOUT.input_coordinates)
                     if max(abs(r - row), abs(c - column)) <= radius)
    return tuple(range(36))


def synthetic_batch(rng: np.random.RandomState, count: int, active: int,
                    allowed_indices=None):
    observations = np.zeros((count, 36), dtype=np.float32)
    values = rng.uniform(-1.0, 1.0, (count, active)).astype(np.float32)
    for row in range(count):
        allowed = tuple(range(36)) if allowed_indices is None else allowed_indices
        indices = rng.choice(allowed, size=active, replace=False)
        observations[row, indices] = values[row]
    # sqrt(2*k) gives target variance 2/3 for every k, matching the
    # original notebook's 4*mean(8) target variance under U[-1,1].
    targets = (math.sqrt(2.0 * active) * values.mean(axis=1, keepdims=True)).astype(np.float32)
    return observations, targets.repeat(6, axis=1)


def policy_batch(strata, rng: np.random.RandomState, count: int, n_max: int, kind: str):
    samples = []
    for _ in range(count):
        n = int(rng.randint(1, n_max + 1))
        goal = int(rng.randint(0, 3))
        choices = strata[(n, goal)]
        samples.append(choices[int(rng.randint(len(choices)))])
    observations = np.asarray([s.observation for s in samples], dtype=np.float32)
    targets = {"routing": routing_targets, "legality": legality_targets,
               "imitation": action_targets}[kind](samples)
    return observations, targets


def task_loss(scores, targets, kind: str, outputs: int):
    torch = require_torch()
    if kind == "local_relay" or kind.startswith("relay_r") or kind in ("broadcast", "combine", "routing"):
        return ((scores[:, :outputs] - targets[:, :outputs]) ** 2).mean(dim=1)
    if kind == "legality":
        return torch.nn.functional.binary_cross_entropy_with_logits(
            scores, targets, reduction="none").mean(dim=1)
    return -(targets * torch.log_softmax(scores, dim=1)).sum(dim=1)


def fresh_validation(runtime, index: int, seed: int, pool=None):
    torch = require_torch()
    kind, width, outputs, _, step_max, _, _ = STAGES[index]
    rng = np.random.RandomState(seed + 10000 + index)
    count = 48
    if kind == "local_relay" or kind.startswith("relay_r") or kind in ("broadcast", "combine"):
        observations, targets = synthetic_batch(
            rng, count, width, allowed_indices=source_indices(kind))
        samples = None
    else:
        corpus = build_corpus()
        eligible = [s for s in corpus if s.actions and v2_split(s) == "validation"
                    and s.state.disk_count <= width]
        chosen = rng.choice(len(eligible), size=count, replace=len(eligible) < count)
        samples = [eligible[int(i)] for i in chosen]
        observations = np.asarray([s.observation for s in samples], dtype=np.float32)
        targets = {"routing": routing_targets, "legality": legality_targets,
                   "imitation": action_targets}[kind](samples)
    state = (runtime.initial_state(count, seed + 20000 + index) if pool is None
             else pool[:count].clone())
    masks = torch.Generator().manual_seed(seed + 30000 + index)
    runtime.model.eval()
    with torch.no_grad():
        evolved = runtime.run(state, torch.from_numpy(observations), step_max, 0.5, masks)
        scores = runtime.readout(evolved)
        target = torch.from_numpy(targets)
        if kind == "local_relay" or kind.startswith("relay_r") or kind in ("broadcast", "combine", "routing"):
            mse = float(((scores[:, :outputs] - target[:, :outputs]) ** 2).mean())
            baseline = float((target[:, :outputs] ** 2).mean())
            metric = mse / max(baseline, 1e-12)
            detail = {"mse": mse, "zero_baseline_mse": baseline, "normalized_mse": metric}
        elif kind == "legality":
            metric = float(((scores > 0) == (target > 0.5)).float().mean())
            detail = {"bit_accuracy": metric}
        else:
            metric = float((scores.argmax(1) == target.argmax(1)).float().mean())
            detail = {"action_accuracy": metric}
        detail["max_abs_state"] = float(evolved.abs().max())
        detail["score_min"] = float(scores.min())
        detail["score_max"] = float(scores.max())
    runtime.model.train()
    return detail


def passed(index: int, fresh: dict, aged: dict) -> bool:
    kind = STAGES[index][0]
    goal = STAGES[index][-1]
    key = ("normalized_mse" if (kind == "local_relay" or kind.startswith("relay_r")
           or kind in ("broadcast", "combine", "routing"))
           else "bit_accuracy" if kind == "legality" else "action_accuracy")
    if max(fresh["max_abs_state"], aged["max_abs_state"]) > 5.0:
        return False
    return (fresh[key] <= goal and aged[key] <= goal) if key == "normalized_mse" else (
        fresh[key] >= goal and aged[key] >= goal)


def train_iteration(runtime, optimizer, pool, strata, rng, mask_rng, index, config):
    torch = require_torch()
    kind, width, outputs, step_min, step_max, *_ = STAGES[index]
    batch = config["batch_size"]
    selected = rng.choice(len(pool), size=batch, replace=False)
    state = pool[selected].clone()
    fresh = rng.random_sample(batch) < config["fresh_fraction"]
    if fresh.any():
        state[fresh] = runtime.initial_state(int(fresh.sum()), int(rng.randint(1, 2**31 - 1)))
    if kind == "local_relay" or kind.startswith("relay_r") or kind in ("broadcast", "combine"):
        obs, target = synthetic_batch(
            rng, batch, width, allowed_indices=source_indices(kind))
    else:
        obs, target = policy_batch(strata, rng, batch, width, kind)
    steps = int(rng.randint(step_min, step_max + 1))
    optimizer.zero_grad(set_to_none=True)
    evolved_parts = []
    task_values = []
    penalty_values = []
    for start in range(0, batch, config["microbatch_size"]):
        stop = min(start + config["microbatch_size"], batch)
        evolved = runtime.run(state[start:stop], torch.from_numpy(obs[start:stop]),
                              steps, 0.5, mask_rng)
        if not bool(torch.isfinite(evolved).all()) or float(evolved.detach().abs().max()) > 50:
            raise FloatingPointError("non-finite or >50 state before optimizer step")
        scores = runtime.readout(evolved)
        task = task_loss(scores, torch.from_numpy(target[start:stop]), kind, outputs).sum() / batch
        stability_penalty = (boundary_margin_penalty if config["operator"] == "smooth"
                             else overflow_penalty)
        penalty = stability_penalty(evolved) * ((stop - start) / batch)
        loss = task + config["overflow_weight"] * penalty
        if not bool(torch.isfinite(loss)):
            raise FloatingPointError("non-finite loss before optimizer step")
        loss.backward()
        evolved_parts.append(evolved.detach())
        task_values.append(float(task.detach()))
        penalty_values.append(float(penalty.detach()))
    grad_norm = float(torch.nn.utils.clip_grad_norm_(runtime.model.parameters(), 1.0))
    if not np.isfinite(grad_norm):
        raise FloatingPointError("non-finite gradient before optimizer step")
    optimizer.step()
    pool[selected] = torch.cat(evolved_parts, dim=0)
    return {"task_loss": sum(task_values), "overflow_penalty": sum(penalty_values),
            "grad_norm": grad_norm, "steps": steps, "max_abs_state": float(pool[selected].abs().max()),
            "fresh_rows": int(fresh.sum())}


def save_progress(output, runtime, optimizer, pool, rng, mask_rng, stage, iteration,
                  total_iterations, config, history, status):
    torch = require_torch()
    payload = {"schema": SCHEMA, "config": config, "stage": stage,
               "iteration": iteration, "total_iterations": total_iterations,
               "model": runtime.model.state_dict(), "optimizer": optimizer.state_dict(),
               "pool": pool, "numpy_rng": rng.get_state(), "mask_rng": mask_rng.get_state(),
               "history": history, "status": status}
    temporary = output / "resume.tmp"
    torch.save(payload, temporary)
    os.replace(temporary, output / "resume.pt")
    write_json(output / "progress.json", {"schema": SCHEMA, "status": status,
        "stage": stage_name(stage) if stage < len(STAGES) else "complete",
        "stage_iteration": iteration, "total_iterations": total_iterations,
        "latest": history[-1] if history else None,
        "checkpoint_sha256": sha256(output / "resume.pt")})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "experiments/p05_v2_paper_flow")
    parser.add_argument("--seed", type=int, default=505)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--microbatch-size", type=int, default=4)
    parser.add_argument("--pool-size", type=int, default=128)
    parser.add_argument("--fresh-fraction", type=float, default=0.5)
    parser.add_argument("--overflow-weight", type=float, default=100.0)
    parser.add_argument("--operator", choices=("smooth", "unclipped"), default="smooth")
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--checkpoint-every", type=int, default=250)
    parser.add_argument("--min-stage-iterations", type=int, default=500)
    parser.add_argument("--stop-after", type=int, default=0)
    parser.add_argument("--eval-cases-per-split", type=int, default=512)
    parser.add_argument("--eval-max-n", type=int, default=8)
    args = parser.parse_args()
    if not (1 <= args.microbatch_size <= args.batch_size <= args.pool_size and args.pool_size >= 48):
        parser.error("invalid batch/pool sizes")
    if not (0 <= args.fresh_fraction <= 1 and args.overflow_weight >= 0 and args.learning_rate > 0):
        parser.error("invalid training coefficients")
    torch = require_torch()
    torch.set_num_threads(min(8, torch.get_num_threads()))
    torch.manual_seed(args.seed)
    output = args.output.resolve()
    if not output.is_relative_to(ROOT):
        parser.error("output must be inside repository")
    output.mkdir(parents=True, exist_ok=True)
    config = {"schema": SCHEMA, "seed": args.seed, "batch_size": args.batch_size,
              "microbatch_size": args.microbatch_size, "pool_size": args.pool_size,
              "fresh_fraction": args.fresh_fraction, "overflow_weight": args.overflow_weight,
              "operator": args.operator, "layout_sha256": sha256(LAYOUT_PATH),
              "learning_rate": args.learning_rate, "checkpoint_every": args.checkpoint_every,
              "min_stage_iterations": args.min_stage_iterations, "stages": STAGES}
    corpus = build_corpus()
    strata = training_strata(corpus)
    runtime_type = TorchNCAV4Runtime if args.operator == "smooth" else TorchNCAV3Runtime
    runtime = runtime_type(build_v2_model(args.seed), layout_path=LAYOUT_PATH)
    optimizer = torch.optim.Adam(runtime.model.parameters(), lr=args.learning_rate)
    checkpoint = output / "resume.pt"
    if checkpoint.exists():
        payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
        if payload["schema"] != SCHEMA or json.dumps(payload["config"]) != json.dumps(config):
            parser.error("checkpoint schema or config mismatch")
        runtime.model.load_state_dict(payload["model"])
        optimizer.load_state_dict(payload["optimizer"])
        pool = payload["pool"]
        rng = np.random.RandomState(); rng.set_state(payload["numpy_rng"])
        mask_rng = torch.Generator(); mask_rng.set_state(payload["mask_rng"])
        stage, iteration = payload["stage"], payload["iteration"]
        total_iterations, history = payload["total_iterations"], payload["history"]
    else:
        unexpected = {p.name for p in output.iterdir()} - {
            "training.stdout.log", "training.stderr.log"}
        if unexpected:
            parser.error(f"nonempty output without resume.pt: {sorted(unexpected)}")
        write_json(output / "config.json", config)
        write_json(output / "partition_manifest.json", partition_manifest(corpus))
        pool = runtime.initial_state(args.pool_size, args.seed + 1)
        rng = np.random.RandomState(args.seed + 2)
        mask_rng = torch.Generator().manual_seed(args.seed + 3)
        stage, iteration, total_iterations, history = 0, 0, 0, []
        save_progress(output, runtime, optimizer, pool, rng, mask_rng,
                      stage, iteration, total_iterations, config, history, "running")
    runtime.model.train()
    newly_trained = 0
    while stage < len(STAGES):
        try:
            latest = train_iteration(runtime, optimizer, pool, strata, rng, mask_rng, stage, config)
        except FloatingPointError as exc:
            write_json(output / "failure.json", {"stage": stage_name(stage),
                "iteration": iteration, "total_iterations": total_iterations, "reason": str(exc)})
            save_progress(output, runtime, optimizer, pool, rng, mask_rng,
                          stage, iteration, total_iterations, config, history, "failed_numerical")
            return 2
        iteration += 1; total_iterations += 1; newly_trained += 1
        periodic = iteration % args.checkpoint_every == 0
        if periodic:
            fresh = fresh_validation(runtime, stage, args.seed)
            aged = fresh_validation(runtime, stage, args.seed, pool)
            record = {"stage": stage_name(stage), "iteration": iteration,
                      "total_iterations": total_iterations, "train": latest,
                      "fresh": fresh, "persistent_pool": aged}
            history.append(record)
            print(json.dumps(record), flush=True)
            success = iteration >= args.min_stage_iterations and passed(stage, fresh, aged)
            exhausted = iteration >= STAGES[stage][5]
            if success:
                save_checkpoint(runtime.model, output / f"passed_{stage_name(stage)}.npz",
                                {"schema": SCHEMA, "record": record})
                stage += 1; iteration = 0
                if stage < len(STAGES):
                    pool = runtime.initial_state(args.pool_size, args.seed + 100000 + stage)
            elif exhausted:
                save_progress(output, runtime, optimizer, pool, rng, mask_rng,
                              stage, iteration, total_iterations, config, history, "failed_gate")
                write_json(output / "failure.json", {"stage": stage_name(stage),
                    "reason": "validation gate not met", "record": record})
                return 3
            save_progress(output, runtime, optimizer, pool, rng, mask_rng,
                          stage, iteration, total_iterations, config, history, "running")
        if args.stop_after and newly_trained >= args.stop_after:
            save_progress(output, runtime, optimizer, pool, rng, mask_rng,
                          stage, iteration, total_iterations, config, history, "running")
            return 0
    save_checkpoint(runtime.model, output / "final_model.npz", {"schema": SCHEMA})
    partitions = {name: [s for s in corpus if v2_split(s) == name]
                  for name in ("train", "validation", "test")}
    open_loop = {name: open_loop_metrics(runtime, samples, args.seed + 7000 + i,
                 args.eval_cases_per_split, 59)
                 for i, (name, samples) in enumerate(partitions.items())}
    specs = [s for s in episode_specs() if s.reset_mode == "standard"
             and s.disk_count <= args.eval_max_n]
    records = evaluate_nca(runtime, specs, 50, 59, args.seed + 8000, True)
    write_json(output / "episode_records.json", records)
    result = {"schema": SCHEMA, "status": "completed_experiment_not_model_freeze",
              "config": config, "python": platform.python_version(),
              "numpy": np.__version__, "torch": torch.__version__,
              "history": history, "open_loop": open_loop,
              "closed_loop": summarize_episodes(records),
              "model_sha256": sha256(output / "final_model.npz")}
    write_json(output / "results.json", result)
    save_progress(output, runtime, optimizer, pool, rng, mask_rng,
                  stage, iteration, total_iterations, config, history, "complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
