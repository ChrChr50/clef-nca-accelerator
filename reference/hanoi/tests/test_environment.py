from __future__ import annotations

import json
from pathlib import Path
import unittest

from reference.hanoi.environment import (
    ACTIONS,
    OBSERVATION_WIDTH,
    EpisodeFinishedError,
    HanoiEnv,
    HanoiState,
    decode_observation,
    encode_observation,
    transition,
)


ROOT = Path(__file__).resolve().parents[3]


class EnvironmentContractTests(unittest.TestCase):
    def test_manifest_and_locked_action_order(self) -> None:
        manifest = json.loads((ROOT / "reference/hanoi/environment_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(8, manifest["n_max"])
        self.assertEqual(36, manifest["observation"]["width"])
        self.assertEqual(((0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1)), ACTIONS)
        self.assertEqual([list(action) for action in ACTIONS], [[item["source"], item["destination"]] for item in manifest["actions"]])
        self.assertIsNone(manifest["reward"])

    def test_exact_observation_layout_and_all_goals(self) -> None:
        for goal in range(3):
            state = HanoiState((2, 0, 1), goal)
            observation = encode_observation(state)
            self.assertEqual(OBSERVATION_WIDTH, len(observation))
            self.assertEqual((0.0, 0.0, 1.0, 1.0), observation[0:4])
            self.assertEqual((1.0, 0.0, 0.0, 1.0), observation[4:8])
            self.assertEqual((0.0, 1.0, 0.0, 1.0), observation[8:12])
            self.assertEqual((0.0,) * 20, observation[12:32])
            self.assertEqual(tuple(1.0 if index == goal else 0.0 for index in range(3)), observation[32:35])
            self.assertEqual(3 / 8, observation[35])
            self.assertEqual(state, decode_observation(observation))

    def test_illegal_action_is_reported_noop_and_consumes_budget(self) -> None:
        state = HanoiState((0, 0), 2)
        successor, legal, moved = transition(state, 2)
        self.assertIs(successor, state)
        self.assertFalse(legal)
        self.assertIsNone(moved)

        env = HanoiEnv(2, goal_peg=2, move_budget=1)
        env.reset(initial_locations=(0, 0))
        result = env.step(2)
        self.assertEqual(state, result.state)
        self.assertFalse(result.legal)
        self.assertTrue(result.truncated)
        with self.assertRaises(EpisodeFinishedError):
            env.step(1)

    def test_legal_move_and_terminal_precedes_budget_truncation(self) -> None:
        env = HanoiEnv(1, goal_peg=2, move_budget=1)
        env.reset(standard_source=0)
        result = env.step(1)
        self.assertTrue(result.legal)
        self.assertEqual(0, result.moved_disk)
        self.assertTrue(result.terminated)
        self.assertFalse(result.truncated)

    def test_reproducible_resets(self) -> None:
        first = HanoiEnv(8, goal_peg=1, move_budget=100)
        second = HanoiEnv(8, goal_peg=1, move_budget=100)
        self.assertEqual(first.reset(seed=20260919), second.reset(seed=20260919))
        self.assertEqual((0, 0, 0, 2, 1, 1, 1, 2), first.state.locations)
        self.assertEqual((0,) * 8, first.reset(standard_source=0).locations)
        self.assertEqual((2, 1, 0, 2, 1, 0, 2, 1), first.reset(initial_locations=(2, 1, 0, 2, 1, 0, 2, 1)).locations)

    def test_serialization_and_hashes_are_canonical(self) -> None:
        state = HanoiState((0, 2, 1), 2)
        expected = b'{"disk_count":3,"goal_peg":2,"locations":[0,2,1]}'
        self.assertEqual(expected, state.serialize())
        self.assertEqual(state, HanoiState.deserialize(expected))
        self.assertEqual("0183c2fd23f28504a37d569c33c12f3cdec9c0c5b59bd2cc0a3e004613244611", state.state_hash)

        env = HanoiEnv(3, goal_peg=2, move_budget=9)
        env.reset(seed=7, initial_locations=(0, 2, 1))
        env.step(4)
        restored = HanoiEnv.deserialize(env.serialize())
        self.assertEqual(env.serialize(), restored.serialize())
        self.assertEqual(env.snapshot_hash, restored.snapshot_hash)

    def test_validation_rejects_noncanonical_inputs(self) -> None:
        with self.assertRaises(ValueError):
            HanoiState((), 2)
        with self.assertRaises(ValueError):
            HanoiState((0, 3), 2)
        with self.assertRaises(ValueError):
            HanoiState((False,), 2)
        with self.assertRaises(ValueError):
            HanoiEnv(2, goal_peg=2, move_budget=1.5)
        with self.assertRaises(ValueError):
            transition(HanoiState((0,), 2), True)
        with self.assertRaises(ValueError):
            decode_observation((0.0,) * OBSERVATION_WIDTH)
        bad = list(encode_observation(HanoiState((0,), 2)))
        bad[4] = 1.0
        with self.assertRaises(ValueError):
            decode_observation(bad)


if __name__ == "__main__":
    unittest.main()
