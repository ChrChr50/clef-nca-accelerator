from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from scripts.check_oracle_firewall import ROOT, violations


class OracleFirewallTests(unittest.TestCase):
    def test_repository_passes_firewall(self) -> None:
        self.assertEqual([], violations(ROOT))

    def test_firewall_rejects_deployable_import_and_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "reference/hanoi").mkdir(parents=True)
            (root / "reference/hanoi/environment.py").write_text("pass\n", encoding="utf-8")
            (root / "reference/hanoi/__init__.py").write_text("pass\n", encoding="utf-8")
            (root / "model_export").mkdir()
            (root / "model_export/export.py").write_text("from reference.hanoi.oracle import optimal_actions\n", encoding="utf-8")
            (root / "rtl").mkdir()
            (root / "rtl/distance_table.mem").write_text("00\n", encoding="utf-8")
            failures = violations(root)
            self.assertTrue(any("forbidden token" in failure for failure in failures))
            self.assertTrue(any("forbidden artifact name" in failure for failure in failures))

    def test_firewall_rejects_indirect_oracle_import(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "reference/hanoi").mkdir(parents=True)
            (root / "reference/hanoi/environment.py").write_text("pass\n", encoding="utf-8")
            (root / "reference/hanoi/__init__.py").write_text("pass\n", encoding="utf-8")
            (root / "model_export").mkdir()
            (root / "model_export/export.py").write_text("from reference.hanoi import oracle\n", encoding="utf-8")
            self.assertTrue(violations(root))


if __name__ == "__main__":
    unittest.main()
