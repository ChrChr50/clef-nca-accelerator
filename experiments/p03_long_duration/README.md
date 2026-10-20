# Long-duration CartPole checkpoint study

This is a **new empirical reconstruction**, outside the immutable
`reference/original_nca/` contract. It is not a claim of bitwise replay of the
paper's training or historical evaluation.

Initial protocol (the released-checkpoint arms were launched before their
outcomes were known):

- Use the three released TensorFlow.js demo checkpoints, pinned by
  `reference/original_nca/checkpoint_hashes.json`; evaluate baseline seeds
  0, 1, and 2 on each checkpoint. The notebook's default is model 2, so use
  that checkpoint for the six published longevity/noise/damage conditions and
  the two-cart-position deletion condition, also at seeds 0, 1, and 2.
- Each episode begins with a seeded random 32x32x6 grid. The grid persists
  between CartPole actions and resets between episodes. Use 50-59 NCA updates
  per action, a 0.5 per-cell update probability, and the original observation
  scaling, readout, damage geometry, and CartPole dynamics.
- The released CartPole terminates after action 10,001. Explicitly raise only
  that horizon to 30,000 actions; treat a run reaching 30,000 as right-censored.
  This is necessary to investigate a paper mean score above the released cap.
- Use one NumPy `RandomState(seed)` for environment and NCA stochastic draws,
  plus the separately seeded initial grid already used in the P03 clean-room
  harness. These are declared reconstruction choices, not known historical RNG
  streams.
- At each CartPole action, damage-after-input is applied with probability 0.5.
  Uniform damage is applied after each NCA update with probability 1/220, an
  approximation to the paper's “one damage every four input updates.” Noise is
  uniform `[-0.01, +0.01]` added to the local delta before the stochastic mask.
- Report accumulated CartPole reward (“score”) and action count separately.
  The paper's main table is a score table, not merely a duration table.
- Do not select a checkpoint or seed for closeness to the paper table after
  observing outcomes. This small-N study is exploratory; it cannot establish
  agreement with a 100-run distribution.

An important unresolved distinction: the upstream notebook configures a 1%
pool reinitialization chance at each prediction, and its test loop does not
explicitly reset the one-element pool between episodes, whereas the paper
describes a fresh grid at the start of each simulation. This study keeps a
persistent grid *within* each episode and a fresh grid *between* episodes,
without random within-episode reinitialization. The difference can materially
change long-run outcomes. The historical evaluation seeds, exact dependency
versions, and table checkpoint identity are unavailable.

After observing the first baseline outcomes and re-reading the notebook, we
added an **exploratory, post-hoc** `--reinit-probability 0.01` arm for model 2.
It approximates the notebook's within-episode pool-reset setting, but does not
reconstruct its separate TensorFlow/Gym/NumPy RNG streams or persistent pool
across episodes. It must not be used to select a preferred result merely
because it is closer to the paper.

We also extended model-2 uniform-damage and two-position-deletion arms from
seeds 0–2 to seeds 0–9 after seeing high variability or a large mismatch,
and ran model-1 two-position deletion at seeds 0–2 as a post-hoc checkpoint
sensitivity check. These extensions are diagnostic, not pre-registered
confirmation. The reinitialization arm completed only seeds 0 and 1 before
being stopped to bound CPU use; no incomplete episode enters the JSONL.

Run or resume an arm with:

```text
.venv-p05\Scripts\python.exe experiments/p03_long_duration/run.py --model model2 --conditions baseline --seeds 0 1 2 --cap 30000
```

The runner appends each finished episode as JSONL and saves progress every
1,000 actions. Repeating the same command skips finished episodes and resumes
an interrupted active episode. A separate parity test compares every condition
to the original reference over a bounded eight-action rollout.
