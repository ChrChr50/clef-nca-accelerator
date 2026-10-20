"""Execute the pinned upstream Python classes; replace only random mask draws.

This local diagnostic needs its own TensorFlow environment. No source or weights
are copied. JSON lines over stdin/stdout carry explicit replay inputs.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[2] / "tmp/p06-matplotlib"))

import numpy as np
import tensorflow as tf


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / "self-organized-control/code"))
    from SelfOrgControl.NeuralCA import NeuralCA
    from SelfOrgControl.CustomCartPoleEnv import CartPoleEnvContiReward

    tf.config.threading.set_inter_op_parallelism_threads(1)
    tf.config.threading.set_intra_op_parallelism_threads(1)
    uniform = tf.Variable(tf.zeros([1, 32, 32, 1]), trainable=False)
    original_uniform = tf.random.uniform

    def supplied_uniform(shape, *args, **kwargs):
        # The inference configuration calls uniform only for the shared mask.
        # 0.25/0.75 are safely on opposite sides of the source <=0.5 predicate.
        return tf.reshape(uniform.read_value(), shape)

    tf.random.uniform = supplied_uniform
    inputs = [(11,26),(25,20),(5,20),(19,6),(19,26),(5,12),(25,12),(11,6)]
    outputs = [(13,16),(17,16)]
    ca = NeuralCA(input_electrodes=inputs, output_electrodes=outputs,
                  custom_input_signal=True, batch_size=1, size=32, channel_n=6,
                  first_lay_size=30, all_cells_alive=True, bound_values=False,
                  use_hidden_inputs=False, add_noise=False)
    base = root / "self-organized-control/demo/models/model2"
    manifest = json.loads((base / "model.json").read_text())
    raw = np.fromfile(base / "group1-shard1of1.bin", dtype="<f4")
    weights, offset = [], 0
    for group in manifest["weightsManifest"]:
        for spec in group["weights"]:
            count = int(np.prod(spec["shape"]))
            weights.append(raw[offset:offset+count].reshape(spec["shape"]))
            offset += count
    assert offset == 1916 == raw.size
    ca.dmodel.set_weights(weights)

    @tf.function(input_signature=[tf.TensorSpec([1,32,32,6], tf.float32),
                                  tf.TensorSpec([8], tf.float32),
                                  tf.TensorSpec([None,1,32,32,1], tf.bool)])
    def advance(grid, updates, masks):
        for index in tf.range(tf.shape(masks)[0]):
            uniform.assign(tf.where(masks[index], 0.25, 0.75))
            grid = ca(grid, updates=updates)
        return grid

    plant = CartPoleEnvContiReward(auto_reset=False, cyclic_boundary=False,
                                  show_arrows=False)
    grid = None
    print(json.dumps({"ready": True, "python": sys.version.split()[0],
                      "numpy": np.__version__, "tensorflow": tf.__version__,
                      "keras": "2.15.0", "oneDNN": False,
                      "source_module": str(Path(sys.modules[NeuralCA.__module__].__file__))}),
          flush=True)
    for line in sys.stdin:
        command = json.loads(line)
        if command["op"] == "init":
            grid = np.frombuffer(bytes.fromhex(command["grid"]), dtype="<f4").copy().reshape(1,32,32,6)
            plant.state = tuple(command["plant"])
            plant.step_nb = int(command.get("steps", 0))
            plant.steps_beyond_done = None
            reply = {"initialized": True,
                     "cut": ca.cut_io_mask.numpy().astype("<f4").tobytes().hex(),
                     "markers": ca.pos_io_channel.numpy().astype("<f4").tobytes().hex()}
        elif command["op"] in ("step", "probe"):
            epochs = int(command["epochs"])
            bits = np.unpackbits(np.frombuffer(bytes.fromhex(command["masks"]), dtype=np.uint8),
                                 bitorder="little")[:epochs*1024]
            masks = bits.astype(bool).reshape(epochs,1,32,32,1)
            if command["op"] == "probe":
                probe_grid = np.frombuffer(bytes.fromhex(command["grid"]), dtype="<f4").copy().reshape(1,32,32,6)
                obs = np.asarray(command["observation"], dtype=np.float32)
                delta = ca.dmodel(tf.convert_to_tensor(probe_grid)).numpy()
                value = advance(probe_grid, np.repeat(obs*np.asarray([2,.25,4,.15],np.float32),2), masks).numpy()
                reply = {"grid": value.astype("<f4").tobytes().hex(),
                         "delta": delta.astype("<f4").tobytes().hex()}
            else:
                # Match E01's declared float32 observation/scaling boundary.
                obs = np.asarray(plant.state, dtype=np.float32)
                updates = np.repeat(obs*np.asarray([2,.25,4,.15],np.float32),2)
                grid = advance(grid, updates, masks).numpy()
                scores = ca.get_output_cell_states(grid).numpy()[0,:,0]
                action = int(np.argmax(scores))
                state, reward, done, _ = plant.step(action)
                reason = None
                if done:
                    if abs(float(state[0])) > plant.x_threshold:
                        reason = "cart_position_limit"
                    elif abs(float(state[2])) > plant.theta_threshold_radians:
                        reason = "pole_angle_limit"
                    else:
                        reason = "source_horizon"
                reply = {"grid": grid.astype("<f4").tobytes().hex(),
                         "scores": scores.tolist(), "action": action,
                         "plant": np.asarray(state, dtype=np.float64).tolist(),
                         "reward": float(reward), "done": bool(done), "reason": reason}
        elif command["op"] == "quit":
            break
        else:
            raise ValueError(command["op"])
        print(json.dumps(reply, allow_nan=False), flush=True)
    tf.random.uniform = original_uniform


if __name__ == "__main__":
    main()
