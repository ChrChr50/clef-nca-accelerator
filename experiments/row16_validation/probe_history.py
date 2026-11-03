"""Bounded seed41 history/observation swaps at four saved late decisions."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import numpy as np
from experiments.row16_validation.diagnose import plant_replay
from model_export.cartpole.freeze import load_frozen,sha256
from reference.original_nca.core import load_tfjs_weights,CanonicalNCA
from reference.original_nca.cartpole import CartPole
from sw.cartpole.qualification import draws_for_action


def main():
    source=ROOT/"artifacts/row16_validation/long/seed_41_progress.npz"
    with np.load(source,allow_pickle=False) as data:meta=json.loads(str(data["metadata"]))
    actions=meta["arms"]["float32"]["actions"]
    states,_,_=plant_replay(actions,41)
    frozen=load_frozen()
    base=ROOT/frozen["weights"]["source"]
    model=CanonicalNCA(load_tfjs_weights(base/"model.json",base/"group1-shard1of1.bin"))
    first=ROOT/"artifacts/row16_validation/screen/seed_41_row16_first_difference.npz"
    with np.load(first,allow_pickle=False) as data:grid=data["float_grid"].copy()
    rng=np.random.RandomState(41)
    CartPole.reset(rng)
    for _ in range(101):draws_for_action(rng)
    result={"scope":"seed41 four one-decision grid/observation swaps; not policy qualification or recovery rollout",
            "checkpoint_sha256":sha256(source),"script_sha256":sha256(Path(__file__)),"cases":[]}
    for index in range(102,1151):
        _,masks=draws_for_action(rng)
        obs=states[index-1].astype(np.float32)[None,:]
        if index in (1139,1143,1145,1150):
            path=ROOT/f"artifacts/row16_validation/diagnosis/before_action_{index}.npz"
            with np.load(path,allow_pickle=False) as data:
                candidate_grid=(data["grid"].astype(np.float64)/1024).astype(np.float32)
                candidate_obs=data["observation"].copy()
                np.testing.assert_array_equal(masks,data["masks"])
            case={"action_index":index,"swaps":[]}
            for name,initial,observations in (("float_history_float_observation",grid,obs),
                ("float_history_candidate_observation",grid,candidate_obs),
                ("candidate_history_float_observation",candidate_grid,obs),
                ("candidate_history_candidate_observation",candidate_grid,candidate_obs)):
                branch=initial.copy()
                for mask in masks:branch=model.step(branch,observations,mask)
                scores=model.readout(branch)[0]
                case["swaps"].append({"case":name,"scores":scores.tolist(),"action":int(np.argmax(scores))})
            result["cases"].append(case)
        for mask in masks:grid=model.step(grid,obs,mask)
        if int(model.action(grid)[0])!=actions[index-1]:raise AssertionError("float action replay mismatch")
        if index%256==0:print(f"float history replay action={index}",flush=True)
    result["all_replayed_float_actions_match_saved_history"]=True
    Path(__file__).with_name("history_probe.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,indent=2),flush=True)


if __name__=="__main__":main()
