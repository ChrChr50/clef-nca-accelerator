# ADR-0005: Gated teaching and smooth-bound P05 experiment

> Historical-scope notice (2026-10-06): retained for provenance, not the active forward implementation plan. ADR-0007 and docs/architecture/EMBODIED_NCA_VISION.md supersede task-specific choices. Original-reference evidence and dated experimental decisions remain preserved; no new embodied acceptance or model freeze is implied.

- Status: **Authorized for a reversible P05 experiment, not model freeze**
- Authorized: 2026-09-30 by the user's request to autonomously repair the
  failed teaching flow and replace its data
- Stage: P05/G3 continuation
- Supersedes: No accepted logical interface or frozen model
- Related: ADR-0002, ADR-0004, `P05_V3_GATED_TEACHING_CONTINUATION.md`

## Context and evidence

The v2 paper-mechanics warm-up failed: all six fresh-validation scores were
hard-clamped at -5, MSE was 25.5460949 versus goal 0.02, and a backward probe
showed zero gradient. Its subsequent imitation loss was ln(6) with zero
gradient. The exact original CartPole operator instead uses a training-only
overflow penalty and no inference hard clipping. The current 36-input mean
target also has lower variance than the original eight-input synthetic target.

A first unclipped relay experiment passed a nearby-input gate at iteration
500, but became numerically unsafe 94 iterations into arbitrary-source
relay. This shows that removing clipping alone is insufficient.

## Experimental decision

Retain P04's 36 observations, six ordered actions, host transition authority,
raw unmasked argmax, and episode reset. Retain the v2 layout, markers, and
2,338-parameter local graph. Replace only the residual bound in a separate
training/runtime variant: for a firing cell, map pre-bound value `z` to
`(10/pi)*atan((pi/10)*z)`. A nonfiring cell retains its old state before the
usual input/marker rewrite. This maps finite values into (-5,5), has unit
derivative at zero and a positive derivative for every finite `z`, and avoids
the exact dead-gradient region of hard clipping. It is not the original
CartPole operator and is not a model freeze.

Train with a boundary-margin penalty, global gradient-norm clipping, Adam
at 0.001, and a half-fresh/half-reused grid batch. Gate stages in order:
local relay, progressively larger single-input source radii, six-output
broadcast, eight-input combination, 36-input combination, routing, legality,
then n=2/4/6/8 oracle imitation. The radius progression was added after the
first smooth-bound trial learned the nearby site but failed distant sources
at short recurrence. Synthetic target scaling `sqrt(2*k)*mean(k inputs)` preserves the
original eight-input target variance. Each stage must pass fresh and reused
validation and remain bounded before the next stage; failed gates stop rather
than silently advancing. All routing, legality, and oracle targets remain in
training/evaluation code only.

## Alternatives and consequences

1. Keep v2 hard clipping: bounded but measured dead-gradient failure.
2. Remove clipping and use only overflow penalty: local relay learned, but
   arbitrary-source training exceeded the safety guard.
3. Smooth bounded residual (selected reversible experiment): bounded and
   differentiable, but adds transcendental arithmetic not yet suitable for a
   portable fixed-point RTL contract. A later G3/G4 choice must decide whether
   approximation or a simpler piecewise function is justified by measured
   policy evidence. No FPGA/ASIC cost or performance is claimed now.

No P06 export, RTL, or functional baseline designation follows from this
experimental authorization. If the training gates or closed-loop evaluation
fail, the result remains negative P05 evidence and G3 stays open.

## 2026-09-30 spatial correction to the reversible trial

The v2 input block was found to have 14 hard-clamped sites with no mutable
neighbor; their observations cannot reach any output under the declared
3-by-3 operator. This invalidates full-input aggregation on that layout.
The next P05 experiment therefore selects a separate, spaced `layout_v6.json`
with columns 9, 11, 13, and 15, while keeping the same logical 36 inputs and
six actions. This is an experimental spatial fork only, not an amendment to
the accepted v2 implementation or a final G3 layout decision. It may increase
communication distance and output bias; those effects must be measured before
any later architectural choice.
