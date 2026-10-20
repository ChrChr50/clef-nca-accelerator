from __future__ import annotations

import unittest

import numpy as np

try:
    import torch
except ImportError:
    torch = None

from training.hanoi_nca.run_v3_teaching import LAYOUT, LAYOUT_PATH, STAGES, passed, source_indices, synthetic_batch
from training.hanoi_nca.layout import load_layout
from training.hanoi_nca.v2_adapter import LAYOUT_PATH as V2_LAYOUT_PATH
from training.hanoi_nca.v3_runtime import TorchNCAV3Runtime, overflow_penalty
from training.hanoi_nca.v4_runtime import TorchNCAV4Runtime, smooth_bound
from training.hanoi_nca.v2_model import build_v2_model


@unittest.skipIf(torch is None, "pinned P05 training environment is not installed")
class V3TeachingTests(unittest.TestCase):
    def test_scaled_synthetic_target_keeps_original_variance(self) -> None:
        for width in (1, 8, 36):
            obs, target = synthetic_batch(np.random.RandomState(7), 4000, width)
            self.assertEqual((4000, 36), obs.shape)
            self.assertEqual((4000, 6), target.shape)
            np.testing.assert_array_equal(target[:, 0:1], target[:, 5:6])
            self.assertTrue(0.60 < float(np.mean(target[:, 0] ** 2)) < 0.73)
            self.assertTrue(np.all(np.count_nonzero(obs, axis=1) == width))

    def test_unclipped_output_keeps_gradient_and_overflow_penalty(self) -> None:
        class ConstantDelta(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.amount = torch.nn.Parameter(torch.tensor(6.0))

            def forward(self, state):
                return torch.ones_like(state) * self.amount

        model = ConstantDelta()
        runtime = TorchNCAV3Runtime(model)
        state = torch.zeros((1, 8, 32, 32))
        observations = torch.zeros((1, 36))
        evolved = runtime.step(state, observations)
        scores = runtime.readout(evolved)
        self.assertEqual(6.0, float(scores[0, 0].detach()))
        self.assertGreater(float(overflow_penalty(evolved).detach()), 0.0)
        scores.mean().backward()
        self.assertEqual(1.0, float(model.amount.grad))

    def test_gate_rejects_aged_or_unstable_states(self) -> None:
        self.assertEqual("local_relay", STAGES[0][0])
        good = {"normalized_mse": 0.10, "max_abs_state": 4.0}
        bad = {"normalized_mse": 0.20, "max_abs_state": 4.0}
        unstable = {"normalized_mse": 0.10, "max_abs_state": 5.1}
        self.assertTrue(passed(0, good, good))
        self.assertFalse(passed(0, good, bad))
        self.assertFalse(passed(0, unstable, good))

    def test_relay_source_radii_expand_to_all_inputs(self) -> None:
        self.assertEqual((23,), source_indices("local_relay"))
        counts = [len(source_indices(f"relay_r{radius}")) for radius in (3, 4, 5, 6, 8)]
        self.assertEqual(sorted(counts), counts)
        self.assertEqual(36, counts[-1])
        self.assertGreater(counts[0], 1)

    def test_v6_layout_unblocks_all_input_sources(self) -> None:
        old = load_layout(V2_LAYOUT_PATH)
        def trapped(layout):
            inputs = set(layout.input_coordinates)
            return [i for i, (row, col) in enumerate(layout.input_coordinates)
                    if all((r, c) in inputs for r in range(row - 1, row + 2)
                           for c in range(col - 1, col + 2))]
        self.assertEqual(14, len(trapped(old)))
        self.assertEqual([], trapped(LAYOUT))
        self.assertEqual(tuple(range(36)), source_indices("relay_r8"))
        self.assertEqual(old.input_names, LAYOUT.input_names)
        self.assertEqual(old.action_names, LAYOUT.action_names)
        self.assertEqual(old.output_coordinates, LAYOUT.output_coordinates)
        self.assertEqual(LAYOUT, load_layout(LAYOUT_PATH))

    def test_explicit_v6_runtime_rewrites_spaced_input_sites(self) -> None:
        runtime = TorchNCAV4Runtime(build_v2_model(7), layout_path=LAYOUT_PATH)
        observations = torch.arange(36, dtype=torch.float32).reshape(1, 36)
        state = runtime.rewrite(torch.zeros((1, 8, 32, 32)), observations)
        for index, (row, col) in enumerate(LAYOUT.input_coordinates):
            self.assertEqual(float(index), float(state[0, 0, row, col]))
            self.assertEqual(1.0, float(state[0, 6, row, col]))
        self.assertEqual(0.0, float(state[0, 0, 15, 10]))
        self.assertEqual(LAYOUT.output_coordinates, runtime.output_coordinates)

    def test_smooth_bound_is_finite_differentiable_and_mask_respecting(self) -> None:
        class ConstantDelta(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.amount = torch.nn.Parameter(torch.tensor(60.0))

            def forward(self, state):
                return torch.ones_like(state) * self.amount

        model = ConstantDelta()
        runtime = TorchNCAV4Runtime(model)
        state = torch.zeros((1, 8, 32, 32))
        observations = torch.zeros((1, 36))
        mask = torch.zeros((1, 1, 32, 32))
        row, column = runtime.output_coordinates[0]
        mask[:, :, row, column] = 1.0
        evolved = runtime.step(state, observations, mask)
        score = runtime.readout(evolved)[0, 0]
        self.assertGreater(float(score.detach()), 4.0)
        self.assertLess(float(score.detach()), 5.0)
        self.assertEqual(0.0, float(runtime.readout(evolved)[0, 1].detach()))
        score.backward()
        self.assertGreater(float(model.amount.grad), 0.0)
        self.assertLess(float(smooth_bound(torch.tensor(1e6))), 5.0)


if __name__ == "__main__":
    unittest.main()
