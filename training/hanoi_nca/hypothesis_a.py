"""Training-only Hypothesis-A curriculum for the locked Hanoi NCA graph.

Nothing in this module is part of the deployable model.  In particular, oracle
labels, auxiliary concepts, probes, and trajectory construction remain on the
training/evaluation side of the P04 firewall.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
import math
from typing import Iterable

import numpy as np

from reference.hanoi.environment import ACTIONS, HanoiEnv, HanoiState, encode_observation, transition
from reference.hanoi.oracle import optimal_actions
from .model import require_torch


PEG_PERMUTATIONS = tuple(permutations(range(3)))
AUX_SCHEMA = "clef.p05.hypothesis-a.auxiliary.v1"


def inverse_permutation(permutation: tuple[int, int, int]) -> tuple[int, int, int]:
    inverse = [0, 0, 0]
    for old, new in enumerate(permutation):
        inverse[new] = old
    return tuple(inverse)


def permute_state(state: HanoiState, permutation: tuple[int, int, int]) -> HanoiState:
    if tuple(sorted(permutation)) != (0, 1, 2):
        raise ValueError("peg permutation must be a bijection of 0,1,2")
    return HanoiState(tuple(permutation[peg] for peg in state.locations), permutation[state.goal_peg])


def permute_action(action: int, permutation: tuple[int, int, int]) -> int:
    source, destination = ACTIONS[action]
    return ACTIONS.index((permutation[source], permutation[destination]))


def top_disks(state: HanoiState) -> tuple[int, int, int]:
    """Smallest disk index on each peg; N_MAX(8) is the empty sentinel."""
    tops = [8, 8, 8]
    for disk, peg in enumerate(state.locations):
        if tops[peg] == 8:
            tops[peg] = disk
    return tuple(tops)


def largest_unsettled_disk(state: HanoiState) -> int:
    """Largest disk not on the goal peg; 8 is the terminal sentinel."""
    for disk in range(state.disk_count - 1, -1, -1):
        if state.locations[disk] != state.goal_peg:
            return disk
    return 8


def peg_roles(state: HanoiState) -> tuple[int, int, int]:
    """Per-peg source/auxiliary/goal labels for the current recursive subgoal.

    Labels are 0=source, 1=auxiliary, 2=goal.  At terminal states the physical
    goal remains goal and the two other pegs receive deterministic source/aux
    labels in numeric order.  These solution-bearing labels are training-only.
    """
    disk = largest_unsettled_disk(state)
    destination = state.goal_peg
    if disk == 8:
        remaining = [peg for peg in range(3) if peg != destination]
        source, auxiliary = remaining
    else:
        source = state.locations[disk]
        auxiliary = next(peg for peg in range(3) if peg not in (source, destination))
    roles = [0, 0, 0]
    roles[source] = 0
    roles[auxiliary] = 1
    roles[destination] = 2
    return tuple(roles)


def legality_bits(state: HanoiState) -> tuple[float, ...]:
    return tuple(float(transition(state, action)[1]) for action in range(6))


def auxiliary_targets(states: Iterable[HanoiState]) -> dict[str, np.ndarray]:
    items = list(states)
    return {
        "legality": np.asarray([legality_bits(state) for state in items], dtype=np.float32),
        "top_disks": np.asarray([top_disks(state) for state in items], dtype=np.int64),
        "peg_roles": np.asarray([peg_roles(state) for state in items], dtype=np.int64),
        "subgoal_disk": np.asarray([largest_unsettled_disk(state) for state in items], dtype=np.int64),
    }


def representation(runtime, state):
    """Read only the six action sites (all channels), never the input cells."""
    torch = require_torch()
    return torch.cat(
        [state[:, :, row, column] for row, column in runtime.output_coordinates],
        dim=1,
    )


def build_auxiliary_heads(seed: int = 0):
    torch = require_torch()
    torch.manual_seed(seed)

    class AuxiliaryHeads(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.legality = torch.nn.Linear(36, 6)
            self.top_disks = torch.nn.ModuleList(torch.nn.Linear(36, 9) for _ in range(3))
            self.peg_roles = torch.nn.ModuleList(torch.nn.Linear(36, 3) for _ in range(3))
            self.subgoal_disk = torch.nn.Linear(36, 9)

        def forward(self, features):
            return {
                "legality": self.legality(features),
                "top_disks": [head(features) for head in self.top_disks],
                "peg_roles": [head(features) for head in self.peg_roles],
                "subgoal_disk": self.subgoal_disk(features),
            }

    return AuxiliaryHeads()


def auxiliary_loss(heads, features, targets: dict[str, np.ndarray]):
    torch = require_torch()
    predictions = heads(features)
    device = features.device
    legality = torch.as_tensor(targets["legality"], device=device)
    top = torch.as_tensor(targets["top_disks"], device=device)
    roles = torch.as_tensor(targets["peg_roles"], device=device)
    subgoal = torch.as_tensor(targets["subgoal_disk"], device=device)
    losses = {
        "legality": torch.nn.functional.binary_cross_entropy_with_logits(predictions["legality"], legality),
        "top_disks": sum(torch.nn.functional.cross_entropy(predictions["top_disks"][peg], top[:, peg]) for peg in range(3)) / 3,
        "peg_roles": sum(torch.nn.functional.cross_entropy(predictions["peg_roles"][peg], roles[:, peg]) for peg in range(3)) / 3,
        "subgoal_disk": torch.nn.functional.cross_entropy(predictions["subgoal_disk"], subgoal),
    }
    return sum(losses.values()) / len(losses), losses


def auxiliary_metrics(heads, features, targets: dict[str, np.ndarray]) -> dict[str, float]:
    torch = require_torch()
    with torch.no_grad():
        predictions = heads(features)
        legality = torch.as_tensor(targets["legality"], device=features.device)
        top = torch.as_tensor(targets["top_disks"], device=features.device)
        roles = torch.as_tensor(targets["peg_roles"], device=features.device)
        subgoal = torch.as_tensor(targets["subgoal_disk"], device=features.device)
        return {
            "legality_bit_accuracy": float(((predictions["legality"] >= 0) == (legality >= 0.5)).float().mean()),
            "top_disk_accuracy": float(torch.stack([(predictions["top_disks"][p].argmax(1) == top[:, p]).float().mean() for p in range(3)]).mean()),
            "peg_role_accuracy": float(torch.stack([(predictions["peg_roles"][p].argmax(1) == roles[:, p]).float().mean() for p in range(3)]).mean()),
            "subgoal_disk_accuracy": float((predictions["subgoal_disk"].argmax(1) == subgoal).float().mean()),
        }


@dataclass(frozen=True)
class MixedStepSchedule:
    short_min: int = 20
    short_max: int = 24
    long_min: int = 50
    long_max: int = 59
    long_every: int = 4

    def draw(self, iteration: int, rng: np.random.RandomState) -> tuple[int, str]:
        if iteration % self.long_every == self.long_every - 1:
            return int(rng.randint(self.long_min, self.long_max + 1)), "long"
        return int(rng.randint(self.short_min, self.short_max + 1)), "short"


def state_stability_penalty(state, bound: float = 5.0):
    torch = require_torch()
    overflow = torch.relu(state.abs() - bound)
    return torch.mean(overflow * overflow)


def state_statistics(state) -> dict[str, float | bool]:
    torch = require_torch()
    detached = state.detach()
    return {
        "finite": bool(torch.isfinite(detached).all()),
        "max_abs": float(torch.nan_to_num(detached.abs(), nan=math.inf, posinf=math.inf).max()),
        "mean_abs": float(torch.nan_to_num(detached.abs(), nan=math.inf, posinf=math.inf).mean()),
    }


def make_environment(state: HanoiState, budget: int) -> HanoiEnv:
    env = HanoiEnv(state.disk_count, state.goal_peg, budget)
    env.reset(seed=0, initial_locations=state.locations)
    return env


def standard_states(max_n: int = 6) -> list[HanoiState]:
    states = []
    for n in range(1, max_n + 1):
        for source in range(3):
            for goal in range(3):
                if source != goal:
                    states.append(HanoiState((source,) * n, goal))
    return states
