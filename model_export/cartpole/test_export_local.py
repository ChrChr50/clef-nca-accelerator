from __future__ import annotations

import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from reference.original_nca.tools.generate_golden import synthetic_weights
from model_export.cartpole.export_local import main, serialize_f32le, validate_round_trip
from sw.cartpole.qualification import load_config
from model_export.cartpole.freeze import load_frozen


class LocalExportTests(unittest.TestCase):
    def test_frozen_manifest_is_restricted_to_repository_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            other = Path(temporary) / "fake-freeze.json"
            other.write_text('{"status":"frozen-by-explicit-user-decision"}')
            with self.assertRaisesRegex(ValueError,"repository's resolved manifest"):
                load_frozen(other)

    def test_synthetic_round_trip_and_reject_corruption(self) -> None:
        weights = synthetic_weights()
        raw = serialize_f32le(weights)
        self.assertEqual(len(raw), 1916 * 4)
        validate_round_trip(weights, raw)
        damaged = bytearray(raw)
        damaged[0] ^= 1
        with self.assertRaises(ValueError):
            validate_round_trip(weights, bytes(damaged))

    def test_export_refuses_unqualified_summary_before_reading_weights(self) -> None:
        config, digest = load_config()
        with tempfile.TemporaryDirectory() as temporary:
            summary = Path(temporary) / "summary.json"
            summary.write_text(json.dumps({
                "qualification_pass": False,
                "config_sha256": digest,
                "tfjs_weight_blob_sha256": config["authority"]["tfjs_weight_blob_sha256"],
                "completed_episodes": 10,
                "checkpoint_golden_pass": True,
            }), encoding="utf-8")
            with patch("sys.argv", ["export_local.py", "--summary", str(summary)]):
                with self.assertRaisesRegex(ValueError, "qualification has not passed"):
                    main()


if __name__ == "__main__":
    unittest.main()
