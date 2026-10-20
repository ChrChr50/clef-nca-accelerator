# P03 CartPole long-duration empirical continuation

## Conclusion

The released checkpoints demonstrate long-duration CartPole control under the
original NCA operator, but this reconstruction does **not** reproduce the
paper's full 100-run performance statistics. The model-2 baseline has two
naturally terminated episodes near the paper's 13,273 mean score and one
episode censored at 30,000 actions. Noise-plus-input-damage is numerically
similar in three seeds. Other conditions, most clearly deleted cart-position
inputs, differ substantially. No checkpoint or seed was selected after the
fact as a substitute for the predeclared model-2 primary arm.

## Protocol and provenance

The executable protocol is `experiments/p03_long_duration/README.md` and
`run.py`. It imports the immutable `reference/original_nca/` implementation
and reads the three local upstream demo checkpoints; it does not vendor or
modify those checkpoints. Source revision, checkpoint hashes, and unresolved
license/dependency facts remain in `reference/original_nca/PROVENANCE.md` and
`checkpoint_hashes.json`. The run used Python 3.12.14 and NumPy 2.3.5.

The only deliberate environment-dynamics change is increasing the released
10,001-action termination horizon to a declared 30,000-action censoring cap.
The paper's baseline mean score of 13,273 cannot occur in the released HEAD
environment under its original horizon. Every episode uses 50–59 NCA steps
per action, a 0.5 stochastic cell-update rate, a persistent grid within the
episode, and a fresh grid between episodes. Historical seeds, original resolved
TensorFlow/Gym/NumPy versions, table checkpoint identity, exact RNG streams,
and the paper's precise uniformly distributed damage probability are not
available. The chosen probability is 1/220 per NCA step. The upstream
notebook's optional 1% grid reinitialization and cross-episode pool persistence
are additional unresolved protocol differences.

The paper reports accumulated **score**, not simply action count. The tables
below therefore compare summed CartPole reward and report duration only in
the raw JSONL. Values are mean ± sample standard deviation; paper values are
100-run statistics except the two-position deletion result, which is 25-run.
Three-run values are exploratory, not a statistical equivalence test. A
censored mean is only a lower bound, and its displayed SD is not an unbiased
estimate of the uncensored distribution.

| Primary model-2 condition | Paper score | Local score | N | Censored |
|---|---:|---:|---:|---:|
| No noise, no damage | 13,273 ± 11,905 | ≥17,676.9 ± 9,994.4 observed | 3 | 1 |
| No noise, damage after input | 2,598.2 ± 2,241 | 5,075.0 ± 3,995.7 | 3 | 0 |
| No noise, uniform damage | 391.6 ± 283 | 1,210.7 ± 986.4 | 10 | 0 |
| Noise, no damage | 1,296.3 ± 899 | 5,580.2 ± 6,889.7 | 3 | 0 |
| Noise, damage after input | 739.7 ± 473 | 849.8 ± 115.8 | 3 | 0 |
| Noise, uniform damage | 345.7 ± 214 | 772.0 ± 524.8 | 10 | 0 |
| Delete both cart-position cells; no noise/damage | 3,926.7 ± 2,383 | 487.3 ± 105.0 | 10 | 0 |

Model-2 baseline per-seed scores were 29,190.1 (censored at 30,000 actions),
12,608.2 (12,948 actions), and 11,232.5 (11,782 actions). The model-2
noise-plus-input-damage scores were 946.4, 721.4, and 881.6. The deletion
scores across ten seeds all lay between 338.8 and 621.7, so that mismatch is
not driven by a single unlucky episode.

Checkpoint sensitivity was large. Under the same baseline protocol and seeds
0–2, model 1 scored 5,293.6 ± 922.8 and model 3 scored 1,187.3 ± 932.8,
both uncensored. As a post-hoc diagnostic, model-1 deletion scores were
1,952.0, 4,658.6, and 623.9; this does not resolve the table-checkpoint
identity. The optional notebook-style 1% reinitialization arm is separately
labeled exploratory in its JSONL and is not mixed with the primary table. Its
two completed baseline seeds scored 29,166.6 (censored at 30,000 actions)
and 19,027.0 (19,660 actions), compared with 29,190.1 and 12,608.2 without
the within-episode resets. The third exploratory seed was not run, so this
ablation has no meaningful population estimate.

## Validation and exact commands

All episode-level action hashes, scores, duration, seed, censoring flags, and
runtime versions are saved in `experiments/p03_long_duration/*.jsonl`; active
episodes have resumable progress snapshots. The following commands were run:

```text
.venv-p05\Scripts\python.exe -m unittest discover -s reference/original_nca/tests -v
.venv-p05\Scripts\python.exe reference/original_nca/tools/verify_upstream.py --upstream self-organized-control
.venv-p05\Scripts\python.exe -m unittest experiments.p03_long_duration.test_run -v
.venv-p05\Scripts\python.exe experiments/p03_long_duration/run.py --model model1 --conditions baseline --seeds 0 1 2 --cap 30000 --output experiments/p03_long_duration/model1.jsonl
.venv-p05\Scripts\python.exe experiments/p03_long_duration/run.py --model model2 --conditions baseline --seeds 0 1 2 --cap 30000
.venv-p05\Scripts\python.exe experiments/p03_long_duration/run.py --model model3 --conditions baseline --seeds 0 1 2 --cap 30000 --output experiments/p03_long_duration/model3.jsonl
.venv-p05\Scripts\python.exe experiments/p03_long_duration/run.py --model model2 --conditions noisy_update damage_after_input noisy_damage_after_input uniform_damage noisy_uniform_damage delete_cart_position --seeds 0 1 2 --cap 30000 --output experiments/p03_long_duration/model2_perturbations.jsonl
.venv-p05\Scripts\python.exe experiments/p03_long_duration/run.py --model model2 --conditions uniform_damage noisy_uniform_damage --seeds 3 4 5 6 7 8 9 --cap 30000 --output experiments/p03_long_duration/model2_uniform_extension.jsonl
.venv-p05\Scripts\python.exe experiments/p03_long_duration/run.py --model model2 --conditions delete_cart_position --seeds 3 4 5 6 7 8 9 --cap 30000 --output experiments/p03_long_duration/model2_deletion_extension.jsonl
.venv-p05\Scripts\python.exe experiments/p03_long_duration/run.py --model model1 --conditions delete_cart_position --seeds 0 1 2 --cap 30000 --output experiments/p03_long_duration/model1_deletion.jsonl
.venv-p05\Scripts\python.exe experiments/p03_long_duration/run.py --model model2 --conditions baseline --seeds 0 1 2 --cap 30000 --reinit-probability 0.01 --output experiments/p03_long_duration/model2_reinit_ablation.jsonl
.venv-p05\Scripts\python.exe experiments/p03_long_duration/summarize.py experiments/p03_long_duration/*.jsonl
```

Observed validation: 17/17 original-reference unit tests passed; upstream
revision, 13 artifact hashes, and three checkpoint operator/CartPole rollouts
passed; the new runner's all-condition bounded parity test passed. The 100-step
model-1 smoke episode exactly matched the earlier P03 action SHA-256
`077dd8039aea1344e213f0a8046f26322dd6417a0549d51bd2514b540147b4f9`
and reward 99.24984243196987. No retraining was attempted or claimed.
The exploratory reinitialization command was stopped after two completed
episodes to bound CPU use; it exited on interruption, with both completed
records saved and no partial episode counted.
Across the eight retained JSONL files there are 53 distinct, completed
model/condition/seed/horizon/reset-arm episode records, of which two hit the
30,000-action censoring cap. The summarizer groups the reset arm separately.

## Interpretation

The original NCA algorithm and released weights are executable and can
control CartPole for more than 10,000 actions. That is stronger empirical
evidence than the prior 100-step-censored P03 attempt. It is **not** evidence
that all published robustness statistics were reproduced. Historical protocol
and checkpoint ambiguities remain, and the large deletion mismatch is a real
negative result for this declared reconstruction. The immutable exact
algorithmic reference and G2/Hanoi interface decisions are unchanged.
