"""P06's pre-registered, resumable source-default CartPole qualification.

This module composes the immutable P03 plant/operator with E01's host seam.
It contains no policy, training target, plant equation, or restricted weights.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from reference.original_nca.cartpole import CartPole
from reference.original_nca.core import CanonicalNCA, seeded_initial_grid
from sw.cartpole.deployment import CartPoleHost, ReferenceController


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "sw/cartpole/qualification.v1.json"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_config(path: Path = CONFIG_PATH) -> tuple[dict, str]:
    raw = path.read_bytes()
    config = json.loads(raw)
    if config["schema_version"] != 1 or config["authority"]["model"] != "model2":
        raise ValueError("not the accepted P06 model2 qualification")
    if config["seeds"] != list(range(10, 20)):
        raise ValueError("held-out seed set changed")
    if config["success_threshold"] != {
        "minimum_horizon_completions": 8,
        "required_completed_episodes": 10,
        "required_checkpoint_golden_pass": True,
    }:
        raise ValueError("accepted threshold changed")
    episode = config["episode"]
    if (episode["plant_max_steps_field"] != 10_000
            or episode["horizon_action_count"] != 10_001
            or episode["in_episode_reinitialization_probability"] != 0.0
            or any(episode[key] for key in ("noise", "damage", "input_deletion"))):
        raise ValueError("accepted source-default protocol changed")
    return config, sha256_bytes(raw)


def draws_for_action(rng: np.random.RandomState) -> tuple[int, np.ndarray]:
    """Sequential logical RNG assignment, independent of service stalls."""

    epochs = int(rng.randint(50, 60))
    masks = rng.random_sample((epochs, 1, 32, 32, 1)) <= 0.5
    return epochs, masks


def termination_reason(plant: CartPole, terminal: bool) -> str | None:
    if not terminal:
        return None
    x, _, theta, _ = plant.state
    if abs(float(x)) > plant.x_threshold:
        return "cart_position_limit"
    if abs(float(theta)) > plant.theta_threshold:
        return "pole_angle_limit"
    if plant.step_count > plant.max_steps:
        return "source_horizon"
    raise AssertionError("terminal plant has no source termination reason")


@dataclass(frozen=True)
class EpisodeResult:
    seed: int
    actions: int
    score: float
    termination_reason: str
    horizon_completed: bool
    actions_sha256: str
    ordered_mask_hashes_sha256: str
    initial_plant_sha256: str
    initial_grid_sha256: str
    final_plant_sha256: str
    final_grid_sha256: str
    config_sha256: str
    tfjs_weight_blob_sha256: str
    python: str
    numpy: str


def _save_progress(
    path: Path, *, seed: int, config_sha256: str, plant: CartPole,
    grid: np.ndarray, rng: np.random.RandomState, score: float,
    actions: bytearray, mask_hashes: bytearray, initial_plant_sha256: str,
    initial_grid_sha256: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state = rng.get_state()
    temporary = path.with_name(path.name + ".tmp.npz")
    np.savez_compressed(
        temporary, seed=seed, config_sha256=config_sha256,
        plant_state=plant.state, step_count=plant.step_count, grid=grid,
        rng_keys=state[1], rng_pos=state[2], rng_gauss_flag=state[3],
        rng_gauss=state[4], score=score,
        actions=np.frombuffer(actions, dtype=np.uint8),
        mask_hashes=np.frombuffer(mask_hashes, dtype=np.uint8),
        initial_plant_sha256=initial_plant_sha256,
        initial_grid_sha256=initial_grid_sha256,
    )
    os.replace(temporary, path)


def run_episode(
    nca: CanonicalNCA, seed: int, config_sha256: str,
    weight_sha256: str, progress: Path, *, checkpoint_interval: int = 500,
    action_limit: int | None = None,
) -> EpisodeResult | None:
    """Return a completed episode, or None after a test/interruption limit."""

    if seed not in range(10, 20):
        raise ValueError("seed not in accepted qualification set")
    if checkpoint_interval < 1:
        raise ValueError("checkpoint_interval must be positive")
    rng = np.random.RandomState(seed)
    plant = CartPole.reset(rng)
    grid = seeded_initial_grid(seed ^ 0x5A17)
    initial_plant_sha256 = sha256_bytes(plant.state.astype("<f8").tobytes())
    initial_grid_sha256 = sha256_bytes(grid.astype("<f4").tobytes())
    score = 0.0
    actions = bytearray()
    mask_hashes = bytearray()
    if progress.is_file():
        with np.load(progress, allow_pickle=False) as saved:
            if int(saved["seed"]) != seed or str(saved["config_sha256"]) != config_sha256:
                raise ValueError("progress has a different seed or protocol")
            plant.state = saved["plant_state"].astype(np.float64)
            plant.step_count = int(saved["step_count"])
            grid = saved["grid"].astype(np.float32)
            rng.set_state(("MT19937", saved["rng_keys"], int(saved["rng_pos"]),
                           int(saved["rng_gauss_flag"]), float(saved["rng_gauss"])))
            score = float(saved["score"])
            actions = bytearray(saved["actions"].tobytes())
            mask_hashes = bytearray(saved["mask_hashes"].tobytes())
            initial_plant_sha256 = str(saved["initial_plant_sha256"])
            initial_grid_sha256 = str(saved["initial_grid_sha256"])
            if len(actions) != plant.step_count or len(mask_hashes) != 32 * plant.step_count:
                raise ValueError("progress trace length mismatch")
    controller = ReferenceController(nca, grid)
    host = CartPoleHost(plant, controller)
    if action_limit is not None and action_limit < plant.step_count:
        raise ValueError("action limit precedes resumed state")
    while not host.terminal:
        if action_limit is not None and plant.step_count >= action_limit:
            return None
        _, masks = draws_for_action(rng)
        trace = host.step(masks)
        score += trace.reward
        actions.append(trace.action)
        mask_hashes.extend(bytes.fromhex(trace.masks_sha256))
        if plant.step_count % checkpoint_interval == 0 and not host.terminal:
            _save_progress(
                progress, seed=seed, config_sha256=config_sha256, plant=plant,
                grid=controller.grid, rng=rng, score=score, actions=actions,
                mask_hashes=mask_hashes, initial_plant_sha256=initial_plant_sha256,
                initial_grid_sha256=initial_grid_sha256,
            )
            print(f"seed {seed}: {plant.step_count} actions", flush=True)
    reason = termination_reason(plant, host.terminal)
    assert reason is not None
    result = EpisodeResult(
        seed=seed, actions=plant.step_count, score=score,
        termination_reason=reason, horizon_completed=reason == "source_horizon",
        actions_sha256=sha256_bytes(actions),
        ordered_mask_hashes_sha256=sha256_bytes(mask_hashes),
        initial_plant_sha256=initial_plant_sha256,
        initial_grid_sha256=initial_grid_sha256,
        final_plant_sha256=sha256_bytes(plant.state.astype("<f8").tobytes()),
        final_grid_sha256=sha256_bytes(controller.grid.astype("<f4").tobytes()),
        config_sha256=config_sha256, tfjs_weight_blob_sha256=weight_sha256,
        python=platform.python_version(), numpy=np.__version__,
    )
    progress.unlink(missing_ok=True)
    return result
