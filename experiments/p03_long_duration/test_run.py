"""The reconstructed runner must preserve the original bounded rollout."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from experiments.p03_long_duration.run import CONDITIONS, ROOT, evaluate
from reference.original_nca.core import CanonicalNCA, load_tfjs_weights
from reference.original_nca.experiment import run_episode


class RunnerParityTests(unittest.TestCase):
    def test_all_conditions_match_reference_for_short_rollouts(self) -> None:
        source = ROOT / "self-organized-control" / "demo" / "models" / "model1"
        nca = CanonicalNCA(load_tfjs_weights(source / "model.json", source / "group1-shard1of1.bin"))
        with tempfile.TemporaryDirectory() as temp:
            for condition, options in CONDITIONS.items():
                with self.subTest(condition=condition):
                    actual = evaluate(nca, 0, condition, 8, Path(temp) / "progress.npz")
                    expected = run_episode(nca, 0, max_steps=8, **options)
                    self.assertEqual(actual["steps"], expected.steps)
                    self.assertEqual(actual["reward_sum"], expected.reward_sum)
                    self.assertEqual(actual["actions_sha256"], expected.actions_sha256)


if __name__ == "__main__":
    unittest.main()
