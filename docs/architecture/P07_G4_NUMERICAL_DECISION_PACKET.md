# P07 / G4 numerical decision packet

Status: **P07 complete; G4 accepted on 2026-10-07; stop before P08**.
ADR-0011 accepts the released model2 weight freeze despite the preserved 6/10
float qualification result. **ADR-0012 is accepted for fidelity32 and the bounded quality scope.**

The options below preserve the gate evidence. The user selected Option A;
`sw/cartpole/arithmetic.accepted.v1.json` is the accepted downstream contract.

## Decision requested

Choose the initial integer format and its quality scope. Recommendation:
**fidelity32**, with exact integer RTL equality and bounded software evidence
accepted for starting arithmetic implementation. This does not assert that
quantized 10,001-action reliability has been demonstrated.

| Candidate | Signed state/activation word, fraction | Kernel word, fraction | Accumulator/bias word, fraction | New 256-action traces identical to float | Worst recurrent grid error in bounded study |
|---|---|---|---|---|---|
| compact18, measured ablation | 18 / 12 | 16 / 14 | 40 / 26 | 1/2 | 0.01170256734 |
| balanced24, viable alternative | 24 / 16 | 18 / 16 | 48 / 32 | 2/2 | 0.002084851265 |
| **fidelity32, recommended** | **32 / 24** | **24 / 22** | **62 / 46** | **2/2** | **0.00001788884401** |

All candidates survived both 256-action caps and had zero saturation in the
predeclared bounded runs. Caps censor survival; they are not full-episode wins.
The 24/32-bit candidates also matched both reused calibration traces of 128
actions. Compact18 altered calibration seed 10 at action 2 (a score tie) and
acceptance seed 20 at action 238. A narrower state word can change decisions
without overflowing: loss of score resolution is a distinct failure mechanism.

## Evidence and limits

- Float profile: seed 10, **10,001 actions / 544,994 epochs**. Actions, score,
  mask and final plant/grid identities exactly match the old P06 result.
- Recurrent state/output hidden range: **[-5.801792145, 15.61518383]**; delta
  **[-17.71842575, 1.614928007]**; no nonfinite values. State/residual/delta
  sampled every epoch; first-two-layer preactivations every 64 epochs.
- Full-horizon minimum float action-score margin: **7.197260857e-6**. Some
  decisions are sensitive to fine precision; this is not a proof of stability
  for arbitrary masks or numerical formats.
- Separate zero-delta marker stress adds up to **590,059** marker increments
  across the maximum recurrent schedule. Compact18 saturates by increment 32;
  other candidates by 128. Learned deltas counteract additions in the measured
  controller. No marker clamp was silently added to the immutable float code.
- Exact signed accumulator bounds use full representable state magnitude and
  actual quantized kernels/biases. Required per-layer signed bits are
  **36/35/35**, **44/43/43**, and **58/57/57**, below allocated 40/48/62.
- **18** restricted complete layer/cell/epoch/readout vector cases replay exactly;
  **144** cells are independently checked with Python-int nested MAC loops.
  Synthetic tests cover rounding, saturation, zero-mask writes, ties, reset,
  service permutations and the existing host seam.

Calibration seeds 10/12 are explicitly reused. Acceptance seeds 20/21 were new
and all formats/caps were declared before execution; no widths were tuned on
them. This gate now sees their results, so future tuning must disclose reuse
and reserve new validation data. Detailed tensors/fixtures remain ignored/local.

## Three viable paths and consequences

**A — Accept fidelity32 and the proposed limited quality scope.** Closest measured
integer reproduction; start future P08 only on explicit authorization. Wider
MACs may increase FPGA/ASIC resources or folding cycles; G5 must measure them.

**B — Accept balanced24 with its larger measured error.** Same bounded action
results at lower word widths/storage. Long-horizon divergence is unmeasured;
do not claim the two formats are equally reliable from these short trials.

**C — Defer G4 and collect longer float/fixed evidence.** Stronger control-loss
assessment before hardware at additional CPU/evaluation time. No change to
the frozen learned weights is required for this option.

| Estimate (not synthesis) | compact18 | balanced24 | fidelity32 |
|---|---:|---:|---:|
| One 32x32x6 state grid, bits | 110,592 | 147,456 | 196,608 |
| Two state buffers, bits | 221,184 | 294,912 | 393,216 |
| 1,860 kernels + 56 wide biases, bits | 32,000 | 36,168 | 48,112 |

These exclude scratch/banking/transport and do not establish board fit, cycles,
Fmax, power or real-time operation. Both viable integer options preserve the
local learned graph, old-grid causality, logical masks and portable arithmetic.
They retain replaceable rule/scheduler/memory/transducer seams for later Clef
without adding organizational labels, plasticity, event variants or closure claims.

## Exit

See the full measurement/command report and `P07_INTEGER_GOLDEN_CONTRACT.md`.
Weights and fidelity32 arithmetic are accepted; measured alternatives remain
preserved. Full-horizon quantized performance remains unverified. The user
explicitly requested a stop after bookkeeping. **P08/RTL remain unstarted.**
