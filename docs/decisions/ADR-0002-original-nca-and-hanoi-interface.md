# ADR-0002: Immutable original NCA and bounded Hanoi interface

- Status: **Accepted**
- Proposed: 2026-09-18
- Accepted: 2026-09-19
- Deciders: User
- Stage: P03
- Human gate: G2
- Supersedes: None
- Superseded by: ADR-0007 for the Hanoi derivative task/interface only, effective 2026-10-06; immutable original reference remains accepted
- Related requirements: BASE-001 through BASE-005, BASE-008, P03-001 through P03-010

## Context

P03 reproduced the original CartPole NCA as an isolated clean-room reference.
Later Hanoi work needs an explicit derivative contract without rewriting the
historical behavior. The complete evidence and options are in
`docs/architecture/P03_G2_OPERATOR_AND_HANOI_CONTRACT_PACKET.md`.

## Decision drivers

- Preserve exact regression lineage to the published NCA.
- Provide six directed actions without hiding illegal-action behavior.
- Support a useful bounded range of disk counts with fixed tensor dimensions.
- Keep the environment, legality grammar, and oracle outside the accelerator.
- Avoid task-solution leakage and preserve portable fixed-shape hardware.

## Options considered

1. Disk-location one-hot plus present mask, goal, and disk count at `N_MAX=8`.
2. Per-peg occupancy/rank matrix at `N_MAX=8`.
3. Disk-location one-hot at the smaller `N_MAX=6`.

## Decision

Accept the original contract in `reference/original_nca/operator_manifest.json`
as immutable. Select Option 1 with `N_MAX=8`, six outputs ordered `0->1`, `0->2`,
`1->0`, `1->2`, `2->0`, `2->1`, unmasked argmax as primary behavior, persistent
hidden state between moves, and episode-boundary reset. The host provides the
36-value bounded observation and applies legal transitions; it does not provide
the next correct move. A separate P05 difference manifest must declare every
architectural and training change.

The user accepted this recommended option without modification at G2 on
2026-09-19. This acceptance freezes the interface decision for P04 and later
stages; changing the bound, encoding, action order, selection policy, or reset
policy requires a superseding ADR.

## Consequences

The original two-output CartPole implementation remains unchanged and continues
to gate later regressions. The derivative will require more input sites and a
six-channel action readout, so it is not checkpoint compatible with the original
model. Fixed `N_MAX=8` gives stable synthesis dimensions and permits exhaustive
small-state environment tests. It does not establish that the learned controller
will generalize to all eight-disk tasks; that is a later measured claim.

## Validation and rollback

G2 acceptance authorizes P04's environment contract, not training. Before P05,
validate observation round trips, action ordering, reset behavior, and the
absence of oracle data from the model interface. A later change to `N_MAX` or
encoding requires a superseding ADR; it does not modify the original reference.

## Claim discipline

This is a conventional fixed-weight NCA derivative interface. It is not evidence
of autopoiesis, closure to efficient cause, or Medium Rosen.
