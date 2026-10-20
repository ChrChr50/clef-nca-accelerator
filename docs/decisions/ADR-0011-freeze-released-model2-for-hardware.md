# ADR-0011: Freeze released model2 for hardware implementation

- Status: **Accepted**
- Accepted: 2026-10-07
- Decider: User
- Stage/gate: P06/G3E resolution; P07 authorized
- Supersedes: ADR-0009's requirement to pass >=8/10 before weight freeze only
- Related requirements: P06-003 through P06-007, CART-003, P07-001

## Accepted decision

The user explicitly instructed: proceed to P07 with the current weights frozen
and address performance with the RTL design later. Freeze the released model2
blob `ee8e4ad597d73dc616e60e91a5af056c96beb9f2c18652cfb1a1906247fbc009`
as the engineering baseline. The original graph, E01 seam, ADR-0009 reset,
source horizon, stochastic schedule, no-perturbation protocol and local-only
rights restriction remain in force. No retraining or weight change is selected.

Complete the resolved P06 contract and verified ignored local export as the
prerequisite bookkeeping for explicitly requested P07. The source-aligned float
baseline remains measured at **6/10** full-horizon completions. This decision
accepts freezing despite that result; it does not retrospectively pass the
original 8/10 criterion, accept the proposed 5,000-action criterion, or claim
the paper's full statistics were reproduced. ADR-0010's options are not selected.

## Evidence and consequences

`P06_UPSTREAM_PARITY.md` directly executes the pinned upstream Python operator
and plant for seed 12: all 1,334 actions, score and plant endpoint agree with
our reproduction; full decision-grid errors remain within P03 tolerance.
This supports source fidelity for that case, not population reliability.

P07 must distinguish quantization/control loss from float-policy limitations
and stop at G4 with arithmetic/quality alternatives. P08 and subsequent RTL
work require separate authorization. A faithful RTL implementation is expected
to reproduce the selected numerical controller; faster execution of a
step-synchronized plant is not evidence that its policy becomes more reliable.
Later performance improvements must be measured and, if behavior changes,
declared as a separate accepted model/numerical variant.

Portable SystemVerilog, vendor/ASIC wrapper isolation and future Clef claim
boundaries remain unchanged. This freezes weights, not arithmetic, board fit,
hardware quality, a public license, or any causal-closure claim.
