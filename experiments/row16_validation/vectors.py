"""Generate/replay restricted candidate vectors without touching P07 authorities."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
from model_export.cartpole.freeze import sha256
from model_export.cartpole.fixed_point import scalar_cell_delta
from model_export.cartpole.row16_candidate import PROTOCOL, load_candidate, write_local_images

HERE = Path(__file__).parent
MANIFEST = HERE / "vectors_manifest.json"
PRIVATE = ROOT / "artifacts/row16_validation/vectors"


def generate():
    model = load_candidate()
    PRIVATE.mkdir(parents=True, exist_ok=True)
    profile_path = ROOT / "experiments/p07_cartpole/float_profile.json"
    profile = json.loads(profile_path.read_text())
    if not profile["complete"] or not profile["matches_recorded_p06"]:
        raise ValueError("profile must be complete and faithful")
    result = {"status": "candidate-not-accepted", "protocol_sha256": sha256(PROTOCOL),
              "script_sha256": sha256(Path(__file__)), "profile_sha256": sha256(profile_path),
              "format": model.fmt.manifest(), "cases": [],
              "image_manifest": write_local_images(ROOT / "artifacts/row16_validation/images", model)}
    cells = [(0,0),(0,31),(31,0),(31,31),(11,26),(13,16),(17,16),(16,16)]
    for snapshot in profile["snapshot_paths"]:
        model = load_candidate()
        with np.load(ROOT / snapshot, allow_pickle=False) as data:
            old = model.initial_grid(data["old_grid"])
            _,trace = model.step(old,data["observation"],data["mask"],trace=True)
            for row,col in cells:
                np.testing.assert_array_equal(trace["delta"][0,row,col],scalar_cell_delta(model,old,row,col))
            masks = np.random.RandomState(907).random_sample((59,1,32,32,1))<=.5
            grid, epochs = old.copy(), []
            for index,mask in enumerate(masks):
                grid = model.step(grid,data["observation"],mask)
                if index in (0,1,58):
                    epochs.append(grid.copy())
            path = PRIVATE / (Path(snapshot).stem + ".npz")
            np.savez_compressed(path, old_grid=old, observation=data["observation"], supplied_mask=data["mask"],
                                **trace, persistent_masks=masks, persistent_epochs=np.stack(epochs),
                                final_readout=model.readout(grid), final_action=np.argmax(model.readout(grid),axis=1))
            result["cases"].append({"source_snapshot": snapshot, "source_sha256": sha256(ROOT / snapshot),
                "path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path),
                "independent_scalar_cells": len(cells), "saved_epochs": [1,2,59], "counters": model.counters,
                "max_abs_one_step_error_to_float":float(np.max(np.abs(model.decode(trace["post_write_epoch"])-data["new_grid"])))})
    MANIFEST.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(f"Generated {len(result['cases'])} row16 cases and local output-major images", flush=True)


def check():
    manifest = json.loads(MANIFEST.read_text())
    if manifest["protocol_sha256"] != sha256(PROTOCOL) or manifest["script_sha256"] != sha256(Path(__file__)):
        raise ValueError("stale candidate vectors")
    for item in manifest["image_manifest"]["files"]:
        if sha256(ROOT / item["path"]) != item["sha256"]:
            raise AssertionError("ROM image hash mismatch")
    for item in manifest["cases"]:
        if sha256(ROOT / item["path"]) != item["sha256"] or sha256(ROOT / item["source_snapshot"]) != item["source_sha256"]:
            raise AssertionError("vector/source identity mismatch")
        model = load_candidate()
        with np.load(ROOT / item["path"],allow_pickle=False) as saved:
            _,trace = model.step(saved["old_grid"],saved["observation"],saved["supplied_mask"],trace=True)
            for name,value in trace.items():
                np.testing.assert_array_equal(value,saved[name])
            grid,epochs = saved["old_grid"].copy(),[]
            for index,mask in enumerate(saved["persistent_masks"]):
                grid = model.step(grid,saved["observation"],mask)
                if index in (0,1,58):
                    epochs.append(grid.copy())
            np.testing.assert_array_equal(np.stack(epochs),saved["persistent_epochs"])
            np.testing.assert_array_equal(model.readout(grid),saved["final_readout"])
            np.testing.assert_array_equal(np.argmax(model.readout(grid),axis=1),saved["final_action"])
    print(f"Row16 vector replay PASS: {len(manifest['cases'])} complete cases",flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true")
    args = parser.parse_args()
    check() if args.check else generate()
