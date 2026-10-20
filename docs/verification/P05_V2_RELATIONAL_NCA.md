# P05 v2 relational-layout and bounded-state NCA experiment

## Scope and disposition

The user authorized a separately named P05 v2 architecture experiment on
2026-09-29. This did not alter the immutable CartPole reference, the accepted
P04 Hanoi environment, or the previously measured six-channel P05 candidate.
The v2 software architecture was implemented and regression-tested. Its first
recorded training run was finite and bounded, but **failed policy competence**.
It is not eligible for a functional model freeze or P06.

## Concrete architecture

- The logical P04 observation remains 36 values for n=1..8, and the six
  directed actions remain in their accepted order. The host still owns
  transitions, illegal no-ops, budget, reset, and terminal status.
- Layout v2 puts the four values for disk d at row 11+d, columns 12..15.
  Goal bits and normalized count occupy row 19, columns 12..15. The six
  off-diagonal action cells are at (17+source,16+destination).
- State is 32x32x8. Channels 0..5 are evolving state, with channel 0 read
  at output cells as raw action scores. Channel 6 identifies input sites;
  channel 7 identifies output sites. The latter two are cleared and rewritten
  each epoch, not allowed to accumulate as hidden state.
- The shared learned rule is zero-padded 3x3x8->20/ReLU,
  1x1x20->30/ReLU, 1x1x30->8/linear, all biased. It has exactly 2,338
  parameters. All cells compute from the same old grid each epoch.
- A new observation is clamped before the first local delta in each
  decision. Each epoch applies one Bernoulli mask bit per cell across all
  eight delta channels, clips the residual to [-5,5], then clamps the inputs
  and rewrites the two marker channels. The same bound is used in training
  and inference. The grid persists between moves and resets between
  episodes.
- No oracle, legality signal, reward, distance, or explicit Hanoi algorithm
  enters the deployment-shaped adapter, model, or runtime.

The machine-readable contract is
training/hanoi_nca/difference_manifest_v2.json. The coordinates are in
training/hanoi_nca/layout_v2.json. The v2 NumPy adapter and PyTorch runtime
agree exactly for tested residual/rewrite vectors.

## Geometry and arithmetic

| Analytic property | Existing P05 v1 | v2 |
|---|---:|---:|
| Input/output collisions | 0 | 0 |
| Mean input-output Chebyshev distance | 5.269 | 4.556 |
| Maximum input-output Chebyshev distance | 9 | 8 |
| Mean input-output Euclidean distance | 5.925 | 5.206 |
| Spread of per-output mean Euclidean distances | 0.665 | 1.452 |
| Grid-centroid offset | 0.688 | 4.610 |
| Shared parameters | 1,916 | 2,338 |
| MACs per cell per epoch | 1,860 | 2,280 |

The v2 grouping and shorter reach come with worse output-distance balance.
Those geometry values are calculated from coordinates, not model performance
or hardware timing.

The chosen 30->8 final layer still computes deltas for marker channels 6/7
that the rewrite immediately discards. That is 62 ineffective parameters
and 60 ineffective MACs per cell per epoch. It is retained to match the
user-authorized v2 graph and to keep this run interpretable; a future
six-working-delta head would be a separately declared efficiency change.

## Recorded training and evaluation

The run used Python 3.12.14, NumPy 2.3.5, PyTorch 2.14.0+cpu, seed 305,
batch size 4, stochastic fire rate 0.5, and 20..24 local epochs per
decision. Source-occupancy/goal routing ran for 80 iterations, six-action
legality for 80, oracle optimal-action imitation for 320, coherent
teacher-forced three-decision training for 80, and coherent on-policy
three-decision DAgger for 80. The action loss consumed complete optimal-action
sets; terminal states contributed no action target. The hash-identity
80/10/10 rule was applied across n=1..8, and training contains every n and
goal. Small held-out strata can be empty (including n=1 in this run);
the partition manifest records exact coverage. Training trajectories
stopped before a held-out state identity was presented.

| Measured result | Value |
|---|---:|
| Routing MSE, first -> last recorded | 0.3269 -> 0.1920 |
| Legality BCE, first -> last recorded | 0.7785 -> 0.6648 |
| Imitation CE, first -> last recorded | 1.8777 -> 1.7071 |
| Teacher-sequence CE, first -> last recorded | 2.1334 -> 1.7476 |
| DAgger-sequence CE, first -> last recorded | 1.8729 -> 1.8786 |
| Fresh-grid train action accuracy | 27/215, 12.56% |
| Fresh-grid validation action accuracy | 30/183, 16.39% |
| Fresh-grid test action accuracy | 25/194, 12.89% |
| Standard-start n=1..4 persistent episodes completed | 1/12 |
| Legal / illegal attempts in those episodes | 12 / 143 |
| 510-decision persistent-state soak | finite, max absolute state 5 |

Open-loop cases were sampled across n/goal strata, with small strata
exhausted. The standard-start closed-loop diagnostic covered all three
goals for n=1..4 only. No closed-loop success result is claimed for n=5..8.
The bounded soak varied observations while retaining one grid; it tests state
range and replay behavior, not task completion. The runner recorded
9261.35 seconds elapsed for the complete CPU experiment; that is not an
FPGA/ASIC speed measurement.

All five phase checkpoints contained finite arrays. The final
after_dagger_sequence.npz SHA-256 is
3260d6bdbbc3d08cd1232d103b930cb2d01c0c4034a4e3491f3d334e7feb9714.
Exact configuration, phase curves, partition coverage/digests, checkpoint
hashes, stratified action metrics, episode records, and soak checkpoints
are retained under experiments/p05_v2/.

## Interpretation and limitations

Explicit inference clipping fixed the observed unbounded-state failure for
this test, but the policy remained approximately chance-level and made many
illegal moves. This run does not isolate which of the simultaneous v2 changes
helps or hurts; it also does not show that eight channels are sufficient or
insufficient. The first run used a modest sampled curriculum and did not
establish tiny-set overfit, exhaustive held-out correctness, full n=1..8
closed-loop performance, robustness across seeds, or fixed-point behavior.
The 510-decision bound is expected from clipping and is not evidence of
semantic long-term stability.

The next scientific decision is whether to authorize a tightly bounded
P05 diagnosis that separates signal transport, spatial layout, channel
capacity, and clipping effects. It is not to pass this checkpoint to P06
as a functional golden model.

## Reproduction and validation

Recorded training command:

    .venv-p05/Scripts/python.exe training/hanoi_nca/run_v2.py --output experiments/p05_v2 --seed 305 --batch-size 4 --step-min 20 --step-max 24 --routing-iterations 80 --legality-iterations 80 --imitation-iterations 320 --teacher-sequence-iterations 80 --dagger-sequence-iterations 80 --sequence-decisions 3 --eval-cases-per-split 256 --eval-max-n 4 --soak-moves 510

Observed regression results:

- P03 original-NCA suite: 17/17 passed.
- P04 Hanoi suite: 11/11 passed, including exhaustive 29,520-state and
  177,120-action checks.
- P05 suite: 18/18 passed, including six new v2 layout/operator/manifest tests.
- Repository smoke, oracle firewall, Python compilation, and diff-format
  checks passed. The five v2 checkpoint arrays were separately scanned
  and found finite.

No RTL, quantization, FPGA, or ASIC result was produced.
