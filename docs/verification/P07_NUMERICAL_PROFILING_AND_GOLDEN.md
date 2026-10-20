# P07 numerical profiling and scheduled golden — 2026-10-07

Status: **P07 complete; G4 accepted on 2026-10-07 through ADR-0012**.
Weights are frozen through accepted ADR-0011; the original float qualification
remains 6/10. Fidelity32 is frozen by `sw/cartpole/arithmetic.accepted.v1.json`;
the measurements below retain their original scope. No P08 primitive, RTL or
FPGA result is claimed. Acceptance bookkeeping and checks are in the implementation status.

## Freeze prerequisite

The user explicitly authorized freezing current model2 and starting only P07,
superseding the old >=8/10 pre-freeze condition. `model_export/cartpole/freeze.py`
creates/verifies a resolved versioned contract binding the accepted ADR, P03
operator/plant, E01 interface/replay and actual qualification/parity evidence.
The ignored 7,664-byte float export round-trips all six tensors bitwise and
matches model2 SHA-256
`ee8e4ad597d73dc616e60e91a5af056c96beb9f2c18652cfb1a1906247fbc009`.
The original default exporter still refuses an unqualified summary; only the
explicit validated `--accepted-freeze` path exercises ADR-0011.


## Full-horizon float profile

Seed 10 is explicitly reused calibration. **10,001 actions / 544,994 epochs**
completed under the unchanged fresh-grid, persistent, 50–59-step primary protocol.
Score **9,718.270307454093** and action/mask/plant/grid endpoint hashes exactly
match P06. Profile execution took approximately **736 seconds** from the runner's
progress timing, including all-epoch range collection. Python 3.12.14,
NumPy 2.3.5, Windows x86-64; no training or noise/damage/reinitialization.

| Quantity | Observed min | Observed max | Sampling |
|---|---:|---:|---|
| Recurrent state, all channels | -5.801792145 | 15.61518383 | Every epoch, per channel |
| Output hidden channels 4/5 | -5.801792145 | 15.61518383 | Every epoch |
| Masked residual before I/O | -6.801792145 | 14.61518383 | Every epoch, per channel |
| Local delta | -17.71842575 | 1.614928007 | Every epoch, per channel |
| Layer 0 preactivation | -6.352028370 | 9.747632980 | Epoch 1 and every 64 epochs |
| Layer 1 preactivation | -7.756903648 | 11.15002346 | Epoch 1 and every 64 epochs |
| Scaled physical observations | -1.093046784 | 0.7812432051 | Every action |
| Absolute action-score margin | 0.000007197260857 | 0.1789983660 | Every action |

All ranges include zero nonfinite values. Raw per-channel minima/maxima and
sample counts are in `float_profile.json`; neural preactivation sampling has
8,516 checkpoints and does not establish exhaustive layer extrema. Kernel/bias
ranges are recorded separately; finite coefficient ranges alone were not used
to bound recurrent state. Output marker additions were preserved: learned deltas
can counteract them, so `epochs` is not the observed marker-channel value.

## Integer alternatives and semantics

The predeclared formats use state/activation widths and fractions **18/12,
24/16, 32/24**; kernel widths/fractions **16/14, 18/16, 24/22**; accumulators/biases
**40/26, 48/32, 62/46**. Signed exact integer products, bias-last accumulation,
ReLU before requantization, nearest ties-even rounding, guard-bit residual sum
and counted signed saturation are explicit. Fan-ins are **54/20/30**.

Analytical maximum signed accumulator requirements using full valid state words
and actual quantized coefficient absolute sums are **36/35/35**, **44/43/43**
and **58/57/57** bits. The allocated 40/48/62 widths contain these bounds, so
NumPy int64 implements exact MACs without host wrap. Bounds and storage estimates
are machine-readable in the evaluation summary. Saturation at layer/state
boundaries is a declared numerical derivative of unclipped float inference.

The complete source post-write order, old-grid epoch commit, held pre-action
observation and integer readout/tie are implemented. `FixedControllerPort`
connects the integer controller to unchanged E01 `CartPoleHost`; no second plant
grammar exists. Score telemetry conversion follows integer action selection.
Physical word packing/transport, hardware RNG and MAC lanes remain G5 decisions.

## Control and persistent drift

All formats/caps were declared before running. Calibration seeds **10/12** reuse
P06; new acceptance seeds **20/21** are disjoint. None was used to adjust a width.
This G4 review is now informed by their outcomes; future tuning must declare
reuse and reserve new validation data. Two short acceptance episodes cannot
establish population or full-horizon reliability.

| Seed/role/cap | Float score | compact18 score | balanced24 score | fidelity32 score |
|---|---:|---:|---:|---:|
| 10 / calibration / 128 | 127.965565177 | 127.904409920 | 127.965565177 | 127.965565177 |
| 12 / calibration / 128 | 127.872909295 | 127.872909295 | 127.872909295 | 127.872909295 |
| 20 / acceptance / 256 | 252.869683621 | 252.860621729 | 252.869683621 | 252.869683621 |
| 21 / acceptance / 256 | 251.731563180 | 251.731563180 | 251.731563180 | 251.731563180 |

Every float/fixed arm reached its action cap and is **right-censored**. The two
wider formats matched every float action/score on all four bounded traces.
Compact18 differed on seed 10 at action **2**, where score resolution produced
a tie, and seed 20 at action **238**. It still reached the caps; no false
full-episode completion or quality pass is assigned to those caps.

Maximum recurrent grid errors under identical pre-action physical observations:
**0.01170256734**, **0.002084851265**, **0.00001788884401**. All saturation counters,
including kernels/biases, layers, observations, residuals and markers, were zero
in these bounded controller runs. State grids remain independent; first actions
and diagnostic snapshots identify where later feedback divergence begins.

Measured model-and-diagnostic execution across the four episodes was **143.898 s,
143.624 s and 144.534 s** for the three integer alternatives, with **41.100 s**
for the float arm, **473.156 s** combined. These are host Python wall-clock
measurements including diagnostic work, not FPGA latency or speed estimates.

Separately labeled analytical marker-only stress: zero delta plus 590,059 `+1`
increments exceeds all finite candidates (first saturation at 32/128/128).
It is not the learned checkpoint's dynamics; extrema tests deliberately exercise
and count saturation. Measured trajectory ranges are not universal guarantees.

## Vectors and independent checks

Six full-horizon snapshots at actions 1/10/100/1,000/5,000/10,000 generate **18**
format/snapshot cases, totaling **9,147,167 ignored bytes**. Each saves full
layer accumulator/output arrays, cell deltas, post-write epochs, exact persistent
masks, epoch 1/2/59 states and final readout/action. **144** selected cells match
independent Python-int nested MAC calculations, including corners/edges/I/O.
All saved arrays replay **exactly** with `check_vectors.py`.

| Maximum one-step error across snapshots | compact18 | balanced24 | fidelity32 |
|---|---:|---:|---:|
| Layer 0 output | 0.0006832480 | 0.0000902414 | 0.0000012517 |
| Layer 1 output | 0.0008447617 | 0.0000937283 | 0.0000014305 |
| Local delta | 0.0009071976 | 0.0000950843 | 0.0000015367 |
| Post-write epoch | 0.0009491891 | 0.0000813007 | 0.0000013337 |

The vector manifest records first quantized-float boundary/coordinate
differences and hashes, without embedding tensor values. Float-to-fixed equality
is not claimed. Future RTL compares bitwise with the G4-accepted integer model,
not with relaxed P03 float tolerances. No checkpoint-derived array was tracked.

## Commands and observed results

| Exact command (all under `.venv-p05/Scripts/python.exe`) | Observed result |
|---|---|
| `-m model_export.cartpole.freeze`; `model_export/cartpole/export_local.py --accepted-freeze` | Resolved freeze generated; 7,664-byte ignored export, all six tensors bitwise round-trip, pinned hash |
| `-u experiments/p07_cartpole/profile_float.py` | Full primary-horizon profile complete; exact old P06 seed-10 match |
| `-u experiments/p07_cartpole/evaluate.py`; `experiments/p07_cartpole/make_summary.py` | Four predeclared episodes per format/float; all bounded results saved, no tuning |
| `experiments/p07_cartpole/generate_vectors.py`; `experiments/p07_cartpole/check_vectors.py` | 18 cases, 144 independently checked cells; all complete vectors replay exactly |
| `-m unittest model_export.cartpole.test_fixed_point -v` | **10/10 pass**, 1.344 s; signed rounding/extrema/bounds/scalar cells/zero-mask/markers/ties/reset/service order/E01 seam |
| `-m unittest model_export.cartpole.test_export_local -v` | **3/3 pass**, 0.019 s; corruption, legacy refusal, fake freeze authority rejection |
| `-m unittest discover -s reference/original_nca/tests -q` | **17/17 pass**, 0.364 s |
| `-m unittest discover -s sw/cartpole/tests -q` | **12/12 pass**, 2.597 s |
| `-m unittest discover -s reference/hanoi/tests -q` | **11/11 pass**, 10.618 s; historical exhaustive corpus preserved |
| `-m unittest discover -s training/hanoi_nca/tests -q` | **30/30 pass**, 9.909 s; historical runs not resumed |
| `-m unittest experiments.p03_long_duration.test_run -q` | **1/1 pass**, 8.934 s; bounded parity only |
| `reference/original_nca/tools/verify_upstream.py --upstream self-organized-control` | Pinned revision, 13 artifact hashes, three checkpoint goldens pass |
| `scripts/run_smoke.py`; `scripts/check_oracle_firewall.py` | Scaffold, 25 governance hashes, locked runtime and firewall pass |
| `-m compileall -q model_export/cartpole experiments/p07_cartpole`; `git diff --check` | Pass |

Total **84 unit tests passed**, plus 18 full vector replays and the long profile.
An initial persistence fixture used compact18 and saturated its marker before
50 epochs; its assumption that the second zero-mask block changes state was
incorrect. Using a larger-range synthetic persistence fixture fixed that test
without altering candidate arithmetic or empirical data. Smoke also caught the
legitimate AGENTS update until its governance binding was recorded. Final passes
supersede these intermediate test failures, which remain disclosed here.

Synthetic integer tests were added to hosted smoke CI; **no hosted CI run is
claimed**. Original P03 and RTL trees are unchanged. User work is preserved on
the development branch; no commit/push/automation/training was performed.

## Artifact identities and gate exit

- Resolved float freeze SHA-256:
  `3e3c40e54a837f599d69588330e81a6af60dd22a00be7afe1a43390569d1c1a7`.
- P07 predeclared protocol:
  `28a809e6955fc224630ea3dc057d1c7599068764d44843c3c74e7db7173736bf`.
- Float profile: `c9113f3ec63237d7aec7bbdfc5c1cdc802f91e0a850d465d85e225f53df93cde`.
- Compact evaluation:
  `99eb4ec5ebfac7630ca9227aa550b1020bb557dc3f3672e302c42358ffc15025`.
- Vector manifest:
  `cd8ed555d3bb6b39702439c89634bc282b15a0cb7d39b580260ef8b105a680e2`.

G4 recommendation: **fidelity32** for the closest measured arithmetic baseline,
with balanced24 and further long evaluation as alternatives. Accumulator proofs,
storage estimates, schedule/portability consequences and explicit quality limits
are in the decision packet and proposed ADR-0012. **Stop at G4; no P08/RTL.**
