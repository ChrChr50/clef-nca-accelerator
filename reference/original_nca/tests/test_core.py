from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

import numpy as np

from reference.original_nca.core import (
    CanonicalNCA,
    conv1x1,
    conv2d_same,
    damage_with_trace,
    make_io_contract,
    seeded_initial_grid,
    seeded_masks,
)
from reference.original_nca.tools.generate_golden import synthetic_weights
from reference.original_nca.training_contract import (
    GridPool,
    curriculum_targets,
    recurrent_step_count,
)


ROOT = Path(__file__).resolve().parents[3]


def digest(array: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(array, dtype="<f4").tobytes(order="C")).hexdigest()


class CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.nca = CanonicalNCA(synthetic_weights())
        vectors = json.loads(
            (ROOT / "reference/original_nca/golden/golden_vectors.json").read_text()
        )
        cls.golden = next(case for case in vectors["cases"] if case["checkpoint"] == "synthetic-v1")
        with np.load(
            ROOT / "reference/original_nca/golden/golden_arrays.npz",
            allow_pickle=False,
        ) as arrays:
            cls.golden_arrays = {name: arrays[name].copy() for name in arrays.files}

    def assert_cross_platform_golden(
        self, observed: np.ndarray, array_name: str, hash_name: str
    ) -> None:
        np.testing.assert_allclose(
            observed,
            self.golden_arrays[array_name],
            rtol=2e-5,
            atol=2e-5,
        )
        if sys.platform == "win32":
            self.assertEqual(digest(observed), self.golden[hash_name])

    def test_parameter_count(self) -> None:
        self.assertEqual(self.nca.weights.parameter_count, 1916)

    def test_local_update_golden(self) -> None:
        delta = self.nca.local_delta(seeded_initial_grid(1701))
        self.assert_cross_platform_golden(
            delta, "local_delta", "local_delta_sha256_f32le"
        )

    def test_local_operator_against_independent_scalar_oracle(self) -> None:
        grid = seeded_initial_grid(1701)
        row, col = 9, 10
        patch = grid[0, row - 1 : row + 2, col - 1 : col + 2]
        w = self.nca.weights
        first = np.empty(20, dtype=np.float32)
        for output in range(20):
            total = np.float32(w.conv0_bias[output])
            for rr in range(3):
                for cc in range(3):
                    for channel in range(6):
                        total = np.float32(
                            total + np.float32(patch[rr, cc, channel] * w.conv0_kernel[rr, cc, channel, output])
                        )
            first[output] = max(np.float32(0.0), total)
        hidden = np.maximum(
            np.float32(first @ w.conv1_kernel.reshape(20, 30) + w.conv1_bias),
            np.float32(0.0),
        )
        expected = np.float32(hidden @ w.conv2_kernel.reshape(30, 6) + w.conv2_bias)
        observed = self.nca.local_delta(grid)[0, row, col]
        np.testing.assert_allclose(observed, expected, rtol=2e-6, atol=2e-6)

    def test_convolution_shapes_are_executable(self) -> None:
        grid = seeded_initial_grid(9)
        w = self.nca.weights
        first = conv2d_same(grid, w.conv0_kernel, w.conv0_bias)
        second = conv1x1(first, w.conv1_kernel, w.conv1_bias)
        self.assertEqual(first.shape, (1, 32, 32, 20))
        self.assertEqual(second.shape, (1, 32, 32, 30))

    def test_complete_step_and_readout_golden(self) -> None:
        grid = seeded_initial_grid(1701)
        mask = seeded_masks(2701, 1)[0]
        observation = np.asarray([[0.01, -0.02, 0.03, -0.04]], dtype=np.float32)
        state = self.nca.step(grid, observation, mask)
        self.assert_cross_platform_golden(
            state, "complete_step", "complete_step_sha256_f32le"
        )
        np.testing.assert_allclose(
            self.nca.readout(state)[0],
            np.asarray(self.golden["complete_step_readout"], np.float32),
            rtol=2e-5,
            atol=2e-5,
        )

    def test_fixed_rollout_golden(self) -> None:
        state = seeded_initial_grid(1701)
        masks = seeded_masks(2701, 4)
        observation = np.asarray([[0.01, -0.02, 0.03, -0.04]], dtype=np.float32)
        for mask in masks:
            state = self.nca.step(state, observation, mask)
        self.assert_cross_platform_golden(
            state, "four_step_rollout", "rollout_sha256_f32le"
        )

    def test_seeded_stochastic_mask_and_supplied_noise(self) -> None:
        seed = 4103
        masks = seeded_masks(seed, 2)
        expected_masks = np.random.RandomState(seed).random_sample(
            (2, 1, 32, 32, 1)
        ) <= 0.5
        np.testing.assert_array_equal(masks, expected_masks)
        np.testing.assert_array_equal(masks, seeded_masks(seed, 2))

        grid = seeded_initial_grid(4104)
        noise = np.linspace(
            -0.01, 0.01, num=32 * 32 * 6, dtype=np.float32
        ).reshape(1, 32, 32, 6)
        observation = np.zeros((1, 4), dtype=np.float32)
        active_inputs = (False,) * 8
        observed = self.nca.step(
            grid,
            observation,
            masks[0],
            update_noise=noise,
            active_inputs=active_inputs,
        )
        delta = np.float32(self.nca.local_delta(grid) + noise)
        expected = np.float32(grid + delta * masks[0].astype(np.float32))
        cut, pos = make_io_contract(1, active_inputs)
        expected = np.float32(expected * cut + pos)
        np.testing.assert_array_equal(observed, expected)

    def test_damage_trace_matches_authoritative_circle_replacement(self) -> None:
        grid = seeded_initial_grid(4201)
        centers = np.asarray([[[[0.125]]], [[[-0.25]]]], dtype=np.float32)
        radii = np.asarray([[[0.35]]], dtype=np.float32)
        replacements = np.linspace(
            -1.0, 1.0, num=32 * 32 * 6, dtype=np.float32
        ).reshape(1, 32, 32, 6)
        observed = damage_with_trace(grid, centers, radii, replacements)

        x = np.linspace(-1.0, 1.0, 32, dtype=np.float32)[None, None, :]
        y = np.linspace(-1.0, 1.0, 32, dtype=np.float32)[None, :, None]
        outside = (
            ((x - centers[0].reshape(1, 1, 1)) / radii) ** 2
            + ((y - centers[1].reshape(1, 1, 1)) / radii) ** 2
        ) > 1.0
        expected = np.float32(np.where(outside[..., None], grid, replacements))
        np.testing.assert_array_equal(observed, expected)
        self.assertTrue(np.all(observed[~outside] == replacements[~outside]))
        self.assertTrue(np.all(observed[outside] == grid[outside]))

    def test_raw_io_clamping_and_output_hidden_accumulation(self) -> None:
        zero = np.zeros((1, 32, 32, 6), dtype=np.float32)
        mask = np.zeros((1, 32, 32, 1), dtype=np.bool_)
        obs = np.asarray([[1.0, 2.0, 3.0, 4.0]], dtype=np.float32)
        state1 = self.nca.step(zero, obs, mask)
        state2 = self.nca.step(state1, obs, mask)
        self.assertEqual(float(state2[0, 11, 26, 4]), 1.0)
        self.assertEqual(float(state2[0, 13, 16, 4]), 2.0)
        self.assertEqual(float(state2[0, 11, 26, 0]), 2.0)

    def test_deleted_input_becomes_intermediate(self) -> None:
        cut, pos = make_io_contract(1, (False, True, True, True, True, True, True, True))
        self.assertTrue(np.all(cut[0, 11, 26, [0, 1, 4, 5]] == 1.0))
        self.assertTrue(np.all(pos[0, 11, 26] == 0.0))

    def test_curriculum_and_pool_contract(self) -> None:
        inputs = np.arange(16, dtype=np.float32).reshape(2, 8)
        targets = curriculum_targets(inputs)
        np.testing.assert_array_equal(targets[:, 0], np.mean(inputs, axis=1) * 4.0)
        np.testing.assert_array_equal(targets[:, 0], targets[:, 1])
        pool = GridPool.initialize(pool_size=2, batch_size=1, seed=7)
        sampled = pool.sample(1)
        updated = sampled + np.float32(1.0)
        pool.commit(updated)
        np.testing.assert_array_equal(pool.sample(1), updated)

    def test_hidden_state_persistence_and_pool_reinitialization(self) -> None:
        pool = GridPool.initialize(pool_size=1, batch_size=1, seed=51)
        initial = pool.sample(0)
        persistent = np.float32(initial + np.float32(0.25))
        pool.commit(persistent)
        resampled = pool.sample(0)
        np.testing.assert_array_equal(resampled, persistent)
        pool.commit(resampled)

        reset = pool.reinitialize_and_sample(0, seed=52)
        np.testing.assert_array_equal(reset, seeded_initial_grid(52))
        self.assertFalse(np.array_equal(reset, persistent))

    def test_recurrent_schedule_is_50_through_59(self) -> None:
        rng = np.random.RandomState(99)
        observed = {recurrent_step_count(rng) for _ in range(1000)}
        self.assertEqual(observed, set(range(50, 60)))


if __name__ == "__main__":
    unittest.main()
