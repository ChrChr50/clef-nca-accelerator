"""Shared local rule for the explicitly separate eight-channel P05 v2 experiment."""

from __future__ import annotations

from .model import require_torch


CHANNELS = 8
PARAMETER_COUNT = 2338


def build_v2_model(seed: int = 0):
    torch = require_torch()
    torch.manual_seed(seed)

    class HanoiNCAV2(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.conv1 = torch.nn.Conv2d(CHANNELS, 20, 3, padding=1, bias=True)
            self.conv2 = torch.nn.Conv2d(20, 30, 1, bias=True)
            self.conv3 = torch.nn.Conv2d(30, CHANNELS, 1, bias=True)
            torch.nn.init.kaiming_uniform_(self.conv1.weight, nonlinearity="relu")
            torch.nn.init.zeros_(self.conv1.bias)
            torch.nn.init.kaiming_uniform_(self.conv2.weight, nonlinearity="relu")
            torch.nn.init.zeros_(self.conv2.bias)
            torch.nn.init.zeros_(self.conv3.weight)
            torch.nn.init.zeros_(self.conv3.bias)

        def forward(self, state):
            return self.conv3(torch.relu(self.conv2(torch.relu(self.conv1(state)))))

    model = HanoiNCAV2()
    if sum(parameter.numel() for parameter in model.parameters()) != PARAMETER_COUNT:
        raise AssertionError("v2 local graph parameter count changed")
    return model
