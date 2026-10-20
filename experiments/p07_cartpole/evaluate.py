"""Predeclared calibration/acceptance float-versus-fixed control alternatives."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import numpy as np
from reference.original_nca.core import CanonicalNCA, load_tfjs_weights, seeded_initial_grid
from reference.original_nca.cartpole import CartPole
from sw.cartpole.qualification import draws_for_action, termination_reason
from model_export.cartpole.fixed_point import FixedNCA, Format
from model_export.cartpole.freeze import load_frozen,sha256


def main():
    load_frozen()
    here = Path(__file__).parent
    protocol = json.loads((here / "protocol.v1.json").read_text())
    private = ROOT / "artifacts/p07_cartpole/evaluation"
    private.mkdir(parents=True,exist_ok=True)
    base = ROOT / "self-organized-control/demo/models/model2"
    weights = load_tfjs_weights(base / "model.json",base / "group1-shard1of1.bin")
    result = {"schema_version":1,"protocol_sha256":sha256(here / "protocol.v1.json"),
              "script_sha256":sha256(Path(__file__)),"fixed_model_sha256":sha256(ROOT / "model_export/cartpole/fixed_point.py"),
              "runtime":{"python":sys.version.split()[0],"numpy":np.__version__},
              "formats":[],"episodes":[],"complete":False}
    for candidate in protocol["candidates"]:
        fmt = Format(**candidate)
        model = FixedNCA(weights,fmt)
        result["formats"].append({"contract":fmt.manifest(),"accumulator_bounds":model.bounds,
            "one_grid_bits":6144*fmt.state_bits,"double_buffer_bits":12288*fmt.state_bits,
            "parameter_bits":1860*fmt.weight_bits+56*fmt.accumulator_bits,
            "marker_only_stress": {"epochs":protocol["stress"]["epochs"],
                                   "first_saturating_epoch":((1 << (fmt.state_bits-1))-1)//(1 << fmt.state_fraction)+1,
                                   "end_value":((1 << (fmt.state_bits-1))-1)/(1 << fmt.state_fraction),
                                   "interpretation":"zero-delta analytic stress, not learned dynamics"}})
    output = here / "evaluation.json"
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    for role in ("calibration","acceptance"):
        seeds = protocol[role]["seeds"]
        limit = protocol[role].get("max_actions",protocol[role].get("fixed_candidate_actions"))
        for seed in seeds:
            rng = np.random.RandomState(seed)
            float_plant = CartPole.reset(rng)
            initial = seeded_initial_grid(seed ^ 0x5A17)
            float_grid = initial.copy()
            nca = CanonicalNCA(weights)
            arms = {}
            for candidate in protocol["candidates"]:
                fmt = Format(**candidate)
                model = FixedNCA(weights,fmt)
                arms[fmt.name] = {"model":model,"grid":model.initial_grid(initial),
                    "plant":CartPole(float_plant.state.copy()),"done":False,"score":0.,"actions":bytearray(),
                    "seconds":0.,"first_action_disagreement":None,"max_grid_error_same_plant":0.,
                    "max_grid_rmse_same_plant":0.,"minimum_margin_integer":None,"reason":None}
            float_done,float_score,float_actions,float_seconds = False,0.,bytearray(),0.
            for logical_action in range(1,limit+1):
                epochs,masks = draws_for_action(rng)
                float_before = float_plant.state.astype(np.float32)
                fa = None
                if not float_done:
                    start = time.monotonic()
                    for mask in masks:
                        float_grid = nca.step(float_grid,float_before[None,:],mask)
                    fa = int(nca.action(float_grid)[0])
                    _,reward,float_done = float_plant.step(fa)
                    float_score += reward
                    float_actions.append(fa)
                    float_seconds += time.monotonic()-start
                for name,arm in arms.items():
                    if arm["done"]:
                        continue
                    start = time.monotonic()
                    obs = arm["plant"].state.astype(np.float32)[None,:]
                    same_plant = np.array_equal(obs[0],float_before) and fa is not None
                    for mask in masks:
                        arm["grid"] = arm["model"].step(arm["grid"],obs,mask)
                    scores = arm["model"].readout(arm["grid"])[0]
                    action = int(np.argmax(scores))
                    margin = abs(int(scores[0])-int(scores[1]))
                    arm["minimum_margin_integer"] = margin if arm["minimum_margin_integer"] is None else min(margin,arm["minimum_margin_integer"])
                    if same_plant:
                        error = arm["model"].decode(arm["grid"])-float_grid.astype(np.float64)
                        arm["max_grid_error_same_plant"] = max(arm["max_grid_error_same_plant"],float(np.max(np.abs(error))))
                        arm["max_grid_rmse_same_plant"] = max(arm["max_grid_rmse_same_plant"],float(np.sqrt(np.mean(error**2))))
                    if fa is not None and arm["first_action_disagreement"] is None and action!=fa:
                        arm["first_action_disagreement"] = {"logical_action":logical_action,"same_observation":same_plant,
                            "float_action":fa,"fixed_action":action,"float_scores":nca.readout(float_grid)[0].tolist(),
                            "fixed_scores_integer":scores.tolist(),"fixed_observation_f32":obs[0].tolist()}
                        np.savez_compressed(private / f"{role}_{seed}_{name}_first_difference.npz",
                                            float_grid=float_grid,fixed_grid=arm["grid"],observation=obs,masks=masks)
                    _,reward,arm["done"] = arm["plant"].step(action)
                    arm["score"] += reward
                    arm["actions"].append(action)
                    arm["reason"] = termination_reason(arm["plant"],arm["done"])
                    arm["seconds"] += time.monotonic()-start
                if logical_action % 32 == 0:
                    # Persist independently resumable state at a logical boundary.
                    state = rng.get_state()
                    values = {"float_grid":float_grid,"float_plant":float_plant.state,
                              "rng_keys":state[1],"rng_pos":state[2],"rng_flag":state[3],"rng_gauss":state[4]}
                    for name,arm in arms.items():
                        values[name+"_grid"] = arm["grid"]
                        values[name+"_plant"] = arm["plant"].state
                    np.savez_compressed(private / f"{role}_{seed}_checkpoint.npz",**values)
                    print(f"{role} seed={seed} action={logical_action} fixed_durations="+
                          str({name:len(arm['actions']) for name,arm in arms.items()}),flush=True)
                if float_done and all(arm["done"] for arm in arms.values()):
                    break
            episode = {"role":role,"seed":seed,"action_cap":limit,"float":{
                "actions":len(float_actions),"score":float_score,"seconds":float_seconds,
                "terminated":float_done,"reason":termination_reason(float_plant,float_done),
                "censored":not float_done,"actions_sha256":hashlib.sha256(float_actions).hexdigest()},"fixed":{}}
            for name,arm in arms.items():
                episode["fixed"][name] = {key:arm[key] for key in ("score","seconds","first_action_disagreement",
                    "max_grid_error_same_plant","max_grid_rmse_same_plant","minimum_margin_integer","reason")}
                episode["fixed"][name].update(actions=len(arm["actions"]),terminated=arm["done"],censored=not arm["done"],
                    saturation_counts=arm["model"].counters,actions_sha256=hashlib.sha256(arm["actions"]).hexdigest(),
                    same_full_action_trace=arm["actions"]==float_actions)
            result["episodes"].append(episode)
            output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
            print(f"Completed {role} seed={seed}",flush=True)
    result["complete"] = True
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")


if __name__ == "__main__":
    main()
