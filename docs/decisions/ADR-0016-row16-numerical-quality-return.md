# ADR-0016: Response to row16 numerical-control degradation

- Status: **Proposed — unaccepted G4 return**
- Proposed: 2026-10-28
- Decider: User
- Stage/gate: P07 extension / G4, before numerical replacement and complete-core integration
- Supersedes: None unless explicitly selected and accepted
- Related: Accepted ADR-0015 direction; accepted ADR-0012 fidelity32; ROW-001 through ROW-006

## New evidence

Row16 (state 16/F10, weights 16/F12, bias/accumulators 48/F22) passes integer operator/layout/vector tests. All four short screens survive their caps without saturation. The longer seed-41 candidate fails at action **1150**, pole-angle limit, while float32 and accepted fidelity32 remain alive through **1488** saved actions. No row16 saturation is recorded. Thus short survival and arithmetic correctness did not establish preserved recurrent control performance. Other long cases are censored at the gate stop; this is not a completed statistical comparison.

Your prior acceptance selects 16-bit **with validation** and delegates implementation choices; it does not explicitly accept this newly measured failure relative to the baseline. All active comparison processes have been stopped and their resumable states retained. Details and commands are in `docs/architecture/ROW_PIPELINE_G4_RETURN_PACKET.md` and `experiments/row16_validation/gate_summary.json`.

## Options

Diagnostic addendum (same date): the user requested deeper diagnosis and hardware-overhead analysis, not gate acceptance. The saved seed-41 first changed action is 101, inside the short cap; same-input probes show coarse observations alone can reverse that decision. The terminal episode ends in 12 consecutive Left actions, with no ties in that final run and no saturation. Replaying the saved candidate history matches every later action and terminal grid exactly. See `docs/verification/ROW16_DIAGNOSIS_AND_PRECISION_COST.md` and its diagnostic summaries for scoped interventions and logical hardware estimates. This evidence does not accept a new precision variant or establish synthesized resource/timing figures.

1. **Recommended: retain fidelity32 for the functional row-pipeline baseline.** Keep the new row organization, in-place storage and stage handoff direction, with arithmetic parameterized and physical lane counts subject to synthesis. Leave row16 as an unaccepted experimental alternative. Wider arithmetic can require more DSPs/logic or fewer physical lanes and longer latency; there is no hard 20 ms deadline. Actual fit is still unmeasured.
2. **Authorize a new bounded 16-bit quantization experiment**, preserving current weights and exact source behavior. Predeclare candidate fractions/per-layer scaling, validation data and loss criteria before testing, retain this failed candidate, and stop again on evidence. This costs additional numerical work before selecting hardware arithmetic. No QAT/retraining is implicit.
3. **Accept row16 as a behavior-changing numerical baseline with the measured limitation.** This explicitly accepts changed actions and at least one earlier failure, not equal-to-paper performance. Keep independent integer/RTL equality mandatory and gather further control/board evidence later. A new accepted arithmetic manifest/decision would be required; this draft does not create it.

## Recommendation, consequences and stop

Recommend Option 1 for the user's goal of converting the faithfully reproduced controller without silently accepting a degraded numerical variant. It preserves the previously accepted arithmetic and current weights, advances the row architecture, and moves physical cost/latency choices to G5. Option 2 keeps a stricter 16-bit target but requires additional research and an honest outcome boundary. Option 3 prioritizes the requested narrow datapath while accepting the observed control difference.

All options retain portable SystemVerilog, vendor-isolated memories/DSPs, and ASIC portability. None changes the local graph or establishes Clef claims. No final complete-core or board result is accepted by this packet. Existing accepted ADR-0012/manifest remains unchanged until disposition. Stop at G4; do not automatically restart comparisons, tune fractions, train, or implement the final core.
