# G3 decision packet: Hanoi training and deployment boundary

> Historical-scope notice (2026-10-06): retained for provenance, not the active forward implementation plan. ADR-0007 and docs/architecture/EMBODIED_NCA_VISION.md supersede task-specific choices. Original-reference evidence and dated experimental decisions remain preserved; no new embodied acceptance or model freeze is implied.

## Gate status

**Awaiting final functional-freeze decision.** The user authorized a bounded
v2 P05 architectural continuation on 2026-09-29, but did not freeze a model.
No P06 export, quantization, or hardware implementation has begun.

The v2 continuation implemented a structured disk-major input layout,
source/destination output matrix, eight-channel local graph, immutable marker
channels, and an inference-time bounded residual. Its first recorded run
completed 1/12 standard-start n=1..4 episodes and achieved 25/194 held-out
fresh-grid action accuracy. The 510-decision state soak was bounded at 5 by
the declared clipping rule. It is a negative policy result, not a functional
freeze. See docs/verification/P05_V2_RELATIONAL_NCA.md and accepted
experimental ADR-0004.

The user authorized the recommended Hypothesis A locked-graph stabilization
experiment. It is complete and negative: the corrected training process
remained finite, but deployed persistent state was unbounded, the policy
completed 2/20 short and 0/20 long diagnostics, and held-out probes did not
establish the requested concepts. See
`docs/verification/P05_HYPOTHESIS_A.md`. This strengthens the recommendation
not to freeze the checkpoint; it does not authorize a graph change or P06.

## Immutable inputs to this gate

- ADR-0002 fixes `N_MAX=8`, the 36-value observation order, six ordered
  unmasked actions, persistent between-move state, and episode reset.
- P04 fixes transition, legality/no-op, serialization, hashing, terminal and
  truncation semantics. It does not define reward or a default budget.
- The original paper implementation remains immutable under
  `reference/original_nca/`.
- The local derivative graph remains 1,916 parameters:
  `3x3x6->20`, ReLU, `1x1 20->30`, ReLU, `1x1 30->6`, linear.

## Measured recommendation

Accept the following interface/training contract, but **do not freeze the
current checkpoint and do not begin P06 yet**:

1. Keep raw P04 observations (binary fields plus `n/8`) with redundancy one.
2. Keep raw six-cell channel-0 scores and complete-set cross entropy with unit
   target mass. Do not inherit the paper's DQN `/0.01` scale.
3. Retain terminal cases in manifests/evaluation and exclude them from action
   loss because they have no target action.
4. Use no reward and no RL in the baseline until a later explicit decision.
5. Use no separate illegal-action loss and expose no legality feedback to the
   model. Report illegal attempts; reserve masking/feedback for labeled
   ablations.
6. Use host budget `2*(2**n-1)` for development. It covers every oracle
   distance while preserving the cost of illegal no-ops.
7. Keep 20--24 recurrent steps as the current compact-layout software-training
   candidate; separately retain 50--59 as an original-schedule comparison.
   Do not freeze a hardware epoch count until stable closed-loop evidence exists.
8. Change output-cell hidden channels 4/5 from raw `+1` accumulation to
   clamp-one after each update. The 59-step probe measured approximately 59
   under accumulation and exactly one under clamping.
9. Keep the host-visible runtime boundary at observations in/six scores out.
   The supervisor may observe legality, terminal/truncated, budget, hashes, and
   training labels, but none are policy inputs or export content.
10. Continue with coherent persistent-grid DAgger as the primary closed-loop
    method and retain independent-grid sampling only as a paper-style control.

The full machine-readable proposal is
`training/hanoi_nca/difference_manifest.json`. Evidence and limitations are in
`docs/verification/P05_HANOI_LEARNABILITY.md` and `experiments/p05/results.json`.

## Why the model is not freeze-eligible

The NCA did learn measurable bounded signal/classification behavior, but its
seen-n open-loop test accuracy is 23.602%, it completed only 13/72 evaluation
episodes, and coherent DAgger encountered non-finite persistent states around
70 moves. The harness rolled back to a finite supervised checkpoint. Freezing
that checkpoint as the functional golden model would turn a known model defect
into downstream quantization and RTL noise.

## Options

### Option A — Accept the contract, require P05 stabilization before freeze (recommended)

Accept ADR-0003's interface choices and retain the current checkpoint as failed
evidence. Authorize a bounded P05 continuation to measure explicit
long-horizon stabilization alternatives (for example, a declared state-range
penalty versus another training-only stabilization), repeat coherent DAgger,
and return to G3 with a finite model that meets preregistered open- and
closed-loop thresholds. P06 remains blocked.

This option keeps model failure separate from quantization/hardware work and
does not weaken the unmasked runtime contract.

**Measured update:** the authorized first stabilization continuation has been
executed and did not meet its acceptance criteria. Repeating Option A now
requires a new bounded rationale rather than assuming more iterations suffice.

### Option B — Freeze the finite checkpoint for structural bring-up only

Accept the same interface choices and freeze SHA-256
`ffb1db3594e4257fa237975bf8da0134385f5f5b7f03bb65ecc87429ef87536b`
solely to exercise export/quantization. It must be labeled nonfunctional and
cannot support Hanoi performance claims. This reduces schedule latency but
risks redoing P06-P12 when training changes.

### Option C — Revise one or more G3 choices

Select different recurrent steps, marker behavior, feedback, loss, budget, or
normalization. Any relaxation such as legality masking must remain a labeled
fallback/ablation, not replace the primary unmasked result. Material changes
must be reflected in ADR-0003 and the difference manifest before more training.

## Decision requested

The user selected an experimental version of Option C by authorizing v2. That
choice authorized implementation and measurement within P05, not acceptance
of ADR-0003 or a functional checkpoint. The original A/B/C alternatives
above remain the historical first G3 packet.

### Updated G3 decision after v2

The exact next decision is whether to authorize another **bounded P05
diagnostic** or to stop software model development. Viable options:

1. **Recommended: diagnostic decomposition before another architecture fork.**
   Test tiny-set overfit, measured input-to-output influence/gradient reach,
   and a controlled v1/v2 factorization of layout, channel count, and bounded
   update. This adds P05 time but avoids exporting another chance-level model.
   It changes neither the accepted host interface nor later Clef claims.
   FPGA/ASIC portability is unaffected until a new operator is chosen.
2. **Structural-only nonfunctional freeze.** A finite v2 checkpoint and
   bounded operator can exercise model export and later hardware arithmetic,
   but the accelerator must be labeled nonfunctional as a Hanoi solver.
   It advances hardware schedule at the cost of likely rework and provides
   no evidence for any later Clef claim. Portable implementation would need
   a new eight-channel numerical/RTL contract.
3. **Pause the NCA training branch for redesign.** Preserve all P05 evidence
   and reconsider representation, topology, or the bounded task objective.
   This defers the guaranteed baseline accelerator and hardware stages;
   no claim or portability benefit follows without further measured work.

ADR-0003 remains an unaccepted final G3 draft. ADR-0004 only authorizes the
completed v2 experiment. Until the user makes a new final G3 choice, P05
remains at G3 and P06 is unauthorized.
