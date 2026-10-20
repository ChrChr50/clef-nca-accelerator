# P05 Hanoi learnability and controls

## Scope and authority

This report records the P05 software experiment only. The immutable original
implementation in `reference/original_nca/` was not modified. Hanoi transitions
come exclusively from `reference/hanoi/environment.py`; oracle labels and
distances are imported only by training/evaluation code. The deployment-shaped
adapter, model, runtime, conventional control, model-export tree, and RTL tree do
not import the oracle.

## Fixed layout and corpus

`training/hanoi_nca/layout_v1.json` is the single configurable mapping for all
36 input cells and six action cells. Tests check the mapping and action order.
There are no collisions. The input and output centroids are `[15.5,
15.5277778]` and `[16,16]`; their offset is 0.6877455 cells. Across all 216
input/output pairs, Euclidean distance is 1.0 to 12.041595 (mean 5.925232),
Chebyshev distance is 1 to 9 (mean 5.268519), and the spread between the six
per-output mean Euclidean distances is 0.665142. This is a compact, nearly
centred layout, but it is not claimed to be exactly rotation/reflection
symmetric; the complete index-to-coordinate table is the JSON artifact.

The canonical corpus contains 29,520 cases and 24 terminal cases. All 29,496
nonterminal cases consumed the tuple-valued oracle API; the measured tuple size
was one in every case. Partitions use canonical P04 state hashes, not reset
seeds: n=1..6 use a fixed 80/10/10 hash bucket, n=7 is the unseen-n validation
set, and n=8 is the unseen-n test set. Exact identities, counts, reset mode,
goal, distance, and terminal status are in
`experiments/p05/dataset_manifest.json`.

## Declared experiment

- Runtime: Python 3.12.14, NumPy 2.3.5, PyTorch 2.14.0+cpu, eight PyTorch CPU
  threads on Windows 11.
- Seed: 105. The conventional control ran 300 epochs.
- NCA graph: the locked 1,916-parameter local graph. The six actions are six
  output cells in channel 0; the final local layer remains six channels.
- Spatial curriculum: 100 iterations with a fixed six-output random projection.
- Supervised imitation: 1,200 iterations, complete-set cross entropy,
  disk-count-balanced progressive n=1..6 sampling, fresh independent NCA grids.
- Recurrent schedule: uniformly sampled 20--24 steps. This is a deliberate P05
  candidate, not an alteration of the immutable original 50--59 schedule.
- Supervised fire rate: 1.0 as a deterministic optimization aid; DAgger and
  evaluation use the accepted stochastic 0.5 fire rate.
- Output marker: channels 4/5 are clamped to one at output cells after every
  update. This is a proposed Hanoi difference pending G3.
- DAgger: collection used coherent `(Hanoi snapshot, persistent NCA grid)`
  trajectories. Each optimization item retained its paired pre-observation NCA
  grid; it did not substitute a fresh grid.
- Evaluation: 72 fixed episodes spanning every n, goal, and seeded/standard/
  explicit reset mode. The host budget was `2*(2**n-1)`. Illegal attempts are
  exact transition no-ops but consume budget.
- RL was not run. Reward is deliberately absent pending G3.

The exact command and every curve point are retained in
`experiments/p05/results.json`; every episode and its initial/final hashes are
retained in `experiments/p05/episode_records.json`.

## Results

The conventional control established that the interface and labels are
learnable but also exposed leakage-safe generalization limits. Its loss fell
from 1.750808 to 0.054757. Accuracy was 99.962% on train, 54.785% on seen-n
validation, 60.559% on seen-n test, 31.976% on unseen n=7, and 32.342% on unseen
n=8. It completed 33/72 closed-loop episodes. A memorized exhaustive subset is
therefore not reported as generalization.

The NCA spatial curriculum had minimum MSE 0.133098 (first 0.206839, final
0.205583). Supervised imitation fell from cross entropy 1.785443 to 1.262405,
with a measured minimum of 0.539306 as progressively harder n values entered.
On deterministic hash-selected open-loop evaluation at stochastic fire rate
0.5, accuracy was 21.680% on 512 sampled train cases, 18.152% on all 303 seen-n
validation cases, 23.602% on all 322 seen-n test cases, 17.969% on 512 unseen
n=7 cases, and 16.016% on 512 unseen n=8 cases. Chance for balanced six-way
choice is approximately 16.7%. This is evidence of bounded learning, not a
successful general Hanoi policy.

The finite supervised NCA completed 13/72 coherent and 13/72 independent-grid
episodes. Coherent trajectories made 731 legal and 8,280 illegal attempts;
independent grids made 1,763 legal and 7,248 illegal attempts. The conventional
control made 7,690 legal and 1,019 illegal attempts. Completion and truncation
are recorded separately; terminal-at-reset cases are included and are not
misreported as learned solutions.

Persistent-state DAgger exposed a model-level numerical failure. Three
collection trajectories became non-finite after 70, 70, and 71 attempted moves;
the first optimization item then produced a non-finite gradient. The harness
aborted and rolled back to the last finite supervised checkpoint. The retained
checkpoint contains only finite arrays, SHA-256
`ffb1db3594e4257fa237975bf8da0134385f5f5b7f03bb65ecc87429ef87536b`.
The failed DAgger restart is not called a policy, budget, or hardware failure.

The 59-step marker probe measured raw accumulation at 58.9266--59.0906 and
whole-state maximum 59.0906. The clamp-one alternative measured exactly 1.0 at
the same cells and whole-state maximum 1.0 for the untrained probe. This
supports the proposed output-marker clamp, but does not by itself solve
long-horizon state growth elsewhere.

## Budget and feedback findings

Budgets `n` and `2**(n-1)` make many states unsolvable by construction. Both
`2**n-1` and `2*(2**n-1)` cover every corpus distance; the latter gives one
standard-bound's worth of room for policy mistakes. P05 recommends the double
standard budget for development, while continuing to report excess moves and
illegal attempts. Terminal status retains priority over truncation on the final
allowed attempt.

The primary model boundary remains 36 observations in and six raw scores out.
No legality mask, reward, distance, budget counter, terminal bit, target, or
oracle value enters the adapter/model/export boundary. Legality masking remains
only a future labeled ablation.

## Disposition

Learnability is established only in the bounded sense above: the conventional
control fits the training contract and the NCA improves below chance loss on
the curriculum. The present NCA is **not eligible for performance freeze**:
open-loop generalization is weak, closed-loop success is low, and coherent
long-horizon DAgger is numerically unstable. G3 should accept or revise the
contract choices but should not authorize P06 with this checkpoint as the
functional baseline. The finite checkpoint is retained as a reproducible
failed candidate/bring-up artifact, not as a frozen model.

## Hypothesis A continuation

The user authorized the recommended locked-graph stabilization continuation.
It restored mixed 50--59-step trials, aligned every phase to fire rate 0.5,
added exact peg-permutation augmentation, standard-first coherent trajectories,
training-only legality/top-disk/peg-role/subgoal losses, independent probes, and
a 510-decision stability soak. The experiment completed but failed every
acceptance predicate: 2/20 short-schedule and 0/20 long-schedule completions,
near-baseline held-out probes, and persistent-state growth to approximately
`2.066e36`. The graph remains non-freeze-eligible. Complete evidence is in
`docs/verification/P05_HYPOTHESIS_A.md` and
`experiments/p05_hypothesis_a/results.json`.
