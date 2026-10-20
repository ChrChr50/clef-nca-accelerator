# P05 baseline reversion and architecture options — 2026-09-30

Status: design review; no active training, model freeze, G3 acceptance, or P06.

## What was restored

The active P05 experiment is again the trial-4 v6 configuration: spaced
`layout_v6.json`, eight-channel/2,338-parameter `v2_model.py`, smooth-bounded
`v4_runtime.py`, and `run_v3_teaching.py` with the gated relay, combination,
routing, legality, then softmax-imitation teaching flow. These source artifacts
were not modified by the v7 teaching experiment. The 36-value P04 observation,
six unmasked output actions, P04 transition authority, and oracle firewall are
unchanged. The v7 action-value runner remains only as a separately named
historical experiment; it is not the active baseline.

The exact trial-4 weights at its ~95%/~96% legality and ~44%/~48% final
two-disk imitation measurements **cannot be restored**. Their bulky run
directory, including the stage-10 and final resume checkpoints, was removed
under the earlier user-requested replacement policy. The retained 10,631-byte
`experiments/p05_v6_verified_warmup_seed.npz` is only the passed stage-8
36-input combination checkpoint (SHA-256
`af8ece9a7e2ed21d46a6a1574c2077d9ea8ba4446857e8c58dd5187e83835147`).
The `experiments/p05_v2/after_legality.npz` file belongs to a different,
earlier v2 layout/teaching run and is not a substitute for trial 4. Trial-4
metrics and its last checkpoint hash remain in
`P05_V3_GATED_TEACHING_CONTINUATION.md`. Exact continuation would require
the missing checkpoint; retraining can reproduce the method, not claim the
identical weight state.

The v7 action-value run was stopped at full-length stage 2 iteration 2,250
(4,250 new-run updates). Its last checkpoint SHA-256 is
`ef510abad673856c6230d51b3a10d801f64195c075242643c11362ffff1b159a`.
Latest fresh/coherent-successor action accuracy was 0/0.375, legality-bit
accuracy 0.4375/0.604167, and maximum absolute grid state 3.139/3.257.
The stopped data is labeled `experiments/p05_v7_stopped/`; its progress file
explicitly records the stop. The hourly teaching continuation was paused to
prevent automatic restart while the architecture is reconsidered.

## Architecture-first hypotheses for the next authorized experiment

1. **Peg-centric spatial topology at eight channels.** Keep the same P04
   36-input meanings and six actions, but arrange each disk's three peg bits
   in three separated, comparable peg columns/regions with mutable relay
   space. Provide learned, mutable summary sites for each peg and place each
   directed action output where the source and destination summaries can
   converge. Static role/location markers may identify these sites, but no
   runtime top-disk, legality, oracle distance, or correct-action bit is
   precomputed. The hypothesis is that the old layout makes the NCA infer
   ordered peg relationships through a spatially arbitrary bottleneck.
   The peg summaries alone would mainly help **legality**, not optimality:
   the shortest next move also depends on the largest disk whose goal is
   unresolved and on the resulting subgoal for smaller disks. A connected,
   mutable disk-order lane from large to small should let the shared rule
   propagate a learned goal-conditioned subgoal alongside peg summaries.
   This is wiring/role structure, not a hand-coded Hanoi recurrence or a
   privileged next-action signal.
2. **Capacity ablation only if topology alone fails.** Test 12 evolving/
   marker channels as a separate graph change after the eight-channel
   topology trial. More channels might retain disk-order, peg occupancy,
   goal, and action comparison information simultaneously, but increase
   parameters and eventual hardware cost. Do not treat this as a free
   improvement or mix it into the first topology comparison.
3. **Separate teaching ablations later.** Action-value targets, an auxiliary
   legality channel, coherent state/grid pairing, or different learning rate
   may be useful, but the v7 run changed these together and was not a clean
   test. They must not be silently called architecture improvements.

For the first topology comparison, run the **same v6 teaching algorithm** on
the old and proposed layouts: same initialization policy, relay/combination/
routing/legality/imitation losses, Adam rate, stochastic mask, 50–59 policy
steps, training partitions, budgets, and pass criteria. Re-run spatial warm-up
on the new layout; weights cannot be copied as an equivalent warm-up when
coordinates move. Report the historical 48-draw validation for continuity
*and* a separate all-distinct-state/multi-grid-seed evaluation, with the
latter controlling any learnability claim. Then require meaningful held-out
larger-n and closed-loop P04 episode evidence. This tests whether changing
communication geometry helps without also changing the teacher.

No architecture can guarantee CartPole-like convergence on Hanoi. A useful
next result would be a reproducible improvement in distinct-state action
accuracy and full episodes over the v6 comparator; numerical boundedness,
legality accuracy, and training loss alone are insufficient. The spatial
layout/marker details and possible channel expansion require an explicit
unaccepted ADR before any final G3 selection.

After the stop/relabel, regressions passed: P03 17/17, exhaustive P04 11/11,
P05 30/30, oracle firewall, and `git diff --check`. The trainer process is
absent. No new training was launched during this reversion.
