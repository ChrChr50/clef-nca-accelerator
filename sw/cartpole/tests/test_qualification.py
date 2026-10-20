from __future__ import annotations

import tempfile
import unittest
import hashlib
from pathlib import Path

import numpy as np

from reference.original_nca.cartpole import CartPole
from reference.original_nca.core import CanonicalNCA, seeded_initial_grid
from reference.original_nca.tools.generate_golden import synthetic_weights
from sw.cartpole.qualification import (
    draws_for_action, load_config, run_episode, termination_reason,
)


class QualificationTests(unittest.TestCase):
    def test_accepted_manifest_and_identity(self) -> None:
        config, digest = load_config()
        self.assertEqual(config["seeds"], list(range(10, 20)))
        self.assertEqual(config["success_threshold"]["minimum_horizon_completions"], 8)
        self.assertEqual(config["episode"]["plant_max_steps_field"], 10_000)
        self.assertEqual(len(digest), 64)

    def test_draw_order_matches_sequential_epoch_draws(self) -> None:
        left = np.random.RandomState(13)
        right = np.random.RandomState(13)
        np.testing.assert_array_equal(CartPole.reset(left).state, CartPole.reset(right).state)
        count, batched = draws_for_action(left)
        self.assertEqual(count, int(right.randint(50, 60)))
        sequential = np.stack(
            [right.random_sample((1, 32, 32, 1)) <= 0.5 for _ in range(count)]
        )
        np.testing.assert_array_equal(batched, sequential)
        self.assertEqual(left.get_state()[2], right.get_state()[2])

    def test_termination_reason_requires_balanced_horizon(self) -> None:
        plant = CartPole(np.zeros(4, np.float64), step_count=10_001)
        self.assertEqual(termination_reason(plant, True), "source_horizon")
        plant.state[2] = 1.0
        self.assertEqual(termination_reason(plant, True), "pole_angle_limit")
        self.assertIsNone(termination_reason(plant, False))

    def test_checkpoint_resume_is_deterministic_and_rejects_wrong_config(self) -> None:
        nca = CanonicalNCA(synthetic_weights())
        _, config_sha256 = load_config()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "progress.npz"
            self.assertIsNone(run_episode(
                nca, 10, config_sha256, "synthetic", path,
                checkpoint_interval=1, action_limit=2,
            ))
            self.assertTrue(path.is_file())
            with np.load(path, allow_pickle=False) as saved:
                self.assertEqual(int(saved["step_count"]), 2)
                first_actions = saved["actions"].tobytes()
            with self.assertRaises(ValueError):
                run_episode(nca, 10, "wrong", "synthetic", path, action_limit=3)
            self.assertIsNone(run_episode(
                nca, 10, config_sha256, "synthetic", path,
                checkpoint_interval=1, action_limit=3,
            ))
            with np.load(path, allow_pickle=False) as saved:
                self.assertEqual(int(saved["step_count"]), 3)
                self.assertEqual(saved["actions"].tobytes()[:2], first_actions)
                self.assertEqual(len(saved["mask_hashes"].tobytes()), 3 * 32)

    def test_e01_qualification_prefix_matches_direct_p03_operator(self) -> None:
        nca = CanonicalNCA(synthetic_weights())
        _, config_sha256 = load_config()
        rng = np.random.RandomState(10)
        plant = CartPole.reset(rng)
        grid = seeded_initial_grid(10 ^ 0x5A17)
        direct_actions = bytearray()
        direct_score = 0.0
        for _ in range(8):
            observation = plant.state.astype(np.float32)[None, :]
            epochs = int(rng.randint(50, 60))
            for _ in range(epochs):
                mask = rng.random_sample((1, 32, 32, 1)) <= 0.5
                grid = nca.step(grid, observation, mask)
            action = int(nca.action(grid)[0])
            direct_actions.append(action)
            _, reward, _ = plant.step(action)
            direct_score += reward
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            progress = folder / "p06.npz"
            self.assertIsNone(run_episode(
                nca, 10, config_sha256, "synthetic", progress,
                checkpoint_interval=1, action_limit=8,
            ))
            with np.load(progress, allow_pickle=False) as saved:
                self.assertEqual(int(saved["step_count"]), 8)
                self.assertEqual(float(saved["score"]), direct_score)
                self.assertEqual(
                    hashlib.sha256(saved["actions"].tobytes()).hexdigest(),
                    hashlib.sha256(direct_actions).hexdigest(),
                )
                np.testing.assert_array_equal(saved["plant_state"], plant.state)
                np.testing.assert_array_equal(saved["grid"], grid)


if __name__ == "__main__":
    unittest.main()
