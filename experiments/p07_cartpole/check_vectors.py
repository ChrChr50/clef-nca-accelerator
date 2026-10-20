"""Replay every saved integer layer/epoch/readout element exactly."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import numpy as np
from reference.original_nca.core import load_tfjs_weights
from model_export.cartpole.fixed_point import Format,FixedNCA
from model_export.cartpole.freeze import load_frozen,sha256


def main():
    load_frozen()
    here = Path(__file__).parent
    protocol = json.loads((here / "protocol.v1.json").read_text())
    manifest = json.loads((here / "vectors_manifest.json").read_text())
    candidates = {candidate["name"]:candidate for candidate in protocol["candidates"]}
    base = ROOT / "self-organized-control/demo/models/model2"
    weights = load_tfjs_weights(base / "model.json",base / "group1-shard1of1.bin")
    count = 0
    for case in manifest["cases"]:
        path = ROOT / case["restricted_vector_path"]
        if sha256(path)!=case["sha256"]:
            raise AssertionError("saved vector hash mismatch")
        with np.load(path,allow_pickle=False) as saved:
            model = FixedNCA(weights,Format(**candidates[case["format"]]))
            _,trace = model.step(saved["old_grid"],saved["observation"],saved["supplied_mask"],trace=True)
            for name,value in trace.items():
                np.testing.assert_array_equal(value,saved[name])
            grid = saved["old_grid"].copy()
            vectors = []
            for index,mask in enumerate(saved["persistent_masks"]):
                grid = model.step(grid,saved["observation"],mask)
                if index in (0,1,58):
                    vectors.append(grid.copy())
            np.testing.assert_array_equal(np.stack(vectors),saved["persistent_epochs"])
            np.testing.assert_array_equal(model.readout(grid),saved["final_readout"])
            np.testing.assert_array_equal(np.argmax(model.readout(grid),axis=1),saved["final_action"])
        count += 1
    print(f"Integer vector replay: PASS ({count} complete layer/epoch/readout cases)")


if __name__ == "__main__":
    main()
