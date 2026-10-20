"""TRAINING/EVALUATION ONLY: independent optimal-distance Hanoi oracle.

This module is outside the environment contract and is forbidden from model
export, deployment packages, and synthesized RTL artifacts.
"""

from __future__ import annotations

from collections import deque
from functools import lru_cache
import hashlib

from .environment import ACTIONS, N_MAX, HanoiState, transition


def encode_locations(locations: tuple[int, ...]) -> int:
    code = 0
    multiplier = 1
    for peg in locations:
        code += peg * multiplier
        multiplier *= 3
    return code


def decode_locations(code: int, disk_count: int) -> tuple[int, ...]:
    if not 1 <= disk_count <= N_MAX or not 0 <= code < 3**disk_count:
        raise ValueError("code or disk_count is out of range")
    locations = []
    for _ in range(disk_count):
        locations.append(code % 3)
        code //= 3
    return tuple(locations)


@lru_cache(maxsize=None)
def reverse_graph_distances(disk_count: int, goal_peg: int) -> tuple[int, ...]:
    """Build exact distances by reverse BFS from the selected terminal state."""
    if not 1 <= disk_count <= N_MAX or goal_peg not in (0, 1, 2):
        raise ValueError("unsupported disk_count or goal_peg")
    count = 3**disk_count
    distances = [-1] * count
    terminal = (goal_peg,) * disk_count
    terminal_code = encode_locations(terminal)
    distances[terminal_code] = 0
    queue: deque[tuple[int, ...]] = deque([terminal])
    while queue:
        locations = queue.popleft()
        distance = distances[encode_locations(locations)]
        state = HanoiState(locations, goal_peg)
        for action in range(len(ACTIONS)):
            successor, legal, _ = transition(state, action)
            if not legal:
                continue
            successor_code = encode_locations(successor.locations)
            if distances[successor_code] == -1:
                distances[successor_code] = distance + 1
                queue.append(successor.locations)
    if any(distance < 0 for distance in distances):
        raise AssertionError("reverse graph did not reach every canonical state")
    return tuple(distances)


def recursive_distance(locations: tuple[int, ...], goal_peg: int) -> int:
    """Independent exact recurrence, used to cross-check reverse BFS."""
    if goal_peg not in (0, 1, 2) or any(peg not in (0, 1, 2) for peg in locations):
        raise ValueError("locations and goal_peg must use pegs 0, 1, and 2")
    if not locations:
        return 0
    largest_peg = locations[-1]
    if largest_peg == goal_peg:
        return recursive_distance(locations[:-1], goal_peg)
    auxiliary = 3 - largest_peg - goal_peg
    return recursive_distance(locations[:-1], auxiliary) + 1 + ((1 << (len(locations) - 1)) - 1)


def optimal_actions(state: HanoiState) -> tuple[int, ...]:
    distances = reverse_graph_distances(state.disk_count, state.goal_peg)
    current = distances[encode_locations(state.locations)]
    if current == 0:
        return ()
    optimal: list[int] = []
    for action in range(len(ACTIONS)):
        successor, legal, _ = transition(state, action)
        if legal and distances[encode_locations(successor.locations)] == current - 1:
            optimal.append(action)
    return tuple(optimal)


def distance_table_hash(disk_count: int, goal_peg: int) -> str:
    distances = reverse_graph_distances(disk_count, goal_peg)
    return hashlib.sha256(bytes(distances)).hexdigest()
