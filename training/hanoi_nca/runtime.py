"""Differentiable NCA runtime using only observation/layout model inputs."""

from __future__ import annotations

import numpy as np

from .layout import load_layout
from .model import require_torch


class TorchNCARuntime:
    def __init__(self, model, output_hidden_policy: str = "accumulate") -> None:
        torch = require_torch()
        if output_hidden_policy not in {"accumulate", "clamp_one"}:
            raise ValueError("unsupported output hidden-channel policy")
        self.model = model
        self.policy = output_hidden_policy
        layout = load_layout()
        global_keep = torch.ones((1, 6, 32, 32), dtype=torch.float32)
        global_keep[:, 2:4, :, :] = 0.0
        input_keep = torch.ones((1, 6, 32, 32), dtype=torch.float32)
        marker = torch.zeros((1, 6, 32, 32), dtype=torch.float32)
        basis = torch.zeros((36, 32, 32), dtype=torch.float32)
        for index, (row, column) in enumerate(layout.input_coordinates):
            input_keep[:, :, row, column] = 0.0
            marker[:, 1, row, column] = 1.0
            marker[:, 2, row, column] = 1.0
            marker[:, 4, row, column] = 1.0
            marker[:, 5, row, column] = 1.0
            basis[index, row, column] = 1.0
        output_clamp_keep = torch.ones((1, 6, 32, 32), dtype=torch.float32)
        for row, column in layout.output_coordinates:
            marker[:, 3, row, column] = 1.0
            marker[:, 4, row, column] = 1.0
            marker[:, 5, row, column] = 1.0
            if self.policy == "clamp_one":
                output_clamp_keep[:, 4:6, row, column] = 0.0
        self.global_keep = global_keep
        self.input_keep = input_keep
        self.output_clamp_keep = output_clamp_keep
        self.marker = marker
        self.basis = basis
        self.output_coordinates = layout.output_coordinates

    def to(self, device):
        for name in ("global_keep", "input_keep", "output_clamp_keep", "marker", "basis"):
            setattr(self, name, getattr(self, name).to(device))
        return self

    def initial_state(self, batch_size: int, seed: int, device="cpu"):
        torch = require_torch()
        rng = np.random.RandomState(seed)
        values = rng.uniform(-0.1, 0.1, size=(batch_size, 6, 32, 32)).astype(np.float32)
        return torch.from_numpy(values).to(device)

    def rewrite(self, state, observations):
        torch = require_torch()
        state = state * self.global_keep
        state = state * self.input_keep
        if self.policy == "clamp_one":
            state = state * self.output_clamp_keep
        state = state + self.marker
        injected = torch.einsum("bi,ihw->bhw", observations, self.basis)
        channel0 = torch.zeros_like(state)
        channel0[:, 0, :, :] = injected
        return state + channel0

    def step(self, state, observations, mask=None):
        delta = self.model(state)
        if mask is not None:
            delta = delta * mask
        return self.rewrite(state + delta, observations)

    def run(self, state, observations, steps: int, fire_rate: float, generator=None):
        torch = require_torch()
        for _ in range(steps):
            mask = None
            if fire_rate < 1.0:
                mask = (
                    torch.rand(
                        (state.shape[0], 1, 32, 32),
                        generator=generator,
                        device=state.device,
                    )
                    <= fire_rate
                ).to(state.dtype)
            state = self.step(state, observations, mask)
        return state

    def readout(self, state):
        torch = require_torch()
        return torch.stack([state[:, 0, row, column] for row, column in self.output_coordinates], dim=1)

    def decide(self, state):
        return self.readout(state).argmax(dim=1)
