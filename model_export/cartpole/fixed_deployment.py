"""Candidate integer controller behind the unchanged E01 simulated-host seam."""
import hashlib
import numpy as np

from model_export.cartpole.fixed_point import ScheduledController
from sw.cartpole.deployment import ControllerDecision


class FixedControllerPort(ScheduledController):
    def decide(self,observation,masks,noise=None):
        if noise is not None:
            raise ValueError("primary frozen protocol has no update noise")
        action,integers = super().decide(observation,masks)
        # Telemetry conversion occurs after integer action selection. It cannot
        # alter argmax/tie behavior. A physical transport/packing choice is G5.
        scores = integers.astype(np.float64)/(1 << self.model.fmt.state_fraction)
        return ControllerDecision(action,(float(scores[0]),float(scores[1])),
            hashlib.sha256(np.asarray(self.grid,dtype="<i8").tobytes()).hexdigest())
