"""Generate restricted layer/cell/epoch/readout vectors and safe metadata."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import numpy as np
from reference.original_nca.core import load_tfjs_weights,CanonicalNCA
from model_export.cartpole.fixed_point import Format,FixedNCA,quantize,scalar_cell_delta
from model_export.cartpole.freeze import load_frozen,sha256


def differences(actual,reference):
    error = np.asarray(actual,dtype=np.float64)-np.asarray(reference,dtype=np.float64)
    index = np.unravel_index(int(np.argmax(np.abs(error))),error.shape)
    return {"max_abs_error":float(np.max(np.abs(error))),"rmse":float(np.sqrt(np.mean(error**2))),
            "max_error_coordinate":[int(i) for i in index]}


def main():
    load_frozen()
    here = Path(__file__).parent
    profile = json.loads((here / "float_profile.json").read_text())
    if not profile["complete"] or not profile["matches_recorded_p06"]:
        raise ValueError("complete faithful full-horizon profile required")
    protocol = json.loads((here / "protocol.v1.json").read_text())
    base = ROOT / "self-organized-control/demo/models/model2"
    weights = load_tfjs_weights(base / "model.json",base / "group1-shard1of1.bin")
    private = ROOT / "artifacts/p07_cartpole/vectors"
    private.mkdir(parents=True,exist_ok=True)
    result = {"schema_version":1,"profile_sha256":sha256(here / "float_profile.json"),
              "protocol_sha256":sha256(here / "protocol.v1.json"),
              "script_sha256":sha256(Path(__file__)),"cases":[],
              "fixture_policy":"all checkpoint-derived arrays remain ignored/local"}
    cells = np.asarray([[0,0],[0,31],[31,0],[31,31],[11,26],[13,16],[17,16],[16,16]],dtype=np.int64)
    for candidate in protocol["candidates"]:
        fmt = Format(**candidate)
        for snapshot in profile["snapshot_paths"]:
            with np.load(ROOT / snapshot,allow_pickle=False) as data:
                model = FixedNCA(weights,fmt)
                old = model.initial_grid(data["old_grid"])
                post,trace = model.step(old,data["observation"],data["mask"],trace=True)
                expected_float = {"layer0_output":data["hidden0"],"layer1_output":data["hidden1"],
                                  "layer2_output":data["delta"],"post_write_epoch":data["new_grid"]}
                metrics = {name:differences(model.decode(trace[name]),array) for name,array in expected_float.items()}
                first = None
                for name,array in expected_float.items():
                    expected,_ = quantize(array,fmt.state_bits,fmt.state_fraction)
                    mismatch = np.argwhere(trace[name]!=expected)
                    if len(mismatch) and first is None:
                        coordinate = tuple(int(v) for v in mismatch[0])
                        first = {"boundary":name,"coordinate":list(coordinate),
                                 "absolute_lsb_difference":abs(int(trace[name][coordinate])-int(expected[coordinate]))}
                cell_delta = np.stack([trace["delta"][0,r,c] for r,c in cells])
                for index,(row,col) in enumerate(cells):
                    if not np.array_equal(cell_delta[index],scalar_cell_delta(model,old,int(row),int(col))):
                        raise AssertionError("vector/scalar cell mismatch")
                # Explicit short persistent epoch trajectory; all draws saved.
                rng = np.random.RandomState(907)
                masks = rng.random_sample((59,1,32,32,1))<=.5
                grid = old.copy()
                epoch_vectors = []
                for index,mask in enumerate(masks):
                    grid = model.step(grid,data["observation"],mask)
                    if index in (0,1,58):
                        epoch_vectors.append(grid.copy())
                filename = fmt.name+"_"+Path(snapshot).stem+".npz"
                target = private / filename
                np.savez_compressed(target,old_grid=old,observation=data["observation"],supplied_mask=data["mask"],
                    cells=cells,cell_delta=cell_delta,**trace,persistent_masks=masks,
                    persistent_epochs=np.stack(epoch_vectors),final_readout=model.readout(grid),
                    final_action=np.argmax(model.readout(grid),axis=1))
                result["cases"].append({"format":fmt.name,"source_snapshot":snapshot,
                    "restricted_vector_path":str(target.relative_to(ROOT)).replace("\\","/"),
                    "sha256":sha256(target),"bytes":target.stat().st_size,"errors":metrics,
                    "first_quantized_float_difference":first,"scalar_cells_verified":len(cells),
                    "persistent_epochs_saved":[1,2,59],"saturation_counts":model.counters})
    (here / "vectors_manifest.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(f"Generated {len(result['cases'])} restricted cases, {len(cells)*len(result['cases'])} independently checked cells")


if __name__ == "__main__":
    main()
