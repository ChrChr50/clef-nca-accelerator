"""Deterministic Tower-of-Hanoi environment contract.

The optimal-distance helper is intentionally not re-exported from this package.
Training and evaluation code must opt into that separate module explicitly.
"""

from .environment import (
    ACTIONS,
    N_MAX,
    OBSERVATION_WIDTH,
    EpisodeFinishedError,
    HanoiEnv,
    HanoiState,
    StepResult,
    decode_observation,
    encode_observation,
    transition,
)

__all__ = [
    "ACTIONS",
    "N_MAX",
    "OBSERVATION_WIDTH",
    "EpisodeFinishedError",
    "HanoiEnv",
    "HanoiState",
    "StepResult",
    "decode_observation",
    "encode_observation",
    "transition",
]
