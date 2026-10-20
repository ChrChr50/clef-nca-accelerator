"""Deterministic checkpoint rollout and empirical evaluation helpers."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .cartpole import CartPole
from .core import CanonicalNCA, seeded_initial_grid


@dataclass(frozen=True)
class EpisodeResult:
    steps: int
    reward_sum: float
    actions_sha256: str


def run_episode(
    nca: CanonicalNCA,
    seed: int,
    *,
    noisy_updates: bool = False,
    deleted_inputs: tuple[int, ...] = (),
    damage_after_input_probability: float = 0.0,
    continuous_damage_probability: float = 0.0,
    max_steps: int = 10_001,
) -> EpisodeResult:
    """Run one executable-source-aligned evaluation episode.

    NumPy supplies a single recorded RNG stream. It cannot claim identity with
    TensorFlow's unavailable historical RNG stream, so these results are
    empirical rather than exact algorithmic evidence.
    """

    import hashlib

    from .core import CHANNELS, GRID_SIZE, damage_with_trace

    rng = np.random.RandomState(seed)
    env = CartPole.reset(rng)
    grid = seeded_initial_grid(seed ^ 0x5A17)
    active = [True] * 8
    for index in deleted_inputs:
        active[index] = False
    actions: list[int] = []
    reward_sum = 0.0
    for _ in range(max_steps):
        observation = env.state.astype(np.float32)[None, :]
        steps = int(rng.randint(50, 60))
        if damage_after_input_probability and rng.random_sample() < damage_after_input_probability:
            grid = _random_damage(grid, rng, damage_with_trace)
        for _ in range(steps):
            mask = rng.random_sample((1, GRID_SIZE, GRID_SIZE, 1)) <= 0.5
            noise = None
            if noisy_updates:
                noise = (
                    np.float32(0.01)
                    * rng.uniform(-1.0, 1.0, size=(1, GRID_SIZE, GRID_SIZE, CHANNELS))
                ).astype(np.float32)
            grid = nca.step(grid, observation, mask, update_noise=noise, active_inputs=active)
            if continuous_damage_probability and rng.random_sample() < continuous_damage_probability:
                grid = _random_damage(grid, rng, damage_with_trace)
        action = int(nca.action(grid)[0])
        actions.append(action)
        _, reward, done = env.step(action)
        reward_sum += reward
        if done:
            break
    digest = hashlib.sha256(bytes(actions)).hexdigest()
    return EpisodeResult(len(actions), reward_sum, digest)


def _random_damage(grid, rng, damage_fn):
    from .core import CHANNELS, GRID_SIZE

    centers = rng.uniform(-0.5, 0.5, size=(2, 1, 1, 1)).astype(np.float32)
    radii = rng.uniform(0.3, 0.4, size=(1, 1, 1)).astype(np.float32)
    replacements = rng.uniform(
        -1.0, 1.0, size=(1, GRID_SIZE, GRID_SIZE, CHANNELS)
    ).astype(np.float32)
    return damage_fn(grid, centers, radii, replacements)
