"""Executable, non-optimizing forms of the released curriculum and pool rules."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from .core import CHANNELS, GRID_SIZE, seeded_initial_grid


def curriculum_targets(inputs: NDArray[np.float32]) -> NDArray[np.float32]:
    """Notebook warm-up target: both outputs equal four times input mean."""

    mean = np.mean(np.asarray(inputs, dtype=np.float32), axis=-1, keepdims=True)
    return np.repeat(mean * np.float32(4.0), 2, axis=-1).astype(np.float32)


def recurrent_step_count(rng: np.random.RandomState) -> int:
    """Released exclusive-upper-bound schedule."""

    return int(rng.randint(50, 60))


@dataclass
class GridPool:
    """Stateful batch pool with explicit sampling and commit semantics.

    Damage and positional perturbation are separate operators because their
    random draws belong in the replay trace.
    """

    batches: NDArray[np.float32]
    current_index: int | None = None

    @classmethod
    def initialize(cls, pool_size: int, batch_size: int, seed: int) -> "GridPool":
        grids = seeded_initial_grid(seed, pool_size * batch_size)
        return cls(grids.reshape(pool_size, batch_size, GRID_SIZE, GRID_SIZE, CHANNELS))

    def sample(self, index: int) -> NDArray[np.float32]:
        if self.current_index is not None:
            raise RuntimeError("a sampled batch must be committed before another sample")
        if not 0 <= index < self.batches.shape[0]:
            raise IndexError(index)
        self.current_index = index
        return self.batches[index].copy()

    def reinitialize_and_sample(self, index: int, seed: int) -> NDArray[np.float32]:
        batch_size = self.batches.shape[1]
        self.batches[index] = seeded_initial_grid(seed, batch_size)
        return self.sample(index)

    def commit(self, updated: NDArray[np.float32]) -> None:
        if self.current_index is None:
            raise RuntimeError("no sampled batch")
        self.batches[self.current_index] = np.asarray(updated, dtype=np.float32)
        self.current_index = None

