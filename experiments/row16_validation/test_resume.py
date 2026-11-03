"""Real-operator interruption/resume comparison with public synthetic weights."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np

from experiments.row16_validation import evaluate
from reference.original_nca.core import NCAWeights
from reference.original_nca.cartpole import CartPole


class ResumeTests(unittest.TestCase):
    def test_resume_restores_rng_grids_plants_counts_and_refuses_wrong_identity(self):
        shapes = [(3,3,6,20),(20,),(1,1,20,30),(30,),(1,1,30,6),(6,)]
        weights = NCAWeights(*(np.zeros(shape,np.float32) for shape in shapes))
        case = {"role":"public resume test","seed":3,"max_actions":17}
        authority = {"phase":"test","identity":"public-synthetic"}
        # A constant-action synthetic network falls before action 16 in the real
        # qualification plant. Widen limits only in this harness unit fixture so
        # it reaches the actual periodic checkpoint; no experiment uses this.
        class HarnessPlant(CartPole):
            def __init__(self,state):
                super().__init__(state,x_threshold=1e9,theta_threshold=1e9)
        parent = evaluate.ROOT / "artifacts/row16_validation/tests"
        parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as directory:
            folder = Path(directory)
            with patch.object(evaluate,"PRIVATE",folder / "whole"), patch.object(evaluate,"CartPole",HarnessPlant):
                whole = evaluate.episode(case,authority,weights)
            original_save = evaluate.save

            class PausedAtLogicalBoundary(Exception):
                pass

            def save_then_pause(path,arrays,meta):
                original_save(path,arrays,meta)
                if meta["logical_action"]==16:
                    raise PausedAtLogicalBoundary()

            with patch.object(evaluate,"PRIVATE",folder / "resumed"), patch.object(evaluate,"CartPole",HarnessPlant):
                with patch.object(evaluate,"save",side_effect=save_then_pause):
                    with self.assertRaises(PausedAtLogicalBoundary):
                        evaluate.episode(case,authority,weights)
                resumed = evaluate.episode(case,authority,weights)
                with self.assertRaises(ValueError):
                    evaluate.episode(case,{**authority,"identity":"tampered"},weights)
            for arm in whole["arms"]:
                expected = {k:v for k,v in whole["arms"][arm].items() if k!="seconds"}
                actual = {k:v for k,v in resumed["arms"][arm].items() if k!="seconds"}
                self.assertEqual(actual,expected)
            self.assertEqual(whole["epochs"],resumed["epochs"])


if __name__=="__main__":
    unittest.main()
