from __future__ import annotations

import dataclasses
import hashlib
import json
import unittest
from pathlib import Path

import numpy as np

from reference.original_nca.cartpole import CartPole
from reference.original_nca.core import CanonicalNCA, NCAWeights, seeded_initial_grid
from reference.original_nca.core import INPUT_COORDINATES, OUTPUT_COORDINATES
from reference.original_nca.tools.generate_golden import synthetic_weights
from sw.cartpole.deployment import CartPoleHost, DecisionTrace, ReferenceController


ROOT = Path(__file__).resolve().parents[3]


def zero_nca() -> CanonicalNCA:
    weights = NCAWeights(
        np.zeros((3, 3, 6, 20), np.float32), np.zeros(20, np.float32),
        np.zeros((1, 1, 20, 30), np.float32), np.zeros(30, np.float32),
        np.zeros((1, 1, 30, 6), np.float32), np.zeros(6, np.float32),
    )
    return CanonicalNCA(weights)


class DeploymentTests(unittest.TestCase):
    def test_versioned_manifests_bind_immutable_sources(self) -> None:
        interface = json.loads((ROOT / "sw/cartpole/interface.v1.json").read_text())
        replay = json.loads((ROOT / "sw/cartpole/replay.v1.json").read_text())
        self.assertEqual(interface["schema_version"], 1)
        self.assertEqual(replay["schema_version"], 1)
        for key, path in (
            ("operator_manifest", "reference/original_nca/operator_manifest.json"),
            ("plant_module", "reference/original_nca/cartpole.py"),
            ("operator_module", "reference/original_nca/core.py"),
        ):
            self.assertEqual(interface["authority"][key], path)
            self.assertEqual(
                interface["authority"][f"{key}_sha256"],
                hashlib.sha256((ROOT / path).read_bytes()).hexdigest(),
            )
        original = json.loads((ROOT / "reference/original_nca/operator_manifest.json").read_text())
        io = interface["host_to_controller"]
        self.assertEqual(io["input_scale"], original["io"]["observation_scale"])
        self.assertEqual(io["input_coordinates_row_col"], original["io"]["input_coordinates"])
        self.assertEqual(io["recurrent_steps_allowed"], original["schedule"]["executed_step_values"])
        self.assertEqual(interface["controller_to_host"]["readout_coordinates_row_col"], original["io"]["output_coordinates"])
        self.assertEqual(interface["controller"]["learned_parameters"], 1916)
        self.assertIn("episode_grid_reset", replay["unresolved_g3e"])
        self.assertEqual(
            replay["decision_record_fields"],
            [field.name for field in dataclasses.fields(DecisionTrace)],
        )

    def test_reference_adapter_matches_direct_operator_and_plant(self) -> None:
        nca = CanonicalNCA(synthetic_weights())
        initial_grid = seeded_initial_grid(17)
        plant_state = np.asarray([0.01, -0.02, 0.03, -0.04], np.float64)
        plant = CartPole(plant_state.copy())
        direct_plant = CartPole(plant_state.copy())
        masks = (np.random.RandomState(23).random_sample((50, 1, 32, 32, 1)) <= 0.5)
        adapter = ReferenceController(nca, initial_grid)
        host = CartPoleHost(plant, adapter)
        trace = host.step(masks)

        direct_grid = initial_grid.copy()
        obs = plant_state.astype(np.float32)[None, :]
        for mask in masks:
            direct_grid = nca.step(direct_grid, obs, mask)
        direct_scores = nca.readout(direct_grid)[0]
        direct_action = int(nca.action(direct_grid)[0])
        _, direct_reward, direct_done = direct_plant.step(direct_action)

        np.testing.assert_array_equal(adapter.grid, direct_grid)
        np.testing.assert_array_equal(plant.state, direct_plant.state)
        self.assertEqual(trace.action, direct_action)
        self.assertEqual(trace.raw_scores_f32le_hex, direct_scores.astype("<f4").tobytes().hex())
        self.assertEqual(trace.reward, direct_reward)
        self.assertEqual(trace.terminal, direct_done)
        self.assertEqual(trace.recurrent_steps, 50)
        self.assertEqual(trace.elapsed_plant_steps, 1)
        self.assertEqual(trace.observation_f32le_hex, plant_state.astype("<f4").tobytes().hex())

    def test_replay_and_persistence_require_explicit_state_and_draws(self) -> None:
        nca = zero_nca()
        grid = np.zeros((1, 32, 32, 6), np.float32)
        masks = np.ones((50, 1, 32, 32, 1), np.bool_)
        noise = np.full((50, 1, 32, 32, 6), 0.001, np.float32)
        plant_state = np.asarray([0.0, 0.0, 0.0, 0.0], np.float64)

        def run_once():
            controller = ReferenceController(nca, grid)
            host = CartPoleHost(CartPole(plant_state.copy()), controller)
            traces = [host.step(masks, noise), host.step(masks, noise)]
            return traces, controller.grid.copy()

        first, first_grid = run_once()
        second, second_grid = run_once()
        self.assertEqual(first, second)
        np.testing.assert_array_equal(first_grid, second_grid)
        self.assertEqual(first[0].action, 0)  # raw-score tie chooses action zero
        self.assertAlmostEqual(float(first_grid[0, 13, 16, 4]), 100.1, places=3)
        self.assertEqual(first[1].plant_before_sha256, first[0].plant_after_sha256)
        self.assertNotEqual(first[0].controller_after_sha256, first[1].controller_after_sha256)
        self.assertIsNotNone(first[0].noise_sha256)

    def test_invalid_schedule_and_terminal_are_rejected(self) -> None:
        controller = ReferenceController(zero_nca(), np.zeros((1, 32, 32, 6), np.float32))
        host = CartPoleHost(CartPole(np.asarray([2.401, 0.0, 0.0, 0.0], np.float64)), controller)
        with self.assertRaises(ValueError):
            host.step(np.zeros((49, 1, 32, 32, 1), np.bool_))
        self.assertEqual(host.plant.step_count, 0)
        trace = host.step(np.zeros((50, 1, 32, 32, 1), np.bool_))
        self.assertTrue(trace.terminal)
        with self.assertRaises(RuntimeError):
            host.step(np.zeros((50, 1, 32, 32, 1), np.bool_))

    def test_plant_and_controller_reset_are_not_implicitly_coupled(self) -> None:
        controller = ReferenceController(zero_nca(), np.zeros((1, 32, 32, 6), np.float32))
        masks = np.zeros((50, 1, 32, 32, 1), np.bool_)
        first = CartPoleHost(CartPole(np.zeros(4, np.float64)), controller)
        first.step(masks)
        retained = controller.grid.copy()
        second = CartPoleHost(CartPole(np.zeros(4, np.float64)), controller)
        np.testing.assert_array_equal(second.controller.grid, retained)
        fresh = ReferenceController(zero_nca(), np.zeros((1, 32, 32, 6), np.float32))
        self.assertFalse(np.array_equal(fresh.grid, retained))

    def test_released_horizon_and_reward_include_terminal_action(self) -> None:
        plant = CartPole(np.zeros(4, np.float64), step_count=10_000)
        host = CartPoleHost(
            plant,
            ReferenceController(zero_nca(), np.zeros((1, 32, 32, 6), np.float32)),
        )
        trace = host.step(np.zeros((50, 1, 32, 32, 1), np.bool_))
        self.assertTrue(trace.terminal)
        self.assertEqual(trace.elapsed_plant_steps, 10_001)
        self.assertGreater(trace.reward, 0.0)

    def test_all_eight_scaled_sites_and_output_markers(self) -> None:
        grid = np.zeros((1, 32, 32, 6), np.float32)
        controller = ReferenceController(zero_nca(), grid)
        observation = np.asarray([1.0, 2.0, 3.0, 4.0], np.float32)
        controller.decide(observation, np.zeros((50, 1, 32, 32, 1), np.bool_))
        expected = [2.0, 2.0, 0.5, 0.5, 12.0, 12.0, 0.6, 0.6]
        for (row, col), value in zip(INPUT_COORDINATES, expected, strict=True):
            self.assertAlmostEqual(float(controller.grid[0, row, col, 0]), value, places=5)
            self.assertEqual(float(controller.grid[0, row, col, 2]), 1.0)
        for row, col in OUTPUT_COORDINATES:
            self.assertEqual(float(controller.grid[0, row, col, 3]), 1.0)
            self.assertEqual(float(controller.grid[0, row, col, 4]), 50.0)
            self.assertEqual(float(controller.grid[0, row, col, 5]), 50.0)


if __name__ == "__main__":
    unittest.main()
