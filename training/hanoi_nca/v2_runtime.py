"""Differentiable bounded eight-channel Hanoi NCA runtime, without task labels."""

from __future__ import annotations

import numpy as np

from .layout import load_layout
from .model import require_torch
from .v2_adapter import LAYOUT_PATH
from .v2_model import CHANNELS


class TorchNCAV2Runtime:
    def __init__(self, model, layout_path=None) -> None:
        torch = require_torch()
        self.model = model
        self.layout = load_layout(LAYOUT_PATH if layout_path is None else layout_path)
        marker_keep = torch.ones((1, CHANNELS, 32, 32), dtype=torch.float32)
        marker_keep[:, 6:8, :, :] = 0.0
        input_keep = torch.ones((1, CHANNELS, 32, 32), dtype=torch.float32)
        marker = torch.zeros((1, CHANNELS, 32, 32), dtype=torch.float32)
        basis = torch.zeros((36, 32, 32), dtype=torch.float32)
        for index, (row, column) in enumerate(self.layout.input_coordinates):
            input_keep[:, :, row, column] = 0.0
            marker[:, 6, row, column] = 1.0
            basis[index, row, column] = 1.0
        for row, column in self.layout.output_coordinates:
            marker[:, 7, row, column] = 1.0
        self.marker_keep = marker_keep
        self.input_keep = input_keep
        self.marker = marker
        self.basis = basis
        self.output_coordinates = self.layout.output_coordinates

    def to(self, device):
        for name in ("marker_keep", "input_keep", "marker", "basis"):
            setattr(self, name, getattr(self, name).to(device))
        self.model.to(device)
        return self

    def initial_state(self, batch_size: int, seed: int, device="cpu"):
        torch = require_torch()
        rng = np.random.RandomState(seed)
        values = rng.uniform(-0.1, 0.1, size=(batch_size, CHANNELS, 32, 32)).astype(np.float32)
        values[:, 6:8, :, :] = 0.0
        return torch.from_numpy(values).to(device)

    def rewrite(self, state, observations):
        torch = require_torch()
        if state.ndim != 4 or state.shape[1:] != (CHANNELS, 32, 32):
            raise ValueError("state must be [batch,8,32,32]")
        if observations.shape != (state.shape[0], 36):
            raise ValueError("observations must be [batch,36]")
        state = state * self.marker_keep * self.input_keep + self.marker
        injected = torch.einsum("bi,ihw->bhw", observations, self.basis)
        channel0 = torch.zeros_like(state)
        channel0[:, 0, :, :] = injected
        return state + channel0

    def step(self, state, observations, mask=None):
        torch = require_torch()
        delta = self.model(state)
        if mask is not None:
            if mask.shape != (state.shape[0], 1, 32, 32):
                raise ValueError("mask must be [batch,1,32,32]")
            delta = delta * mask
        return self.rewrite(torch.clamp(state + delta, -5.0, 5.0), observations)

    def run(self, state, observations, steps: int, fire_rate: float, generator=None, masks=None):
        torch = require_torch()
        if steps < 0 or not 0.0 <= fire_rate <= 1.0:
            raise ValueError("steps and fire rate are invalid")
        if masks is not None and len(masks) != steps:
            raise ValueError("mask trace length does not match steps")
        # Unlike v1, each new observation is present before the first local update.
        state = self.rewrite(state, observations)
        for index in range(steps):
            if masks is not None:
                mask = masks[index]
            elif fire_rate < 1.0:
                mask = (
                    torch.rand(
                        (state.shape[0], 1, 32, 32),
                        generator=generator,
                        device=state.device,
                    )
                    <= fire_rate
                ).to(state.dtype)
            else:
                mask = None
            state = self.step(state, observations, mask)
        return state

    def readout(self, state):
        torch = require_torch()
        return torch.stack(
            [state[:, 0, row, column] for row, column in self.output_coordinates], dim=1
        )

    def decide(self, state):
        return self.readout(state).argmax(dim=1)
