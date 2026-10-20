"""Resolved source/episode contract for the explicitly accepted model2 freeze."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FREEZE_PATH = ROOT / "sw/cartpole/deployment.freeze.v1.json"
ADR_PATH = "docs/decisions/ADR-0011-freeze-released-model2-for-hardware.md"
BLOB_SHA256 = "ee8e4ad597d73dc616e60e91a5af056c96beb9f2c18652cfb1a1906247fbc009"
BOUND_PATHS = (ADR_PATH, "reference/original_nca/operator_manifest.json",
               "reference/original_nca/core.py", "reference/original_nca/cartpole.py",
               "sw/cartpole/interface.v1.json", "sw/cartpole/replay.v1.json",
               "sw/cartpole/qualification.v1.json", "experiments/p06_cartpole/summary.json",
               "experiments/p06_cartpole/results.jsonl",
               "experiments/p06_upstream_parity/results/summary.json")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_manifest() -> dict:
    adr = (ROOT / ADR_PATH).read_text()
    if "Status: **Accepted**" not in adr or BLOB_SHA256 not in adr:
        raise ValueError("explicit model2 freeze decision is not accepted")
    operator = json.loads((ROOT / BOUND_PATHS[1]).read_text())
    summary = json.loads((ROOT / "experiments/p06_cartpole/summary.json").read_text())
    if (summary["tfjs_weight_blob_sha256"] != BLOB_SHA256
            or summary["completed_episodes"] != 10 or not summary["checkpoint_golden_pass"]):
        raise ValueError("source/qualification identity mismatch")
    return {"schema_version": 1, "status": "frozen-by-explicit-user-decision",
            "acceptance_adr": ADR_PATH,
            "bound_artifacts": {path:sha256(ROOT / path) for path in BOUND_PATHS},
            "weights": {"model":"model2","blob_sha256":BLOB_SHA256,
                        "parameter_count":1916,"source":"self-organized-control/demo/models/model2",
                        "rights":"local-only; no redistribution of weights or derived images"},
            "upstream_revision":operator["identity"]["upstream_revision"],
            "graph":operator["graph"],"state":operator["state"],
            "io":operator["io"],"readout":operator["readout"],
            "episode": {"plant_max_steps":10000,"balanced_terminal_action":10001,
                        "fresh_grid":True,"persistent_between_actions":True,
                        "in_episode_reinitialization":False,"noise":False,"damage":False,
                        "input_deletion":False,"epochs_per_action":[50,59],
                        "timing":"step-synchronized; no accepted wall-clock deadline"},
            "replay": {"rng":"NumPy RandomState MT19937",
                       "plant_and_draw_rng_seed":"episode seed",
                       "grid_rng_seed":"episode seed XOR 0x5A17",
                       "initial_plant":"uniform[-0.05,0.05) four float64 values",
                       "initial_grid":"uniform[-0.1,0.1) [1,32,32,6] cast float32",
                       "draw_order":"plant reset; per action randint(50,60); then C-order masks",
                       "mask_predicate":"random_sample <= 0.5",
                       "mask_shape":["epochs",1,32,32,1],"mask_bit_order":"little",
                       "logical_ownership":"draws independent of physical service stalls"},
            "qualification": {"original_pass":bool(summary["qualification_pass"]),
                              "horizon_completions":summary["horizon_completions"],
                              "episodes":10,"freeze_basis":"explicit accepted ADR-0011 override",
                              "paper_statistics_reproduced":False},
            "host_boundary":"float64 plant -> four pre-action float32 observations -> controller scaling once",
            "arithmetic":"original float32; fixed-point choice pending G4"}


def load_frozen(path: Path = FREEZE_PATH) -> dict:
    if path.resolve() != FREEZE_PATH.resolve():
        raise ValueError("freeze authority must be the repository's resolved manifest")
    manifest = json.loads(path.read_text())
    if manifest != build_manifest():
        raise ValueError("freeze manifest is stale or differs from the accepted contract")
    return manifest


if __name__ == "__main__":
    FREEZE_PATH.write_text(json.dumps(build_manifest(),indent=2,sort_keys=True)+"\n")
    print(f"Resolved explicit-decision freeze: {FREEZE_PATH}")
