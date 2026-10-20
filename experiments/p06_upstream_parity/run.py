"""Paired seed-12 diagnostic: original TensorFlow Python vs P06 NumPy.

Run with the unchanged P06 Python environment. Both plants evolve independently
after the first differing action. Full grids/checkpoints stay in ignored artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
from reference.original_nca.cartpole import CartPole
from reference.original_nca.core import CanonicalNCA, load_tfjs_weights, seeded_initial_grid, make_io_contract
from sw.cartpole.qualification import draws_for_action, termination_reason


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def compare_arrays(local: np.ndarray, upstream: np.ndarray) -> dict:
    error = np.abs(local.astype(np.float64)-upstream.astype(np.float64))
    tolerance = 2e-5 + 2e-5*np.abs(upstream.astype(np.float64))
    return {"max_abs": float(error.max()), "rmse": float(np.sqrt(np.mean(error**2))),
            "elements_outside_p03_tolerance": int(np.count_nonzero(error>tolerance)),
            "bitwise_equal": bool(np.array_equal(local.view(np.uint32), upstream.view(np.uint32)))}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--action-limit", type=int, default=10001)
    parser.add_argument("--output", type=Path, default=ROOT / "experiments/p06_upstream_parity/results")
    parser.add_argument("--worker-python", type=Path, default=ROOT / ".venv-p06-parity/Scripts/python.exe")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    private = ROOT / "artifacts/p06_upstream_parity"
    private.mkdir(parents=True, exist_ok=True)
    checkpoint = private / (args.output.name + "_progress.npz")
    base = ROOT / "self-organized-control/demo/models/model2"
    nca = CanonicalNCA(load_tfjs_weights(base / "model.json", base / "group1-shard1of1.bin"))
    blob_hash = digest((base / "group1-shard1of1.bin").read_bytes())
    if blob_hash != "ee8e4ad597d73dc616e60e91a5af056c96beb9f2c18652cfb1a1906247fbc009":
        raise ValueError("model2 identity changed")
    rng = np.random.RandomState(12)
    plant = CartPole.reset(rng)
    grid = seeded_initial_grid(12 ^ 0x5A17)
    upstream_grid, upstream_plant = grid.copy(), plant.state.copy()
    summary = {"schema_version": 1, "seed": 12, "model": "model2", "blob_sha256": blob_hash,
               "local_runtime": {"python": sys.version.split()[0], "numpy": np.__version__},
               "first_nonbitwise_grid_action": None, "first_tolerance_breach_action": None,
               "first_action_disagreement": None, "local": {"actions":0,"score":0.,"done":False},
               "upstream": {"actions":0,"score":0.,"done":False}, "paired_actions":0,
               "max_grid_error_before_action_disagreement":0.,
               "initial_grid_sha256":digest(grid.astype("<f4").tobytes()),
               "initial_plant_sha256":digest(plant.state.astype("<f8").tobytes()),
               "upstream_revision":subprocess.check_output(["git","-C",str(ROOT / "self-organized-control"),"rev-parse","HEAD"],text=True).strip(),
               "runner_sha256":digest(Path(__file__).read_bytes()),
               "worker_sha256":digest(Path(__file__).with_name("upstream_worker.py").read_bytes())}
    local_actions, upstream_actions, mask_hashes = bytearray(), bytearray(), bytearray()
    if checkpoint.is_file():
        with np.load(checkpoint, allow_pickle=False) as data:
            summary = json.loads(str(data["summary"]))
            if summary["blob_sha256"] != blob_hash:
                raise ValueError("resume checkpoint identity changed")
            grid, upstream_grid = data["grid"], data["upstream_grid"]
            plant.state, upstream_plant = data["plant"], data["upstream_plant"]
            plant.step_count = summary["local"]["actions"]
            rng.set_state(("MT19937",data["rng_keys"],int(data["rng_pos"]),int(data["rng_gauss_flag"]),float(data["rng_gauss"])))
            local_actions = bytearray(data["local_actions"].tobytes())
            upstream_actions = bytearray(data["upstream_actions"].tobytes())
            mask_hashes = bytearray(data["mask_hashes"].tobytes())
    logs = args.output / "comparisons.jsonl"
    if logs.is_file():
        # A checkpoint is the committed boundary; trim any later log rows.
        rows = [json.loads(line) for line in logs.read_text().splitlines()]
        logs.write_text("".join(json.dumps(row,sort_keys=True)+"\n" for row in rows if row["logical_action"]<=summary["paired_actions"]))
    with (args.output / "worker_stderr.log").open("a", encoding="utf-8") as err:
        worker = subprocess.Popen([str(args.worker_python),"-u",str(Path(__file__).with_name("upstream_worker.py"))],
                                  cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,
                                  text=True,encoding="utf-8",bufsize=1)

        def request(command):
            worker.stdin.write(json.dumps(command)+"\n")
            worker.stdin.flush()
            line = worker.stdout.readline()
            if not line:
                raise RuntimeError("upstream worker exited; inspect worker_stderr.log")
            return json.loads(line)

        ready = worker.stdout.readline()
        if not ready:
            raise RuntimeError("upstream initialization failed; inspect worker_stderr.log")
        summary["upstream_runtime"] = json.loads(ready)
        initialization = request({"op":"init","grid":upstream_grid.astype("<f4").tobytes().hex(),
                                  "plant":upstream_plant.tolist(),"steps":summary["upstream"]["actions"]})
        cut, markers = make_io_contract(1)
        if (initialization["cut"] != cut.astype("<f4").tobytes().hex()
                or initialization["markers"] != markers.astype("<f4").tobytes().hex()):
            raise ValueError("upstream I/O masks differ from P03")
        summary["source_io_contract_bitwise_equal"] = True
        if summary["paired_actions"] == 0:
            probe_rng = np.random.RandomState(12)
            probe_plant = CartPole.reset(probe_rng)
            _, masks = draws_for_action(probe_rng)
            packed = np.packbits(masks[:1].reshape(-1),bitorder="little").tobytes()
            probe = request({"op":"probe","grid":grid.astype("<f4").tobytes().hex(),
                             "observation":probe_plant.state.astype(np.float32).tolist(),
                             "epochs":1,"masks":packed.hex()})
            expected_delta = np.frombuffer(bytes.fromhex(probe["delta"]),dtype="<f4").reshape(grid.shape)
            expected_step = np.frombuffer(bytes.fromhex(probe["grid"]),dtype="<f4").reshape(grid.shape)
            summary["identical_input_probe"] = {
                "delta":compare_arrays(nca.local_delta(grid),expected_delta),
                "step":compare_arrays(nca.step(grid,plant.state.astype(np.float32)[None,:],masks[0]),expected_step)}
        started = time.monotonic()

        def save():
            state = rng.get_state()
            temporary = checkpoint.with_suffix(".tmp.npz")
            np.savez_compressed(temporary, summary=json.dumps(summary), grid=grid, upstream_grid=upstream_grid,
                plant=plant.state, upstream_plant=upstream_plant, rng_keys=state[1],rng_pos=state[2],
                rng_gauss_flag=state[3],rng_gauss=state[4],
                local_actions=np.frombuffer(local_actions,dtype=np.uint8),
                upstream_actions=np.frombuffer(upstream_actions,dtype=np.uint8),
                mask_hashes=np.frombuffer(mask_hashes,dtype=np.uint8))
            os.replace(temporary,checkpoint)
            (args.output / "summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")

        try:
            with logs.open("a",encoding="utf-8") as log:
                while summary["paired_actions"] < args.action_limit and not all(summary[key]["done"] for key in ("local","upstream")):
                    logical_action = summary["paired_actions"]+1
                    epochs,masks = draws_for_action(rng)
                    packed = np.packbits(masks.reshape(-1),bitorder="little").tobytes()
                    mask_hashes.extend(hashlib.sha256(packed).digest())
                    local_before, upstream_before = grid.copy(), upstream_grid.copy()
                    matched_input = bool(np.array_equal(plant.state.astype(np.float32),upstream_plant.astype(np.float32)))
                    local_action, upstream_action = None,None
                    if not summary["local"]["done"]:
                        obs = plant.state.astype(np.float32)[None,:]
                        for mask in masks:
                            grid = nca.step(grid,obs,mask)
                        scores = nca.readout(grid)[0]
                        local_action = int(np.argmax(scores))
                        _,reward,done = plant.step(local_action)
                        local_actions.append(local_action)
                        summary["local"].update(actions=plant.step_count,score=summary["local"]["score"]+reward,
                                                done=done,reason=termination_reason(plant,done))
                        if done:
                            summary["local"]["ordered_mask_hashes_sha256"] = digest(bytes(mask_hashes))
                    reply = None
                    if not summary["upstream"]["done"]:
                        reply = request({"op":"step","epochs":epochs,"masks":packed.hex()})
                        upstream_grid = np.frombuffer(bytes.fromhex(reply["grid"]),dtype="<f4").copy().reshape(grid.shape)
                        upstream_plant = np.asarray(reply["plant"],dtype=np.float64)
                        upstream_action = reply["action"]
                        upstream_actions.append(upstream_action)
                        summary["upstream"].update(actions=summary["upstream"]["actions"]+1,
                                                  score=summary["upstream"]["score"]+reply["reward"],
                                                  done=reply["done"],reason=reply["reason"])
                        if reply["done"]:
                            summary["upstream"]["ordered_mask_hashes_sha256"] = digest(bytes(mask_hashes))
                    comparison = compare_arrays(grid,upstream_grid)
                    row = {"logical_action":logical_action,"epochs":epochs,"same_observation":matched_input,
                           "local_action":local_action,"upstream_action":upstream_action,"grid":comparison,
                           "local_scores":nca.readout(grid)[0].tolist(),
                           "upstream_scores":reply["scores"] if reply else None,
                           "plant_max_abs":float(np.max(np.abs(plant.state-upstream_plant))),
                           "local_done":summary["local"]["done"],"upstream_done":summary["upstream"]["done"],
                           "mask_sha256":digest(packed)}
                    if local_action is not None and upstream_action is not None:
                        if not comparison["bitwise_equal"] and summary["first_nonbitwise_grid_action"] is None:
                            summary["first_nonbitwise_grid_action"] = logical_action
                        if comparison["elements_outside_p03_tolerance"] and summary["first_tolerance_breach_action"] is None:
                            summary["first_tolerance_breach_action"] = logical_action
                        if summary["first_action_disagreement"] is None:
                            summary["max_grid_error_before_action_disagreement"] = max(summary["max_grid_error_before_action_disagreement"],comparison["max_abs"])
                            if local_action != upstream_action:
                                summary["first_action_disagreement"] = row
                                np.savez_compressed(private / "first_action_disagreement.npz",local_before=local_before,
                                                    upstream_before=upstream_before,local_after=grid,upstream_after=upstream_grid,
                                                    masks=masks,local_plant=plant.state,upstream_plant=upstream_plant)
                    summary["paired_actions"] = logical_action
                    log.write(json.dumps(row,sort_keys=True)+"\n")
                    if logical_action % 25 == 0:
                        log.flush()
                        save()
                        print(f"action={logical_action} local={summary['local']['actions']} upstream={summary['upstream']['actions']} first_action_difference={summary['first_action_disagreement']['logical_action'] if summary['first_action_disagreement'] else None} elapsed={time.monotonic()-started:.1f}s",flush=True)
                summary["complete"] = all(summary[key]["done"] for key in ("local","upstream"))
                for key,actions,plant_state,state in (("local",local_actions,plant.state,grid),("upstream",upstream_actions,upstream_plant,upstream_grid)):
                    summary[key].update(actions_sha256=digest(bytes(actions)),plant_sha256=digest(plant_state.astype("<f8").tobytes()),grid_sha256=digest(state.astype("<f4").tobytes()))
                summary["ordered_mask_hashes_sha256"] = digest(bytes(mask_hashes))
                if summary["local"]["done"]:
                    baseline = next(json.loads(line) for line in (ROOT / "experiments/p06_cartpole/results.jsonl").read_text().splitlines()
                                    if json.loads(line)["seed"]==12)
                    summary["local_matches_recorded_p06"] = {
                        key: summary["local"][key] == baseline[key]
                        for key in ("actions","score","actions_sha256","ordered_mask_hashes_sha256")}
                    summary["local_matches_recorded_p06"].update(
                        final_grid_sha256=summary["local"]["grid_sha256"]==baseline["final_grid_sha256"],
                        final_plant_sha256=summary["local"]["plant_sha256"]==baseline["final_plant_sha256"],
                        termination_reason=summary["local"]["reason"]==baseline["termination_reason"])
                save()
        finally:
            worker.stdin.write(json.dumps({"op":"quit"})+"\n")
            worker.stdin.flush()
            worker.wait(timeout=30)
    print(json.dumps(summary,indent=2,sort_keys=True),flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
