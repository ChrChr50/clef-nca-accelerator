from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import unittest

import numpy as np

try:
    import torch
except ImportError:
    torch = None

from reference.hanoi.environment import ACTIONS, HanoiState, encode_observation
from training.hanoi_nca.layout import layout_statistics, load_layout
from training.hanoi_nca.v2_adapter import HanoiV2Adapter, LAYOUT_PATH
from training.hanoi_nca.v2_model import PARAMETER_COUNT, build_v2_model
from training.hanoi_nca.v2_runtime import TorchNCAV2Runtime


ROOT = Path(__file__).resolve().parents[3]


class V2LayoutTests(unittest.TestCase):
    def test_disk_major_input_and_directed_action_matrix(self) -> None:
        layout = load_layout(LAYOUT_PATH)
        self.assertEqual(36, len(layout.input_coordinates))
        self.assertEqual(6, len(layout.output_coordinates))
        for disk in range(8):
            self.assertEqual(
                tuple((11 + disk, 12 + field) for field in range(4)),
                layout.input_coordinates[4 * disk : 4 * disk + 4],
            )
        self.assertEqual(tuple((19, 12 + field) for field in range(4)), layout.input_coordinates[32:36])
        self.assertEqual(
            tuple(f"{source}->{destination}" for source, destination in ACTIONS),
            layout.action_names,
        )
        self.assertEqual(
            tuple((17 + source, 16 + destination) for source, destination in ACTIONS),
            layout.output_coordinates,
        )
        stats = layout_statistics(layout)
        self.assertEqual(0, stats["collision_count"])
        self.assertEqual(8, stats["chebyshev_input_output"]["maximum"])

    def test_deployment_shaped_modules_do_not_import_oracle(self) -> None:
        for name in ("v2_adapter.py", "v2_model.py", "v2_runtime.py"):
            path = ROOT / "training" / "hanoi_nca" / name
            tree = ast.parse(path.read_text(encoding="utf-8"))
            modules = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    modules.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    modules.append(node.module or "")
            self.assertFalse(any("oracle" in item for item in modules), name)

    def test_v2_manifest_and_checkpoint_remain_experimental(self) -> None:
        path = ROOT / "training" / "hanoi_nca" / "difference_manifest_v2.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(36, manifest["logical_interface"]["observation_width"])
        self.assertEqual(2338, manifest["local_graph"]["parameter_count"])
        self.assertEqual([-5, 5], manifest["epoch"]["inference_bound"])
        self.assertFalse(manifest["functional_freeze_eligible"])
        checkpoint = ROOT / manifest["measured_candidate"]["checkpoint"]
        self.assertEqual(
            manifest["measured_candidate"]["checkpoint_sha256"],
            hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
        )


@unittest.skipIf(torch is None, "pinned P05 training environment is not installed")
class V2RuntimeTests(unittest.TestCase):
    def test_graph_shape_count_and_zero_padded_perception(self) -> None:
        model = build_v2_model(17)
        self.assertEqual(PARAMETER_COUNT, sum(parameter.numel() for parameter in model.parameters()))
        self.assertEqual((20, 8, 3, 3), tuple(model.conv1.weight.shape))
        self.assertEqual((30, 20, 1, 1), tuple(model.conv2.weight.shape))
        self.assertEqual((8, 30, 1, 1), tuple(model.conv3.weight.shape))
        rng = np.random.RandomState(11)
        state = rng.uniform(-1, 1, (1, 8, 32, 32)).astype(np.float32)
        weight = model.conv1.weight.detach().numpy()
        bias = model.conv1.bias.detach().numpy()
        with torch.no_grad():
            layer = model.conv1(torch.from_numpy(state)).numpy()
        for row, column in ((0, 0), (15, 16), (31, 31)):
            patch = np.zeros((8, 3, 3), dtype=np.float32)
            for dr in range(-1, 2):
                for dc in range(-1, 2):
                    rr, cc = row + dr, column + dc
                    if 0 <= rr < 32 and 0 <= cc < 32:
                        patch[:, dr + 1, dc + 1] = state[0, :, rr, cc]
            expected = np.sum(weight * patch[None, ...], axis=(1, 2, 3)) + bias
            np.testing.assert_allclose(layer[0, :, row, column], expected, rtol=2e-5, atol=2e-5)

    def test_numpy_torch_rewrite_and_bounded_step_agree(self) -> None:
        rng = np.random.RandomState(12)
        state = rng.uniform(-4, 4, (2, 32, 32, 8)).astype(np.float32)
        delta = rng.uniform(-7, 7, (2, 32, 32, 8)).astype(np.float32)
        mask = rng.randint(0, 2, (2, 32, 32, 1)).astype(np.float32)
        observations = np.asarray(
            [
                encode_observation(HanoiState((0, 2, 1), 2)),
                encode_observation(HanoiState((1, 0, 2, 1), 0)),
            ],
            dtype=np.float32,
        )
        adapter = HanoiV2Adapter()
        runtime = TorchNCAV2Runtime(build_v2_model(3))
        expected = adapter.step(state, observations, delta, mask)
        with torch.no_grad():
            observed = runtime.rewrite(
                torch.clamp(
                    torch.from_numpy(state.transpose(0, 3, 1, 2))
                    + torch.from_numpy(delta.transpose(0, 3, 1, 2))
                    * torch.from_numpy(mask.transpose(0, 3, 1, 2)),
                    -5.0,
                    5.0,
                ),
                torch.from_numpy(observations),
            ).numpy().transpose(0, 2, 3, 1)
        np.testing.assert_array_equal(observed, expected)
        self.assertLessEqual(float(np.max(np.abs(observed))), 5.0)
        self.assertEqual(0, int(adapter.select_action(np.zeros((1, 6), dtype=np.float32))[0]))

    def test_markers_input_clamp_persistence_and_supplied_masks(self) -> None:
        model = build_v2_model(4)
        with torch.no_grad():
            for parameter in model.parameters():
                parameter.zero_()
            model.conv3.bias.fill_(10.0)
        runtime = TorchNCAV2Runtime(model)
        observation = torch.tensor(
            [encode_observation(HanoiState((0, 2, 1), 2))], dtype=torch.float32
        )
        state = runtime.initial_state(1, 10)
        zero = torch.zeros((1, 1, 32, 32))
        one = torch.ones((1, 1, 32, 32))
        with torch.no_grad():
            injected = runtime.run(state, observation, 0, 0.5)
            unchanged = runtime.run(injected, observation, 1, 0.5, masks=[zero])
            fired = runtime.run(injected, observation, 1, 0.5, masks=[one])
            repeated = runtime.run(fired, observation, 2, 0.5, masks=[one, one])
            changed_observation = torch.tensor(
                [encode_observation(HanoiState((2, 1, 0), 1))], dtype=torch.float32
            )
            mask_zero_rewrite = runtime.run(injected, changed_observation, 1, 0.5, masks=[zero])
            random_a = runtime.run(injected, observation, 3, 0.5, torch.Generator().manual_seed(99))
            random_b = runtime.run(injected, observation, 3, 0.5, torch.Generator().manual_seed(99))
        self.assertEqual(observation[0, 0].item(), injected[0, 0, 11, 12].item())
        self.assertEqual(1.0, injected[0, 6, 11, 12].item())
        self.assertEqual(1.0, injected[0, 7, 17, 17].item())
        self.assertTrue(torch.all(unchanged[:, :6] == injected[:, :6]))
        self.assertEqual(5.0, fired[0, 0, 0, 0].item())
        self.assertEqual(1.0, fired[0, 7, 17, 17].item())
        self.assertEqual(0.0, fired[0, 6, 0, 0].item())
        self.assertLessEqual(float(repeated.abs().max()), 5.0)
        self.assertEqual(changed_observation[0, 2].item(), mask_zero_rewrite[0, 0, 11, 14].item())
        self.assertTrue(torch.equal(random_a, random_b))
        self.assertEqual(0, int(runtime.decide(torch.zeros_like(injected))[0]))


if __name__ == "__main__":
    unittest.main()
