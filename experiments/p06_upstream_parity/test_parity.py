"""Local-only replay-injection and direct-source contract checks."""
import json
from pathlib import Path
import subprocess
import unittest

import numpy as np

from reference.original_nca.core import CanonicalNCA, load_tfjs_weights, make_io_contract, seeded_initial_grid
from experiments.p06_upstream_parity.run import compare_arrays

ROOT = Path(__file__).resolve().parents[2]


class DirectSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.worker = subprocess.Popen([
            str(ROOT / ".venv-p06-parity/Scripts/python.exe"), "-u",
            str(Path(__file__).with_name("upstream_worker.py"))],cwd=ROOT,
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
            text=True,encoding="utf-8")
        cls.ready = json.loads(cls.worker.stdout.readline())
        base = ROOT / "self-organized-control/demo/models/model2"
        cls.nca = CanonicalNCA(load_tfjs_weights(base / "model.json",base / "group1-shard1of1.bin"))
        cls.grid = seeded_initial_grid(12 ^ 0x5A17)
        cls.obs = np.asarray([.01,-.02,.03,-.04],np.float32)

    @classmethod
    def tearDownClass(cls):
        cls.worker.stdin.write(json.dumps({"op":"quit"})+"\n")
        cls.worker.stdin.flush()
        cls.worker.wait(timeout=30)
        cls.worker.stdin.close()
        cls.worker.stdout.close()

    @classmethod
    def request(cls, command):
        cls.worker.stdin.write(json.dumps(command)+"\n")
        cls.worker.stdin.flush()
        return json.loads(cls.worker.stdout.readline())

    def probe(self,masks):
        command = {"op":"probe","epochs":len(masks),
                   "masks":np.packbits(masks.reshape(-1),bitorder="little").tobytes().hex(),
                   "grid":self.grid.astype("<f4").tobytes().hex(),"observation":self.obs.tolist()}
        reply = self.request(command)
        return np.frombuffer(bytes.fromhex(reply["grid"]),dtype="<f4").reshape(self.grid.shape)

    def test_source_io_templates_match_bitwise(self):
        reply = self.request({"op":"init","grid":self.grid.astype("<f4").tobytes().hex(),"plant":[0,0,0,0]})
        cut,pos = make_io_contract(1)
        self.assertEqual(reply["cut"],cut.astype("<f4").tobytes().hex())
        self.assertEqual(reply["markers"],pos.astype("<f4").tobytes().hex())

    def test_zero_masks_preserve_source_clamps_and_markers_exactly(self):
        masks = np.zeros((3,1,32,32,1),dtype=bool)
        local = self.grid.copy()
        for mask in masks:
            local = self.nca.step(local,self.obs[None,:],mask)
        np.testing.assert_array_equal(self.probe(masks),local)

    def test_all_update_mask_matches_and_replay_is_deterministic(self):
        masks = np.ones((1,1,32,32,1),dtype=bool)
        local = self.nca.step(self.grid,self.obs[None,:],masks[0])
        source = self.probe(masks)
        self.assertEqual(compare_arrays(local,source)["elements_outside_p03_tolerance"],0)
        np.testing.assert_array_equal(source,self.probe(masks))

    def test_59_step_explicit_mask_recurrence(self):
        masks = np.random.RandomState(123).random_sample((59,1,32,32,1))<=.5
        local = self.grid.copy()
        for mask in masks:
            local = self.nca.step(local,self.obs[None,:],mask)
        self.assertEqual(compare_arrays(local,self.probe(masks))["elements_outside_p03_tolerance"],0)


if __name__ == "__main__":
    unittest.main()
