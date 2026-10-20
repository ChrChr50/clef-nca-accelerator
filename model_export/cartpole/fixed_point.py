"""Candidate integer scheduled golden for the immutable CartPole graph.

G4 has not accepted a format. All tensor-derived vectors remain local/ignored.
Products and sums are exact integers; only declared boundaries requantize.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import numpy as np

from reference.original_nca.core import INPUT_COORDINATES, OUTPUT_COORDINATES, INPUT_SCALE, NCAWeights


@dataclass(frozen=True)
class Format:
    name: str
    state_bits: int
    state_fraction: int
    weight_bits: int
    weight_fraction: int
    accumulator_bits: int

    def __post_init__(self):
        if not (2 <= self.state_bits <= 32 and 2 <= self.weight_bits <= 24
                and 2 <= self.accumulator_bits <= 62
                and 0 <= self.state_fraction < self.state_bits-1
                and 0 <= self.weight_fraction < self.weight_bits-1):
            raise ValueError("unsupported signed integer format")
        if self.state_bits+self.weight_bits+6 > 63:
            raise ValueError("unproved int64 host accumulation safety")

    def manifest(self):
        return {**asdict(self),"rounding":"nearest-ties-even","overflow":"signed saturation",
                "bias_fraction":self.state_fraction+self.weight_fraction,
                "fan_ins":[54,20,30],"accumulation_order":"kernel row, column, channel; bias last",
                "relu":"after bias, before requantization","activation_format":"state format",
                "residual":"guard-bit sum then state saturation",
                "quantization_boundary":"unscaled E01 float32 observations; source float32 scaling once",
                "post_write_order":"residual; clears; markers; scaled observation scatter",
                "schedule":"old-grid reads, full new-grid commit each supplied logical epoch",
                "tie":"lowest action index"}


def signed_limits(bits):
    if not 2 <= bits <= 62:
        raise ValueError("signed width must be in 2..62")
    return -(1 << (bits-1)),(1 << (bits-1))-1


def saturate(values,bits):
    low,high = signed_limits(bits)
    values = np.asarray(values,dtype=np.int64)
    return np.clip(values,low,high),int(np.count_nonzero((values<low)|(values>high)))


def round_shift(values,shift):
    """Arithmetic quotient/remainder implements nearest-even for both signs."""
    values = np.asarray(values,dtype=np.int64)
    if not 0 <= shift <= 62:
        raise ValueError("invalid requantization shift")
    if shift == 0:
        return values.copy()
    quotient = values >> shift
    remainder = values-(quotient << shift)
    half = 1 << (shift-1)
    increment = (remainder>half)|((remainder==half)&((quotient&1)!=0))
    return quotient+increment.astype(np.int64)


def quantize(values,bits,fraction):
    values = np.asarray(values,dtype=np.float64)
    if not np.all(np.isfinite(values)):
        raise ValueError("nonfinite value at quantization boundary")
    low,high = signed_limits(bits)
    scaled = np.rint(values*(1 << fraction))
    count = int(np.count_nonzero((scaled<low)|(scaled>high)))
    return np.clip(scaled,low,high).astype(np.int64),count


class FixedNCA:
    def __init__(self,weights:NCAWeights,fmt:Format):
        if weights.parameter_count != 1916:
            raise ValueError("requires frozen original graph")
        self.fmt = fmt
        self.counters = {}
        self.kernels,self.biases = [],[]
        for index in range(3):
            kernel,count = quantize(getattr(weights,f"conv{index}_kernel"),fmt.weight_bits,fmt.weight_fraction)
            self.kernels.append(kernel)
            bias,count_bias = quantize(getattr(weights,f"conv{index}_bias"),fmt.accumulator_bits,
                                       fmt.state_fraction+fmt.weight_fraction)
            self.biases.append(bias)
            self.counters[f"weight{index}"] = count
            self.counters[f"bias{index}"] = count_bias
        self.bounds = self.accumulator_bounds()
        if any(item["required_signed_bits"]>fmt.accumulator_bits for item in self.bounds):
            raise ValueError("candidate accumulator cannot contain analytical full-range bound")

    def accumulator_bounds(self):
        # Full signed-state magnitude and actual quantized coefficients, not
        # an empirical trajectory bound. Products fit int64 by Format validation.
        magnitude = 1 << (self.fmt.state_bits-1)
        result = []
        for index,(kernel,bias) in enumerate(zip(self.kernels,self.biases)):
            sums = np.abs(kernel.reshape(-1,kernel.shape[-1])).sum(axis=0)
            bound = max(magnitude*int(total)+abs(int(b)) for total,b in zip(sums,bias))
            result.append({"layer":index,"fan_in":kernel.size//kernel.shape[-1],
                           "max_abs_accumulator_integer_bound":bound,
                           "required_signed_bits":bound.bit_length()+1,
                           "allocated_signed_bits":self.fmt.accumulator_bits})
        return result

    def clip(self,values,bits,label):
        result,count = saturate(values,bits)
        self.counters[label] = self.counters.get(label,0)+count
        return result

    def initial_grid(self,grid):
        result,count = quantize(grid,self.fmt.state_bits,self.fmt.state_fraction)
        self.counters["initial_grid"] = self.counters.get("initial_grid",0)+count
        return result

    def observations(self,observation):
        observation = np.asarray(observation,dtype=np.float32)
        if observation.shape != (1,4):
            raise ValueError("four unscaled E01 observations required")
        result,count = quantize(observation*INPUT_SCALE,self.fmt.state_bits,self.fmt.state_fraction)
        self.counters["observation"] = self.counters.get("observation",0)+count
        return np.repeat(result,2,axis=1)

    def layer(self,state,index):
        kernel = self.kernels[index]
        if index == 0:
            padded = np.pad(state,((0,0),(1,1),(1,1),(0,0)))
            windows = np.lib.stride_tricks.sliding_window_view(padded,(3,3),axis=(1,2))
            matrix = windows.transpose(0,1,2,4,5,3).reshape(-1,54)
        else:
            matrix = state.reshape(-1,state.shape[-1])
        # Int64 matmul performs exact products and sums. The analytical bound
        # proves that bias-last and serial MAC orders give the same result.
        acc = matrix @ kernel.reshape(matrix.shape[-1],kernel.shape[-1])
        acc = acc+self.biases[index]
        acc = self.clip(acc,self.fmt.accumulator_bits,f"accumulator{index}")
        act = np.maximum(acc,0) if index<2 else acc
        output = self.clip(round_shift(act,self.fmt.weight_fraction),self.fmt.state_bits,f"layer{index}")
        return output.reshape(1,32,32,kernel.shape[-1]),acc.reshape(1,32,32,kernel.shape[-1])

    def delta(self,grid,trace=False):
        arrays = {}
        state = np.asarray(grid,dtype=np.int64)
        for index in range(3):
            state,acc = self.layer(state,index)
            if trace:
                arrays[f"layer{index}_accumulator"] = acc
                arrays[f"layer{index}_output"] = state
        return (state,arrays) if trace else state

    def step(self,grid,observation,mask,*,trace=False,cell_order=None):
        grid = np.asarray(grid,dtype=np.int64)
        mask = np.asarray(mask)
        if grid.shape != (1,32,32,6) or mask.shape != (1,32,32,1) or mask.dtype != np.bool_:
            raise ValueError("requires [1,32,32,6] integer state and shared bool mask")
        low,high = signed_limits(self.fmt.state_bits)
        if np.any((grid<low)|(grid>high)):
            raise ValueError("grid exceeds declared state width")
        delta,arrays = self.delta(grid,True)
        residual_raw = grid+delta*mask.astype(np.int64)
        new = self.clip(residual_raw,self.fmt.state_bits,"residual")
        new[...,2:4] = 0
        one = 1 << self.fmt.state_fraction
        for row,col in INPUT_COORDINATES:
            new[:,row,col,:] = 0
            new[:,row,col,[1,2,4,5]] = one
        for row,col in OUTPUT_COORDINATES:
            new[:,row,col,3] = one
            new[:,row,col,4:] = self.clip(new[:,row,col,4:]+one,self.fmt.state_bits,"output_marker")
        updates = self.observations(observation)
        for index,(row,col) in enumerate(INPUT_COORDINATES):
            new[:,row,col,0] = updates[:,index]
        if cell_order is not None:
            order = np.asarray(cell_order)
            if order.shape != (1024,) or not np.array_equal(np.sort(order),np.arange(1024)):
                raise ValueError("cell service order must visit each cell exactly once")
            # Service writes into a distinct destination; all deltas read old.
            committed = np.empty_like(new).reshape(1024,6)
            committed[order] = new.reshape(1024,6)[order]
            new = committed.reshape(1,32,32,6)
        if trace:
            arrays.update(delta=delta,residual_before_saturation=residual_raw,post_write_epoch=new)
            return new,arrays
        return new

    def decode(self,grid):
        return np.asarray(grid,dtype=np.float64)/(1 << self.fmt.state_fraction)

    @staticmethod
    def readout(grid):
        return np.stack([grid[:,r,c,0] for r,c in OUTPUT_COORDINATES],axis=1)


class ScheduledController:
    """Persistent integer state, supplied logical masks, final-epoch readout."""
    def __init__(self,model:FixedNCA,grid):
        self.model = model
        self.grid = model.initial_grid(grid)
        self.epochs = 0

    def decide(self,observation,masks,*,cell_order=None):
        if masks.dtype != np.bool_ or masks.shape[1:] != (1,32,32,1) or len(masks) not in range(50,60):
            raise ValueError("requires the original 50-59 supplied shared-mask epochs")
        obs = np.asarray(observation,dtype=np.float32)[None,:]
        for mask in masks:
            self.grid = self.model.step(self.grid,obs,mask,cell_order=cell_order)
            self.epochs += 1
        scores = self.model.readout(self.grid)[0]
        return int(np.argmax(scores)),scores.copy()


def scalar_cell_delta(weights:FixedNCA,grid,row,col):
    """Independent Python-int cell calculation for primitive/RTL verification."""
    fmt = weights.fmt
    patch = []
    for kr in range(3):
        for kc in range(3):
            rr,cc = row+kr-1,col+kc-1
            for ch in range(6):
                patch.append(int(grid[0,rr,cc,ch]) if 0<=rr<32 and 0<=cc<32 else 0)
    values = patch
    for layer,(kernel,bias) in enumerate(zip(weights.kernels,weights.biases)):
        matrix = kernel.reshape(len(values),-1)
        outputs = []
        for out in range(matrix.shape[1]):
            acc = sum(int(value)*int(matrix[index,out]) for index,value in enumerate(values))+int(bias[out])
            low,high = signed_limits(fmt.accumulator_bits)
            acc = max(low,min(high,acc))
            if layer<2:
                acc = max(0,acc)
            divisor = 1 << fmt.weight_fraction
            quotient,remainder = divmod(acc,divisor)
            if remainder*2>divisor or (remainder*2==divisor and quotient%2):
                quotient += 1
            low,high = signed_limits(fmt.state_bits)
            outputs.append(max(low,min(high,quotient)))
        values = outputs
    return np.asarray(values,dtype=np.int64)
