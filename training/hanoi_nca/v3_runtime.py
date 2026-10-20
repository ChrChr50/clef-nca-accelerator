"""Unclipped P05 teaching variant of the v2 Hanoi NCA runtime.

This intentionally leaves the accepted v2 runtime unchanged. Stability is
encouraged by a differentiable training loss, not a hard state clamp.
"""

from __future__ import annotations

from .model import require_torch
from .v2_runtime import TorchNCAV2Runtime


class TorchNCAV3Runtime(TorchNCAV2Runtime):
    def step(self, state, observations, mask=None):
        delta = self.model(state)
        if mask is not None:
            if mask.shape != (state.shape[0], 1, 32, 32):
                raise ValueError("mask must be [batch,1,32,32]")
            delta = delta * mask
        return self.rewrite(state + delta, observations)


def overflow_penalty(state):
    torch = require_torch()
    return torch.mean((state - torch.clamp(state, -5.0, 5.0)) ** 2)
