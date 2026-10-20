# P06 direct upstream model2 comparison — 2026-10-07

## Result

The user authorized the paired comparison of a failing seed against the original
implementation. **Seed 12 matched across all 1,334 actions**: both the original
TensorFlow Python NCA and the P06 NumPy reproduction chose the same action at
every decision, obtained score **1,307.0921457820718**, and terminated at the
pole-angle limit on action **1,334**. The final pole angle was
**12.562940480621434 degrees**, above the source's 12-degree threshold.

This specific early failure occurs with the released source operator too under
the declared replay protocol. It is not evidence of an inferior port. One seed
does not establish equality of overall reliability, directly verify the other
nine P06 seeds, or reproduce the historical paper's 100-run table. ADR-0009's
failed 8/10 gate remains unchanged; no weights were frozen or exported.

| Comparison | Observed result |
|---|---|
| Controller decisions | 1,334/1,334 identical; no first action disagreement |
| Plant observations and post-action states | Identical at every decision; maximum float64 state error 0 |
| Recurrent schedules and cell masks | Identical supplied sequence; 72,714 NCA epochs per arm |
| Final score, termination and action-trace hash | Exactly identical |
| Source-generated cut masks and markers versus P03 | Bitwise identical |
| Identical-input model2 local-delta probe | Max absolute error 1.4901161193847656e-7 |
| Identical-input complete-step probe | Max absolute error 1.1920928955078125e-7 |
| Full decision-grid comparisons | Maximum absolute error 5.0067901611328125e-6; zero elements outside `atol=rtol=2e-5` at every decision |
| Raw grid bytes | Differ beginning at action 1; numerical cross-backend agreement, not bitwise grid identity |
| Minimum local action-score margin | 3.828108310699463e-5 |
| Replay versus old P06 seed-12 record | Exact actions, score, mask/action hashes, final plant/grid hashes and termination |

The arrays were compared in full at every control-decision endpoint. The report
does not claim that every internal epoch was individually compared or that this
observed error bound is guaranteed on other trajectories.

## Independent source execution and limits

`experiments/p06_upstream_parity/upstream_worker.py` imports the unchanged
`NeuralCA` and `CartPoleEnvContiReward` classes from the ignored local clone at
revision `8c85be11b0838ea14ac51a11dac3098db43afed2`. The upstream worker does not
import P03/NumPy inference or plant code. It independently parses the shipped
model2 manifest/blob and installs all 1,916 float32 weights into the upstream
Keras model. Weight-blob SHA-256:
`ee8e4ad597d73dc616e60e91a5af056c96beb9f2c18652cfb1a1906247fbc009`.

The worker executes the actual upstream neural step and plant equations.
Its sole stochastic interception replaces `tf.random.uniform` mask draws at
runtime with supplied 0.25/0.75 values, reproducing exactly the caller's mask
bits under the original `<=0.5` predicate. Noise and other stochastic variants
are disabled. No upstream source file, checkpoint or canonical P03 file changed.

This reconstructs the accepted ADR-0009 single-episode deployment protocol:
fresh initial grid, persistence within the episode, 50–59 epochs, no damage,
noise or optional reinitialization, and source horizon. Initial plant/grid and
all schedules/masks are the exact original P06 seed-12 values. Each arm advances
its own plant; a differing action would make later observations potentially
different, and the harness records this explicitly. No such divergence occurred.

Both arms use notebook/checkpoint input coordinate (5,12), rather than the
discrepant DQN constructor's (5,13), and E01's declared float32-before-scaling
input boundary. This is not an execution of the whole released DQN evaluation
harness with its pool/reset behavior and float64-before-scaling path. Historical
table checkpoint/reset/dependency questions remain unresolved.

The upstream environment is an isolated, explicitly modern source execution:
Python 3.11.9, TensorFlow/Intel 2.15.1, Keras 2.15.0, NumPy 1.26.4 and Gym
0.23.1. TensorFlow oneDNN is disabled; inter/intra-op threads are 1. The full
installed dependency lock is `upstream-runtime.lock`. The local reproduction
retains the original P06 Python 3.12.14/NumPy 2.3.5 runtime. This was not the
unavailable historical paper runtime. Package installation first failed under
restricted network access; the isolated download succeeded with reviewed
network escalation. No global Python packages were changed.

## Evidence and reproducibility

Runner: `experiments/p06_upstream_parity/run.py`; user-level instructions:
`experiments/p06_upstream_parity/README.md`. Compact result:
`experiments/p06_upstream_parity/results/summary.json`.

- Summary SHA-256: `6f9c17dc44513a4199517e400b3fbc67bb107a4bd1309290739298ad4cb51c73`.
- Ignored full per-action comparisons SHA-256:
  `4b2562962b7b31ad3339d31b77f12715e90a7c3a60462a7ed2cf4beca553ba45`.
- Shared action SHA-256:
  `dd7635921ca8c1417f132eff49c984e8d19512e83a686102b21549c6899944fa`.
- Ordered mask-hash digest:
  `0c600f8cd619245ff81db7ea58c92b895c5bb905b491d74d622289d59cfd413c`.

Full grids and atomic resume checkpoints remain in ignored `artifacts/`.
No restricted weights or tensor fixtures were added to tracked artifacts.
Every 25 decisions is checkpointed. A separately bounded 3-to-5-action resumed
run matched a fresh 5-action run in its entire summary and JSONL trace.

| Command/check | Observed result |
|---|---|
| `.venv-p05/Scripts/python.exe -u experiments/p06_upstream_parity/run.py` | Completed both episodes in about 164 s after worker initialization; matched 1,334 actions/72,714 epochs and original P06 record |
| `.venv-p05/Scripts/python.exe -m unittest experiments.p06_upstream_parity.test_parity -v` | 4/4 pass, 11.363 s: source I/O templates, exact zero-mask rewrites, all-update deterministic replay, 59-step explicit-mask recurrence |
| Runner with `--action-limit 3 --output tmp/parity-resume`, then limit 5; fresh limit 5 in `tmp/parity-fresh` | Exact full summary and trace equality after resume |
| `.venv-p05/Scripts/python.exe -m unittest discover -s reference/original_nca/tests -q` | 17/17 pass, 0.216 s |
| `.venv-p05/Scripts/python.exe -m unittest discover -s sw/cartpole/tests -q` | 12/12 pass, 1.435 s |
| `.venv-p05/Scripts/python.exe reference/original_nca/tools/verify_upstream.py --upstream self-organized-control` | Pinned revision, 13 artifacts and 3 checkpoint goldens pass |
| `.venv-p05/Scripts/python.exe scripts/run_smoke.py` | Scaffold, 23 governance hashes, locked runtime and oracle firewall pass |
| `.venv-p06-parity/Scripts/python.exe -m pip check` | No broken requirements |
| `git diff --check`; local source/reference preservation audit | Pass; no canonical reference edits or upstream edits |

## FPGA implication

This adds direct, long-running source evidence for the existing NCA software
operator. Its smallest P06 failure is reproducible with the original source
and weights. It supports keeping the original operator as the hardware
specification and investigating paper/deployment protocol comparability before
asserting that a stronger controller or weaker quality requirement is needed.
It does not waive the accepted freeze gate, select fixed-point arithmetic,
guarantee other seeds, or authorize P07/RTL. The user-authorized diagnostic is
complete; the existing G3E gate remains open.
