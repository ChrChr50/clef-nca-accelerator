"""Bounded post-gate diagnosis of saved seed 41; never resumes qualification.

Replay recorded plant actions, reconstruct the first divergent decision, perform
same-input one-decision numerical ablations, and replay only the saved candidate
history through its already observed failure. No tuning, training or new seeds.
"""
from pathlib import Path
import json
import math
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import numpy as np
from model_export.cartpole.accepted_arithmetic import accepted_format
from model_export.cartpole.fixed_point import FixedNCA,Format
from model_export.cartpole.freeze import load_frozen,sha256
from model_export.cartpole.row16_candidate import EXPECTED
from reference.original_nca.core import CanonicalNCA,load_tfjs_weights,seeded_initial_grid,INPUT_COORDINATES,OUTPUT_COORDINATES
from reference.original_nca.cartpole import CartPole
from sw.cartpole.qualification import draws_for_action,termination_reason

PRIVATE=ROOT/"artifacts/row16_validation/diagnosis"


def plant_replay(actions,seed):
    plant=CartPole.reset(np.random.RandomState(seed))
    states=[plant.state.copy()]
    rewards=[]
    for action in actions:
        _,reward,done=plant.step(action)
        states.append(plant.state.copy())
        rewards.append(reward)
        if done and len(states)-1!=len(actions):
            raise AssertionError("stored actions continue past terminal")
    return np.asarray(states),rewards,plant


def main():
    PRIVATE.mkdir(parents=True,exist_ok=True)
    source=ROOT/"artifacts/row16_validation/long/seed_41_progress.npz"
    first=ROOT/"artifacts/row16_validation/screen/seed_41_row16_first_difference.npz"
    with np.load(source,allow_pickle=False) as data:
        meta=json.loads(str(data["metadata"]))
        saved={k:data[k].copy() for k in data.files if k!="metadata"}
    with np.load(first,allow_pickle=False) as data:
        divergence={k:data[k].copy() for k in data.files}
    seed=meta["case"]["seed"]
    expected_first=meta["arms"]["row16"]["first_action_difference"]["logical_action"]
    if seed!=41 or expected_first!=101:
        raise ValueError("this declared diagnostic is only seed41/action101")
    frozen=load_frozen()
    base=ROOT/frozen["weights"]["source"]
    if sha256(base/"group1-shard1of1.bin")!=frozen["weights"]["blob_sha256"]:
        raise ValueError("weight identity mismatch")
    weights=load_tfjs_weights(base/"model.json",base/"group1-shard1of1.bin")
    result={"scope":"bounded saved-case post-gate diagnosis; no new qualification or tuning",
            "seed":seed,"source_checkpoint_sha256":sha256(source),"first_difference_sha256":sha256(first),
            "script_sha256":sha256(Path(__file__)),"plant":{},"numerical_ablations":{}}
    states={}
    for name,arm in meta["arms"].items():
        states[name],rewards,plant=plant_replay(arm["actions"],seed)
        np.testing.assert_array_equal(plant.state,saved[name+"_plant"])
        if not math.isclose(sum(rewards),arm["score"],abs_tol=1e-10):
            raise AssertionError("plant reward replay mismatch")
        angles=np.rad2deg(states[name][:,2])
        result["plant"][name]={"actions":len(arm["actions"]),"terminal":arm["terminal"],"reason":arm["reason"],
            "max_abs_angle_degrees":float(np.max(np.abs(angles))),"final_angle_degrees":float(angles[-1]),
            "angle_degrees_at_candidate_failure":float(angles[min(1150,len(angles)-1)]),
            "max_abs_cart_position":float(np.max(np.abs(states[name][:,0]))),
            "last_20_actions":arm["actions"][-20:],"nonzero_saturation_counts":{k:v for k,v in arm["counters"].items() if v}}
        for threshold in (3,6,9,11):
            hits=np.flatnonzero(np.abs(angles)>=threshold)
            result["plant"][name][f"first_action_abs_angle_ge_{threshold}_degrees"]=int(hits[0]) if len(hits) else None
    actions=np.asarray(meta["arms"]["row16"]["actions"])
    float_actions=np.asarray(meta["arms"]["float32"]["actions"][:len(actions)])
    mismatch=np.flatnonzero(actions!=float_actions)+1
    result["action_history"]={"first_difference":int(mismatch[0]),"different_actions_through_failure":len(mismatch),
                              "compared_actions":len(actions),"fidelity32_identical_to_float":meta["arms"]["fidelity32"]["actions"]==meta["arms"]["float32"]["actions"]}
    rng=np.random.RandomState(seed)
    CartPole.reset(rng)
    grid=seeded_initial_grid(seed^0x5A17)
    float_model=CanonicalNCA(weights)
    for index in range(1,expected_first+1):
        count,masks=draws_for_action(rng)
        observation=states["float32"][index-1].astype(np.float32)[None,:]
        before=grid.copy()
        for mask in masks:
            grid=float_model.step(grid,observation,mask)
    np.testing.assert_array_equal(grid,divergence["float_grid"])
    np.testing.assert_array_equal(observation,divergence["observation"])
    np.testing.assert_array_equal(masks,divergence["masks"])
    result["first_divergent_decision"]={"action":101,"epochs":count,"float_replay_bit_exact":True,
        "float_scores":float_model.readout(grid)[0].tolist(),
        "row16_scores":(FixedNCA.readout(divergence["fixed_grid"])[0]/1024).tolist(),
        "row16_integer_scores":FixedNCA.readout(divergence["fixed_grid"])[0].tolist(),
        "observation":observation[0].tolist()}
    error=divergence["fixed_grid"].astype(np.float64)/1024-grid.astype(np.float64)
    result["first_divergent_decision"].update(max_grid_error=float(np.max(np.abs(error))),
        grid_rmse=float(np.sqrt(np.mean(error**2))),
        max_error_by_channel=np.max(np.abs(error),axis=(0,1,2)).tolist())
    formats=[EXPECTED,Format("state16_weight24",16,10,24,22,62),
             Format("state32_weight16",32,24,16,12,62),accepted_format()]
    private_arrays={"float_before_action101":before}
    for fmt in formats:
        model=FixedNCA(weights,fmt)
        current=model.initial_grid(before)
        for mask in masks:
            current=model.step(current,observation,mask)
        scores=model.readout(current)[0]/(1<<fmt.state_fraction)
        result["numerical_ablations"][fmt.name]={"start":"same float pre-action101 grid quantized independently; no earlier fixed history",
            "scores":scores.tolist(),"action":int(np.argmax(scores)),
            "max_grid_error":float(np.max(np.abs(model.decode(current)-grid))),
            "nonzero_counts":{k:v for k,v in model.counters.items() if v}}
        private_arrays[fmt.name+"_fresh_after101"]=current

    class CoarseInputOnly(FixedNCA):
        def observations(self,obs):
            coarse=FixedNCA.observations(coarse_model,obs)
            return coarse << (self.fmt.state_fraction-EXPECTED.state_fraction)

    coarse_model=FixedNCA(weights,EXPECTED)
    input_model=CoarseInputOnly(weights,accepted_format())
    current=input_model.initial_grid(before)
    for mask in masks:current=input_model.step(current,observation,mask)
    result["numerical_ablations"]["coarse_input_only"]={"start":"fidelity32 state/weights, but input samples quantized to row16 resolution",
        "scores":(input_model.readout(current)[0]/(1<<24)).tolist(),"action":int(np.argmax(input_model.readout(current)[0])),
        "max_grid_error":float(np.max(np.abs(input_model.decode(current)-grid)))}
    private_arrays["coarse_input_after101"]=current
    np.savez_compressed(PRIVATE/"first_divergence_ablations.npz",**private_arrays)

    # Reproduce only the already recorded candidate history from its exact saved
    # first-divergence grid through the saved terminal action. Qualification stays stopped.
    model=FixedNCA(weights,EXPECTED)
    current=divergence["fixed_grid"].copy()
    trajectory=[]
    late_probes=[]
    tie_actions=[]
    for index in range(102,len(actions)+1):
        count,masks=draws_for_action(rng)
        obs=states["row16"][index-1].astype(np.float32)[None,:]
        if index in (1139,1143,1145,1150):
            old_decoded=model.decode(current).astype(np.float32)
            fp=old_decoded.copy()
            wide_model=FixedNCA(weights,accepted_format())
            wide=wide_model.initial_grid(old_decoded)
            np.savez_compressed(PRIVATE/f"before_action_{index}.npz",grid=current,observation=obs,masks=masks)
            for supplied in masks:
                fp=float_model.step(fp,obs,supplied)
                wide=wide_model.step(wide,obs,supplied)
            late_probes.append({"action_index":index,"start":"identical decoded candidate pre-action grid and candidate observation/masks",
                "recorded_row16_action":int(actions[index-1]),
                "float_action":int(np.argmax(float_model.readout(fp)[0])),"float_scores":float_model.readout(fp)[0].tolist(),
                "fidelity32_action":int(np.argmax(wide_model.readout(wide)[0])),
                "fidelity32_scores":(wide_model.readout(wide)[0]/(1<<24)).tolist()})
        for mask in masks:current=model.step(current,obs,mask)
        scores=model.readout(current)[0]
        action=int(np.argmax(scores))
        if action!=int(actions[index-1]):raise AssertionError(f"candidate replay diverges at {index}")
        if scores[0]==scores[1]:tie_actions.append(index)
        trajectory.append({"action_index":index,"action":action,"score_gap_lsb":abs(int(scores[0])-int(scores[1])),
            "max_abs_grid":float(np.max(np.abs(model.decode(current)))),
            "angle_before_degrees":float(np.rad2deg(obs[0,2])),
            "angular_velocity_before":float(obs[0,3])})
        if index%128==0:print(f"diagnostic saved-case replay action={index}",flush=True)
    np.testing.assert_array_equal(current,saved["row16_grid"])
    result["candidate_replay"]={"from_action":102,"through_action":len(actions),"all_actions_and_terminal_grid_exact":True,
        "tie_count":len(tie_actions),"tie_actions":tie_actions,"minimum_gap_lsb":min(t["score_gap_lsb"] for t in trajectory),
        "nonzero_counts":{k:v for k,v in model.counters.items() if v},
        "last_20_decisions":trajectory[-20:]}
    result["late_same_state_probes"]=late_probes
    np.savez_compressed(PRIVATE/"plant_trajectories.npz",**states)
    (PRIVATE/"candidate_decisions.json").write_text(json.dumps(trajectory,indent=2)+"\n")
    target=Path(__file__).with_name("diagnosis_summary.json")
    target.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"first_difference":result["first_divergent_decision"],"ablations":result["numerical_ablations"],
                      "plant":result["plant"],"ties":len(tie_actions)},indent=2),flush=True)


if __name__=="__main__":main()
