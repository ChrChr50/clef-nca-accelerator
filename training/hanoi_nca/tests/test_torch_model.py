from __future__ import annotations

import unittest

import numpy as np

try:
    import torch
except ImportError:
    torch = None

from reference.original_nca.core import CanonicalNCA, NCAWeights
from training.hanoi_nca.adapter import HanoiAdapter
from training.hanoi_nca.model import PARAMETER_COUNT, build_model
from training.hanoi_nca.runtime import TorchNCARuntime


@unittest.skipIf(torch is None, "pinned P05 training environment is not installed")
class TorchModelTests(unittest.TestCase):
    def test_graph_parameter_count_and_numpy_operator_equivalence(self) -> None:
        model = build_model(44)
        self.assertEqual(PARAMETER_COUNT, sum(parameter.numel() for parameter in model.parameters()))
        state_dict = model.state_dict()
        weights = NCAWeights(
            state_dict["conv1.weight"].numpy().transpose(2, 3, 1, 0),
            state_dict["conv1.bias"].numpy(),
            state_dict["conv2.weight"].numpy().transpose(2, 3, 1, 0),
            state_dict["conv2.bias"].numpy(),
            state_dict["conv3.weight"].numpy().transpose(2, 3, 1, 0),
            state_dict["conv3.bias"].numpy(),
        )
        rng = np.random.RandomState(4)
        grid = rng.uniform(-0.1, 0.1, (2, 32, 32, 6)).astype(np.float32)
        expected = CanonicalNCA(weights).local_delta(grid)
        with torch.no_grad():
            observed = model(torch.from_numpy(grid.transpose(0, 3, 1, 2))).numpy().transpose(0, 2, 3, 1)
        np.testing.assert_allclose(observed, expected, rtol=2e-5, atol=2e-5)

    def test_torch_and_numpy_rewrite_match_for_both_marker_policies(self) -> None:
        rng = np.random.RandomState(7)
        state = rng.uniform(-2.0, 2.0, (2, 32, 32, 6)).astype(np.float32)
        observations = rng.uniform(-1.0, 1.0, (2, 36)).astype(np.float32)
        for policy in ("accumulate", "clamp_one"):
            expected = HanoiAdapter(output_hidden_policy=policy).rewrite(state, observations)
            runtime = TorchNCARuntime(build_model(1), policy)
            with torch.no_grad():
                observed = runtime.rewrite(
                    torch.from_numpy(state.transpose(0, 3, 1, 2)),
                    torch.from_numpy(observations),
                ).numpy().transpose(0, 2, 3, 1)
            np.testing.assert_array_equal(observed, expected)


if __name__ == "__main__":
    unittest.main()
