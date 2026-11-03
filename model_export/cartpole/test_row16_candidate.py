"""Public synthetic tests of the unaccepted row16 contract; no learned weights."""
from pathlib import Path
import tempfile
import unittest
import numpy as np

from model_export.cartpole.accepted_arithmetic import accepted_format
from model_export.cartpole.fixed_point import FixedNCA, scalar_cell_delta
from model_export.cartpole.row16_candidate import (EXPECTED, candidate_format, output_major_images,
                                                  recover_input_major, write_local_images)
from model_export.cartpole.test_fixed_point import fixture
from model_export.cartpole.freeze import ROOT
from reference.original_nca.core import NCAWeights, INPUT_COORDINATES, OUTPUT_COORDINATES


def routed_fixture():
    shapes = [(3,3,6,20),(20,),(1,1,20,30),(30,),(1,1,30,6),(6,)]
    arrays = [np.zeros(shape, np.float32) for shape in shapes]
    arrays[0][1,0,0,0] = 1
    arrays[2][0,0,0,0] = 1
    arrays[4][0,0,0,0] = 1
    return NCAWeights(*arrays)


class Row16CandidateTests(unittest.TestCase):
    def test_versioned_candidate_does_not_replace_accepted_arithmetic(self):
        self.assertEqual(candidate_format(), EXPECTED)
        self.assertEqual(accepted_format().name, "fidelity32")
        self.assertEqual(candidate_format().manifest()["bias_fraction"], 22)

    def test_analytical_bounds_and_scalar_operator_corners_and_interior(self):
        model = FixedNCA(fixture(), EXPECTED)
        rng = np.random.RandomState(813)
        grid = rng.randint(-32768,32768,(1,32,32,6)).astype(np.int64)
        result, trace = model.delta(grid, trace=True)
        for row,col in ((0,0),(0,31),(31,0),(31,31),(1,1),(16,16),(11,26),(13,16),(17,16)):
            np.testing.assert_array_equal(result[0,row,col], scalar_cell_delta(model,grid,row,col))
        for index,bound in enumerate(model.bounds):
            self.assertLessEqual(bound["required_signed_bits"], 48)
            self.assertLessEqual(int(np.max(np.abs(trace[f"layer{index}_accumulator"]))),
                                 bound["max_abs_accumulator_integer_bound"])

    def test_current_observation_is_injected_after_first_neighborhood_evaluation(self):
        model = FixedNCA(routed_fixture(), EXPECTED)
        grid = np.zeros((1,32,32,6),np.int64)
        obs = np.asarray([[.5,0,0,0]],np.float32)
        mask = np.ones((1,32,32,1),bool)
        row,col = INPUT_COORDINATES[0]
        first = model.step(grid,obs,mask)
        self.assertEqual(int(first[0,row,col,0]),1024)
        self.assertEqual(int(first[0,row,col+1,0]),0)
        second = model.step(first,obs,mask)
        self.assertEqual(int(second[0,row,col+1,0]),1024)

    def test_zero_mask_postwrites_output_accumulation_and_guard_saturation(self):
        model = FixedNCA(routed_fixture(), EXPECTED)
        grid = np.full((1,32,32,6),19,np.int64)
        obs = np.zeros((1,4),np.float32)
        mask = np.zeros((1,32,32,1),bool)
        first = model.step(grid,obs,mask)
        second = model.step(first,obs,mask)
        self.assertEqual(int(second[0,0,0,0]),19)
        np.testing.assert_array_equal(second[0,0,0,2:4],[0,0])
        for row,col in INPUT_COORDINATES:
            np.testing.assert_array_equal(second[0,row,col],[0,1024,1024,0,1024,1024])
        for row,col in OUTPUT_COORDINATES:
            np.testing.assert_array_equal(second[0,row,col,3:],[1024,2067,2067])
            grid[0,row,col,4:] = 32767
        saturated = model.step(grid,obs,mask)
        for row,col in OUTPUT_COORDINATES:
            np.testing.assert_array_equal(saturated[0,row,col,4:],[32767,32767])
        self.assertEqual(model.counters["output_marker"],4)

    def test_equal_scores_choose_lowest_index(self):
        model = FixedNCA(routed_fixture(), EXPECTED)
        grid = np.zeros((1,32,32,6),np.int64)
        self.assertEqual(int(np.argmax(model.readout(grid)[0])),0)

    def test_output_major_layout_roundtrip_and_declared_address_order(self):
        model = FixedNCA(fixture(), EXPECTED)
        images,biases = output_major_images(model)
        recovered = recover_input_major(images,[k.shape for k in model.kernels])
        for index,(a,b) in enumerate(zip(recovered,model.kernels,strict=True)):
            np.testing.assert_array_equal(a,b)
            np.testing.assert_array_equal(biases[index],model.biases[index])
        for dr,dc,ch,f in ((0,0,0,0),(2,2,5,19),(1,0,4,3)):
            self.assertEqual(int(images[0][f,(dr*3+dc)*6+ch]),int(model.kernels[0][dr,dc,ch,f]))
        with self.assertRaises(ValueError):
            recover_input_major(images[:2],[k.shape for k in model.kernels])

    def test_hex_width_sign_roundtrip_and_local_only_export_guard(self):
        model = FixedNCA(fixture(), EXPECTED)
        with self.assertRaises(ValueError):
            write_local_images(ROOT / "rtl/unsafe_candidate_images",model)
        parent = ROOT / "artifacts/row16_validation/tests"
        parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as directory:
            manifest = write_local_images(Path(directory),model)
            self.assertEqual(sum(item["words"] for item in manifest["files"]),1916)
            images,biases = output_major_images(model)
            for item in manifest["files"]:
                width = item["bits"]
                lines = (ROOT / item["path"]).read_text().splitlines()
                self.assertTrue(all(len(line)==(width+3)//4 for line in lines))
                decoded = np.asarray([int(s,16)-(1<<width) if int(s,16)&(1<<(width-1)) else int(s,16) for s in lines],np.int64)
                expected = images[item["layer"]] if item["kind"]=="kernel" else biases[item["layer"]]
                np.testing.assert_array_equal(decoded,expected.ravel())


if __name__ == "__main__":
    unittest.main()
