# E02 — CartPole software readiness and G3E decision packet

Status: **G3E accepted 2026-10-07** via ADR-0009. The options below are the
original E02 decision evidence; the accepted outcome is conditional model2
under the recommended protocol. The ten-seed qualification has **not** run,
model2 is not frozen, and P06 has not started. This packet does not authorize
weight distribution or restart training. E01's host-neutral interface and the
immutable P03 reference remain the executable authorities. No historical
Hanoi P05 run or automation was resumed.

## Decision presented at G3E

Choose a checkpoint and explicit deployment/evaluation protocol, or require
more evidence before freezing one. In the same decision, choose the
cross-episode grid reset, ordinary versus diagnostic horizon, robustness
protocol, control thresholds, timing claim, reference-preserving optimization
boundary, and rights disposition. Numerical format and RTL realization remain
G4/G5 matters; G3E must not silently impose clipping or event sleeping.

### Checkpoint comparison (same reconstructed baseline arm)

The P03 30,000-action study used seeds 0–2, fresh initial grid per episode,
persistent grid between actions, 50–59 recurrent steps/action, 0.5 stochastic
cell-update rate, no noise/damage, and the source plant with **only** its
horizon extended. Score is accumulated cosine reward, not action count.

| Released checkpoint | Action counts, seeds 0/1/2 | Scores, seeds 0/1/2 | 30,000 censoring | Assessment |
|---|---:|---:|---:|---|
| model1 | 4,789 / 6,312 / 6,634 | 4,228.6 / 5,798.9 / 5,853.4 | 0/3 | Controls for thousands of actions, but none reached the released 10,001-action horizon in this arm. |
| model2 | 30,000 / 12,948 / 11,782 | 29,190.1 / 12,608.2 / 11,232.5 | 1/3 | Only candidate with all three trajectories beyond 10,001 actions; one score is a lower bound. |
| model3 | 2,962 / 774 / 1,073 | 2,260.1 / 734.7 / 567.3 | 0/3 | Not a credible long-control baseline on this evidence. |

These are **three reconstruction seeds**, not the paper's 100-run population.
The extended trajectories imply that model2 survived the earlier source
10,001-action point under this runner's otherwise identical prefix, but they
are not separately executed source-default episodes. Model2 is a candidate,
not a selected checkpoint or established success probability. Fixed
eight-action goldens for all three and the current ignored upstream clone
passed the P03 verifier on 2026-10-07: revision
`8c85be11b0838ea14ac51a11dac3098db43afed2`, 13 tracked artifact
SHA-256 identities, and three checkpoint operator/CartPole rollouts. The
three TFJS weight-blob hashes are pinned in
`reference/original_nca/checkpoint_hashes.json`; no bytes are copied here.

### Remaining protocol evidence and proposed choices

| Issue | Measured/source evidence | Recommended G3E choice and consequence |
|---|---|---|
| Episode-grid reset | Paper describes a random grid per simulation. Released one-element evaluation pool is not explicitly reset across episodes. P03's long study chose fresh grid per episode; its model2 1% *within-episode* reinit arm has only two post-hoc seeds (one censored), so it cannot settle the historical table. | Fresh seeded grid at each episode; persist it between all actions; no random in-episode reinitialization in the primary baseline. Label this a declared deployment protocol, not a reconstruction of the released multi-episode harness. Retain carry-over/reinit as separate diagnostics. |
| Horizon and robustness | Source `max_steps=10000` terminates after action 10,001 when balanced. Paper mean 13,273 cannot be obtained under that limit. P03 explicitly extended to 30,000; model2 deletion of both cart-position sites scored 487.3 ± 105.0 over 10 seeds versus paper 3,926.7 ± 2,383, a significant negative reconstruction result. | Primary FPGA demo uses the unchanged released horizon, no injected noise/damage/deletion. Keep 30,000-action, noise, damage and deletion as separately labeled software diagnostics, with exact intervention probabilities, seeds and censoring. Never fold diagnostic results into primary success claims. |
| Control acceptance | P03 baseline has three seeds/checkpoint; no held-out 10-seed source-default qualification or hardware quality measurement. | Pre-register a direct source-default software qualification before final weight freeze: seeds 10–19, fresh-grid/no-perturbation protocol, report every score/action count and fraction reaching 10,001. Proposed pass threshold: at least 8/10 horizon completions, **plus** all pinned fixed-checkpoint golden tests. This threshold is prospective, not already met. If it fails, return to G3E with measured alternatives; no automatic retraining. |
| Long-duration threshold | Only model2 reached 30,000 in one of three baseline seeds; 30,000 is a censoring cap, not a solved-task terminal. | Diagnostic only: report 30,000-cap survival fraction, score distribution and censoring over at least the three existing seeds; do not require a paper-table mean or claim 100-run equivalence. Any later robustness threshold needs a separately pre-registered sample/protocol. |
| Numerical range | All 1,916 released weights/checkpoint are finite. Observed weight extrema: model1 [-1.357552, 1.427202], model2 [-1.760053, 1.217146], model3 [-1.061512, 1.133169]. Original inference has no state clipping; output hidden channels 4/5 receive `+1` markers every NCA step, in addition to neural residuals. | Preserve float semantics at G3E; do not adopt training-only [-5,5] overflow penalty as an inference clamp. P07 must profile full state/delta/accumulator and long rollout ranges under the selected protocol before proposing fixed-point width, saturation or numerical equivalence. Finite weights do **not** bound recurrent state. |
| Timing | Plant's `tau=0.02` is simulated integration, not an FPGA inference deadline. No measured DE1-SoC end-to-end latency exists. | Step-synchronized simulated plant: wait for a complete 50–59-step controller decision, then apply one physics step. Log wall-clock latency/jitter; do not promise 20 ms real time before P12–P14 measurement. Strict pacing is a later separately evaluated option. |
| Rights | Upstream lacks a complete LICENSE/NOTICE grant; `setup.py` says `license='MIT'`, which alone is not a redistribution license. Source, TF checkpoints, and TFJS blobs are local ignored artifacts. | Allow local verification of hash-pinned weights only. Do not commit, publish, ship, or provide FPGA weight images externally until institutional/upstream rights review or explicit alternative authorization. P06 may prepare a local-only manifest but must not export restricted bytes into Git; if freeze requires a distributable image, this is a blocking rights gate. |

The proposed 8/10 control threshold is deliberately prospective: current
three-seed longevity data make model2 worth qualifying, not already qualified.
A qualification run is bounded and much smaller than repeating the paper
study; its estimated runtime is not asserted. No E02 retraining or new
long-control episode was run because the existing equal-protocol comparison
is sufficient to present checkpoint options, and a human choice is required
before spending on a freeze-qualification branch.

For rights, G3E can (1) permit **local-only** use of the hash-pinned ignored
weight source for a private lab prototype, with no weight bytes in Git or
shared images (recommended pending review); (2) defer any deployable weight
image until an explicit grant/institutional determination permits it; or
(3) request separately authorized clean-room training if the released
checkpoint cannot be used. Option 3 is not an E02 activity and would need
new control evidence. None of these options asserts that the upstream license
has been resolved by the `setup.py` metadata.

## Reference execution versus event variants

The baseline reproduces every logical NCA epoch, including its 50–59 count,
0.5 mask draws, residual, global clears, input clamps, output markers and
persistent state. A hardware optimizer may omit arithmetic or memory work
**only if** the complete post-epoch state, action/readout, finite-value
behavior and logical RNG assignment remain equivalent to the accepted
scheduled golden model; counting an enable signal alone is not work savings.
Mask-zero MAC skipping, for example, still has to preserve all subsequent
clear/clamp/marker writes and any implementation-relevant floating/fixed-point
exception behavior. P07–P12 must prove and measure a particular skip before
claiming an exact-preserving optimization.

State-change-triggered sleeping, threshold events, skipped logical epochs,
altered mask draws, maintenance timers, or new asynchronous update order
change the controller unless separately proven equivalent. They are **not**
the paper controller and are not a condition of the first CartPole freeze.
If later requested, they need a named derivative, separate deterministic
vectors, control-quality and work/energy measurements, and a human gate.
CartPole's single four-value observation and two-force output do not by
themselves demonstrate body-wide event locality or Clef causal closure.

## Viable G3E paths

| Path | Baseline schedule/risk | Later Clef and FPGA/ASIC implications |
|---|---|---|
| **A — Recommend conditional model2** under the protocol above; qualify on ten held-out source-default seeds before final P06 freeze. | Reuses the strongest measured released controller and avoids speculative training. Qualification or rights review can stop P06; no hardware competence is presumed. | Portable original 1,916-weight graph is a controlled ancestor, leaving event variants and Clef claims separate. Same weight/rights and numerical obligations on FPGA and ASIC. |
| B — Use model1 as an alternative released checkpoint, with the same held-out qualification. | Its 3/3 observed lifetimes were below 10,001, so the proposed horizon-completion criterion is unlikely to pass without changing the criterion or task. It may be useful if damage/deletion is prioritized over ordinary longevity, but that trade must be explicit. | Same graph/portability; changing checkpoint is low structural cost, high control-quality risk. Does not advance event or Clef evidence. |
| C — Defer any freeze and collect more checkpoint/reset/robustness evidence or resolve rights first. | Minimizes premature commitments but delays the one-semester FPGA baseline; no retraining is authorized by deferral alone. | Preserves every hardware option, but yields no new architecture/closure evidence while delayed. |

Model3 remains a documented candidate checkpoint, but its observed baseline
performance does not support recommending it for the long-control goal.
Recommendation A was accepted on 2026-10-07 as the **conditional** candidate.
The other options remain the considered alternatives, not active branches.
This choice does not permit historical Hanoi training, new CartPole training,
RTL, weight publication, or an event-gated derivative.

## Evidence limits and handoff

P03 reconstructed the released operator exactly at declared comparison
boundaries but did not reconstruct the complete historical 100-run paper
table. Historical table checkpoint, seeds, resolved dependencies and exact
evaluation reset behavior remain unknown. The present three-seed comparison
has no confidence interval suitable for a population guarantee. The
upstream verifier checks the local ignored clone and goldens, not licensing.

Under accepted ADR-0009, P06 must bind the actual checkpoint blob hash,
episode/reset/horizon protocol, ordered RNG draws or accepted generator,
goldens, and rights restrictions without editing `reference/original_nca/`.
P07 then measures recurrent numerical range and quantization rather than
silently imposing one. The ten-seed held-out qualification and exact goldens
must pass before final P06 freeze. Accepted decision:
`ADR-0009-cartpole-readiness-and-event-boundary.md`.
