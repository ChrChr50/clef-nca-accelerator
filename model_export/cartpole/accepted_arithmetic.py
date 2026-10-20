"""Accepted G4 manifest generation/validation; no RTL implementation."""
from __future__ import annotations

import json
from pathlib import Path

from model_export.cartpole.fixed_point import Format
from model_export.cartpole.freeze import ROOT, load_frozen, sha256

MANIFEST_PATH = ROOT / "sw/cartpole/arithmetic.accepted.v1.json"
ADR_PATH = "docs/decisions/ADR-0012-cartpole-fixed-point-numerical-contract.md"
BOUND_PATHS = (
    ADR_PATH,
    "sw/cartpole/deployment.freeze.v1.json",
    "model_export/cartpole/fixed_point.py",
    "model_export/cartpole/fixed_deployment.py",
    "model_export/cartpole/accepted_arithmetic.py",
    "experiments/p07_cartpole/protocol.v1.json",
    "experiments/p07_cartpole/float_profile.json",
    "experiments/p07_cartpole/evaluation_summary.json",
    "experiments/p07_cartpole/vectors_manifest.json",
)


def build_manifest() -> dict:
    frozen = load_frozen()
    if "Status: **Accepted**" not in (ROOT / ADR_PATH).read_text():
        raise ValueError("G4 arithmetic decision is not accepted")
    protocol = json.loads((ROOT / "experiments/p07_cartpole/protocol.v1.json").read_text())
    candidate = next(item for item in protocol["candidates"] if item["name"]=="fidelity32")
    expected = Format("fidelity32",32,24,24,22,62)
    if Format(**candidate)!=expected:
        raise ValueError("candidate differs from the explicitly accepted G4 format")
    vectors = json.loads((ROOT / "experiments/p07_cartpole/vectors_manifest.json").read_text())
    selected = [item for item in vectors["cases"] if item["format"]==expected.name]
    if len(selected)!=6:
        raise ValueError("accepted candidate's six original vector cases are missing")
    return {
        "schema_version":1,
        "status":"accepted-G4-fidelity32",
        "accepted_date":"2026-10-07",
        "acceptance_adr":ADR_PATH,
        "weights_sha256":frozen["weights"]["blob_sha256"],
        "bound_artifacts":{path:sha256(ROOT / path) for path in BOUND_PATHS},
        "arithmetic":expected.manifest(),
        "quality":{
            "rtl_comparison":"exact signed integer equality at layer/cell/epoch/readout boundaries",
            "wrap":"forbidden; full-valid-state accumulator bounds prove host MAC safety",
            "saturation":"defined signed saturation; all events counted; zero observed in bounded primary runs",
            "evidence_scope":"reused 10/12 calibration at 128 actions; new 20/21 at 256 actions, all censored",
            "float_action_agreement":"all four measured bounded traces identical",
            "full_horizon_quantized_qualified":False,
            "acceptable_full_horizon_control_loss":"not selected; measure and explicitly decide later",
        },
        "verification_vectors":selected,
        "rights":"checkpoint-derived arrays remain ignored/local; manifest includes hashes and aggregate metrics only",
        "next_stage":"P08 requires a separate explicit user request; not authorized by G4 acceptance",
    }


def load_accepted_arithmetic(path:Path=MANIFEST_PATH) -> dict:
    if path.resolve()!=MANIFEST_PATH.resolve():
        raise ValueError("arithmetic authority must be the repository's accepted manifest")
    manifest = json.loads(path.read_text())
    if manifest!=build_manifest():
        raise ValueError("accepted arithmetic manifest is stale or inconsistent")
    return manifest


def accepted_format() -> Format:
    manifest = load_accepted_arithmetic()
    value = manifest["arithmetic"]
    return Format(**{key:value[key] for key in
                     ("name","state_bits","state_fraction","weight_bits","weight_fraction","accumulator_bits")})


if __name__ == "__main__":
    MANIFEST_PATH.write_text(json.dumps(build_manifest(),indent=2,sort_keys=True)+"\n")
    print(f"Accepted G4 manifest: {MANIFEST_PATH}")
