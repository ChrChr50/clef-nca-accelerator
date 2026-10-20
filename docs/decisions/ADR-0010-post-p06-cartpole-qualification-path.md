# ADR-0010: Response to failed model2 full-horizon qualification

- Status: **Proposed — G3E return gate unaccepted**
- Subsequent disposition: options not selected; user chose a different freeze path in accepted ADR-0011. Retained as historical proposal.
- Proposed: 2026-10-07
- Decider: User
- Stage/gate: P06 return to G3E
- Supersedes: None unless an option is explicitly accepted
- Related requirements: EMB-003, CART-003/004, P06-002 through P06-006

## Context

ADR-0009 conditionally selected the released model2 checkpoint and required
at least 8/10 held-out seeds 10–19 to reach the source's balanced
10,001-action horizon plus pinned goldens before P06 freeze. The P06 run
completed all ten without retries: goldens passed, **6/10** reached the
horizon, and four stopped at the pole-angle limit. See
`docs/verification/P06_CARTPOLE_QUALIFICATION.md` and
`docs/architecture/P06_G3E_QUALIFICATION_RETURN_PACKET.md`. No freeze or
restricted export exists.

## Options considered

1. **Retain the original bar:** authorize a separately scoped original-graph
   training/reselection program and new held-out validation. This preserves
   the stronger full-horizon competence requirement but risks the semester
   schedule. Released model2 remains a fixed control; no paper-statistics
   equivalence or checkpoint swap is assumed.
2. **Recommend a narrower baseline claim:** retain the exact released model2,
   source plant/horizon and reference-faithful update behavior, but replace
   the primary pre-freeze quality criterion with >=8/10 reaching 5,000
   actions on a **new pre-registered seeds 20–29** set. Continue to report
   full-episode outcomes and this 6/10-at-10,001 failure. The 5,000-action
   threshold is chosen after observing seeds 10–19 and cannot be validated
   by reusing them. No freeze occurs unless a new independent test passes.
3. **Investigate a distinct reset/reinitialization protocol:** authorize a
   bounded prospective experiment with explicit reset/RNG semantics, then
   return for a deployment choice. This may alter the model's temporal
   behavior and hardware reset needs; the existing two post-hoc P03 seeds do
   not establish benefit.

## Recommendation

Option 2 best preserves the one-semester *faithful released-checkpoint FPGA*
path without claiming the rejected full-horizon reliability. Its new held-out
test is mandatory and can fail. Option 1 is preferable if the 8/10 full
10,001-action bar is essential; Option 3 is exploratory. This recommendation
is **not authorization** to change ADR-0009 or run a new experiment.

## Decision

**Pending user decision.** ADR-0009's failed threshold remains authoritative.
No new checkpoint, quality threshold, reset policy, export, training run or
P07 stage is accepted by this draft.

## Consequences and validation if accepted

Any accepted option must explicitly identify which part of ADR-0009 it
supersedes and preserve its other source/operator, local-only rights,
step-synchronized timing, and event-variant boundaries unless separately
changed. The original reference and E01 contracts remain immutable.
Prospective seeds/thresholds, full scores/action counts, golden vectors and
rights-safe export checks must precede a P06 freeze. P07/G4 numerical and
P12–P14 hardware evidence remain later, independent gates. Neither a
controller-quality change nor an FPGA realization establishes autopoiesis,
CEC, Medium Rosen or body-wide sparse scaling.
