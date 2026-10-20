from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import numpy as np

try:
    import torch
except ImportError:
    torch = None

from training.hanoi_nca.run_v2_paper_flow import (
    initialize_pool,
    load_progress,
    sample_batch,
    save_progress,
    train_iteration,
)
from training.hanoi_nca.v2_model import build_v2_model
from training.hanoi_nca.v2_runtime import TorchNCAV2Runtime


@unittest.skipIf(torch is None, "pinned P05 training environment is not installed")
class PaperFlowTests(unittest.TestCase):
    def test_synthetic_warmup_has_equal_targets_at_all_six_outputs(self) -> None:
        observations, targets, n_max = sample_batch("warmup", {}, np.random.RandomState(2), 5, 0)
        self.assertIsNone(n_max)
        self.assertEqual((5, 36), observations.shape)
        np.testing.assert_allclose(targets, (4 * observations.mean(axis=1, keepdims=True)).repeat(6, axis=1))

    def test_resume_restores_pool_optimizer_and_random_streams(self) -> None:
        config = {
            "batch_size": 2,
            "microbatch_size": 1,
            "step_min": 2,
            "step_max": 2,
            "replacement_probability": 0.01,
            "imitation_iterations": 3,
        }
        runtime = TorchNCAV2Runtime(build_v2_model(11))
        optimizer = torch.optim.Adam(runtime.model.parameters(), lr=0.005)
        pool = initialize_pool(runtime, 4, 12)
        rng = np.random.RandomState(13)
        masks = torch.Generator().manual_seed(14)
        train_iteration(runtime, optimizer, pool, {}, rng, masks, "warmup", 0, config)
        with tempfile.TemporaryDirectory() as folder:
            checkpoint = Path(folder) / "resume.pt"
            save_progress(checkpoint, runtime, optimizer, pool, rng, masks, "warmup", 1, config, [], 0.0)
            twin = TorchNCAV2Runtime(build_v2_model(99))
            twin_optimizer = torch.optim.Adam(twin.model.parameters(), lr=0.005)
            twin_pool, twin_rng, twin_masks, phase, iteration, _ = load_progress(
                checkpoint, twin, twin_optimizer, config
            )
            self.assertEqual(("warmup", 1), (phase, iteration))
            next_a = train_iteration(runtime, optimizer, pool, {}, rng, masks, "warmup", 1, config)
            next_b = train_iteration(twin, twin_optimizer, twin_pool, {}, twin_rng, twin_masks, "warmup", 1, config)
            self.assertEqual(next_a, next_b)
            self.assertTrue(torch.equal(pool, twin_pool))
            for left, right in zip(runtime.model.parameters(), twin.model.parameters()):
                self.assertTrue(torch.equal(left, right))


if __name__ == "__main__":
    unittest.main()
