# P03 exact algorithmic reproduction report

## Scope

This report covers deterministic algorithmic equivalence, not stochastic
training reproducibility. The source authority is pinned in
`reference/original_nca/provenance.json`; the executable contract is
`reference/original_nca/operator_manifest.json`.

## Comparison points

For identical float32 weights, initial grid, four-value observation, supplied
cell masks, and optional supplied noise/damage values, the suite checks:

1. the learned local delta after 3x3/ReLU, 1x1/ReLU, and 1x1/linear layers;
2. one complete residual NCA step including I/O clearing and rewriting;
3. ordered output-cell channel-zero readout and argmax tie behavior;
4. a four-step persistent-state rollout;
5. an eight-action closed-loop CartPole rollout for each of the three released
   checkpoints, with a fixed environment/grid/RNG seed and action-trace hash;
6. seeded stochastic mask generation, mask sharing across channels, and supplied
   update noise before masking;
7. supplied-trace circular damage, including all-channel replacement inside the
   circle and unchanged state outside it; and
8. raw input clamp, output hidden-channel accumulation, deletion-to-intermediate
   behavior, curriculum targets, pool persistence/reinitialization, and the
   50-through-59 schedule.

The checked-in byte contract is C-order little-endian IEEE-754 binary32. Exact
hashes apply to the declared Windows x86-64, Python 3.12.14, NumPy 2.3.5
arithmetic runtime. NumPy wheels on Windows and Linux may use different BLAS or
vector reduction orders despite matching versions, so cross-platform CI compares
the complete arrays in `golden/golden_arrays.npz` elementwise with
`rtol=2e-5, atol=2e-5`. This is a full-array check, not a sampled or hash-bypass
check. A scalar local-rule oracle separately agrees within `2e-6`, and the
TensorFlow.js comparison uses the same `2e-5` cross-backend ceiling.

## Checkpoint coverage

All three released browser checkpoint binaries are parsed in their manifest
tensor order. Each has 1,916 float32 values. The upstream verification command
checks the local clone revision, 13 artifact hashes, and fixed rollouts for
models 1, 2, and 3 without copying checkpoint bytes into this repository.

## Persistence and reset boundary

The released pool implementation proves that a committed grid is resampled and
therefore persists across controller moves. Its `reinit_and_sample` path creates
a fresh random grid and is covered by a deterministic reset test. The released
multi-episode evaluation harness does not call that grid reset between CartPole
episodes, despite the paper saying that each simulation starts from a random
grid. Therefore cross-episode grid reset is an explicit unresolved source gap:
the reference tests both executable persistence and the available reset operator,
but do not claim an unobserved historical episode-reset policy.

## Acceptance result

The clean-room reference passes the declared operator acceptance criteria.
This does not prove that the historical stochastic training run or paper tables
can be recreated. Those limitations are reported separately.
