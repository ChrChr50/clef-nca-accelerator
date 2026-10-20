from __future__ import annotations

import unittest
import numpy as np

from reference.original_nca.core import NCAWeights, INPUT_COORDINATES, OUTPUT_COORDINATES
from model_export.cartpole.fixed_point import Format, FixedNCA, ScheduledController, quantize, round_shift, saturate, scalar_cell_delta
from model_export.cartpole.fixed_deployment import FixedControllerPort
from reference.original_nca.cartpole import CartPole
from sw.cartpole.deployment import CartPoleHost


def fixture():
    # Public synthetic fixture; never derived from released model2 tensors.
    rng = np.random.RandomState(709)
    shapes = [(3,3,6,20),(20,),(1,1,20,30),(30,),(1,1,30,6),(6,)]
    return NCAWeights(*(rng.uniform(-.08,.08,shape).astype(np.float32) for shape in shapes))


class IntegerGoldenTests(unittest.TestCase):
    def setUp(self):
        self.fmt = Format("synthetic",18,12,16,14,40)
        self.model = FixedNCA(fixture(),self.fmt)

    def test_nearest_even_positive_negative_ties_and_extremes(self):
        values = np.arange(-63,64,dtype=np.int64)
        for shift in (0,1,2,4):
            expected = np.asarray([round(int(x)/(1 << shift)) for x in values],np.int64)
            np.testing.assert_array_equal(round_shift(values,shift),expected)
        extrema = np.asarray([-(1<<61),(1<<61)-1],np.int64)
        for shift in (1,22):
            expected = []
            for value in extrema:
                q,r = divmod(int(value),1<<shift)
                expected.append(q+int(2*r>(1<<shift) or (2*r==(1<<shift) and q%2)))
            np.testing.assert_array_equal(round_shift(extrema,shift),expected)

    def test_saturation_and_finite_boundary(self):
        clipped,count = saturate(np.asarray([-129,-128,127,128]),8)
        np.testing.assert_array_equal(clipped,[-128,-128,127,127])
        self.assertEqual(count,2)
        for value in (np.nan,np.inf,-np.inf):
            with self.assertRaises(ValueError):
                quantize([value],18,12)
        value,_ = quantize([-.625,-.375,.375,.625],8,2)
        np.testing.assert_array_equal(value,[-2,-2,2,2])

    def test_full_signed_range_bound_contains_extreme_layer_inputs(self):
        for sign in (-1,1):
            value = -(1<<17) if sign<0 else (1<<17)-1
            grid = np.full((1,32,32,6),value,dtype=np.int64)
            _,trace = self.model.delta(grid,True)
            for layer,bound in enumerate(self.model.bounds):
                self.assertLessEqual(int(np.max(np.abs(trace[f"layer{layer}_accumulator"]))),
                                     bound["max_abs_accumulator_integer_bound"])
        self.assertTrue(all(self.model.counters.get(f"accumulator{i}",0)==0 for i in range(3)))

    def test_vector_integer_mac_matches_independent_scalar_cells(self):
        grid = np.random.RandomState(71).randint(-8192,8192,(1,32,32,6)).astype(np.int64)
        delta = self.model.delta(grid)
        for row,col in ((0,0),(0,31),(31,0),(31,31),(1,15),(16,16)):
            np.testing.assert_array_equal(delta[0,row,col],scalar_cell_delta(self.model,grid,row,col))

    def test_zero_mask_still_clears_clamps_and_accumulates_markers(self):
        grid = np.full((1,32,32,6),7,dtype=np.int64)
        obs = np.asarray([[.5,2.,-.25,4.]],np.float32)
        updated = self.model.step(grid,obs,np.zeros((1,32,32,1),bool))
        self.assertEqual(int(updated[0,0,0,0]),7)
        self.assertEqual(int(updated[0,0,0,2]),0)
        one = 1<<12
        for index,(row,col) in enumerate(INPUT_COORDINATES):
            self.assertEqual(int(updated[0,row,col,0]),int(self.model.observations(obs)[0,index]))
            np.testing.assert_array_equal(updated[0,row,col,1:],[one,one,0,one,one])
        for row,col in OUTPUT_COORDINATES:
            np.testing.assert_array_equal(updated[0,row,col,3:],[one,one+7,one+7])

    def test_marker_overflow_counts_and_saturates(self):
        grid = np.zeros((1,32,32,6),np.int64)
        for row,col in OUTPUT_COORDINATES:
            grid[:,row,col,4:] = (1<<17)-1
        out = self.model.step(grid,np.zeros((1,4),np.float32),np.zeros((1,32,32,1),bool))
        self.assertEqual(self.model.counters["output_marker"],4)
        for row,col in OUTPUT_COORDINATES:
            np.testing.assert_array_equal(out[0,row,col,4:],[(1<<17)-1]*2)

    def test_service_order_cannot_change_old_grid_epoch(self):
        grid = self.model.initial_grid(np.random.RandomState(72).uniform(-.1,.1,(1,32,32,6)))
        mask = np.random.RandomState(73).random_sample((1,32,32,1))<=.5
        obs = np.asarray([[.01,.02,.03,.04]],np.float32)
        expected = self.model.step(grid,obs,mask)
        for order in (np.arange(1024)[::-1],np.random.RandomState(74).permutation(1024)):
            np.testing.assert_array_equal(expected,self.model.step(grid,obs,mask,cell_order=order))
        with self.assertRaises(ValueError):
            self.model.step(grid,obs,mask,cell_order=np.zeros(1024,int))

    def test_persistent_schedule_tie_and_reset_boundary(self):
        grid = np.zeros((1,32,32,6),np.float32)
        # Compact18's marker-only state saturates by epoch 32. Use a range
        # that contains both 50-epoch decisions to test persistence separately.
        model = FixedNCA(fixture(),Format("persistence",24,16,18,16,48))
        controller = ScheduledController(model,grid)
        masks = np.zeros((50,1,32,32,1),bool)
        action,_ = controller.decide(np.zeros(4,np.float32),masks)
        self.assertEqual(action,0)
        self.assertEqual(controller.epochs,50)
        first = controller.grid.copy()
        controller.decide(np.zeros(4,np.float32),masks)
        self.assertEqual(controller.epochs,100)
        self.assertFalse(np.array_equal(first,controller.grid))
        fresh = ScheduledController(model,grid)
        self.assertEqual(fresh.epochs,0)
        with self.assertRaises(ValueError):
            fresh.decide(np.zeros(4,np.float32),masks[:49])

    def test_input_scaling_once_and_signed_configuration_checks(self):
        obs = np.asarray([[1.,4.,.25,1.]],np.float32)
        expected = np.repeat(np.rint((obs*np.asarray([2.,.25,4.,.15],np.float32))*(1<<12)).astype(np.int64),2,axis=1)
        np.testing.assert_array_equal(self.model.observations(obs),expected)
        with self.assertRaises(ValueError):
            Format("bad",33,12,16,14,40)
        with self.assertRaises(ValueError):
            FixedNCA(fixture(),Format("bad-accumulator",18,12,16,14,20))

    def test_fixed_controller_uses_existing_host_plant_and_rejects_noise(self):
        initial = np.asarray([.01,.02,.03,.04],np.float64)
        controller = FixedControllerPort(self.model,np.zeros((1,32,32,6),np.float32))
        plant = CartPole(initial.copy())
        trace = CartPoleHost(plant,controller).step(np.zeros((50,1,32,32,1),bool))
        direct = CartPole(initial.copy())
        expected,_,_ = direct.step(trace.action)
        np.testing.assert_array_equal(plant.state,expected)
        self.assertEqual(controller.epochs,50)
        self.assertEqual(len(trace.controller_after_sha256),64)
        with self.assertRaises(ValueError):
            controller.decide(np.zeros(4,np.float32),np.zeros((50,1,32,32,1),bool),
                              np.zeros((50,1,32,32,6),np.float32))


if __name__ == "__main__":
    unittest.main()
