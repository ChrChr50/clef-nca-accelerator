"""The 1,916-parameter Hanoi derivative of the immutable local NCA graph."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    import torch


PARAMETER_COUNT = 1916


def require_torch():
    try:
        import torch
    except ImportError as error:
        raise RuntimeError("P05 training requires the pinned training environment") from error
    return torch


def build_model(seed: int = 0):
    torch = require_torch()
    torch.manual_seed(seed)

    class HanoiNCA(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.conv1 = torch.nn.Conv2d(6, 20, 3, padding=1, bias=True)
            self.conv2 = torch.nn.Conv2d(20, 30, 1, bias=True)
            self.conv3 = torch.nn.Conv2d(30, 6, 1, bias=True)
            torch.nn.init.kaiming_uniform_(self.conv1.weight, nonlinearity="relu")
            torch.nn.init.zeros_(self.conv1.bias)
            torch.nn.init.kaiming_uniform_(self.conv2.weight, nonlinearity="relu")
            torch.nn.init.zeros_(self.conv2.bias)
            torch.nn.init.zeros_(self.conv3.weight)
            torch.nn.init.zeros_(self.conv3.bias)

        def forward(self, state):
            hidden = torch.relu(self.conv1(state))
            hidden = torch.relu(self.conv2(hidden))
            return self.conv3(hidden)

    model = HanoiNCA()
    if sum(parameter.numel() for parameter in model.parameters()) != PARAMETER_COUNT:
        raise AssertionError("local graph parameter count changed")
    return model


def save_checkpoint(model, path: Path, metadata: dict[str, object]) -> None:
    arrays: dict[str, object] = {"metadata_json": np.asarray(__import__("json").dumps(metadata, sort_keys=True))}
    for name, tensor in model.state_dict().items():
        arrays[name] = tensor.detach().cpu().numpy().astype(np.float32)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **arrays)


def load_checkpoint(path: Path):
    torch = require_torch()
    model = build_model()
    archive = np.load(path, allow_pickle=False)
    state = {name: torch.from_numpy(archive[name].copy()) for name in model.state_dict()}
    model.load_state_dict(state)
    return model
