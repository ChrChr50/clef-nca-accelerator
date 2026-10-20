# ADR-0003: Hanoi training and runtime boundary

> Historical-scope notice (2026-10-06): retained for provenance, not the active forward implementation plan. ADR-0007 and docs/architecture/EMBODIED_NCA_VISION.md supersede task-specific choices. Original-reference evidence and dated experimental decisions remain preserved; no new embodied acceptance or model freeze is implied.

- Status: **Proposed**
- Proposed: 2026-09-19
- Accepted: Not accepted
- Deciders: User
- Stage: P05
- Human gate: G3
- Supersedes: None
- Superseded by: None
- Related requirements: BASE-001, BASE-002, BASE-005, BASE-007, BASE-009,
  P05-001 through P05-012

## Context

P05 implemented the derivative adapter/model, canonical data partitions,
conventional control, staged NCA training, closed-loop evaluation, and the
oracle firewall. The measured alternatives and failures are recorded in
`docs/architecture/P05_G3_TRAINING_AND_INTERFACE_PACKET.md`.

The subsequently authorized Hypothesis A continuation kept the graph fixed and
tested aligned stochastic updates, mixed short/original recurrent schedules,
exact peg permutations, standard-first coherent trajectories, training-only
auxiliary concepts, independent probes, and hard stability rejection. It
failed its bounded-soak, closed-loop, and probe acceptance predicates. This
new evidence does not accept this ADR or authorize P06.

The user later authorized a separate eight-channel relational-layout v2
experiment under ADR-0004. Its bounded 510-decision soak passed, but the
first policy run completed only 1/12 standard-start n=1..4 episodes and
achieved 25/194 held-out fresh-grid action accuracy. ADR-0004 authorizes
that experiment only. It does not accept this G3 runtime/model-freeze draft;
the six-channel choices below remain the historical v1 proposal, not an
implicit v2 contract.

## Proposed decision

Accept raw P04 observations with redundancy one; raw six-cell scores and unit
mass complete-set cross entropy; terminal samples excluded only from action
loss; no reward or RL; no direct legality feedback or separate illegal-action
loss; host budget `2*(2**n-1)`; current software-training schedule 20--24 steps
with 50--59 retained as a comparison; clamp-one output marker channels 4/5;
and the host boundary of 36 observations in and six scores out. Use coherent
persistent-grid trajectories as primary and independent grids as a control.

Do not freeze the current NCA as the functional baseline. It is finite and
reproducible but has weak generalization, low closed-loop completion, and a
recorded long-horizon DAgger numerical failure. The recommended choice is G3
Option A: accept the contract and require a bounded P05 stabilization iteration
before authorizing P06.

After the negative Hypothesis A and v2 continuations, the current
recommendation is the updated G3 packet's bounded diagnostic decomposition,
not an automatic repeat of either training run. This ADR remains unaccepted.

## Consequences

The deployable model remains free of transition grammar, oracle data, reward,
legality, distance, budget, and terminal status. Output marker clamping is an
explicit Hanoi derivative difference and must be implemented exactly by later
software/RTL if accepted. No checkpoint is a performance golden model until G3
explicitly accepts it.

## Validation and rollback

Validation requires the P03/P04 regressions, P05 contract tests, firewall,
finite checkpoint scan, reproducible experiment hashes, and preregistered
performance/stability thresholds for the stabilization run. Rejection leaves
ADR-0002 and P04 unchanged. Any feedback or architectural revision requires an
updated proposal or superseding ADR.

## Claim discipline

The NCA is a conventional learned controller. The recorded bounded learning
does not establish robust Hanoi competence, autopoiesis, closure to efficient
cause, or Medium Rosen.
