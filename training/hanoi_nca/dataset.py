"""Training/evaluation-only canonical corpus and leakage-safe partitions."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from reference.hanoi.environment import HanoiState, encode_observation, iter_states
from reference.hanoi.oracle import encode_locations, optimal_actions, reverse_graph_distances


PARTITION_SCHEMA = "clef.hanoi.partition.v1"


@dataclass(frozen=True)
class Sample:
    state: HanoiState
    state_hash: str
    observation: tuple[float, ...]
    actions: tuple[int, ...]
    distance: int
    split: str
    reset_mode: str = "exhaustive_explicit"


def identity_bucket(state_hash: str) -> int:
    return int(state_hash[:8], 16) % 100


def split_for(state: HanoiState) -> str:
    if state.disk_count == 7:
        return "validation_unseen_n"
    if state.disk_count == 8:
        return "test_unseen_n"
    bucket = identity_bucket(state.state_hash)
    if bucket < 80:
        return "train"
    if bucket < 90:
        return "validation_seen_n"
    return "test_seen_n"


def build_corpus() -> list[Sample]:
    samples: list[Sample] = []
    for disk_count in range(1, 9):
        for goal in range(3):
            distances = reverse_graph_distances(disk_count, goal)
            for state in iter_states(disk_count, goal):
                samples.append(
                    Sample(
                        state=state,
                        state_hash=state.state_hash,
                        observation=encode_observation(state),
                        actions=optimal_actions(state),
                        distance=distances[encode_locations(state.locations)],
                        split=split_for(state),
                    )
                )
    return samples


def supervised_arrays(samples: list[Sample], split: str) -> tuple[NDArray[np.float32], NDArray[np.float32], list[Sample]]:
    selected = [sample for sample in samples if sample.split == split and sample.actions]
    observations = np.asarray([sample.observation for sample in selected], dtype=np.float32)
    targets = np.zeros((len(selected), 6), dtype=np.float32)
    for row, sample in enumerate(selected):
        targets[row, list(sample.actions)] = 1.0 / len(sample.actions)
    return observations, targets, selected


def manifest(samples: list[Sample]) -> dict[str, object]:
    split_counts = Counter(sample.split for sample in samples)
    terminal_counts = Counter(sample.split for sample in samples if not sample.actions)
    uniqueness = Counter(len(sample.actions) for sample in samples if sample.actions)
    coverage: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    digests: dict[str, hashlib._Hash] = {}
    for sample in samples:
        key = f"n={sample.state.disk_count}|goal={sample.state.goal_peg}|distance={sample.distance}|terminal={not sample.actions}|reset={sample.reset_mode}"
        coverage[sample.split][key] += 1
        digest = digests.setdefault(sample.split, hashlib.sha256())
        digest.update(
            (
                f"{sample.state_hash},{sample.distance},"
                f"{';'.join(str(action) for action in sample.actions)},{sample.reset_mode}\n"
            ).encode("ascii")
        )
    return {
        "schema": PARTITION_SCHEMA,
        "partition_rule": {
            "n_1_through_6": "first 32 state-hash bits modulo 100: 0-79 train, 80-89 validation, 90-99 test",
            "n_7": "validation_unseen_n",
            "n_8": "test_unseen_n",
            "identity": "SHA-256 of canonical P04 state serialization, including goal",
        },
        "case_count": len(samples),
        "split_counts": dict(sorted(split_counts.items())),
        "terminal_counts": dict(sorted(terminal_counts.items())),
        "nonterminal_optimal_action_set_size_counts": {str(key): value for key, value in sorted(uniqueness.items())},
        "split_identity_digests": {key: digest.hexdigest() for key, digest in sorted(digests.items())},
        "coverage": {split: dict(sorted(counts.items())) for split, counts in sorted(coverage.items())},
    }


def write_manifest(path: Path) -> dict[str, object]:
    result = manifest(build_corpus())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result
