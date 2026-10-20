import unittest
import numpy as np
from tb.p08_primitives.run import cases, generate, literal, rounded, SOURCES
from model_export.cartpole.fixed_point import round_shift


class PrimitiveVectors(unittest.TestCase):
    def test_accepted_width_independent_rounding(self):
        values=np.asarray([-(1<<61),(1<<61)-1,*range(-40,41)],np.int64)
        for shift in (0,1,22):
            np.testing.assert_array_equal([rounded(int(v),shift) for v in values],round_shift(values,shift))

    def test_deterministic_public_vectors_and_coverage(self):
        a,meta=generate(); b,again=generate()
        self.assertEqual(a,b);self.assertEqual(meta,again)
        self.assertGreater(meta['round_cases'],600)
        self.assertEqual(meta['guard_add_cases'],72)
        self.assertEqual(meta['mac_transactions'],180)
        self.assertFalse(meta['restricted_bindings'])
        rounds,adds,packs,macs,_=cases()
        self.assertTrue(any(s for _,_,_,s in rounds))
        self.assertTrue(any(s for _,_,_,_,s in adds))
        self.assertTrue(any(s for _,_,_,s in macs))
        self.assertEqual({len(t) for t,_,_,_ in macs},{1,20,30,54})
        self.assertEqual(literal(-1,32),"32'shffffffff")

    def test_sources_are_portable_and_complete(self):
        self.assertEqual(len(SOURCES),6)
        for source in SOURCES:
            self.assertTrue(source.is_file())
            self.assertNotIn('altera_',source.read_text().lower())


if __name__=='__main__': unittest.main()
