# E01 — CartPole plant, transducer and replay contract

Status: E01 structural consolidation, 2026-10-07. This is not G3E checkpoint
or episode-protocol acceptance and does not freeze a model for P06.

## Authority and boundary

The versioned contracts are `sw/cartpole/interface.v1.json` and
`sw/cartpole/replay.v1.json`. Their source hashes bind the original P03
operator manifest, local-rule implementation and modified CartPole plant.
`sw/cartpole/deployment.py` is an executable adapter over those authorities;
it does not reimplement plant physics, train a controller, choose weights, or
silently use stock Gymnasium CartPole. It accepts any controller satisfying
the host-neutral port, with `ReferenceController` as the P03 float adapter.

One decision proceeds as follows:

1. The host samples the four-value **pre-action** plant state in the original
   order, converting float64 plant values to float32 observations.
2. The verification caller supplies a count in 50–59 and an exact, ordered
   one-bit-per-cell mask for every internal epoch; optional noise is an
   explicit float32 trace. This is a replay seam, not a requirement to carry
   masks over a future host/FPGA bus. E01 does not choose a deployed RNG,
   seeds, draw location, or pacing policy.
3. The controller alone performs the original recurrent NCA updates, including
   shared masks, zero padding, post-residual clears/clamps/markers, scaled
   duplicated sites, and persistent grid. Its two raw channel-zero scores and
   lowest-index-tie argmax action are returned; the host does not compute a
   desired action.
4. The host applies the returned left/right action to exactly one source
   `CartPole.step`. The source explicit-Euler transition, runtime cosine
   reward (including terminal transition), and `>10000` horizon are not
   duplicated in the wrapper. A terminal episode rejects further steps.

`CartPoleHost` construction requires an explicit plant and controller object.
Constructing a new plant does not reset a reused controller; constructing a
new `ReferenceController` requires an explicit initial grid. This lets E02/G3E
select a documented episode-grid policy without embedding a default in E01.
Startup, plant, controller, episode and recovery resets remain distinguishable.

The controller port is a transport-neutral software seam. It does not define
an FPGA bus, clock domain, fixed-point format, queue, weight export or board
driver. Raw scores are telemetry; action selection belongs in the controller.
The simulated `0.02`-second plant integration step is not asserted to be a
measured wall-clock inference deadline.

## Replay contract

Each decision trace records exact float32 observation and score bit patterns,
the ordered packed-mask hash, optional noise hash, action, reward, terminal
flag, elapsed plant actions, before/after plant hashes, and optional read-only
controller-state hash. Exact replay additionally requires the initial plant
state/step count/horizon, initial NCA grid, checkpoint or synthetic weights,
and the full ordered mask/noise arrays. **Hashes alone are not sufficient to
reconstruct the draws.** A later exporter/transport must either retain the
draw arrays or bind an accepted PRNG algorithm, seeds, and logical draw
assignment. Different arithmetic runtimes follow P03's declared float
tolerance; future RTL compares to the P07 bit-accurate scheduled model.

The released horizon is 10,001 actions when the pole remains balanced,
because the source terminates on `step_count > 10000`. The separately recorded
30,000-action P03 diagnostic is not made the default by E01. Runtime reward
is not the DQN training-only `-100` terminal replay target.

## Coverage map and E02 handoff

| Concern | Reused evidence | E01 evidence | Still open for E02/G3E or later |
|---|---|---|---|
| Plant integration, limits, reward, action force | P03 `cartpole.py`, golden rollouts | Source-bound manifest; direct-transition and terminal-horizon wrapper tests | Chosen deployment horizon and control-quality thresholds |
| Four observations, eight scaled sites, two readouts | P03 `operator_manifest.json`, `core.py`, golden tests | Host/controller manifest; direct-operator parity test | Selected checkpoint, weights rights/export |
| 50–59 epochs, shared masks, noise, I/O rewrite | P03 exact suite and discrepancies | Explicit mask/noise port and replay hashes; bounded parity tests | Deployed RNG/seed/draw assignment; noise/damage policy |
| Persistent grid and reset | P03 pool tests; paper/harness discrepancy | Explicit controller construction, no implicit plant/controller coupling | Episode-grid and recovery-reset policy |
| Deterministic replay | P03 fixed vectors and checkpoints | Versioned replay schema; identical two-decision traces under identical initial state/draws | External trace retention and fixed-point scheduled golden at P07 |
| Independent conventional control | P03 DQN interface is historical, not an E01 comparator | Host/controller port permits a separate equal-I/O backend without host teacher leakage | E02 comparator/competence evidence and fairness protocol |
| Long-duration robustness | P03 empirical and extended diagnostics | Explicit distinction between released and diagnostic horizons | G3E thresholds; full paper statistics remain unreproduced |
| Sparse/event execution | Reference mask semantics and active vision | No state-change gating introduced | E02/G3E distinction between exact-preserving work avoidance and changed event model |
| Rights/provenance | P03 pinned ignored upstream clone and hashes; incomplete license | No checkpoint bytes copied or exported | G3E/P06 rights disposition |
| Physical timing and platform | G1 provisional DE1-SoC | No bus, RTL, timing or power claim | P07–P14 numerical/physical evidence |

All E01 artifacts remain separate from `reference/original_nca/`; historical
Hanoi code, experiments and automation state are untouched. E02 may now assess
which released checkpoint and explicit deployment protocol are competent and
permitted, using existing P03 evidence before any bounded new evaluation.
G3E remains the human gate; E01 makes no checkpoint, reset, horizon, event,
timing or rights selection for it.

## Observed E01 validation

On 2026-10-07 the seven E01 wrapper tests passed, as did 17 original-P03,
11 historical P04 and 30 historical P05 unit tests. The repository smoke gate
passed with 19 governance hashes and the oracle firewall. The pinned-upstream
verifier passed its revision, 13 artifact hashes and three fixed-checkpoint
rollouts. Python compilation of `sw/cartpole/`, `git diff --check`, and a scope
check showing no modification under `reference/original_nca/` also passed.
The first E01 test pass had one incorrect expected hidden-channel value: the
test supplied positive update noise, which adds to the output channel before
the mandatory `+1` marker. Correcting that expectation yielded the final
passing suite; no original-reference code was changed. No training, new
competence benchmark, RTL, timing, power or FPGA measurement was performed.
