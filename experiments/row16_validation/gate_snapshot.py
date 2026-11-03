"""Publish safe aggregates from stopped private checkpoints; never resume runs."""
import hashlib
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import numpy as np
from model_export.cartpole.freeze import sha256


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--runs-confirmed-stopped",action="store_true",required=True,
                        help="Operator has checked that these comparison processes are stopped")
    parser.parse_args()
    private=ROOT/"artifacts/row16_validation/long"
    result={"stage":"P07 extension / G4 return", "status":"stopped-at-human-gate",
            "long_campaign_complete":False,"runs_confirmed_stopped_by_operator":True,
            "screen_summary_sha256":sha256(Path(__file__).with_name("screen_summary.json")),
            "cases":[]}
    for path in sorted(private.glob("seed_*_progress.npz")):
        with np.load(path,allow_pickle=False) as data:
            meta=json.loads(str(data["metadata"]))
            item={"identity":meta["identity"],"case":meta["case"],"last_saved_logical_action":meta["logical_action"],
                  "logical_epoch_draws":meta["epochs"],"checkpoint_path":path.relative_to(ROOT).as_posix(),
                  "checkpoint_sha256":sha256(path),"arms":{}}
            for name,arm in meta["arms"].items():
                value={k:v for k,v in arm.items() if k!="actions"}
                dtype="<f4" if name=="float32" else "<i8"
                value.update(actions=len(arm["actions"]),censored=not arm["terminal"],
                    actions_sha256=hashlib.sha256(bytes(arm["actions"])).hexdigest(),
                    final_grid_sha256=hashlib.sha256(np.asarray(data[name+"_grid"],dtype=dtype).tobytes()).hexdigest(),
                    final_plant_sha256=hashlib.sha256(np.asarray(data[name+"_plant"],dtype="<f8").tobytes()).hexdigest())
                item["arms"][name]=value
            result["cases"].append(item)
    failures=[]
    for case in result["cases"]:
        fixed,floating=case["arms"]["row16"],case["arms"]["float32"]
        if fixed["terminal"] and fixed["reason"]!="source_horizon" and fixed["actions"]<floating["actions"]:
            failures.append({"seed":case["case"]["seed"],"candidate_terminal_action":fixed["actions"],
                             "reason":fixed["reason"],"float_actions_observed":floating["actions"],
                             "fidelity32_actions_observed":case["arms"]["fidelity32"]["actions"]})
    result["observed_earlier_candidate_failures"]=failures
    if not failures:
        raise ValueError("no measured earlier candidate failure; do not invent a gate result")
    output=Path(__file__).with_name("gate_summary.json")
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(failures,indent=2))


if __name__=="__main__":main()
