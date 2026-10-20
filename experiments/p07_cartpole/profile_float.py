"""Primary-horizon float profiling with unchanged original arithmetic."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import numpy as np
from reference.original_nca.core import CanonicalNCA, conv2d_same, conv1x1, relu, load_tfjs_weights, seeded_initial_grid, OUTPUT_COORDINATES
from reference.original_nca.cartpole import CartPole
from sw.cartpole.qualification import draws_for_action, termination_reason
from model_export.cartpole.freeze import load_frozen, sha256


class Ranges:
    def __init__(self, saved=None):
        self.values = saved or {}

    def add(self,name,array,channels=False):
        value = np.asarray(array)
        axes = tuple(range(value.ndim-1)) if channels else None
        low,high = np.min(value,axis=axes),np.max(value,axis=axes)
        entry = self.values.get(name)
        if entry is None:
            entry = {"min":np.asarray(low).tolist(),"max":np.asarray(high).tolist(),"samples":0,"nonfinite":0}
            self.values[name] = entry
        entry["min"] = np.minimum(entry["min"],low).tolist()
        entry["max"] = np.maximum(entry["max"],high).tolist()
        entry["samples"] += 1
        entry["nonfinite"] += int(value.size-np.count_nonzero(np.isfinite(value)))


class ProfiledNCA(CanonicalNCA):
    def __init__(self,weights,ranges,epoch=0):
        super().__init__(weights)
        self.ranges,self.epoch = ranges,epoch

    def local_delta(self,grid):
        w = self.weights
        self.pre0 = conv2d_same(grid,w.conv0_kernel,w.conv0_bias)
        self.hidden0 = relu(self.pre0)
        self.pre1 = conv1x1(self.hidden0,w.conv1_kernel,w.conv1_bias)
        self.hidden1 = relu(self.pre1)
        self.delta = conv1x1(self.hidden1,w.conv2_kernel,w.conv2_bias)
        return self.delta

    def step(self,grid,observations,mask,**kwargs):
        result = super().step(grid,observations,mask,**kwargs)
        self.epoch += 1
        self.ranges.add("recurrent_state_per_channel",result,True)
        self.ranges.add("masked_residual_per_channel",grid+self.delta*mask.astype(np.float32),True)
        self.ranges.add("delta_per_channel",self.delta,True)
        self.ranges.add("output_hidden_4_5",np.stack([result[:,r,c,4:] for r,c in OUTPUT_COORDINATES]))
        if self.epoch == 1 or self.epoch % 64 == 0:
            for name,array in (("layer0_preactivation",self.pre0),("layer0_relu",self.hidden0),
                               ("layer1_preactivation",self.pre1),("layer1_relu",self.hidden1)):
                self.ranges.add(name,array,True)
        return result


def main():
    load_frozen()
    protocol = json.loads((Path(__file__).with_name("protocol.v1.json")).read_text())
    private = ROOT / "artifacts/p07_cartpole/float_profile"
    private.mkdir(parents=True,exist_ok=True)
    progress = private / "progress.npz"
    output = Path(__file__).with_name("float_profile.json")
    base = ROOT / "self-organized-control/demo/models/model2"
    weights = load_tfjs_weights(base / "model.json",base / "group1-shard1of1.bin")
    rng = np.random.RandomState(protocol["calibration"]["full_float_profile_seed"])
    plant = CartPole.reset(rng)
    grid = seeded_initial_grid(10 ^ 0x5A17)
    actions = bytearray()
    mask_hashes = bytearray()
    summary = {"schema_version":1,"seed":10,"role":"reused calibration; primary horizon",
               "ranges":{},"score":0.,"actions":0,"epochs":0,"complete":False,
               "profile_script_sha256":sha256(Path(__file__)),
               "protocol_sha256":sha256(Path(__file__).with_name("protocol.v1.json")),
               "snapshot_paths":[],"runtime":{"python":sys.version.split()[0],"numpy":np.__version__}}
    if progress.is_file():
        with np.load(progress,allow_pickle=False) as saved:
            summary = json.loads(str(saved["summary"]))
            if summary["profile_script_sha256"] != sha256(Path(__file__)):
                raise ValueError("profile code changed since checkpoint")
            grid,plant.state = saved["grid"],saved["plant"]
            plant.step_count = summary["actions"]
            rng.set_state(("MT19937",saved["rng_keys"],int(saved["rng_pos"]),int(saved["rng_flag"]),float(saved["rng_gauss"])))
            actions,mask_hashes = bytearray(saved["actions"].tobytes()),bytearray(saved["mask_hashes"].tobytes())
    ranges = Ranges(summary["ranges"])
    nca = ProfiledNCA(weights,ranges,summary["epochs"])
    for name,value in weights.__dict__.items():
        if name not in ranges.values:
            ranges.add(name,value)
    started = time.monotonic()

    def save():
        summary["ranges"],summary["epochs"],summary["actions"] = ranges.values,nca.epoch,plant.step_count
        state = rng.get_state()
        temp = progress.with_suffix(".tmp.npz")
        np.savez_compressed(temp,summary=json.dumps(summary),grid=grid,plant=plant.state,
                            rng_keys=state[1],rng_pos=state[2],rng_flag=state[3],rng_gauss=state[4],
                            actions=np.frombuffer(actions,np.uint8),mask_hashes=np.frombuffer(mask_hashes,np.uint8))
        temp.replace(progress)
        output.write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")

    while not summary["complete"]:
        obs = plant.state.astype(np.float32)[None,:]
        ranges.add("scaled_observations",obs*np.asarray([2,.25,4,.15],np.float32),True)
        epochs,masks = draws_for_action(rng)
        mask_hashes.extend(hashlib.sha256(np.packbits(masks.reshape(-1),bitorder="little").tobytes()).digest())
        for index,mask in enumerate(masks):
            before = grid
            grid = nca.step(grid,obs,mask)
            if index == 0 and plant.step_count in (0,9,99,999,4999,9999):
                path = private / f"action_{plant.step_count+1}_epoch_1.npz"
                np.savez_compressed(path,old_grid=before,observation=obs,mask=mask,
                                    pre0=nca.pre0,hidden0=nca.hidden0,pre1=nca.pre1,hidden1=nca.hidden1,
                                    delta=nca.delta,new_grid=grid)
                summary["snapshot_paths"].append(str(path.relative_to(ROOT)).replace("\\","/"))
        scores = nca.readout(grid)[0]
        ranges.add("readout_margin",np.asarray(abs(float(scores[0])-float(scores[1]))))
        action = int(np.argmax(scores))
        _,reward,done = plant.step(action)
        summary["score"] += reward
        actions.append(action)
        if plant.step_count % 100 == 0:
            save()
            print(f"float profile actions={plant.step_count} epochs={nca.epoch} elapsed={time.monotonic()-started:.1f}s",flush=True)
        if done:
            summary.update(complete=True,termination=termination_reason(plant,done),
                           actions_sha256=hashlib.sha256(actions).hexdigest(),
                           ordered_mask_hashes_sha256=hashlib.sha256(mask_hashes).hexdigest(),
                           final_grid_sha256=hashlib.sha256(grid.astype("<f4").tobytes()).hexdigest(),
                           final_plant_sha256=hashlib.sha256(plant.state.astype("<f8").tobytes()).hexdigest())
            baseline = next(json.loads(line) for line in (ROOT / "experiments/p06_cartpole/results.jsonl").read_text().splitlines() if json.loads(line)["seed"]==10)
            summary["matches_recorded_p06"] = all(summary[k]==baseline[k] for k in
                ("score","actions_sha256","ordered_mask_hashes_sha256","final_grid_sha256","final_plant_sha256")) and plant.step_count==baseline["actions"]
            save()
    print(json.dumps({k:v for k,v in summary.items() if k!="ranges"},indent=2),flush=True)


if __name__ == "__main__":
    main()
