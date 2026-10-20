"""Executable contract for the published CartPole NCA.

The API makes all stochastic inputs explicit. A caller supplies update masks
and optional noise arrays, which permits exact replay independently of RNG
implementation details.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from numpy.typing import NDArray


FloatArray = NDArray[np.float32]
BoolArray = NDArray[np.bool_]

GRID_SIZE = 32
CHANNELS = 6
FIRE_RATE = 0.5
INPUT_SCALE = np.asarray([2.0, 0.25, 4.0, 0.15], dtype=np.float32)
OUTPUT_SCALE = np.float32(0.01)
INPUT_COORDINATES = (
    (11, 26),
    (25, 20),
    (5, 20),
    (19, 6),
    (19, 26),
    (5, 12),
    (25, 12),
    (11, 6),
)
OUTPUT_COORDINATES = ((13, 16), (17, 16))


@dataclass(frozen=True)
class NCAWeights:
    """The six tensors in authoritative Keras/TensorFlow.js manifest order."""

    conv0_kernel: FloatArray
    conv0_bias: FloatArray
    conv1_kernel: FloatArray
    conv1_bias: FloatArray
    conv2_kernel: FloatArray
    conv2_bias: FloatArray

    @property
    def parameter_count(self) -> int:
        return sum(int(value.size) for value in self.__dict__.values())


def _as_float32(value: NDArray[np.generic]) -> FloatArray:
    return np.asarray(value, dtype=np.float32)


def load_tfjs_weights(model_json: Path, binary: Path) -> NCAWeights:
    """Load a shipped TFJS checkpoint without TensorFlow or copied source."""

    manifest = json.loads(model_json.read_text(encoding="utf-8"))["weightsManifest"]
    specs = [spec for group in manifest for spec in group["weights"]]
    raw = np.fromfile(binary, dtype="<f4")
    tensors: list[FloatArray] = []
    offset = 0
    for spec in specs:
        shape = tuple(int(x) for x in spec["shape"])
        count = int(np.prod(shape))
        tensors.append(_as_float32(raw[offset : offset + count].reshape(shape)))
        offset += count
    if offset != raw.size or len(tensors) != 6:
        raise ValueError(f"unexpected TFJS checkpoint layout: {len(tensors)} tensors, {raw.size} values")
    weights = NCAWeights(*tensors)
    if weights.parameter_count != 1916:
        raise ValueError(f"expected 1916 parameters, found {weights.parameter_count}")
    return weights


def conv2d_same(x: FloatArray, kernel: FloatArray, bias: FloatArray) -> FloatArray:
    """NHWC, stride-one, zero-padded TensorFlow-style cross-correlation."""

    if x.ndim != 4 or kernel.ndim != 4:
        raise ValueError("x and kernel must be rank four")
    batch, height, width, in_channels = x.shape
    kh, kw, kernel_channels, out_channels = kernel.shape
    if kernel_channels != in_channels or kh % 2 == 0 or kw % 2 == 0:
        raise ValueError("incompatible or even-sized kernel")
    padded = np.pad(x, ((0, 0), (kh // 2, kh // 2), (kw // 2, kw // 2), (0, 0)))
    windows = np.lib.stride_tricks.sliding_window_view(padded, (kh, kw), axis=(1, 2))
    out = np.einsum("bhwcij,ijco->bhwo", windows, kernel, optimize=True)
    return _as_float32(out + bias)


def conv1x1(x: FloatArray, kernel: FloatArray, bias: FloatArray) -> FloatArray:
    matrix = kernel.reshape(kernel.shape[2], kernel.shape[3])
    return _as_float32(np.tensordot(x, matrix, axes=([3], [0])) + bias)


def relu(x: FloatArray) -> FloatArray:
    return _as_float32(np.maximum(x, np.float32(0.0)))


def make_io_contract(
    batch: int,
    active_inputs: Iterable[bool] | None = None,
) -> tuple[FloatArray, FloatArray]:
    """Build upstream `cut_io_mask` and `pos_io_channel` arrays."""

    active = tuple(active_inputs) if active_inputs is not None else (True,) * 8
    if len(active) != 8:
        raise ValueError("active_inputs must contain eight booleans")
    cut = np.ones((batch, GRID_SIZE, GRID_SIZE, CHANNELS), dtype=np.float32)
    cut[..., 2:4] = np.float32(0.0)
    pos = np.zeros_like(cut)
    for enabled, (row, col) in zip(active, INPUT_COORDINATES, strict=True):
        if not enabled:
            continue
        cut[:, row, col, :] = np.float32(0.0)
        pos[:, row, col, 1] = np.float32(1.0)
        pos[:, row, col, 2] = np.float32(1.0)
        pos[:, row, col, 4:] = np.float32(1.0)
    for row, col in OUTPUT_COORDINATES:
        pos[:, row, col, 3] = np.float32(1.0)
        pos[:, row, col, 4:] = np.float32(1.0)
    return cut, pos


class CanonicalNCA:
    """Raw upstream inference semantics with explicit stochastic inputs."""

    def __init__(self, weights: NCAWeights):
        if weights.parameter_count != 1916:
            raise ValueError("canonical graph requires 1916 parameters")
        self.weights = weights

    def local_delta(self, grid: FloatArray) -> FloatArray:
        """Apply learned 3x3 perception and two pointwise layers."""

        w = self.weights
        x = relu(conv2d_same(_as_float32(grid), w.conv0_kernel, w.conv0_bias))
        x = relu(conv1x1(x, w.conv1_kernel, w.conv1_bias))
        return conv1x1(x, w.conv2_kernel, w.conv2_bias)

    def step(
        self,
        grid: FloatArray,
        observations: FloatArray,
        update_mask: BoolArray,
        *,
        update_noise: FloatArray | None = None,
        active_inputs: Iterable[bool] | None = None,
    ) -> FloatArray:
        """Execute one full upstream NCA call, including post-update I/O writes."""

        state = _as_float32(grid).copy()
        if state.shape[1:] != (GRID_SIZE, GRID_SIZE, CHANNELS):
            raise ValueError(f"expected [B,32,32,6], found {state.shape}")
        batch = state.shape[0]
        mask = np.asarray(update_mask, dtype=np.bool_)
        if mask.shape == (batch, GRID_SIZE, GRID_SIZE):
            mask = mask[..., None]
        if mask.shape != (batch, GRID_SIZE, GRID_SIZE, 1):
            raise ValueError("update_mask must have shape [B,32,32] or [B,32,32,1]")
        dx = self.local_delta(state)
        if update_noise is not None:
            dx = _as_float32(dx + _as_float32(update_noise))
        state = _as_float32(state + dx * mask.astype(np.float32))
        cut, pos = make_io_contract(batch, active_inputs)
        state = _as_float32(state * cut + pos)

        obs = _as_float32(observations)
        if obs.shape == (batch, 4):
            obs = np.repeat(obs * INPUT_SCALE, 2, axis=1)
        if obs.shape != (batch, 8):
            raise ValueError("observations must have shape [B,4] or pre-expanded [B,8]")
        active = tuple(active_inputs) if active_inputs is not None else (True,) * 8
        for index, (row, col) in enumerate(INPUT_COORDINATES):
            if active[index]:
                state[:, row, col, 0] += obs[:, index]
        return state

    @staticmethod
    def readout(grid: FloatArray) -> FloatArray:
        values = [grid[:, row, col, 0] for row, col in OUTPUT_COORDINATES]
        return _as_float32(np.stack(values, axis=1))

    @staticmethod
    def action(grid: FloatArray) -> NDArray[np.int64]:
        return np.argmax(CanonicalNCA.readout(grid), axis=1)


def seeded_initial_grid(seed: int, batch: int = 1) -> FloatArray:
    """Reproduce upstream NumPy RandomState initialization in [-0.1, 0.1)."""

    rng = np.random.RandomState(seed)
    return _as_float32((rng.random_sample((batch, GRID_SIZE, GRID_SIZE, CHANNELS)) - 0.5) * 0.2)


def seeded_masks(seed: int, steps: int, batch: int = 1) -> BoolArray:
    """Portable replay masks; values <= 0.5 update, matching upstream predicate."""

    rng = np.random.RandomState(seed)
    return np.asarray(
        rng.random_sample((steps, batch, GRID_SIZE, GRID_SIZE, 1)) <= FIRE_RATE,
        dtype=np.bool_,
    )


def damage_with_trace(
    grids: FloatArray,
    centers: FloatArray,
    radii: FloatArray,
    replacements: FloatArray,
) -> FloatArray:
    """Apply the upstream circular damage equation from supplied random draws."""

    batch, height, width, _ = grids.shape
    x = np.linspace(-1.0, 1.0, width, dtype=np.float32)[None, None, :]
    y = np.linspace(-1.0, 1.0, height, dtype=np.float32)[None, :, None]
    cx = centers[0].reshape(batch, 1, 1)
    cy = centers[1].reshape(batch, 1, 1)
    radius = radii.reshape(batch, 1, 1)
    outside = (((x - cx) / radius) ** 2 + ((y - cy) / radius) ** 2) > 1.0
    return _as_float32(np.where(outside[..., None], grids, replacements))
