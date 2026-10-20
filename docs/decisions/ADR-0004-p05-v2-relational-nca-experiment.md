# ADR-0004: P05 v2 relational Hanoi NCA experiment

> Historical-scope notice (2026-10-06): retained for provenance, not the active forward implementation plan. ADR-0007 and docs/architecture/EMBODIED_NCA_VISION.md supersede task-specific choices. Original-reference evidence and dated experimental decisions remain preserved; no new embodied acceptance or model freeze is implied.

- Status: **Accepted for a bounded P05 experiment, not for model freeze**
- Proposed and authorized: 2026-09-29
- Decider: User
- Stage: P05
- Human gate: G3 continuation; final G3 model-freeze decision remains open
- Supersedes: Six-channel graph assumption for this separately named P05 v2 experiment only
- Superseded by: None
- Related requirements: BASE-001 through BASE-005, BASE-007 through BASE-009, P05-001 through P05-012

## Context

ADR-0002 and P04 fix the logical 36-value observation, six ordered unmasked
actions, three-peg transition grammar, host boundary, and episode reset. The
immutable CartPole reference and the P05 six-channel candidate remain intact.

The first P05 candidate completed 13/72 episodes and coherent DAgger became
non-finite near 70 attempted moves. The locked-graph Hypothesis A continuation
completed 2/20 short and 0/20 long diagnostic episodes; a 510-decision
persistent-state soak reached approximately 2.066e36. These are measured
reasons to test spatial and dynamical changes, not proof that an NCA cannot
solve the bounded Hanoi task.

## Options considered

1. Repeat training on the scattered input/output layout and unbounded
   six-channel residual. This is the smallest code change, but the measured
   continuation failed despite aligned fire rates, permutations, coherent
   trajectories, and auxiliary supervision.
2. Introduce a structured disk-major input block, source-by-destination output
   matrix, eight-channel state with two fixed marker channels, and a bounded
   residual. This is the selected reversible P05 experimental fork.
3. Move to larger or explicitly symbolic/legality-masked controllers now.
   That increases hardware and scientific confounding before the smaller
   structural hypothesis is tested.

## Decision

The user authorized implementing the v2 proposal on 2026-09-29. This selects
Option 2 for a bounded P05 experiment, **not** the proposed ADR-0003 contract
and **not** a functional model freeze.

- Keep the accepted P04 environment, observation order, N_MAX=8, action order,
  raw six-score unmasked argmax, between-move grid persistence, and episode
  reset.
- Map disk d fields 0..3 to grid (11+d,12+field); map goal bits and count to
  (19,12..15); map action (source,destination) to
  (17+source,16+destination) for distinct pegs. The machine-readable mapping
  is training/hanoi_nca/layout_v2.json.
- Use state [B,32,32,8]. Channels 0..5 are evolving working channels;
  channel 0 at an output is its score. Channel 6 is an input-site marker,
  channel 7 an output-site marker. Both marker channels are cleared globally
  and rewritten every epoch. Active input sites are fully clamped to their
  observation in channel 0 and marker 6 = 1.
- Use learned zero-padded 3x3x8 -> 20 plus ReLU, pointwise 20 -> 30 plus
  ReLU, and pointwise 30 -> 8 linear, all biased: 2,338 shared parameters.
  Six actions remain six output cells, not six state channels.
- Before every local epoch, rewrite the new observation and markers so the
  first delta can see the observation. Each epoch computes all deltas from
  the same old grid, applies one Bernoulli mask bit per cell shared over all
  eight channels, saturates the residual to [-5,5], then rewrites inputs and
  markers. The bound is present in both training and inference.
- Use P04 transitions and training-only oracle labels for routing/legality
  curricula, supervised optimal-action imitation, and teacher/on-policy
  multi-decision training. No reward, DQN Q scaling, runtime legality mask,
  oracle distance, or solver enters the deployment-shaped model.

## Consequences

The v2 local graph requires 2,338 rather than 1,916 parameters and 2,280
rather than 1,860 MACs per grid cell per epoch by arithmetic count. The
bounded update adds saturation and requires a new fixed-point/RTL contract if
v2 is ever frozen. The layout has maximum input-output Chebyshev distance
eight, versus nine for v1; its per-output Euclidean mean-distance spread is
larger, so action bias must be measured rather than assumed absent.

The design remains a conventional fixed-weight NCA and preserves the
observation/action host boundary. No Clef plasticity, privileged functional
label, explicit Hanoi algorithm, vendor primitive, or technology-specific
device is added. Portable FPGA/ASIC implementation remains feasible in
principle, but no fit, timing, power, or performance claim is made at P05.

## Validation and rollback

The separate v2 layout/model/adapter/runtime/experiment files allow complete
rollback without altering original or v1 behavior. Required P05 evidence:
layout geometry and collision checks, exact tensor/parameter checks, NumPy
versus PyTorch rewrite equivalence, masked/marker/boundary behavior,
deterministic mask replay, training curves, bounded persistent soak, open-loop
and closed-loop Hanoi evaluation, old P03/P04/P05 regressions, and the oracle
firewall. Failed policy performance keeps G3 open and blocks P06 functional
freeze. Existing ADR-0003 remains proposed until a separate final G3 choice.

## Claim discipline

Architectural authorization and numeric boundedness do not establish
successful Hanoi reasoning, shortest-path competence, autopoiesis, CEC, or
Medium Rosen.
