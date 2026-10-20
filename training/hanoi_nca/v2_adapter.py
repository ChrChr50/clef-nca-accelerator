"""NumPy reference for the P05 v2 post-update I/O and bounded residual."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from reference.hanoi.environment import OBSERVATION_WIDTH
from .layout import Layout, load_layout
from .v2_model import CHANNELS


GRID_SIZE = 32
STATE_BOUND = np.float32(5.0)
LAYOUT_PATH = Path(__file__).with_name("layout_v2.json")


class HanoiV2Adapter:
    def __init__(self, layout: Layout | None = None) -> None:
        self.layout = layout or load_layout(LAYOUT_PATH)

    def rewrite(
        self,
        state: NDArray[np.float32],
        observations: NDArray[np.float32],
    ) -> NDArray[np.float32]:
        updated = np.asarray(state, dtype=np.float32).copy()
        values = np.asarray(observations, dtype=np.float32)
        if updated.ndim != 4 or updated.shape[1:] != (GRID_SIZE, GRID_SIZE, CHANNELS):
            raise ValueError("state must be [batch,32,32,8]")
        if values.shape != (updated.shape[0], OBSERVATION_WIDTH):
            raise ValueError("observations must be [batch,36]")
        # Channels 6 and 7 are immutable site-type markers, not working memory.
        updated[..., 6:8] = 0.0
        for index, (row, column) in enumerate(self.layout.input_coordinates):
            updated[:, row, column, :] = 0.0
            updated[:, row, column, 0] = values[:, index]
            updated[:, row, column, 6] = 1.0
        for row, column in self.layout.output_coordinates:
            updated[:, row, column, 7] = 1.0
        return updated

    def step(
        self,
        state: NDArray[np.float32],
        observations: NDArray[np.float32],
        delta: NDArray[np.float32],
        mask: NDArray[np.float32],
    ) -> NDArray[np.float32]:
        old = np.asarray(state, dtype=np.float32)
        proposed = np.asarray(delta, dtype=np.float32)
        selected = np.asarray(mask, dtype=np.float32)
        if proposed.shape != old.shape or selected.shape != (*old.shape[:3], 1):
            raise ValueError("delta or mask shape mismatch")
        residual = np.clip(old + selected * proposed, -STATE_BOUND, STATE_BOUND)
        return self.rewrite(residual, observations)

    def readout(self, state: NDArray[np.float32]) -> NDArray[np.float32]:
        values = np.asarray(state, dtype=np.float32)
        return np.stack(
            [values[:, row, column, 0] for row, column in self.layout.output_coordinates],
            axis=1,
        ).astype(np.float32)

    @staticmethod
    def select_action(scores: NDArray[np.float32]) -> NDArray[np.int64]:
        return np.argmax(np.asarray(scores), axis=-1).astype(np.int64)
