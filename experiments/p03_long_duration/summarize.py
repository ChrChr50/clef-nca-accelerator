"""Summarize complete and right-censored checkpoint episodes without hiding either."""

from __future__ import annotations

import argparse
import glob
import json
import statistics
from collections import defaultdict
from pathlib import Path

PAPER_SCORE = {
    "baseline": (13273.0, 11905.0),
    "damage_after_input": (2598.19, 2241.0),
    "uniform_damage": (391.6, 283.0),
    "noisy_update": (1296.3, 899.0),
    "noisy_damage_after_input": (739.7, 473.0),
    "noisy_uniform_damage": (345.7, 214.0),
    "delete_cart_position": (3926.7, 2383.0),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    groups = defaultdict(list)
    for pattern in args.paths:
        matches = [Path(name) for name in glob.glob(str(pattern))]
        if not matches:
            raise FileNotFoundError(pattern)
        for path in matches:
            for line in path.read_text(encoding="utf-8").splitlines():
                item = json.loads(line)
                groups[(item["model"], item["condition"],
                        float(item.get("reinit_probability", 0.0)))].append(item)
    for (model, condition, reinit_probability), episodes in sorted(groups.items()):
        rewards = [float(item["reward_sum"]) for item in episodes]
        steps = [int(item["steps"]) for item in episodes]
        censored = sum(bool(item["right_censored"]) for item in episodes)
        print(json.dumps({
            "model": model, "condition": condition,
            "reinit_probability": reinit_probability,
            "paper_mean_score": PAPER_SCORE[condition][0],
            "paper_sd_score": PAPER_SCORE[condition][1],
            "n": len(episodes), "seeds": [item["seed"] for item in episodes],
            "censored": censored,
            "mean_observed_score": statistics.mean(rewards),
            "sd_observed_score": statistics.stdev(rewards) if len(rewards) > 1 else None,
            "mean_observed_steps": statistics.mean(steps),
            "sd_observed_steps": statistics.stdev(steps) if len(steps) > 1 else None,
            "scores": rewards, "steps": steps,
        }, sort_keys=True))


if __name__ == "__main__":
    main()
