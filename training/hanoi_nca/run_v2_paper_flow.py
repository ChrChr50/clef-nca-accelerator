#!/usr/bin/env python3
"""Resumable P05 v2 experiment using the paper's teaching mechanics.

The paper's synthetic mean warm-up, persistent grid pool, 50..59 steps,
per-tensor gradient normalization, and long training budget are retained.
Hanoi's exact training-only optimal-action labels replace CartPole DQN targets;
this is not a literal reproduction of the CartPole reinforcement learner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
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
from training.hanoi_nca.model import require_torch, save_checkpoint
from training.hanoi_nca.run_experiment import episode_specs, evaluate_nca, summarize_episodes
from training.hanoi_nca.run_v2 import (
    action_targets,
    open_loop_metrics,
    partition_manifest,
    soft_target_loss,
    training_strata,
    v2_split,
    write_json,
)
from training.hanoi_nca.v2_adapter import LAYOUT_PATH
from training.hanoi_nca.v2_model import PARAMETER_COUNT, build_v2_model
from training.hanoi_nca.v2_runtime import TorchNCAV2Runtime

SCHEMA = "clef.p05.hanoi-v2-paper-teaching.v1"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixed_config(args: argparse.Namespace) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "seed": args.seed,
        "batch_size": args.batch_size,
        "microbatch_size": args.microbatch_size,
        "pool_size": args.pool_size,
        "step_min": args.step_min,
        "step_max": args.step_max,
        "warmup_min": args.warmup_min,
        "warmup_max": args.warmup_max,
        "warmup_mse_goal": args.warmup_mse_goal,
        "imitation_iterations": args.imitation_iterations,
        "learning_rate": args.learning_rate,
        "fire_rate": 0.5,
        "replacement_probability": 0.01,
        "layout_sha256": file_sha256(LAYOUT_PATH),
        "local_parameters": PARAMETER_COUNT,
        "objective": "synthetic 4*mean(36 inputs) then complete-set oracle cross-entropy",
        "oracle_boundary": "training and evaluation only",
        "training_state": "independently sampled persistent grid pool; no environment-grid pairing",
        "inference_state": "persistent within episode, reset between episodes",
    }


def initialize_pool(runtime: TorchNCAV2Runtime, size: int, seed: int):
    return runtime.initial_state(size, seed).clone()


def sample_batch(phase: str, strata, rng: np.random.RandomState, batch_size: int, iteration: int):
    if phase == "warmup":
        observations = rng.uniform(-1.0, 1.0, (batch_size, 36)).astype(np.float32)
        target = (4.0 * observations.mean(axis=1, keepdims=True)).repeat(6, axis=1)
        return observations, target, None
    n_max = 2 if iteration < 2500 else (4 if iteration < 5000 else (6 if iteration < 7500 else 8))
    samples = []
    for _ in range(batch_size):
        n = int(rng.randint(1, n_max + 1))
        goal = int(rng.randint(0, 3))
        cases = strata[(n, goal)]
        samples.append(cases[int(rng.randint(len(cases)))])
    observations = np.asarray([sample.observation for sample in samples], dtype=np.float32)
    return observations, action_targets(samples), n_max


def warmup_validation(runtime: TorchNCAV2Runtime, seed: int, steps: int) -> float:
    torch = require_torch()
    rng = np.random.RandomState(seed + 880001)
    observations = rng.uniform(-1.0, 1.0, (48, 36)).astype(np.float32)
    target = torch.from_numpy((4.0 * observations.mean(axis=1, keepdims=True)).repeat(6, axis=1))
    mask_rng = torch.Generator().manual_seed(seed + 880002)
    runtime.model.eval()
    with torch.no_grad():
        state = runtime.initial_state(48, seed + 880003)
        scores = runtime.readout(runtime.run(state, torch.from_numpy(observations), steps, 0.5, mask_rng))
        value = float(torch.mean((scores - target) ** 2))
    runtime.model.train()
    return value


def normalized_step(model, optimizer) -> float:
    torch = require_torch()
    norms = []
    for parameter in model.parameters():
        if parameter.grad is None:
            continue
        norm = torch.linalg.vector_norm(parameter.grad)
        if not bool(torch.isfinite(norm)):
            raise FloatingPointError("non-finite parameter gradient")
        norms.append(float(norm))
        parameter.grad.div_(norm + 1e-8)
    optimizer.step()
    return max(norms, default=0.0)


def train_iteration(runtime, optimizer, pool, strata, rng, mask_rng, phase, iteration, config):
    torch = require_torch()
    batch_size = int(config["batch_size"])
    microbatch_size = int(config["microbatch_size"])
    indices = rng.choice(len(pool), size=batch_size, replace=False)
    observations, targets, n_max = sample_batch(phase, strata, rng, batch_size, iteration)
    steps = int(rng.randint(int(config["step_min"]), int(config["step_max"]) + 1))
    optimizer.zero_grad(set_to_none=True)
    next_states = []
    row_losses = []
    for start in range(0, batch_size, microbatch_size):
        stop = min(start + microbatch_size, batch_size)
        state = pool[indices[start:stop]].clone()
        obs = torch.from_numpy(observations[start:stop])
        target = torch.from_numpy(targets[start:stop])
        evolved = runtime.run(state, obs, steps, 0.5, mask_rng)
        scores = runtime.readout(evolved)
        if phase == "warmup":
            per_row = ((scores - target) ** 2).mean(dim=1)
        else:
            per_row = -(target * torch.log_softmax(scores, dim=1)).sum(dim=1)
        loss = per_row.sum() / batch_size
        if not bool(torch.isfinite(loss)) or not bool(torch.isfinite(evolved).all()):
            raise FloatingPointError(f"non-finite {phase} state/loss at iteration {iteration}")
        loss.backward()
        next_states.append(evolved.detach())
        row_losses.append(per_row.detach())
    gradient_norm = normalized_step(runtime.model, optimizer)
    evolved_batch = torch.cat(next_states, dim=0)
    per_sample = torch.cat(row_losses, dim=0)
    pool[indices] = evolved_batch
    if rng.random_sample() < float(config["replacement_probability"]):
        worst = int(torch.argmax(per_sample))
        pool[indices[worst]] = runtime.initial_state(1, int(rng.randint(1, 2**31 - 1)))[0]
    return {
        "phase": phase,
        "iteration": iteration + 1,
        "loss": float(per_sample.mean()),
        "steps": steps,
        "n_max": n_max,
        "gradient_norm_before_per_tensor_normalization": gradient_norm,
        "pool_max_abs": float(pool.abs().max()),
    }


def save_progress(path: Path, runtime, optimizer, pool, rng, mask_rng, phase, iteration, config, curves, started):
    torch = require_torch()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": SCHEMA,
        "config": config,
        "phase": phase,
        "iteration": iteration,
        "model": runtime.model.state_dict(),
        "optimizer": optimizer.state_dict(),
        "pool": pool,
        "numpy_rng": rng.get_state(),
        "mask_rng": mask_rng.get_state(),
        "curves": curves,
        "elapsed_seconds": time.perf_counter() - started,
    }
    temporary = path.with_suffix(".tmp")
    torch.save(payload, temporary)
    os.replace(temporary, path)
    write_json(path.parent / "progress.json", {
        "schema": SCHEMA,
        "phase": phase,
        "iteration": iteration,
        "imitation_target": config["imitation_iterations"],
        "latest": curves[-1] if curves else None,
        "checkpoint_sha256": file_sha256(path),
    })


def load_progress(path: Path, runtime, optimizer, config):
    torch = require_torch()
    payload = torch.load(path, map_location="cpu", weights_only=False)
    if payload.get("schema") != SCHEMA or payload.get("config") != config:
        raise ValueError("checkpoint schema/config differs from requested run")
    runtime.model.load_state_dict(payload["model"])
    optimizer.load_state_dict(payload["optimizer"])
    rng = np.random.RandomState()
    rng.set_state(payload["numpy_rng"])
    mask_rng = torch.Generator()
    mask_rng.set_state(payload["mask_rng"])
    return payload["pool"], rng, mask_rng, payload["phase"], payload["iteration"], payload["curves"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "experiments/p05_v2_paper_flow")
    parser.add_argument("--seed", type=int, default=405)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--microbatch-size", type=int, default=4)
    parser.add_argument("--pool-size", type=int, default=128)
    parser.add_argument("--step-min", type=int, default=50)
    parser.add_argument("--step-max", type=int, default=59)
    parser.add_argument("--warmup-min", type=int, default=4000)
    parser.add_argument("--warmup-max", type=int, default=12000)
    parser.add_argument("--warmup-mse-goal", type=float, default=0.02)
    parser.add_argument("--imitation-iterations", type=int, default=15000)
    parser.add_argument("--learning-rate", type=float, default=0.005)
    parser.add_argument("--checkpoint-every", type=int, default=250)
    parser.add_argument("--stop-after", type=int, default=0, help="save and stop after this many new iterations; 0 means full run")
    parser.add_argument("--eval-cases-per-split", type=int, default=512)
    parser.add_argument("--eval-max-n", type=int, default=8)
    args = parser.parse_args()
    if not (1 <= args.microbatch_size <= args.batch_size <= args.pool_size):
        parser.error("require 1 <= microbatch <= batch <= pool")
    if not (1 <= args.step_min <= args.step_max and 1 <= args.warmup_min <= args.warmup_max):
        parser.error("invalid step or warm-up bounds")
    torch = require_torch()
    torch.set_num_threads(min(8, torch.get_num_threads()))
    torch.manual_seed(args.seed)
    started = time.perf_counter()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT):
        parser.error("output must be within repository")
    output.mkdir(parents=True, exist_ok=True)
    config = fixed_config(args)
    checkpoint = output / "resume.pt"
    corpus = build_corpus()
    strata = training_strata(corpus)
    runtime = TorchNCAV2Runtime(build_v2_model(args.seed))
    optimizer = torch.optim.Adam(runtime.model.parameters(), lr=args.learning_rate)
    if checkpoint.exists():
        pool, rng, mask_rng, phase, iteration, curves = load_progress(checkpoint, runtime, optimizer, config)
    else:
        if any(output.iterdir()):
            parser.error("nonempty output without resume.pt; choose another output")
        write_json(output / "config.json", config)
        write_json(output / "partition_manifest.json", partition_manifest(corpus))
        pool = initialize_pool(runtime, args.pool_size, args.seed + 1)
        rng = np.random.RandomState(args.seed + 2)
        mask_rng = torch.Generator().manual_seed(args.seed + 3)
        phase, iteration, curves = "warmup", 0, []
        save_progress(checkpoint, runtime, optimizer, pool, rng, mask_rng, phase, iteration, config, curves, started)
    trained = 0
    runtime.model.train()
    while phase in ("warmup", "imitation"):
        metrics = train_iteration(runtime, optimizer, pool, strata, rng, mask_rng, phase, iteration, config)
        iteration += 1
        trained += 1
        periodic = iteration % args.checkpoint_every == 0
        if periodic or iteration == 1:
            if phase == "warmup":
                metrics["fresh_validation_mse"] = warmup_validation(runtime, args.seed, args.step_max)
            curves.append(metrics)
            print(json.dumps(metrics), flush=True)
        if phase == "warmup" and iteration >= args.warmup_min and periodic:
            if metrics["fresh_validation_mse"] <= args.warmup_mse_goal or iteration >= args.warmup_max:
                phase, iteration = "imitation", 0
                save_checkpoint(runtime.model, output / "after_warmup.npz", {"schema": SCHEMA, "warmup": metrics})
        elif phase == "imitation" and iteration >= args.imitation_iterations:
            phase = "evaluation"
            save_checkpoint(runtime.model, output / "after_imitation.npz", {"schema": SCHEMA, "imitation": metrics})
        if periodic or phase == "evaluation" or (args.stop_after and trained >= args.stop_after):
            save_progress(checkpoint, runtime, optimizer, pool, rng, mask_rng, phase, iteration, config, curves, started)
        if args.stop_after and trained >= args.stop_after:
            return 0
    if phase == "evaluation":
        partitions = {name: [sample for sample in corpus if v2_split(sample) == name] for name in ("train", "validation", "test")}
        open_loop = {
            name: open_loop_metrics(runtime, samples, args.seed + 7000 + index, args.eval_cases_per_split, args.step_max)
            for index, (name, samples) in enumerate(partitions.items())
        }
        specs = [spec for spec in episode_specs() if spec.reset_mode == "standard" and spec.disk_count <= args.eval_max_n]
        records = evaluate_nca(runtime, specs, args.step_min, args.step_max, args.seed + 8000, True)
        write_json(output / "episode_records.json", records)
        result = {
            "schema": SCHEMA,
            "status": "completed_experiment_not_model_freeze",
            "config": config,
            "python": platform.python_version(),
            "numpy": np.__version__,
            "torch": torch.__version__,
            "curves": curves,
            "open_loop": open_loop,
            "closed_loop": summarize_episodes(records),
            "checkpoint_sha256": file_sha256(output / "after_imitation.npz"),
            "elapsed_seconds": time.perf_counter() - started,
            "claim": "paper-mechanics adaptation with oracle imitation; not literal DQN or model freeze",
        }
        write_json(output / "results.json", result)
        phase = "complete"
        save_progress(checkpoint, runtime, optimizer, pool, rng, mask_rng, phase, iteration, config, curves, started)
        print(json.dumps({"result": str(output / "results.json"), "open_loop": open_loop, "closed_loop": result["closed_loop"]}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
