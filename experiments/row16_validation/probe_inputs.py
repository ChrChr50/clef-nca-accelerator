"""Same-state one-decision probes of individual coarse observation channels."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import numpy as np
from model_export.cartpole.accepted_arithmetic import accepted_format
from model_export.cartpole.fixed_point import FixedNCA
from model_export.cartpole.row16_candidate import EXPECTED
from reference.original_nca.core import load_tfjs_weights,INPUT_SCALE
from model_export.cartpole.freeze import load_frozen,sha256


def main():
    frozen=load_frozen()
    base=ROOT/frozen["weights"]["source"]
    weights=load_tfjs_weights(base/"model.json",base/"group1-shard1of1.bin")
    before_path=ROOT/"artifacts/row16_validation/diagnosis/first_divergence_ablations.npz"
    with np.load(before_path,allow_pickle=False) as saved:before=saved["float_before_action101"].copy()
    with np.load(ROOT/"artifacts/row16_validation/screen/seed_41_row16_first_difference.npz",allow_pickle=False) as data:
        obs,masks=data["observation"].copy(),data["masks"].copy()
    coarse=FixedNCA(weights,EXPECTED)
    labels=["cart_position","cart_velocity","pole_angle","pole_angular_velocity"]
    result={"scope":"seed41/action101 only; same float starting grid; one-decision input sensitivity, not policy qualification",
            "start_sha256":sha256(before_path),"cases":[],"physical_input_quantum_approx":{}}
    for index,label in enumerate(labels):
        result["physical_input_quantum_approx"][label]=2**(-10)/float(INPUT_SCALE[index])
    for selected in ((),(0,),(1,),(2,),(3,),(0,1,2,3)):
        class PartialCoarse(FixedNCA):
            def observations(self,observation):
                fine=super().observations(observation)
                low=coarse.observations(observation)<<14
                for index in selected:fine[:,2*index:2*index+2]=low[:,2*index:2*index+2]
                return fine
        model=PartialCoarse(weights,accepted_format())
        grid=model.initial_grid(before)
        for mask in masks:grid=model.step(grid,obs,mask)
        scores=model.readout(grid)[0]/(1<<24)
        result["cases"].append({"coarse_inputs":[labels[i] for i in selected],
                                "scores":scores.tolist(),"action":int(np.argmax(scores))})
    output=Path(__file__).with_name("input_precision_probe.json")
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
