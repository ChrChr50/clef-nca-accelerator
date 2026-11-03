"""Resumable predeclared paired float/fidelity32/row16 experiment; no training."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
from model_export.cartpole.accepted_arithmetic import accepted_format
from model_export.cartpole.fixed_point import FixedNCA
from model_export.cartpole.freeze import load_frozen, sha256
from model_export.cartpole.row16_candidate import PROTOCOL, candidate_format
from reference.original_nca.core import CanonicalNCA, load_tfjs_weights, seeded_initial_grid
from reference.original_nca.cartpole import CartPole
from sw.cartpole.qualification import draws_for_action, termination_reason

HERE = Path(__file__).parent
PRIVATE = ROOT / "artifacts/row16_validation"


def identity(phase):
    frozen = load_frozen()
    return {"phase": phase, "protocol_sha256": sha256(PROTOCOL),
            "runner_sha256": sha256(Path(__file__)),
            "candidate_source_sha256": sha256(ROOT / "model_export/cartpole/row16_candidate.py"),
            "golden_sha256": sha256(ROOT / "model_export/cartpole/fixed_point.py"),
            "weights_sha256": frozen["weights"]["blob_sha256"],
            "python": sys.version.split()[0], "numpy": np.__version__}


def digest(array, dtype):
    return hashlib.sha256(np.asarray(array, dtype=dtype).tobytes()).hexdigest()


def save(path, arrays, meta):
    temporary = path.with_suffix(".tmp.npz")
    np.savez_compressed(temporary, **arrays, metadata=np.asarray(json.dumps(meta, sort_keys=True)))
    temporary.replace(path)


def episode(case, authority, weights):
    seed, limit = case["seed"], case["max_actions"]
    folder = PRIVATE / authority["phase"]
    folder.mkdir(parents=True, exist_ok=True)
    progress = folder / f"seed_{seed}_progress.npz"
    completed = folder / f"seed_{seed}_complete.json"
    if completed.exists():
        result = json.loads(completed.read_text())
        if result["identity"] != authority or result["case"] != case:
            raise ValueError("stale completed case; preserve it and use a new version")
        return result
    models = {"float32": CanonicalNCA(weights), "fidelity32": FixedNCA(weights, accepted_format()),
              "row16": FixedNCA(weights, candidate_format())}
    rng = np.random.RandomState(seed)
    plant = CartPole.reset(rng)
    initial = seeded_initial_grid(seed ^ 0x5A17)
    plants = {name: CartPole(plant.state.copy()) for name in models}
    grids = {name: initial.copy() if name == "float32" else model.initial_grid(initial)
             for name, model in models.items()}
    meta = {"identity": authority, "case": case, "logical_action": 0, "epochs": 0,
            "initial_plant_sha256": digest(plant.state, "<f8"),
            "initial_grid_sha256": digest(initial, "<f4"), "arms": {}}
    for name in models:
        meta["arms"][name] = {"actions": [], "score": 0., "terminal": False, "reason": None,
            "seconds": 0., "first_action_difference": None, "matched_observation_samples": 0,
            "max_grid_error_matched_observation": 0., "minimum_score_margin": None,
            "grid_absolute_peak": 0., "counters": {}}
    if progress.exists():
        with np.load(progress, allow_pickle=False) as data:
            meta = json.loads(str(data["metadata"]))
            if meta["identity"] != authority or meta["case"] != case:
                raise ValueError("resume identity changed; preserve progress, do not overwrite")
            for name in models:
                grids[name] = data[name + "_grid"].copy()
                plants[name].state = data[name + "_plant"].copy()
                plants[name].step_count = len(meta["arms"][name]["actions"])
                if name != "float32":
                    models[name].counters = meta["arms"][name]["counters"].copy()
            rng.set_state(("MT19937", data["rng_keys"], int(data["rng_pos"]),
                           int(data["rng_flag"]), float(data["rng_gauss"])))
        print(f"Resuming {authority['phase']} seed={seed} after action={meta['logical_action']}", flush=True)

    def checkpoint():
        state = rng.get_state()
        arrays = {"rng_keys": state[1], "rng_pos": state[2], "rng_flag": state[3], "rng_gauss": state[4]}
        for name in models:
            arrays[name + "_grid"] = grids[name]
            arrays[name + "_plant"] = plants[name].state
            if name != "float32":
                meta["arms"][name]["counters"] = models[name].counters.copy()
        save(progress, arrays, meta)

    for index in range(meta["logical_action"] + 1, limit + 1):
        count, masks = draws_for_action(rng)
        meta["epochs"] += count
        before = {name: p.state.astype(np.float32)[None, :] for name, p in plants.items()}
        current_actions, current_scores = {}, {}
        for name, model in models.items():
            arm = meta["arms"][name]
            if arm["terminal"]:
                continue
            start = time.perf_counter()
            for mask in masks:
                grids[name] = model.step(grids[name], before[name], mask)
            scores = model.readout(grids[name])[0]
            action = int(np.argmax(scores))
            current_actions[name] = action
            current_scores[name] = scores.copy()
            decoded = grids[name] if name == "float32" else model.decode(grids[name])
            arm["grid_absolute_peak"] = max(arm["grid_absolute_peak"], float(np.max(np.abs(decoded))))
            margin = abs(float(scores[0])-float(scores[1]))
            if name != "float32":
                margin /= 1 << model.fmt.state_fraction
            arm["minimum_score_margin"] = margin if arm["minimum_score_margin"] is None else min(margin, arm["minimum_score_margin"])
            _, reward, terminal = plants[name].step(action)
            arm["score"] += reward
            arm["actions"].append(action)
            arm["terminal"] = bool(terminal)
            arm["reason"] = termination_reason(plants[name], terminal)
            arm["seconds"] += time.perf_counter() - start
        for name in ("fidelity32", "row16"):
            arm = meta["arms"][name]
            if name not in current_actions or "float32" not in current_actions:
                continue
            matched = np.array_equal(before[name], before["float32"])
            if matched:
                arm["matched_observation_samples"] += 1
                error = models[name].decode(grids[name]) - grids["float32"].astype(np.float64)
                arm["max_grid_error_matched_observation"] = max(arm["max_grid_error_matched_observation"], float(np.max(np.abs(error))))
            if arm["first_action_difference"] is None and current_actions[name] != current_actions["float32"]:
                arm["first_action_difference"] = {"logical_action": index, "same_observation": matched,
                    "float_action": current_actions["float32"], "fixed_action": current_actions[name],
                    "float_scores": current_scores["float32"].tolist(), "fixed_integer_scores": current_scores[name].tolist()}
                np.savez_compressed(folder / f"seed_{seed}_{name}_first_difference.npz",
                                    float_grid=grids["float32"], fixed_grid=grids[name],
                                    observation=before[name], masks=masks)
        meta["logical_action"] = index
        if index % 16 == 0 or all(a["terminal"] for a in meta["arms"].values()) or index == limit:
            checkpoint()
            print(f"{authority['phase']} seed={seed} action={index} durations="
                  f"{ {k: len(v['actions']) for k,v in meta['arms'].items()} }", flush=True)
        if all(a["terminal"] for a in meta["arms"].values()):
            break
    checkpoint()
    result = {"identity": authority, "case": case, "complete": True, "epochs": meta["epochs"], "arms": {}}
    for name, arm in meta["arms"].items():
        result["arms"][name] = {k: v for k, v in arm.items() if k != "actions"}
        result["arms"][name].update(actions=len(arm["actions"]), actions_sha256=hashlib.sha256(bytes(arm["actions"])).hexdigest(),
            censored=not arm["terminal"], final_plant_sha256=digest(plants[name].state, "<f8"),
            final_grid_sha256=digest(grids[name], "<f4" if name == "float32" else "<i8"))
    completed.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("screen", "long"), default="screen")
    args = parser.parse_args()
    protocol = json.loads(PROTOCOL.read_text())
    authority = identity(args.phase)
    frozen = load_frozen()
    base = ROOT / frozen["weights"]["source"]
    blob = base / "group1-shard1of1.bin"
    if sha256(blob) != authority["weights_sha256"]:
        raise ValueError("checkpoint hash mismatch")
    weights = load_tfjs_weights(base / "model.json", blob)
    cases = protocol["screen"]
    if args.phase == "long":
        screen = json.loads((HERE / "screen_summary.json").read_text())
        if not screen["complete"] or screen["return_to_G4"] or screen["identity"]["protocol_sha256"] != sha256(PROTOCOL):
            raise ValueError("long comparison requires the declared screen to clear its early-rejection condition")
        cases = [{"role": "long paired comparison; disclose screen reuse", "seed": seed,
                  "max_actions": protocol["long_comparison"]["max_actions"]}
                 for seed in protocol["long_comparison"]["seeds"]]
    model = FixedNCA(weights, candidate_format())
    result = {"identity": authority, "format": model.fmt.manifest(), "accumulator_bounds": model.bounds,
              "initialization_counters": model.counters, "cases": [], "complete": False, "return_to_G4": False}
    output = HERE / f"{args.phase}_summary.json"
    for case in cases:
        value = episode(case, authority, weights)
        result["cases"].append(value)
        arms = value["arms"]
        if arms["row16"]["terminal"] and arms["row16"]["reason"] != "source_horizon" and arms["row16"]["actions"] < arms["float32"]["actions"]:
            result["return_to_G4"] = True
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    result["complete"] = True
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"Complete {args.phase}: return_to_G4={result['return_to_G4']}", flush=True)


if __name__ == "__main__":
    main()
