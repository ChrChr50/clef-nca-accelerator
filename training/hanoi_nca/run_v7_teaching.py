#!/usr/bin/env python3
"""Gated P05 action-value teaching from the verified v6 spatial warm-up.

The oracle is used only here to form labels and evaluation; runtime inference
still observes 36 P04 values and reads six channel-zero NCA output cells.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.hanoi.environment import HanoiEnv, encode_observation, transition
from reference.hanoi.oracle import encode_locations, reverse_graph_distances
from training.hanoi_nca.dataset import build_corpus
from training.hanoi_nca.model import require_torch, save_checkpoint
from training.hanoi_nca.run_experiment import episode_specs, evaluate_nca, summarize_episodes
from training.hanoi_nca.run_v2 import identity_bucket, partition_manifest, training_strata, v2_split, write_json
from training.hanoi_nca.run_v3_teaching import LAYOUT_PATH, boundary_margin_penalty, sha256
from training.hanoi_nca.v2_model import build_v2_model
from training.hanoi_nca.v4_runtime import TorchNCAV4Runtime

SCHEMA = "clef.p05.hanoi-v7-action-value.r2"
# Maximum n, minimum/maximum recurrence, update budget, held-out action gate.
STAGES = ((2, 12, 24, 1000, None), (2, 25, 40, 1000, None),
          (2, 50, 59, 5000, 0.85), (4, 50, 59, 6000, 0.80),
          (6, 50, 59, 7000, 0.80), (8, 50, 59, 8000, 0.80))


def action_values(state):
    """Exact one-step progress, not a runtime feature or a legality mask."""
    distances = reverse_graph_distances(state.disk_count, state.goal_peg)
    current = distances[encode_locations(state.locations)]
    values = []
    legal = []
    for action in range(6):
        successor, permitted, _ = transition(state, action)
        legal.append(float(permitted))
        values.append(float(current - distances[encode_locations(successor.locations)]))
    return np.asarray(values, np.float32), np.asarray(legal, np.float32)


def outputs(runtime, state):
    torch = require_torch()
    coordinates = runtime.output_coordinates
    policy = runtime.readout(state)
    legality = torch.stack([state[:, 1, row, col] for row, col in coordinates], dim=1)
    return policy, legality


def draw(strata, rng, maximum):
    n = int(rng.randint(1, maximum + 1))
    goal = int(rng.randint(0, 3))
    cases = strata[(n, goal)]
    return cases[int(rng.randint(len(cases)))]


def paired_successor(sample, rng):
    """Advance environment and NCA state together; avoid train/holdout leakage."""
    action = sample.actions[int(rng.randint(len(sample.actions)))]
    env = HanoiEnv(sample.state.disk_count, sample.state.goal_peg,
                   move_budget=max(3, 2 ** sample.state.disk_count + 1))
    env.reset(initial_locations=sample.state.locations)
    successor = env.step(action).state
    if successor.terminal or identity_bucket(successor.state_hash) >= 80:
        return None
    # Corpus lookup is supplied by the caller; preserve state identity here.
    return successor


def evaluate(runtime, samples, seed, steps, persistent=False, grid_seeds=4, cap=256):
    """Every unique eligible state for small n, deterministic hash subset above cap."""
    torch = require_torch()
    selected = sorted(samples, key=lambda s: s.state_hash)[:cap]
    if not selected:
        return {"unique_states": 0, "accuracy": None}
    correct = legal_correct = total = 0
    margins = []
    largest = 0.0
    runtime.model.eval()
    with torch.no_grad():
        for rep in range(grid_seeds):
            for start in range(0, len(selected), 16):
                batch = selected[start:start + 16]
                obs = torch.tensor([s.observation for s in batch], dtype=torch.float32)
                state = runtime.initial_state(len(batch), seed + 100003 * rep + start)
                masks = torch.Generator().manual_seed(seed + 200003 * rep + start)
                if persistent:
                    # Advance the P04 state and the same grid together for one
                    # teacher action; then evaluate the successor decision.
                    state = runtime.run(state, obs, steps, 0.5, masks)
                    successors = []
                    for sample in batch:
                        env = HanoiEnv(sample.state.disk_count, sample.state.goal_peg,
                                       move_budget=2 ** sample.state.disk_count + 1)
                        env.reset(initial_locations=sample.state.locations)
                        successors.append(env.step(sample.actions[0]).state)
                    obs = torch.tensor([encode_observation(s) for s in successors],
                                       dtype=torch.float32)
                state = runtime.run(state, obs, steps, 0.5, masks)
                scores, legality = outputs(runtime, state)
                prediction = scores.argmax(1).tolist()
                legal_prediction = (legality > 0).tolist()
                for i, sample in enumerate(batch):
                    judged = successors[i] if persistent else sample.state
                    values, legal = action_values(judged)
                    optimal = np.flatnonzero(values > 0.5)
                    if len(optimal) == 0:
                        continue
                    correct += int(prediction[i] in optimal)
                    legal_correct += sum(int(bool(x) == bool(y)) for x, y in zip(legal_prediction[i], legal))
                    good = max(float(scores[i, a]) for a in optimal)
                    bad = max(float(scores[i, a]) for a in range(6) if a not in optimal)
                    margins.append(good - bad)
                largest = max(largest, float(state.abs().max()))
                total += len(batch) if not persistent else sum(not s.terminal for s in successors)
    runtime.model.train()
    return {"unique_states": len(selected), "available_states": len(samples),
            "grid_seeds": grid_seeds, "decisions": total, "accuracy": correct / total,
            "legality_bit_accuracy": legal_correct / (6 * total),
            "mean_optimal_margin": float(np.mean(margins)), "max_abs_state": largest}


def train_iteration(runtime, optimizer, pool, paired, lookup, strata, rng, mask_rng,
                    stage, batch_size, microbatch, fresh_fraction):
    torch = require_torch()
    maximum, step_min, step_max, *_ = STAGES[stage]
    indices = rng.choice(len(pool), size=batch_size, replace=False)
    old = pool[indices].clone()
    samples = []
    fresh = rng.random_sample(batch_size) < fresh_fraction
    for i, slot in enumerate(indices):
        sample = paired[int(slot)]
        if fresh[i] or sample is None or sample.state.disk_count > maximum:
            sample = draw(strata, rng, maximum)
            old[i] = runtime.initial_state(1, int(rng.randint(1, 2**31 - 1)))[0]
        samples.append(sample)
    obs = np.asarray([s.observation for s in samples], np.float32)
    targets = np.stack([action_values(s.state)[0] for s in samples])
    legal = np.stack([action_values(s.state)[1] for s in samples])
    steps = int(rng.randint(step_min, step_max + 1))
    optimizer.zero_grad(set_to_none=True)
    evolved_parts = []
    loss_value = 0.0
    for start in range(0, batch_size, microbatch):
        stop = min(start + microbatch, batch_size)
        evolved = runtime.run(old[start:stop], torch.from_numpy(obs[start:stop]),
                              steps, 0.5, mask_rng)
        if not bool(torch.isfinite(evolved).all()) or float(evolved.detach().abs().max()) > 5.01:
            raise FloatingPointError("non-finite or out-of-bound evolving grid")
        policy, legality = outputs(runtime, evolved)
        value_target = torch.from_numpy(targets[start:stop])
        legal_target = torch.from_numpy(legal[start:stop])
        value_loss = ((policy - value_target) ** 2).mean()
        legal_loss = torch.nn.functional.binary_cross_entropy_with_logits(legality, legal_target)
        optimal = value_target > 0.5
        worst_good = policy.masked_fill(~optimal, float("inf")).min(dim=1).values
        best_other = policy.masked_fill(optimal, -float("inf")).max(dim=1).values
        ranking = torch.relu(0.5 + best_other - worst_good).mean()
        loss = ((value_loss + 0.2 * legal_loss + 0.5 * ranking +
                 100.0 * boundary_margin_penalty(evolved)) * ((stop - start) / batch_size))
        if not bool(torch.isfinite(loss)):
            raise FloatingPointError("non-finite training loss")
        loss.backward()
        loss_value += float(loss.detach())
        evolved_parts.append(evolved.detach())
    grad_norm = float(torch.nn.utils.clip_grad_norm_(runtime.model.parameters(), 1.0))
    if not np.isfinite(grad_norm):
        raise FloatingPointError("non-finite gradient")
    optimizer.step()
    pool[indices] = torch.cat(evolved_parts, dim=0)
    for i, slot in enumerate(indices):
        successor = paired_successor(samples[i], rng)
        paired[int(slot)] = lookup.get(successor.state_hash) if successor is not None else None
        if paired[int(slot)] is None:
            pool[int(slot)] = runtime.initial_state(1, int(rng.randint(1, 2**31 - 1)))[0]
    return {"loss": loss_value, "grad_norm": grad_norm, "steps": steps,
            "fresh_rows": int(fresh.sum()), "max_abs_state": float(pool[indices].abs().max())}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "experiments/p05_v2_paper_flow")
    parser.add_argument("--seed-checkpoint", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=705)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--microbatch-size", type=int, default=4)
    parser.add_argument("--pool-size", type=int, default=128)
    parser.add_argument("--fresh-fraction", type=float, default=0.5)
    parser.add_argument("--learning-rate", type=float, default=0.0003)
    parser.add_argument("--checkpoint-every", type=int, default=250)
    parser.add_argument("--min-stage-iterations", type=int, default=500)
    parser.add_argument("--stop-after", type=int, default=0)
    args = parser.parse_args()
    if not (1 <= args.microbatch_size <= args.batch_size <= args.pool_size):
        parser.error("invalid batch/microbatch/pool size")
    output = args.output.resolve()
    if not output.is_relative_to(ROOT):
        parser.error("output must be inside repository")
    output.mkdir(parents=True, exist_ok=True)
    torch = require_torch()
    torch.set_num_threads(min(8, torch.get_num_threads()))
    corpus = build_corpus()
    strata = training_strata(corpus)
    lookup = {s.state_hash: s for s in corpus if s.actions and v2_split(s) == "train"}
    runtime = TorchNCAV4Runtime(build_v2_model(args.seed), layout_path=LAYOUT_PATH)
    config = {"schema": SCHEMA, "seed": args.seed, "seed_checkpoint_sha256": sha256(args.seed_checkpoint),
              "layout_sha256": sha256(LAYOUT_PATH), "stages": STAGES,
              "batch_size": args.batch_size, "microbatch_size": args.microbatch_size,
              "pool_size": args.pool_size, "fresh_fraction": args.fresh_fraction,
              "learning_rate": args.learning_rate, "checkpoint_every": args.checkpoint_every,
              "min_stage_iterations": args.min_stage_iterations,
              "output_semantics": "channel0 signed one-step progress; channel1 auxiliary legality logit"}
    optimizer = torch.optim.Adam(runtime.model.parameters(), lr=args.learning_rate)
    checkpoint = output / "resume.pt"
    if checkpoint.exists():
        payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
        if payload["config"] != config:
            parser.error("resume configuration mismatch")
        runtime.model.load_state_dict(payload["model"])
        optimizer.load_state_dict(payload["optimizer"])
        pool, paired_hashes = payload["pool"], payload["paired_hashes"]
        paired = [lookup.get(key) if key else None for key in paired_hashes]
        rng = np.random.RandomState(); rng.set_state(payload["numpy_rng"])
        mask_rng = torch.Generator(); mask_rng.set_state(payload["mask_rng"])
        stage, iteration, total, history = (payload[key] for key in
                                            ("stage", "iteration", "total_iterations", "history"))
    else:
        unexpected = {path.name for path in output.iterdir()} - {
            "training.stdout.log", "training.stderr.log"}
        if unexpected:
            parser.error("output must be empty without a resume checkpoint")
        with np.load(args.seed_checkpoint, allow_pickle=False) as archive:
            runtime.model.load_state_dict({key: torch.from_numpy(archive[key].copy())
                                           for key in runtime.model.state_dict()})
        write_json(output / "config.json", config)
        write_json(output / "partition_manifest.json", partition_manifest(corpus))
        pool = runtime.initial_state(args.pool_size, args.seed + 1)
        paired = [None] * args.pool_size
        rng = np.random.RandomState(args.seed + 2)
        mask_rng = torch.Generator().manual_seed(args.seed + 3)
        stage = iteration = total = 0
        history = []

    def save(status):
        temporary = output / "resume.tmp"
        torch.save({"config": config, "model": runtime.model.state_dict(),
                    "optimizer": optimizer.state_dict(), "pool": pool,
                    "paired_hashes": [s.state_hash if s else None for s in paired],
                    "numpy_rng": rng.get_state(), "mask_rng": mask_rng.get_state(),
                    "stage": stage, "iteration": iteration, "total_iterations": total,
                    "history": history}, temporary)
        os.replace(temporary, checkpoint)
        write_json(output / "progress.json", {"schema": SCHEMA, "status": status,
                   "stage": stage if stage < len(STAGES) else "complete", "stage_iteration": iteration,
                   "total_iterations": total, "latest": history[-1] if history else None,
                   "checkpoint_sha256": sha256(checkpoint)})

    runtime.model.train()
    save("running")
    newly = 0
    while stage < len(STAGES):
        try:
            latest = train_iteration(runtime, optimizer, pool, paired, lookup, strata, rng,
                                     mask_rng, stage, args.batch_size, args.microbatch_size,
                                     args.fresh_fraction)
        except FloatingPointError as error:
            write_json(output / "failure.json", {"stage": stage, "iteration": iteration,
                       "reason": str(error)})
            save("failed_numerical")
            return 2
        iteration += 1; total += 1; newly += 1
        if iteration % args.checkpoint_every == 0:
            maximum, _, step_max, budget, goal = STAGES[stage]
            heldout = [s for s in corpus if s.actions and v2_split(s) == "validation"
                       and s.state.disk_count <= maximum]
            fresh = evaluate(runtime, heldout, args.seed + stage * 1000, step_max)
            persistent = evaluate(runtime, heldout, args.seed + stage * 1000, step_max, True)
            record = {"stage": stage, "iteration": iteration, "total_iterations": total,
                      "train": latest, "fresh": fresh, "persistent": persistent}
            history.append(record)
            print(json.dumps(record), flush=True)
            stable = max(fresh["max_abs_state"], persistent["max_abs_state"]) <= 5.0
            success = ((stage < 2 and iteration >= budget and stable) or
                       (stage >= 2 and iteration >= args.min_stage_iterations and stable
                        and fresh["accuracy"] >= goal and persistent["accuracy"] >= goal))
            if success:
                save_checkpoint(runtime.model, output / f"passed_stage_{stage}.npz",
                                {"schema": SCHEMA, "record": record})
                stage += 1; iteration = 0
                pool = runtime.initial_state(args.pool_size, args.seed + 100000 + stage)
                paired = [None] * args.pool_size
            elif iteration >= budget:
                write_json(output / "failure.json", {"stage": stage, "reason": "gate not met",
                           "record": record})
                save("failed_gate")
                return 3
            save("running")
        if args.stop_after and newly >= args.stop_after:
            save("running")
            return 0
    save_checkpoint(runtime.model, output / "candidate_not_frozen.npz", {"schema": SCHEMA})
    heldout = {}
    for split in ("validation", "test"):
        cases = [s for s in corpus if s.actions and v2_split(s) == split]
        heldout[split] = {
            "fresh": evaluate(runtime, cases, args.seed + 9000, 59, cap=512),
            "persistent": evaluate(runtime, cases, args.seed + 9000, 59, True, cap=512),
        }
    specs = [s for s in episode_specs() if s.reset_mode == "standard"]
    episodes = evaluate_nca(runtime, specs, 50, 59, args.seed + 10000, True)
    write_json(output / "episode_records.json", episodes)
    write_json(output / "results.json", {"schema": SCHEMA,
               "status": "evaluated_candidate_not_frozen", "heldout": heldout,
               "closed_loop": summarize_episodes(episodes),
               "candidate_sha256": sha256(output / "candidate_not_frozen.npz")})
    save("evaluated_candidate_not_frozen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
