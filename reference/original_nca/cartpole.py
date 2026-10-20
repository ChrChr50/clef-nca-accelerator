"""Clean-room executable form of the upstream modified CartPole dynamics."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass
class CartPole:
    state: NDArray[np.float64]
    step_count: int = 0
    max_steps: int = 10_000

    gravity: float = 9.8
    masscart: float = 1.0
    masspole: float = 0.1
    length: float = 0.5
    force_mag: float = 10.0
    tau: float = 0.02
    x_threshold: float = 2.4
    theta_threshold: float = 12.0 * 2.0 * math.pi / 360.0

    @classmethod
    def reset(cls, rng: np.random.RandomState) -> "CartPole":
        return cls(rng.uniform(-0.05, 0.05, size=4).astype(np.float64))

    def step(self, action: int) -> tuple[NDArray[np.float64], float, bool]:
        if action not in (0, 1):
            raise ValueError("action must be 0 or 1")
        self.step_count += 1
        x, x_dot, theta, theta_dot = (float(value) for value in self.state)
        total_mass = self.masspole + self.masscart
        polemass_length = self.masspole * self.length
        force = self.force_mag if action == 1 else -self.force_mag
        costheta, sintheta = math.cos(theta), math.sin(theta)
        temp = (force + polemass_length * theta_dot**2 * sintheta) / total_mass
        theta_acc = (self.gravity * sintheta - costheta * temp) / (
            self.length * (4.0 / 3.0 - self.masspole * costheta**2 / total_mass)
        )
        x_acc = temp - polemass_length * theta_acc * costheta / total_mass
        x += self.tau * x_dot
        x_dot += self.tau * x_acc
        theta += self.tau * theta_dot
        theta_dot += self.tau * theta_acc
        self.state = np.asarray([x, x_dot, theta, theta_dot], dtype=np.float64)
        done = bool(
            abs(x) > self.x_threshold
            or abs(theta) > self.theta_threshold
            or self.step_count > self.max_steps
        )
        # This is the executable environment's final assignment. The DQN wrapper
        # separately substitutes -100 for terminal transitions during training.
        reward = float(np.cos((x / self.x_threshold) * (np.pi / 2.0)) ** 2)
        return self.state.copy(), reward, done

