"""Deterministic, reward-free Tower-of-Hanoi transition environment.

Disk zero is the smallest disk. A state is the tuple of peg locations in
smallest-to-largest order; disk ordering on each peg is therefore implicit.
This module deliberately contains no shortest-path or target-shaping logic.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Iterable, Iterator, Sequence


N_MAX = 8
OBSERVATION_WIDTH = 4 * N_MAX + 3 + 1
ACTIONS: tuple[tuple[int, int], ...] = (
    (0, 1),
    (0, 2),
    (1, 0),
    (1, 2),
    (2, 0),
    (2, 1),
)
_SNAPSHOT_SCHEMA = "clef.hanoi.snapshot.v1"


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _seeded_locations(seed: int, disk_count: int) -> tuple[int, ...]:
    """Generate a runtime-independent reset assignment using SHA-256 counters."""
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be an integer")
    return tuple(
        hashlib.sha256(f"clef.hanoi.reset.v1:{seed}:{disk}".encode("ascii")).digest()[0] % 3
        for disk in range(disk_count)
    )


@dataclass(frozen=True, slots=True)
class HanoiState:
    """Canonical Hanoi state and goal, independent of episode bookkeeping."""

    locations: tuple[int, ...]
    goal_peg: int

    def __post_init__(self) -> None:
        if any(isinstance(value, bool) or not isinstance(value, int) for value in self.locations):
            raise ValueError("every disk location must be an integer")
        if not 1 <= len(self.locations) <= N_MAX:
            raise ValueError(f"disk count must be in [1, {N_MAX}]")
        if isinstance(self.goal_peg, bool) or not isinstance(self.goal_peg, int) or self.goal_peg not in (0, 1, 2):
            raise ValueError("goal_peg must be 0, 1, or 2")
        if any(peg not in (0, 1, 2) for peg in self.locations):
            raise ValueError("every disk location must be 0, 1, or 2")

    @property
    def disk_count(self) -> int:
        return len(self.locations)

    @property
    def terminal(self) -> bool:
        return all(peg == self.goal_peg for peg in self.locations)

    def as_dict(self) -> dict[str, object]:
        return {
            "disk_count": self.disk_count,
            "goal_peg": self.goal_peg,
            "locations": list(self.locations),
        }

    def serialize(self) -> bytes:
        return _canonical_json(self.as_dict())

    @classmethod
    def deserialize(cls, payload: bytes | str) -> "HanoiState":
        raw = json.loads(payload)
        if set(raw) != {"disk_count", "goal_peg", "locations"}:
            raise ValueError("state has unknown or missing fields")
        locations = tuple(raw["locations"])
        if raw["disk_count"] != len(locations):
            raise ValueError("disk_count does not match locations")
        return cls(locations=locations, goal_peg=raw["goal_peg"])

    @property
    def state_hash(self) -> str:
        return hashlib.sha256(self.serialize()).hexdigest()


@dataclass(frozen=True, slots=True)
class StepResult:
    state: HanoiState
    action: int
    source_peg: int
    destination_peg: int
    legal: bool
    moved_disk: int | None
    moves_taken: int
    terminated: bool
    truncated: bool


class EpisodeFinishedError(RuntimeError):
    """Raised if step is called after terminal or move-budget completion."""


def top_disk(locations: Sequence[int], peg: int) -> int | None:
    if peg not in (0, 1, 2):
        raise ValueError("peg must be 0, 1, or 2")
    return next((disk for disk, location in enumerate(locations) if location == peg), None)


def transition(state: HanoiState, action: int) -> tuple[HanoiState, bool, int | None]:
    """Apply one ordered action; an illegal action is an exact state no-op."""
    if isinstance(action, bool) or not isinstance(action, int) or not 0 <= action < len(ACTIONS):
        raise ValueError("action must be an integer in [0, 5]")
    source, destination = ACTIONS[action]
    moving = top_disk(state.locations, source)
    destination_top = top_disk(state.locations, destination)
    legal = moving is not None and (destination_top is None or moving < destination_top)
    if not legal:
        return state, False, None
    updated = list(state.locations)
    updated[moving] = destination
    return HanoiState(tuple(updated), state.goal_peg), True, moving


def encode_observation(state: HanoiState) -> tuple[float, ...]:
    """Encode the locked 36-value observation in disk-slot-major order."""
    observation = [0.0] * OBSERVATION_WIDTH
    for disk, peg in enumerate(state.locations):
        offset = 4 * disk
        observation[offset + peg] = 1.0
        observation[offset + 3] = 1.0
    observation[4 * N_MAX + state.goal_peg] = 1.0
    observation[-1] = state.disk_count / N_MAX
    return tuple(observation)


def decode_observation(observation: Sequence[float]) -> HanoiState:
    """Strictly decode an observation produced by :func:`encode_observation`."""
    if len(observation) != OBSERVATION_WIDTH:
        raise ValueError(f"observation must contain {OBSERVATION_WIDTH} values")
    goal_bits = tuple(observation[4 * N_MAX : 4 * N_MAX + 3])
    if goal_bits.count(1.0) != 1 or any(value not in (0.0, 1.0) for value in goal_bits):
        raise ValueError("goal field must be exactly one-hot")
    disk_count_value = observation[-1] * N_MAX
    disk_count = int(disk_count_value)
    if disk_count_value != disk_count or not 1 <= disk_count <= N_MAX:
        raise ValueError("normalized disk count is not an exact supported count")
    locations: list[int] = []
    for disk in range(N_MAX):
        slot = tuple(observation[4 * disk : 4 * disk + 4])
        if disk < disk_count:
            if slot[3] != 1.0 or slot[:3].count(1.0) != 1 or any(
                value not in (0.0, 1.0) for value in slot
            ):
                raise ValueError("present disk slot is not canonical")
            locations.append(slot[:3].index(1.0))
        elif slot != (0.0, 0.0, 0.0, 0.0):
            raise ValueError("absent disk slots must be all zero")
    return HanoiState(tuple(locations), goal_bits.index(1.0))


def iter_states(disk_count: int, goal_peg: int) -> Iterator[HanoiState]:
    """Yield all 3**disk_count canonical assignments in base-three order."""
    if not 1 <= disk_count <= N_MAX:
        raise ValueError(f"disk_count must be in [1, {N_MAX}]")
    if goal_peg not in (0, 1, 2):
        raise ValueError("goal_peg must be 0, 1, or 2")
    for code in range(3**disk_count):
        value = code
        locations = []
        for _ in range(disk_count):
            locations.append(value % 3)
            value //= 3
        yield HanoiState(tuple(locations), goal_peg)


class HanoiEnv:
    """Episode wrapper around the pure transition function.

    Every attempted action, legal or illegal, consumes one move-budget unit.
    Reward and target shaping are deliberately absent.
    """

    def __init__(
        self,
        disk_count: int,
        goal_peg: int,
        move_budget: int,
    ) -> None:
        if isinstance(disk_count, bool) or not isinstance(disk_count, int) or not 1 <= disk_count <= N_MAX:
            raise ValueError(f"disk_count must be in [1, {N_MAX}]")
        if isinstance(goal_peg, bool) or not isinstance(goal_peg, int) or goal_peg not in (0, 1, 2):
            raise ValueError("goal_peg must be 0, 1, or 2")
        self.disk_count = disk_count
        self.goal_peg = goal_peg
        self.move_budget = move_budget
        if isinstance(self.move_budget, bool) or not isinstance(self.move_budget, int) or self.move_budget <= 0:
            raise ValueError("move_budget must be positive")
        self.state = HanoiState((0,) * disk_count, goal_peg)
        self.moves_taken = 0
        self.reset_seed: int | None = None
        self.truncated = False

    @property
    def terminated(self) -> bool:
        return self.state.terminal

    def reset(
        self,
        *,
        seed: int = 0,
        initial_locations: Iterable[int] | None = None,
        standard_source: int | None = None,
    ) -> HanoiState:
        if initial_locations is not None and standard_source is not None:
            raise ValueError("initial_locations and standard_source are mutually exclusive")
        if standard_source is not None:
            if standard_source not in (0, 1, 2):
                raise ValueError("standard_source must be 0, 1, or 2")
            locations = (standard_source,) * self.disk_count
        elif initial_locations is not None:
            locations = tuple(initial_locations)
        else:
            locations = _seeded_locations(seed, self.disk_count)
        state = HanoiState(locations, self.goal_peg)
        if state.disk_count != self.disk_count:
            raise ValueError("initial_locations length must equal disk_count")
        self.state = state
        self.moves_taken = 0
        self.reset_seed = seed
        self.truncated = False
        return state

    def step(self, action: int) -> StepResult:
        if self.terminated or self.truncated:
            raise EpisodeFinishedError("reset is required after episode completion")
        source, destination = ACTIONS[action] if 0 <= action < 6 else (-1, -1)
        next_state, legal, moved_disk = transition(self.state, action)
        self.state = next_state
        self.moves_taken += 1
        self.truncated = self.moves_taken >= self.move_budget and not self.terminated
        return StepResult(
            state=self.state,
            action=action,
            source_peg=source,
            destination_peg=destination,
            legal=legal,
            moved_disk=moved_disk,
            moves_taken=self.moves_taken,
            terminated=self.terminated,
            truncated=self.truncated,
        )

    def serialize(self) -> bytes:
        return _canonical_json(
            {
                "disk_count": self.disk_count,
                "goal_peg": self.goal_peg,
                "move_budget": self.move_budget,
                "moves_taken": self.moves_taken,
                "reset_seed": self.reset_seed,
                "schema": _SNAPSHOT_SCHEMA,
                "state": self.state.as_dict(),
                "truncated": self.truncated,
            }
        )

    @classmethod
    def deserialize(cls, payload: bytes | str) -> "HanoiEnv":
        raw = json.loads(payload)
        expected = {
            "disk_count",
            "goal_peg",
            "move_budget",
            "moves_taken",
            "reset_seed",
            "schema",
            "state",
            "truncated",
        }
        if set(raw) != expected or raw["schema"] != _SNAPSHOT_SCHEMA:
            raise ValueError("snapshot schema or fields are invalid")
        env = cls(raw["disk_count"], raw["goal_peg"], raw["move_budget"])
        state = HanoiState.deserialize(_canonical_json(raw["state"]))
        if state.disk_count != env.disk_count or state.goal_peg != env.goal_peg:
            raise ValueError("snapshot state/configuration mismatch")
        moves_taken = raw["moves_taken"]
        if not isinstance(moves_taken, int) or not 0 <= moves_taken <= env.move_budget:
            raise ValueError("moves_taken is invalid")
        if not isinstance(raw["truncated"], bool):
            raise ValueError("truncated must be boolean")
        if raw["truncated"] != (moves_taken >= env.move_budget and not state.terminal):
            raise ValueError("truncated flag is inconsistent")
        env.state = state
        env.moves_taken = moves_taken
        env.reset_seed = raw["reset_seed"]
        env.truncated = raw["truncated"]
        return env

    @property
    def snapshot_hash(self) -> str:
        return hashlib.sha256(self.serialize()).hexdigest()
