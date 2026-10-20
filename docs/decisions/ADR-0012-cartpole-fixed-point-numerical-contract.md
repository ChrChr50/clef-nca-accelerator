# ADR-0012: CartPole fixed-point arithmetic and quality contract

- Status: **Accepted**
- Accepted: 2026-10-07
- Proposed: 2026-10-07
- Decider: User
- Stage/gate: P07/G4
- Supersedes: None until explicitly accepted
- Related requirements: P07-001 through P07-007

## Context

Accepted ADR-0011 freezes released model2 while preserving its measured float
limitations. P07 implements three numerical alternatives and profiles a faithful
full-horizon float episode. Complete measurements are in
`docs/architecture/P07_G4_NUMERICAL_DECISION_PACKET.md` and
`docs/verification/P07_NUMERICAL_PROFILING_AND_GOLDEN.md`.

## Options

1. **Recommend fidelity32:** signed 32-bit states/activations with 24 fractional
   bits; signed 24-bit kernels with 22 fractional bits; signed 62-bit accumulators
   and biases at 46 fractional bits. Nearest ties-even rounding, signed saturation
   with counters, bias-last exact MACs, ReLU before requantization, source post-
   writes, persistent old-grid epochs and integer argmax/lowest-index tie.
2. **balanced24:** signed 24-bit states/activations with 16 fractional bits;
   signed 18-bit kernels with 16 fractional bits; signed 48-bit accumulators/biases
   at 32 fractional bits. Same operation/scheduling rules. Lower storage and
   multiplier widths, but substantially larger measured numerical drift.
3. **Defer the numerical choice:** run longer independently declared fixed/float
   comparisons before selecting a format. No arithmetic or RTL commitment.

Compact18 is retained as a measured ablation. It changed an action on calibration
seed 10 at move 2 through a score tie, and on acceptance seed 20 at move 238.
It is not recommended for the first faithful numerical baseline.

## Accepted quality boundary

Accept fidelity32 as the initial integer specification, with exact
integer equality required from RTL at every declared layer/cell/epoch/readout
boundary. Forbid silent wrap and explicitly count all saturation events; the current
bounded calibration/acceptance runs observed zero saturation and exact float
action/score agreement. Preserve those measured results as bounded, censored
evidence; they do not qualify 10,001-action quantized or FPGA performance.

Long-run control loss, new arithmetic tuning and board performance must be
measured later against the unchanged frozen float baseline. No acceptable
percentage of full-horizon control loss is inferred from P06's 6/10 result.
Further tuning must identify reused seeds and use newly declared validation
data. G5 controls actual lanes/memory/transport; hardware fit/timing are unmeasured.

## Recommendation and consequences

Choose Option 1 to minimize measured numerical changes before RTL. The 32-bit
candidate matched both new 256-action traces and had maximum recurrent grid
error 1.788884401e-5 in the bounded study, versus 0.002084851265 for balanced24.
It requires wider multipliers/accumulators and 393,216 state double-buffer bits,
versus 294,912 for balanced24. These are bit-count estimates, not synthesis/PPA.

Both options preserve the local NCA graph and vendor-independent integer rules
for portable SystemVerilog and ASIC exploration. No event dynamics, host policy,
online plasticity or Clef closure mechanism is added. Deferred evaluation costs
software time but preserves the hardware choice. A faithful fixed controller
does not itself improve the frozen float policy's learned performance.

## Decision

On 2026-10-07 the user explicitly accepted the recommended **Option 1,
fidelity32**, including the bounded quality scope above. Freeze signed 32-bit
states/activations with 24 fractional bits, signed 24-bit kernels with 22
fractional bits, and signed 62-bit accumulators/biases with 46 fractional bits.
The declared nearest ties-even rounding, counted signed saturation, bias-last
exact accumulation, ReLU before requantization, source post-writes, persistent
old-grid epochs and lowest-index integer argmax tie rule are accepted.

Require exact integer RTL equality at layer/cell/epoch/readout boundaries.
Arithmetic must never wrap silently; saturation events remain explicitly counted.
The zero-saturation, identical-action results are evidence for the measured
bounded runs, not a guarantee on all possible inputs or full-length episodes.
Full-horizon quantized/FPGA control loss, board fit and timing remain unmeasured.

`sw/cartpole/arithmetic.accepted.v1.json` binds this decision, the resolved
weight freeze, executable integer golden and existing P07 evidence. Alternative
formats and the original experiment declarations remain preserved.

G4 is complete. Current weights remain frozen by ADR-0011. The user explicitly
requested bookkeeping and a stop: **P08 and RTL are not authorized or started**.
