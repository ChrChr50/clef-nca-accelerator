"""Compact public-safe telemetry: omit checkpoint-derived vector values."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path


def main():
    here = Path(__file__).parent
    source = here / "evaluation.json"
    data = json.loads(source.read_text())
    if not data["complete"]:
        raise ValueError("evaluation is incomplete")
    summary = copy.deepcopy(data)
    summary["detailed_local_result_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    summary["interpretation"] = "Bounded/censored P07 numerical comparison; no population or full-horizon quantized claim"
    for episode in summary["episodes"]:
        for values in episode["fixed"].values():
            difference = values["first_action_disagreement"]
            if difference is not None:
                values["first_action_disagreement"] = {key:difference[key] for key in
                    ("logical_action","same_observation","float_action","fixed_action")}
    summary["aggregate"] = {}
    for candidate in summary["formats"]:
        name = candidate["contract"]["name"]
        records = [episode["fixed"][name] for episode in summary["episodes"]]
        acceptance = [episode["fixed"][name] for episode in summary["episodes"] if episode["role"]=="acceptance"]
        summary["aggregate"][name] = {"calibration_and_acceptance_episodes":len(records),
            "acceptance_episodes":len(acceptance),
            "acceptance_cap_completions":sum(row["censored"] for row in acceptance),
            "identical_full_acceptance_action_traces":sum(row["same_full_action_trace"] for row in acceptance),
            "max_error_under_identical_plant_observation":max(row["max_grid_error_same_plant"] for row in records),
            "total_fixed_seconds":sum(row["seconds"] for row in records),
            "saturations":sum(sum(row["saturation_counts"].values()) for row in records)}
    target = here / "evaluation_summary.json"
    target.write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
    print(json.dumps(summary["aggregate"],indent=2))


if __name__ == "__main__":
    main()
