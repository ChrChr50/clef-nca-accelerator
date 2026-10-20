"""Focused checks for the P05 action-value teaching revision."""

import unittest

from reference.hanoi.environment import HanoiState
from training.hanoi_nca.run_v7_teaching import STAGES, action_values


class ActionValueTeachingTests(unittest.TestCase):
    def test_progress_and_illegal_noop_are_distinct(self):
        values, legal = action_values(HanoiState((0, 0), 2))
        self.assertEqual(values.tolist(), [1.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        self.assertEqual(legal.tolist(), [1.0, 1.0, 0.0, 0.0, 0.0, 0.0])

    def test_no_runtime_oracle_features(self):
        from training.hanoi_nca.v4_runtime import TorchNCAV4Runtime
        self.assertNotIn("oracle", TorchNCAV4Runtime.__module__)

    def test_full_accuracy_gate_begins_at_paper_length(self):
        self.assertIsNone(STAGES[0][-1])
        self.assertIsNone(STAGES[1][-1])
        self.assertEqual(STAGES[2][1:3], (50, 59))
        self.assertEqual(STAGES[2][-1], 0.85)


if __name__ == "__main__":
    unittest.main()
