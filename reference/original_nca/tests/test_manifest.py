from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


class ManifestTests(unittest.TestCase):
    def test_operator_manifest_contract(self) -> None:
        manifest = json.loads(
            (ROOT / "reference/original_nca/operator_manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["graph"]["parameter_count_executable"], 1916)
        self.assertEqual(manifest["graph"]["parameter_count_paper"], 1854)
        self.assertEqual(manifest["schedule"]["executed_step_values"], list(range(50, 60)))
        self.assertEqual(manifest["state"]["shape"], [None, 32, 32, 6])
        self.assertEqual(manifest["readout"]["tie_break"], "lowest action index")

    def test_hanoi_is_absent_from_reference_manifest(self) -> None:
        text = (ROOT / "reference/original_nca/operator_manifest.json").read_text().lower()
        self.assertNotIn("hanoi", text)

    def test_checkpoint_cartpole_golden_vectors_are_complete(self) -> None:
        golden = json.loads(
            (ROOT / "reference/original_nca/golden/golden_vectors.json").read_text(
                encoding="utf-8"
            )
        )
        cases = {case["checkpoint"]: case for case in golden["cases"]}
        self.assertEqual(set(cases), {"synthetic-v1", "model1", "model2", "model3"})
        for model in ("model1", "model2", "model3"):
            rollout = cases[model]["fixed_cartpole_rollout"]
            self.assertEqual(rollout["seed"], 31415)
            self.assertEqual(rollout["environment_step_cap"], 8)
            self.assertEqual(rollout["steps"], 8)
            self.assertEqual(len(rollout["actions_sha256"]), 64)

    def test_empirical_result_provenance_and_censoring(self) -> None:
        result = json.loads(
            (ROOT / "reference/original_nca/empirical_results.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(result["runtime"]["python"], "3.12.14")
        self.assertEqual(result["runtime"]["numpy"], "2.3.5")
        self.assertEqual(result["seeds"], [0, 1, 2])
        self.assertEqual(len(result["conditions"]), 15)
        self.assertEqual(result["conditions_with_censoring"], 14)
        self.assertTrue(
            all(len(condition["episodes"]) == 3 for condition in result["conditions"].values())
        )


if __name__ == "__main__":
    unittest.main()
