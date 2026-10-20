"""Smoothly bounded P05 teaching variant of the v2 Hanoi NCA operator.

The arctangent residual has unit slope at zero, stays strictly within +/-5,
and has a nonzero derivative at every finite pre-bound value. It is an
experimental alternative to both v2 hard clipping and v3 unbounded state.
"""

from __future__ import annotations

import math

from .model import require_torch
from .v2_runtime import TorchNCAV2Runtime


def smooth_bound(value):
    torch = require_torch()
    return (10.0 / math.pi) * torch.atan((math.pi / 10.0) * value)


class TorchNCAV4Runtime(TorchNCAV2Runtime):
    def step(self, state, observations, mask=None):
        delta = self.model(state)
        proposed = smooth_bound(state + delta)
        if mask is not None:
            if mask.shape != (state.shape[0], 1, 32, 32):
                raise ValueError("mask must be [batch,1,32,32]")
            proposed = state + mask * (proposed - state)
        return self.rewrite(proposed, observations)


def boundary_margin_penalty(state):
    torch = require_torch()
    return torch.mean(torch.relu(state.abs() - 4.0) ** 2)
