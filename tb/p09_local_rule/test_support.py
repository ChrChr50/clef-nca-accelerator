import unittest
import numpy as np
from tb.p09_local_rule.support import encode,decode,active_cycles,fixtures,words,patch,compute


class LocalRuleTests(unittest.TestCase):
    def test_signed_images(self):
        for width in (24,62):
            v=[-(1<<(width-1)),(1<<(width-1))-1,-1,0,1]
            np.testing.assert_array_equal(decode(encode(v,width),width),v)
            with self.assertRaises(ValueError):encode([1<<(width-1)],width)
            with self.assertRaises(ValueError):decode(f'{1<<width:x}',width)

    def test_synthetic_all_layers_and_order(self):
        model,cases,bindings=fixtures()
        self.assertEqual(len(cases),6);self.assertFalse(bindings)
        k,b=words(model);self.assertEqual((len(k),len(b)),(1860,56))
        for p,delta,trace in cases:
            self.assertEqual([sum(t[0]==i for t in trace) for i in range(3)],[20,30,6])
            self.assertEqual(len(delta),6)
            self.assertEqual(compute(model,p)[0],delta)

    def test_padding_and_reject_short_patch(self):
        grid=np.ones((1,32,32,6),np.int64)
        self.assertEqual(patch(grid,0,0).count(0),30)
        self.assertEqual(patch(grid,0,16).count(0),18)
        model,_,_=fixtures()
        with self.assertRaises(ValueError):compute(model,[0]*53)

    def test_cycle_alternatives_and_tail_groups(self):
        self.assertEqual([active_cycles(n) for n in (1,2,3,4)],[1862,932,640,492])
        with self.assertRaises(ValueError):active_cycles(0)

    def test_delta_boundary_residual_and_postwrites_once(self):
        from reference.original_nca.core import INPUT_COORDINATES,OUTPUT_COORDINATES
        from tb.p08_primitives.run import clipped
        model,_,_=fixtures()
        grid=np.random.RandomState(919).randint(-1000000,1000000,(1,32,32,6),dtype=np.int64)
        obs=np.asarray([[.1,.2,.3,.4]],np.float32)
        for fire in (False,True):
            actual=model.step(grid,obs,np.full((1,32,32,1),fire,bool))
            coords=[(0,0),(16,16),INPUT_COORDINATES[0],OUTPUT_COORDINATES[0]]
            for row,col in coords:
                delta,_=compute(model,patch(grid,row,col))
                cell=[clipped(int(grid[0,row,col,c])+(delta[c] if fire else 0),32)[0] for c in range(6)]
                cell[2:4]=[0,0];one=1<<24
                if (row,col) in INPUT_COORDINATES:
                    idx=INPUT_COORDINATES.index((row,col))
                    cell=[int(model.observations(obs)[0,idx]),one,one,0,one,one]
                if (row,col) in OUTPUT_COORDINATES:
                    cell[3]=one
                    cell[4:]=[clipped(v+one,32)[0] for v in cell[4:]]
                np.testing.assert_array_equal(cell,actual[0,row,col])


if __name__=='__main__':unittest.main()
