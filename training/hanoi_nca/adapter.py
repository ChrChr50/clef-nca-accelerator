"""Deployment-shaped Hanoi NCA adapter with no training labels or task grammar."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from reference.hanoi.environment import OBSERVATION_WIDTH
from .layout import Layout, load_layout


GRID_SIZE = 32
CHANNELS = 6


class HanoiAdapter:
    def __init__(self, layout: Layout | None = None, output_hidden_policy: str = "accumulate") -> None:
        self.layout = layout or load_layout()
        if output_hidden_policy not in {"accumulate", "clamp_one"}:
            raise ValueError("unsupported output hidden-channel policy")
        self.output_hidden_policy = output_hidden_policy

    def rewrite(
        self,
        state: NDArray[np.float32],
        observations: NDArray[np.float32],
    ) -> NDArray[np.float32]:
        updated = np.asarray(state, dtype=np.float32).copy()
        values = np.asarray(observations, dtype=np.float32)
        if updated.ndim != 4 or updated.shape[1:] != (GRID_SIZE, GRID_SIZE, CHANNELS):
            raise ValueError("state must be [batch,32,32,6]")
        if values.shape != (updated.shape[0], OBSERVATION_WIDTH):
            raise ValueError("observations must be [batch,36]")
        updated[..., 2] = 0.0
        updated[..., 3] = 0.0
        for index, (row, column) in enumerate(self.layout.input_coordinates):
            updated[:, row, column, :] = 0.0
            updated[:, row, column, 0] = values[:, index]
            updated[:, row, column, 1] = 1.0
            updated[:, row, column, 2] = 1.0
            updated[:, row, column, 4] = 1.0
            updated[:, row, column, 5] = 1.0
        for row, column in self.layout.output_coordinates:
            updated[:, row, column, 3] = 1.0
            if self.output_hidden_policy == "accumulate":
                updated[:, row, column, 4] += 1.0
                updated[:, row, column, 5] += 1.0
            else:
                updated[:, row, column, 4] = 1.0
                updated[:, row, column, 5] = 1.0
        return updated

    def readout(self, state: NDArray[np.float32]) -> NDArray[np.float32]:
        values = np.asarray(state, dtype=np.float32)
        return np.stack(
            [values[:, row, column, 0] for row, column in self.layout.output_coordinates], axis=1
        ).astype(np.float32)

    @staticmethod
    def select_action(scores: NDArray[np.float32]) -> NDArray[np.int64]:
        return np.argmax(np.asarray(scores), axis=-1).astype(np.int64)
