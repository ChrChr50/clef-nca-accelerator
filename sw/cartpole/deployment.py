"""Thin E01 host/controller boundary over the immutable P03 CartPole reference.

No plant equations, target actions, checkpoint selection, or RNG policy live here.
The caller supplies an episode's plant/controller state and every stochastic
NCA draw. A later transport can implement ControllerPort without changing the
host's plant authority.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from reference.original_nca.cartpole import CartPole
from reference.original_nca.core import CHANNELS, GRID_SIZE, CanonicalNCA


def _digest(array: NDArray[np.generic], dtype: str) -> str:
    return hashlib.sha256(np.asarray(array, dtype=dtype).tobytes(order="C")).hexdigest()


@dataclass(frozen=True)
class ControllerDecision:
    action: int
    raw_scores: tuple[float, float]
    state_sha256: str | None = None  # Optional read-only controller trace hook.


class ControllerPort(Protocol):
    def decide(
        self,
        observation: NDArray[np.float32],
        masks: NDArray[np.bool_],
        noise: NDArray[np.float32] | None = None,
    ) -> ControllerDecision: ...


@dataclass(frozen=True)
class DecisionTrace:
    observation_f32le_hex: str
    plant_before_sha256: str
    masks_sha256: str
    noise_sha256: str | None
    recurrent_steps: int
    action: int
    raw_scores_f32le_hex: str
    controller_after_sha256: str | None
    plant_after_sha256: str
    reward: float
    terminal: bool
    elapsed_plant_steps: int


class ReferenceController:
    """P03-backed adapter, with explicit initial grid and no implicit reset."""

    def __init__(self, nca: CanonicalNCA, initial_grid: NDArray[np.float32]):
        grid = np.asarray(initial_grid, dtype=np.float32)
        if grid.shape != (1, GRID_SIZE, GRID_SIZE, CHANNELS):
            raise ValueError("initial grid must have shape [1,32,32,6]")
        self.nca = nca
        self.grid = grid.copy()

    def decide(
        self,
        observation: NDArray[np.float32],
        masks: NDArray[np.bool_],
        noise: NDArray[np.float32] | None = None,
    ) -> ControllerDecision:
        _validate_draws(observation, masks, noise)
        obs = np.asarray(observation, dtype=np.float32)[None, :]
        for index, mask in enumerate(masks):
            update_noise = None if noise is None else noise[index]
            self.grid = self.nca.step(self.grid, obs, mask, update_noise=update_noise)
        scores = self.nca.readout(self.grid)[0]
        action = int(self.nca.action(self.grid)[0])
        return ControllerDecision(
            action,
            (float(scores[0]), float(scores[1])),
            _digest(self.grid, "<f4"),
        )


def _validate_draws(
    observation: NDArray[np.float32],
    masks: NDArray[np.bool_],
    noise: NDArray[np.float32] | None,
) -> None:
    if np.asarray(observation).shape != (4,):
        raise ValueError("observation must have four values")
    if masks.ndim != 5 or masks.shape[0] not in range(50, 60) or masks.shape[1:] != (1, 32, 32, 1):
        raise ValueError("masks must have shape [50..59,1,32,32,1]")
    if masks.dtype != np.bool_:
        raise TypeError("masks must be bool, with one bit shared across six channels")
    if noise is not None and (noise.shape != (masks.shape[0], 1, 32, 32, 6) or noise.dtype != np.float32):
        raise ValueError("noise must be float32 [steps,1,32,32,6]")


class CartPoleHost:
    """One explicit plant episode; never chooses controller or reset policy."""

    def __init__(self, plant: CartPole, controller: ControllerPort):
        self.plant = plant
        self.controller = controller
        self.terminal = False

    def step(
        self,
        masks: NDArray[np.bool_],
        noise: NDArray[np.float32] | None = None,
    ) -> DecisionTrace:
        if self.terminal:
            raise RuntimeError("episode already terminated; construct a new explicit episode")
        observation = self.plant.state.astype(np.float32)
        _validate_draws(observation, masks, noise)
        before = _digest(self.plant.state, "<f8")
        decision = self.controller.decide(observation, masks, noise)
        if decision.action not in (0, 1):
            raise ValueError("controller action must be 0 or 1")
        scores = np.asarray(decision.raw_scores, dtype=np.float32)
        if scores.shape != (2,):
            raise ValueError("controller must return two raw scores")
        _, reward, done = self.plant.step(decision.action)
        self.terminal = done
        packed_masks = np.packbits(masks.reshape(-1), bitorder="little")
        return DecisionTrace(
            observation_f32le_hex=np.asarray(observation, dtype="<f4").tobytes().hex(),
            plant_before_sha256=before,
            masks_sha256=hashlib.sha256(packed_masks.tobytes()).hexdigest(),
            noise_sha256=None if noise is None else _digest(noise, "<f4"),
            recurrent_steps=int(masks.shape[0]),
            action=decision.action,
            raw_scores_f32le_hex=np.asarray(scores, dtype="<f4").tobytes().hex(),
            controller_after_sha256=decision.state_sha256,
            plant_after_sha256=_digest(self.plant.state, "<f8"),
            reward=reward,
            terminal=done,
            elapsed_plant_steps=self.plant.step_count,
        )
