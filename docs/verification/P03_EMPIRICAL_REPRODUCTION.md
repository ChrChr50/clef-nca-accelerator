# P03 empirical CartPole reproduction report

## Status

Empirical reproduction was attempted with the released model 1 checkpoint,
clean-room CartPole dynamics, explicit recorded seeds, the released 50-through-59
NCA-step schedule, persistent grid state, and the raw Python I/O semantics.
These are new measurements, not the paper's historical runs.

## Paper targets

The paper reports 100-run mean +/- standard deviation scores of:

| Update noise | No damage | Damage after input | Uniformly distributed damage |
|---|---:|---:|---:|
| Off | 13,273 +/- 11,905 | 2,598.19 +/- 2,241 | 391.6 +/- 283 |
| On | 1,296.3 +/- 899 | 739.7 +/- 473 | 345.7 +/- 214 |

It also reports eight individual input-deletion experiments over 25 runs with
noise and damage, and deletion of both cart-position cells at 3,926.7 +/- 2,383
over 25 runs without noise or damage.

## Released-artifact blockers

The exact historical experiment cannot be reconstructed from the release:

- no training or evaluation seeds are recorded;
- TensorFlow, Gym, NumPy, CUDA, cuDNN, and GPU versions are unpinned;
- the released environment terminates after step 10,000, making the reported
  13,273-step mean impossible under current HEAD;
- the released test loop does not explicitly reset its one-element NCA pool
  between episodes, while the paper says a random grid initializes each
  simulation;
- the paper does not identify unambiguously which shipped model generated each
  table, and the notebook defaults to model 2 while the demo labels three models;
- the exact conversion relationship between archived TensorFlow checkpoints and
  browser checkpoints is not recorded;
- the per-step probability used for "one uniform damage every four input
  updates" is not stated; this attempt uses `1/(4*55) = 1/220`.

## Bounded attempt

To keep this stage reproducible on a CPU-only development machine, the recorded
attempt used model 1, seeds 0-2, and a 100-environment-step censoring cap. It
covered baseline, update noise, damage after input with probability 0.5,
uniform damage with per-NCA-step probability 1/220, both damage modes combined
with update noise, all eight single-input deletions under noise and damage, and
deletion of both cart-position inputs without noise/damage.

The exact command was:

```text
python reference/original_nca/tools/run_empirical.py --upstream self-organized-control --model model1 --episodes 3 --max-steps 100
```

The complete per-seed results, reward sums, action hashes, censoring flags, and
runtime versions are retained in
`reference/original_nca/empirical_results.json`.

Scores at 100 are right-censored and must not be compared as uncensored paper
scores. Observed episode lengths (mean +/- sample standard deviation, with
minimum and maximum) were:

| Condition | N | Steps |
|---|---:|---:|
| Baseline | 3 | 100.0 +/- 0.0 (100-100) |
| Noisy update | 3 | 100.0 +/- 0.0 (100-100) |
| Damage after input | 3 | 100.0 +/- 0.0 (100-100) |
| Noisy + damage after input | 3 | 100.0 +/- 0.0 (100-100) |
| Uniform damage | 3 | 100.0 +/- 0.0 (100-100) |
| Noisy + uniform damage | 3 | 100.0 +/- 0.0 (100-100) |
| Delete both cart-position cells, no noise/damage | 3 | 100.0 +/- 0.0 (100-100) |
| Delete input 0, noise + damage | 3 | 100.0 +/- 0.0 (100-100) |
| Delete input 1, noise + damage | 3 | 100.0 +/- 0.0 (100-100) |
| Delete input 2, noise + damage | 3 | 100.0 +/- 0.0 (100-100) |
| Delete input 3, noise + damage | 3 | 100.0 +/- 0.0 (100-100) |
| Delete input 4, noise + damage | 3 | 100.0 +/- 0.0 (100-100) |
| Delete input 5, noise + damage | 3 | 34.67 +/- 10.69 (28-47) |
| Delete input 6, noise + damage | 3 | 100.0 +/- 0.0 (100-100) |
| Delete input 7, noise + damage | 3 | 89.67 +/- 17.04 (70-100) |

Because 14 of 15 condition summaries include censored episodes and N=3, these
measurements establish executable coverage and qualitative perturbation response
only. They do not validate the paper's numerical means or tolerances.

### Statistical comparison rule and result

The intended comparison unit is episode length, reported as mean, sample
standard deviation, minimum, maximum, seed list, and censoring status for every
condition. A paper-comparability pass would require uncensored samples under a
declared environment horizon and a 95% confidence interval for the reproduced
mean that overlaps the paper's reported mean plus or minus one reported standard
deviation. No condition is assigned that pass here: `N=3` is exploratory, 14
condition summaries contain right-censored episodes, historical seeds and core
dependency versions are unavailable, and the released 10,001-step maximum is
incompatible with the paper's 13,273-step baseline mean. These are recorded
failure cases, not silently widened tolerances.

The clean-room run used Python 3.12.14 and NumPy 2.3.5. The known historical
metadata is Python 3.8.1, Keras 2.2.4-tf, and TensorFlow.js Converter 3.7.0;
historical TensorFlow, Gym, NumPy, CUDA, cuDNN, and seed values remain unknown.

## Training attempt

Retraining was not represented as successful reproduction. The historical
dependency lock and seeds do not exist, and installing a modern TensorFlow/Gym
stack would create a new training environment rather than restore the original.
The curriculum target, pool sampling/commit behavior, damage rule, DQN interface,
and 50-through-59 schedule are nevertheless executable and regression-tested.

## Interpretation

The operator-level reference is accepted; the paper-level empirical claim is
only partially reproduced. Longer uncensored statistics require a separately
approved reconstruction protocol that either obtains the authors' historical
environment/seeds or labels every changed dependency and horizon as a new
replication study.

## Later long-duration continuation

On 2026-10-01, a separately labeled 30,000-action-horizon reconstruction was
run against the released checkpoints, with per-episode evidence and explicit
censoring. See `P03_LONG_DURATION_CONTINUATION.md`. It demonstrates episodes
longer than 10,000 actions but does not reproduce all paper robustness means;
in particular, the cart-position deletion result remains far below the paper
in the declared ten-seed model-2 arm. This later evidence does not alter the
immutable original operator contract or turn the historical 100-run table into
a verified reproduction.
