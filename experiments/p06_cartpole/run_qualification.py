"""Run the accepted P06 ten-seed qualification; no training or weight export."""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from reference.original_nca.core import CanonicalNCA, load_tfjs_weights  # noqa: E402
from sw.cartpole.qualification import load_config, run_episode  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", type=Path, default=ROOT / "self-organized-control")
    parser.add_argument("--results", type=Path, default=ROOT / "experiments/p06_cartpole/results.jsonl")
    parser.add_argument("--summary", type=Path, default=ROOT / "experiments/p06_cartpole/summary.json")
    parser.add_argument("--progress-dir", type=Path, default=ROOT / "artifacts/p06_cartpole/progress")
    args = parser.parse_args()
    config, config_sha256 = load_config()
    verifier = subprocess.run(
        [sys.executable, str(ROOT / "reference/original_nca/tools/verify_upstream.py"),
         "--upstream", str(args.upstream)], cwd=ROOT, check=False,
    )
    if verifier.returncode:
        return verifier.returncode
    model = args.upstream / "demo/models/model2"
    blob = model / "group1-shard1of1.bin"
    weight_sha256 = hashlib.sha256(blob.read_bytes()).hexdigest()
    if weight_sha256 != config["authority"]["tfjs_weight_blob_sha256"]:
        raise ValueError("model2 weight-blob identity mismatch")
    nca = CanonicalNCA(load_tfjs_weights(model / "model.json", blob))
    args.results.parent.mkdir(parents=True, exist_ok=True)
    existing = [json.loads(line) for line in args.results.read_text().splitlines()] if args.results.is_file() else []
    by_seed = {}
    for record in existing:
        seed = record["seed"]
        if seed in by_seed or seed not in config["seeds"]:
            raise ValueError("duplicate or unexpected completed seed")
        if record["config_sha256"] != config_sha256 or record["tfjs_weight_blob_sha256"] != weight_sha256:
            raise ValueError("existing result belongs to a different protocol or weight blob")
        by_seed[seed] = record
    for seed in config["seeds"]:
        if seed in by_seed:
            continue
        progress = args.progress_dir / f"seed_{seed}.npz"
        record = run_episode(nca, seed, config_sha256, weight_sha256, progress)
        assert record is not None
        row = dataclasses.asdict(record)
        with args.results.open("a", encoding="utf-8") as output:
            output.write(json.dumps(row, sort_keys=True) + "\n")
        by_seed[seed] = row
        print(json.dumps(row, sort_keys=True), flush=True)
    rows = [by_seed[seed] for seed in config["seeds"]]
    successes = sum(int(row["horizon_completed"]) for row in rows)
    summary = {
        "schema_version": 1,
        "config_sha256": config_sha256,
        "model": "model2",
        "tfjs_weight_blob_sha256": weight_sha256,
        "checkpoint_golden_pass": True,
        "completed_episodes": len(rows),
        "horizon_completions": successes,
        "required_horizon_completions": config["success_threshold"]["minimum_horizon_completions"],
        "qualification_pass": successes >= config["success_threshold"]["minimum_horizon_completions"],
        "seeds": config["seeds"],
        "results_jsonl": "experiments/p06_cartpole/results.jsonl",
    }
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True), flush=True)
    return 0 if summary["qualification_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
