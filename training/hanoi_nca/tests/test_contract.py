from __future__ import annotations

import ast
import hashlib
import json
import math
from pathlib import Path
import unittest

import numpy as np

from reference.hanoi.environment import ACTIONS, HanoiState, encode_observation
from training.hanoi_nca.adapter import HanoiAdapter
from training.hanoi_nca.dataset import build_corpus, manifest
from training.hanoi_nca.layout import layout_statistics, load_layout


ROOT = Path(__file__).resolve().parents[3]


class P05ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus = build_corpus()

    def test_layout_is_complete_collision_free_and_ordered(self) -> None:
        layout = load_layout()
        statistics = layout_statistics(layout)
        self.assertEqual(0, statistics["collision_count"])
        self.assertEqual(36, len(layout.input_coordinates))
        self.assertEqual(6, len(layout.output_coordinates))
        self.assertEqual(tuple(f"{source}->{destination}" for source, destination in ACTIONS), layout.action_names)
        self.assertLess(statistics["centroid_offset"], 1.0)
        self.assertLessEqual(statistics["chebyshev_input_output"]["maximum"], 9)
        self.assertLess(statistics["per_output_mean_spread"], 1.0)

    def test_numpy_adapter_rewrite_readout_and_ties(self) -> None:
        layout = load_layout()
        adapter = HanoiAdapter(layout, "accumulate")
        state = np.zeros((1, 32, 32, 6), dtype=np.float32)
        observation = np.asarray([encode_observation(HanoiState((0, 2, 1), 2))], dtype=np.float32)
        rewritten = adapter.rewrite(state, observation)
        for index, (row, column) in enumerate(layout.input_coordinates):
            self.assertEqual(observation[0, index], rewritten[0, row, column, 0])
            np.testing.assert_array_equal(rewritten[0, row, column, [1, 2, 4, 5]], np.ones(4))
        for row, column in layout.output_coordinates:
            self.assertEqual(1.0, rewritten[0, row, column, 3])
            self.assertEqual(1.0, rewritten[0, row, column, 4])
        self.assertEqual(0, int(adapter.select_action(adapter.readout(rewritten))[0]))

    def test_canonical_corpus_and_complete_set_contract(self) -> None:
        result = manifest(self.corpus)
        self.assertEqual(29520, result["case_count"])
        self.assertEqual(24, sum(result["terminal_counts"].values()))
        self.assertEqual({"1": 29496}, result["nonterminal_optimal_action_set_size_counts"])
        hashes = [sample.state_hash for sample in self.corpus]
        self.assertEqual(len(hashes), len(set(hashes)))
        self.assertEqual({1, 2, 3, 4, 5, 6, 7, 8}, {sample.state.disk_count for sample in self.corpus})
        self.assertEqual({0, 1, 2}, {sample.state.goal_peg for sample in self.corpus})

    def test_adapter_model_runtime_do_not_import_training_labels(self) -> None:
        for relative in (
            "training/hanoi_nca/adapter.py",
            "training/hanoi_nca/model.py",
            "training/hanoi_nca/runtime.py",
            "training/hanoi_nca/control.py",
        ):
            text = (ROOT / relative).read_text(encoding="utf-8")
            tree = ast.parse(text)
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module or "")
            self.assertFalse(any(name.endswith(".oracle") or "hanoi.oracle" in name for name in imports), relative)

    def test_difference_manifest_preserves_graph_and_gate_status(self) -> None:
        difference = json.loads((ROOT / "training/hanoi_nca/difference_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(1916, difference["unchanged_local_graph"]["parameter_count"])
        self.assertIn("not_accepted", difference["status"])
        self.assertFalse(difference["measured_candidate_profile"]["runtime_legality_feedback"])

    def test_recorded_candidate_is_finite_and_not_mislabeled_frozen(self) -> None:
        difference = json.loads((ROOT / "training/hanoi_nca/difference_manifest.json").read_text(encoding="utf-8"))
        checkpoint = ROOT / difference["candidate_disposition"]["checkpoint"]
        digest = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
        self.assertEqual(difference["candidate_disposition"]["sha256"], digest)
        self.assertFalse(difference["candidate_disposition"]["functional_freeze_eligible"])
        with np.load(checkpoint, allow_pickle=False) as archive:
            for name in archive.files:
                if name != "metadata_json":
                    self.assertTrue(np.isfinite(archive[name]).all(), name)

        results = json.loads((ROOT / "experiments/p05/results.json").read_text(encoding="utf-8"))
        self.assertEqual("aborted_and_rolled_back", results["dagger"]["status"])
        self.assertTrue(results["dagger"]["numerical_failures"])

        def assert_finite(value: object) -> None:
            if isinstance(value, float):
                self.assertTrue(math.isfinite(value))
            elif isinstance(value, dict):
                for item in value.values():
                    assert_finite(item)
            elif isinstance(value, list):
                for item in value:
                    assert_finite(item)

        assert_finite(results)


if __name__ == "__main__":
    unittest.main()
