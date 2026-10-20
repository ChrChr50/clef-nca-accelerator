from __future__ import annotations

import unittest

import numpy as np

from reference.hanoi.environment import ACTIONS, HanoiState, transition
from training.hanoi_nca.hypothesis_a import (
    PEG_PERMUTATIONS,
    MixedStepSchedule,
    auxiliary_targets,
    inverse_permutation,
    largest_unsettled_disk,
    peg_roles,
    permute_action,
    permute_state,
    top_disks,
)
from training.hanoi_nca.run_hypothesis_a import diagnostic_episode_specs


class HypothesisAContractTests(unittest.TestCase):
    def test_all_peg_permutations_preserve_transition_equivariance(self) -> None:
        states = [HanoiState((0, 2, 1, 0), 2), HanoiState((1, 1, 0), 2)]
        for state in states:
            for permutation in PEG_PERMUTATIONS:
                transformed = permute_state(state, permutation)
                self.assertEqual(state, permute_state(transformed, inverse_permutation(permutation)))
                for action in range(len(ACTIONS)):
                    original = transition(state, action)
                    mapped = transition(transformed, permute_action(action, permutation))
                    self.assertEqual(original[1], mapped[1])
                    self.assertEqual(permute_state(original[0], permutation), mapped[0])

    def test_auxiliary_targets_have_declared_meanings_and_shapes(self) -> None:
        state = HanoiState((0, 0, 2, 1), 2)
        self.assertEqual((0, 3, 2), top_disks(state))
        self.assertEqual(3, largest_unsettled_disk(state))
        self.assertEqual((1, 0, 2), peg_roles(state))
        targets = auxiliary_targets([state])
        self.assertEqual((1, 6), targets["legality"].shape)
        self.assertEqual((1, 3), targets["top_disks"].shape)
        self.assertEqual((1, 3), targets["peg_roles"].shape)
        self.assertEqual((1,), targets["subgoal_disk"].shape)

    def test_mixed_schedule_contains_short_and_original_length_trials(self) -> None:
        schedule = MixedStepSchedule()
        rng = np.random.RandomState(5)
        draws = [schedule.draw(index, rng) for index in range(20)]
        self.assertTrue(all(20 <= steps <= 24 for steps, kind in draws if kind == "short"))
        self.assertTrue(all(50 <= steps <= 59 for steps, kind in draws if kind == "long"))
        self.assertEqual(5, sum(kind == "long" for _, kind in draws))

    def test_diagnostic_set_is_bounded_and_retains_unseen_large_cases(self) -> None:
        specs = diagnostic_episode_specs()
        self.assertEqual(20, len(specs))
        self.assertTrue(all(spec.reset_mode == "standard" for spec in specs))
        self.assertEqual({1, 2, 3, 4, 5, 6, 7, 8}, {spec.disk_count for spec in specs})
        self.assertEqual(1, sum(spec.disk_count == 8 for spec in specs))


if __name__ == "__main__":
    unittest.main()
