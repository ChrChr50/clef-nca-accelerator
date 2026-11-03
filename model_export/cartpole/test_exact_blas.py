"""Compare accelerated integer arithmetic with independent int64/scalar paths."""
import unittest
import numpy as np
from model_export.cartpole.exact_blas import ExactBlasFixedNCA
from model_export.cartpole.fixed_point import FixedNCA, Format
from model_export.cartpole.row16_candidate import EXPECTED
from model_export.cartpole.test_fixed_point import fixture
from reference.original_nca.core import NCAWeights


class ExactBlasTests(unittest.TestCase):
    def test_extreme_signed_grids_all_layers_trace_and_counters(self):
        rng = np.random.RandomState(496)
        for fmt in (EXPECTED,Format("fidelity32",32,24,24,22,62)):
            ordinary = FixedNCA(fixture(),fmt)
            fast = ExactBlasFixedNCA(fixture(),fmt)
            lo,hi = -(1 << (fmt.state_bits-1)),(1 << (fmt.state_bits-1))-1
            for grid in (np.full((1,32,32,6),lo,np.int64),np.full((1,32,32,6),hi,np.int64),
                         rng.randint(lo,hi+1,(1,32,32,6),dtype=np.int64)):
                _,a = ordinary.delta(grid,trace=True)
                _,b = fast.delta(grid,trace=True)
                for name in a:
                    np.testing.assert_array_equal(a[name],b[name])
            self.assertEqual(ordinary.counters,fast.counters)

    def test_split_path_with_maximum_safe_synthetic_kernel_and_cancellation(self):
        fmt = Format("split_extreme",32,24,24,22,62)
        tensors = []
        rng = np.random.RandomState(494)
        for shape in ((3,3,6,20),(20,),(1,1,20,30),(30,),(1,1,30,6),(6,)):
            tensors.append(rng.choice([-1.999999,1.999999],size=shape).astype(np.float32))
        weights = NCAWeights(*tensors)
        ordinary,fast = FixedNCA(weights,fmt),ExactBlasFixedNCA(weights,fmt)
        self.assertFalse(all(fast.direct))
        grid = rng.randint(-(1<<31),1<<31,(1,32,32,6),dtype=np.int64)
        _,a = ordinary.delta(grid,trace=True)
        _,b = fast.delta(grid,trace=True)
        for name in a:
            np.testing.assert_array_equal(a[name],b[name])
        self.assertEqual(ordinary.counters,fast.counters)

    def test_persistent_epochs_include_masks_postwrites_and_saturation(self):
        rng = np.random.RandomState(495)
        for fmt in (EXPECTED,Format("fidelity32",32,24,24,22,62)):
            a,b = FixedNCA(fixture(),fmt),ExactBlasFixedNCA(fixture(),fmt)
            old = rng.uniform(-.1,.1,(1,32,32,6)).astype(np.float32)
            ga,gb = a.initial_grid(old),b.initial_grid(old)
            for _ in range(8):
                mask = rng.random_sample((1,32,32,1))<=.5
                obs = rng.uniform(-1,1,(1,4)).astype(np.float32)
                ga,gb = a.step(ga,obs,mask),b.step(gb,obs,mask)
                np.testing.assert_array_equal(ga,gb)
            self.assertEqual(a.counters,b.counters)


if __name__ == "__main__":
    unittest.main()
