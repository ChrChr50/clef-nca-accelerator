# G5 — Shared-row functional architecture and remaining physical decision

Date: 2026-10-30. Status: **Decision packet; G5 not accepted.**
Read ADR-0017, proposed ADR-0018, the epoch-core interface document and the
verification report. Earlier G4 row16 findings remain unchanged.

## What is implemented

One persistent four-bank grid, three tagged shared old rows, common convolution
decode, scalar-per-column operand delivery, explicit coefficient broadcasts,
three concurrent whole-row stages, mask-based MAC gating, guarded in-place
writeback, and a complete epoch barrier. Fidelity32 is the default. Tests cover
source postwrites, persistent epochs, boundaries, stalls, reset and every final
grid word. Exact commands/outcomes are in the stage ledger.

There is no autonomous RNG, complete 50–59-epoch action controller, UART parser,
FPGA wrapper, physical fit, timing or board-control result in this submission.
Supplied masks and scaled/quantized observations are an explicit test seam.

## Alternatives and consequences

| Choice | Evidence and consequences |
|---|---|
| Continue the fidelity32 row pipeline through targeted synthesis before final G5 signoff | Preserves accepted arithmetic and the requested shared-row architecture. Functional epoch equivalence is tested. DSP mapping, ROM ports, register cost and timing remain unknown; lanes/banking remain provisional pending those results. Recommended. |
| Return to the existing folded cell engine with a double grid | Existing cell arithmetic tests pass. Two complete grids alone require 393,216 state bits at fidelity32. It still needs an integrated epoch scheduler/controller; it does not inherit the new row pipeline's complete epoch test merely by sharing arithmetic semantics. Retain as capacity/routing fallback. |
| Select row16 now | Smaller declared storage/data widths, but measured control degradation at action 1150 remains unresolved in ADR-0016. Exact row16 HDL equivalence would not make its policy performance acceptable. Not recommended without a separate numerical decision. |

Logical arithmetic only, **not mapped FPGA resources**: the new fidelity32 grid
contains 196,608 bits; three old rows contain 18,432 bits. Producer outputs,
dense input registers and the owned writeback delta/old row total 120,832 bits.
The existing 1,860 kernels and 56 biases add 48,112 logical bits. Masks,
configuration-valid bitmaps, tags, observations and counters are additional.
These totals do not establish an ALM/M10K fit; wide captured rows may map to
registers rather than the desired RAM structures. Initial lane targets are
32/24/8, not 62 proven physical DSP blocks. Dense 1 has three coefficient read
groups; convolution and Dense 2 have one each. Synthesis must establish actual
replication, multiplier decomposition and critical recurrence paths.

## Proposed remaining interface decisions

- Retain one compute clock and synchronous invalidating reset in the portable
  core. Put PLLs, physical buses and any clock-domain crossing in board wrappers.
- Use the existing complete-layer configuration commit and complete-grid
  initialization validity before start. Later controller transport must make
  session/reset/reconfiguration atomic; the epoch seam alone is not that parser.
- Keep the exact supplied-grid/mask/epoch replay path. Recommend host-generated
  source draws for first verification integration; evaluate source-compatible
  MT19937 hardware separately if transport/service measurements justify it.
  A replacement PRNG is a distinct behavioral decision.
- Keep observation float32 scaling and quantization in the verified host frontend
  initially, supplying eight exact integer words to the epoch engine. Later
  wire/controller integration must preserve the four-observation E01 contract
  and prove frontend equivalence rather than reinterpret its float payload.
- Retain a portable byte-interface seam for the proposed framed UART, with HPS
  bridging as a board alternative. Physical route and measured service capacity
  remain unresolved. At 115200 baud, 8N1, 55 supplied masks alone occupy about
  0.611 seconds of wire time per action (`55*128*10/115200`), before framing.
  This is an arithmetic estimate, not measured service or an accepted deadline.
- Preserve executed-work diagnostic counters separately from full-golden
  logical diagnostics. A skipped inactive cell can omit an irrelevant internal
  saturation even though its final postwritten state is identical.

## Stop and next evidence

The recommendation is to authorize targeted synthesis/inference of this
fidelity32 candidate before accepting final G5 lanes/storage/transport. Report
mapped RAM/DSP/ALM counts, recurrence timing, bank conflicts, routing estimates
and achievable clock with explicit tool/device identities. If it does not fit,
return with measured alternatives; do not silently select row16 or change the
local graph. After G5 is accepted, implement the action controller, exact draw
assignment, integer readout/argmax, recovery and transport, then complete P12–P14
verification. No board performance or restored paper-level performance follows
from this functional epoch result.
