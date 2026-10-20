"""Conventional learned control using the identical 36-input/six-score contract."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .model import require_torch


def build_control(seed: int = 0):
    torch = require_torch()
    torch.manual_seed(seed)
    return torch.nn.Sequential(
        torch.nn.Linear(36, 128),
        torch.nn.ReLU(),
        torch.nn.Linear(128, 128),
        torch.nn.ReLU(),
        torch.nn.Linear(128, 6),
    )


def save_control(model, path: Path) -> None:
    arrays = {name: tensor.detach().cpu().numpy().astype(np.float32) for name, tensor in model.state_dict().items()}
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **arrays)
