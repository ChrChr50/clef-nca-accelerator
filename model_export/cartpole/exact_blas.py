"""Exact integer research acceleration using bounded binary64 dot products.

This is not a changed quantizer or an RTL arithmetic contract. Integer operands
are decomposed so every product and every possible partial sum is exactly
representable below 2**53; recombination/bias/rounding remain integer operations.
The unmodified FixedNCA remains the independent golden comparison.
"""
import numpy as np
from model_export.cartpole.fixed_point import FixedNCA, round_shift


class ExactBlasFixedNCA(FixedNCA):
    def __init__(self, weights, fmt):
        super().__init__(weights, fmt)
        self.binary64_kernels = [k.reshape(-1,k.shape[-1]).astype(np.float64) for k in self.kernels]
        self.direct = []
        for kernel in self.kernels:
            sums = np.abs(kernel.reshape(-1,kernel.shape[-1])).sum(axis=0)
            coefficient_sum = max(int(v) for v in sums)
            bound = (1 << (fmt.state_bits-1))*coefficient_sum
            direct = bound < (1 << 53)
            if not direct:
                for magnitude in ((1<<16)-1,1 << max(0,fmt.state_bits-17)):
                    if magnitude*coefficient_sum >= (1 << 53):
                        raise ValueError("binary64 partial-sum exactness not proved")
            self.direct.append(direct)

    def layer(self, state, index):
        kernel = self.kernels[index]
        if index == 0:
            padded = np.pad(state,((0,0),(1,1),(1,1),(0,0)))
            windows = np.lib.stride_tricks.sliding_window_view(padded,(3,3),axis=(1,2))
            matrix = windows.transpose(0,1,2,4,5,3).reshape(-1,54)
        else:
            matrix = state.reshape(-1,state.shape[-1])
        weight = self.binary64_kernels[index]
        if self.direct[index]:
            acc = (matrix.astype(np.float64) @ weight).astype(np.int64)
        else:
            high = matrix >> 16
            low = matrix - (high << 16)
            hi_acc = (high.astype(np.float64) @ weight).astype(np.int64)
            lo_acc = (low.astype(np.float64) @ weight).astype(np.int64)
            acc = (hi_acc << 16) + lo_acc
        acc = self.clip(acc+self.biases[index],self.fmt.accumulator_bits,f"accumulator{index}")
        act = np.maximum(acc,0) if index < 2 else acc
        output = self.clip(round_shift(act,self.fmt.weight_fraction),self.fmt.state_bits,f"layer{index}")
        return output.reshape(1,32,32,kernel.shape[-1]),acc.reshape(1,32,32,kernel.shape[-1])
