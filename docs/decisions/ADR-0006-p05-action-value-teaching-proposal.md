# ADR-0006 — P05 action-value teaching and conditional spatial fork (draft)

> Historical-scope notice (2026-10-06): retained for provenance, not the active forward implementation plan. ADR-0007 and docs/architecture/EMBODIED_NCA_VISION.md supersede task-specific choices. Original-reference evidence and dated experimental decisions remain preserved; no new embodied acceptance or model freeze is implied.

Status: proposed experiment only; not a G3 acceptance or model freeze.

Update 2026-09-30: the action-value-first run was stopped at the user's
request to return to the previous architecture/teaching baseline. The
peg-summary and channel-capacity items remain **unimplemented proposals**;
the stopped run is not evidence about their effectiveness. See
`docs/verification/P05_BASELINE_REVERSION_AND_ARCHITECTURE_OPTIONS.md`.

## Context

The spaced v6 layout passed relay, aggregation, routing, and legality gates,
then failed two-disk imitation after 4,000 updates: fresh/persistent action
accuracy 0.4375/0.4792 against 0.85. Its training batch loss was 0.00756,
so in-sample fit did not predict held-out decision behavior. Validation drew
48 examples with replacement from only four distinct two-disk states.

## Proposed controlled sequence

1. Retain the P04 36-observation/six-action boundary, v6 spaced layout,
   8-channel/2,338-parameter local rule, stochastic updates, smooth bound,
   and verified 36-input warm-up checkpoint.
2. Teach channel-zero action scores as six signed one-step distance changes
   from the training-only oracle. Teach channel-one output values as auxiliary
   legality logits simultaneously. There is no inference-time legality mask,
   oracle feature, or distance table. Include a ranking margin and a lower
   policy learning rate. This is supervised action-value regression, not DQN.
3. Pair persistent grids with P04 states and advance each pair through the
   same teacher transition, resetting both together at terminal or before a
   trajectory would cross into a held-out identity. Mix fresh grids and
   short-to-50–59-step recurrence.
4. Evaluate every distinct small-n held-out state across multiple grid/mask
   seeds, a coherent persistent successor, numerical bounds, then larger-n
   held-out and closed-loop episodes. Never call training loss a success gate.
5. If this same-topology test fails, run a separately identified spatial
   fork: symmetric three-peg input groups and learned peg-summary sites
   feeding six action sites, with static role markers but no runtime
   precomputed top disk. Compare 8 channels first; only then test 12 channels
   as an explicit capacity ablation. Do not confound this fork with the
   first action-value test.

## Consequences and gate

The changed target and auxiliary channel are experimental model semantics,
not an accepted hardware contract. Distance labels require an oracle during
training/evaluation but must not enter runtime/export. A failure calls for
the controlled topology/capacity ablation, not P06. A passing teaching
curriculum still requires meaningful held-out and closed-loop Hanoi results
and an explicit human G3 decision before any freeze.
