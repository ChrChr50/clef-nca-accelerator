"""Bookkeeping guards need no licensed weights or restricted vector arrays."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from model_export.cartpole.accepted_arithmetic import MANIFEST_PATH, accepted_format, load_accepted_arithmetic
from model_export.cartpole.fixed_point import Format


class AcceptedArithmeticTests(unittest.TestCase):
    def test_accepted_format_and_scope(self):
        self.assertEqual(accepted_format(),Format("fidelity32",32,24,24,22,62))
        manifest = load_accepted_arithmetic()
        self.assertFalse(manifest["quality"]["full_horizon_quantized_qualified"])
        self.assertEqual(len(manifest["verification_vectors"]),6)
        self.assertTrue(all(case["format"]=="fidelity32" for case in manifest["verification_vectors"]))

    def test_external_authority_rejected(self):
        with self.assertRaisesRegex(ValueError,"repository's accepted manifest"):
            load_accepted_arithmetic(Path("unapproved-arithmetic.json"))

    def test_stale_format_rejected(self):
        manifest = json.loads(MANIFEST_PATH.read_text())
        manifest["arithmetic"]["state_fraction"] = 23
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "tampered.json"
            target.write_text(json.dumps(manifest))
            with patch("model_export.cartpole.accepted_arithmetic.MANIFEST_PATH",target):
                with self.assertRaisesRegex(ValueError,"stale or inconsistent"):
                    load_accepted_arithmetic(target)


if __name__ == "__main__":
    unittest.main()
