# P07 candidate scheduled integer contract

Status: **G4 accepted on 2026-10-07: fidelity32**, per accepted ADR-0012.
The selected downstream authority is `sw/cartpole/arithmetic.accepted.v1.json`;
its validator is `model_export/cartpole/accepted_arithmetic.py`. Alternatives
and the original predeclared experiment remain unchanged. P08 is not started.
Accepted ADR-0011 freezes original model2 weights and the resolved float contract
in `sw/cartpole/deployment.freeze.v1.json`. The immutable P03 operator is intact.

## Numerical boundaries

`model_export/cartpole/fixed_point.py` implements three predeclared alternatives
from `experiments/p07_cartpole/protocol.v1.json`. Signed values represent integer
`q / 2^fraction`. State and all neural-layer outputs use the candidate state
format; kernels use its weight format. Biases use the accumulator width and
product fraction `state_fraction + weight_fraction`.

All MAC products and sums are exact signed integers. Kernel traversal is row,
column, input channel; add bias after the complete fan-in (54, 20 or 30).
Declared signed accumulator saturation is counted. A full-state-range bound
using actual quantized coefficient absolute sums and bias proves the int64
software implementation cannot wrap, and that allocated accumulators contain
all possible valid input words. This is stronger than observed trajectory ranges;
it does not prove all neural activations or recurrent states avoid saturation.

For the first two layers apply ReLU after bias. Requantize by the weight-fraction
right shift using nearest rounding with ties to even for both signs, then saturate
to the signed state format. The final local layer is linear. Float32 source
reduction order is not a bitwise specification for this integer derivative.

The host provides four unscaled pre-action E01 float32 observations. Apply source
float32 scales once, quantize to state integers and duplicate to eight sites.
Those observation values remain constant throughout the decision's 50–59 epochs.
Initial random float32 grid quantization is explicit. Reject nonfinite boundary
values. The physical plant remains the P03 float64 CartPole outside the controller.

## Epoch and action semantics

Every local delta reads the entire **old epoch**. Add masked integer deltas with
a guard bit, then saturate the residual to state width. A mask bit is shared
across six channels. Follow the source post-write order:

1. Clear channels 2/3 globally and all channels at active input sites.
2. Set input marker channels 1/2/4/5 to integer `1 << state_fraction`.
3. Set output channel 3 to that marker and increment output channels 4/5 by it,
   with explicitly counted signed saturation.
4. Write duplicated quantized observations at input channel 0.
5. Commit the entire destination epoch before any next-epoch neighborhood read.

`ScheduledController` persists its integer grid between decisions and accepts
the original supplied 50–59 ordered masks. It reads the two channel-0 output
integers after the final committed epoch and chooses the lowest-index argmax
on ties. Constructing a new controller quantizes an explicitly supplied fresh
grid; no hidden plant-triggered recovery reset is added.

An optional cell service permutation changes destination-write order only.
Every delta still reads old state; tests reverse and randomize that order and
require exact integer equality. This is a functional scheduling contract, not a
choice of MAC lanes, physical cycles, bus, clocks or bank ports. Those remain G5.
Logical masks are supplied using the frozen MT19937 replay construction; no new
hardware RNG, state-triggered sleeping or asynchronous updates were introduced.

## Vectors, checks and qualification scope

`scalar_cell_delta` independently uses Python integers and nested kernel loops.
Tests exercise corners/edges, random valid words, full signed-range bounds,
positive/negative rounding ties, saturations, mask-zero I/O, observation scaling,
persistence and service order. Public fixtures are synthetic, not learned tensors.

`generate_vectors.py` saves restricted layer accumulators/outputs, selected cells,
post-write epochs, exact masks and final readouts/actions in ignored `artifacts/`.
Vector containers use NumPy int64; the candidate widths still govern every word.
Safe manifests contain hashes and aggregate float-to-fixed errors, with first
boundary/coordinate differences. No weights, grids or array fixture values are
tracked. RTL will require exact integer equality to the **accepted** candidate;
P03 float tolerances must not relax that comparison.

Calibration seeds 10/12 are explicitly reused. New seeds 20/21 are reserved for
the predeclared 256-action bounded comparison; no format or threshold is tuned
on those results. Each fixed arm and float arm evolves its own plant using the
same initial state and logical masks. Grid error is summarized under identical
plant observations; after a differing action, later trajectory differences also
include plant feedback and are not labeled pure arithmetic error.

The full-horizon float calibration profiles every residual/delta/recurrent epoch
and samples first-two-layer preactivations every 64 epochs. All marker channels
are included. Marker-only zero-delta stress is separately analytical: repeated
`+1` can exceed any proposed finite state range. Learned deltas may counteract
those additions; measured ranges are not universal bounds.

G4 accepts fidelity32 and the bounded numerical/control evidence in ADR-0012.
The bounded comparison does not establish 10,001-action quantized reliability,
paper-table equivalence, FPGA latency/area/power, or a 20 ms wall-clock deadline.
