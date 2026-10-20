# P07 numerical study and scheduled integer golden

Status: G4 accepted on 2026-10-07; P07 complete. Frozen weights/protocol are bound
by accepted ADR-0011 and `sw/cartpole/deployment.freeze.v1.json`. Accepted
ADR-0012 selects fidelity32 and its bounded quality contract; the validated
authority is `sw/cartpole/arithmetic.accepted.v1.json`. P08 remains unstarted.

All formats, calibration/acceptance roles and action caps were predeclared in
`protocol.v1.json` before the runs. Reused calibration seeds 10/12 are not called
held out. Seeds 20/21 were new for this bounded 256-action comparison. No widths
were tuned on their results. Future tuning must disclose these now-used seeds.

```powershell
.venv-p05/Scripts/python.exe -m model_export.cartpole.freeze
.venv-p05/Scripts/python.exe model_export/cartpole/export_local.py --accepted-freeze
.venv-p05/Scripts/python.exe -u experiments/p07_cartpole/profile_float.py
.venv-p05/Scripts/python.exe -u experiments/p07_cartpole/evaluate.py
.venv-p05/Scripts/python.exe experiments/p07_cartpole/make_summary.py
.venv-p05/Scripts/python.exe experiments/p07_cartpole/generate_vectors.py
.venv-p05/Scripts/python.exe experiments/p07_cartpole/check_vectors.py
.venv-p05/Scripts/python.exe -m unittest model_export.cartpole.test_fixed_point -v
```

The profile resumes from atomic ignored checkpoints every 100 actions and
verifies the executed script hash. It exactly reproduces the original P06
seed-10 horizon endpoint. It profiles every state/residual/delta epoch and samples
first-two-layer preactivations at epoch 1/every 64 epochs. Six saved snapshots
span actions 1, 10, 100, 1,000, 5,000 and 10,000.

The evaluation compares three integer controllers and the original float
controller using the same starting plant/grid and logical masks. Each controller
advances its own sole-authority P03 CartPole. Grid errors are summarized when
pre-action physical observations match; later feedback divergence is separately
labeled by first differing action. All episodes hit their declared cap, so they
are censored. `evaluation.json` and diagnostic snapshots are local/ignored;
`evaluation_summary.json` is compact safe telemetry. Evaluation snapshots record
grid/plant/RNG boundaries, but there is no automatic evaluator resume loader;
re-run a bounded evaluation if interrupted. Completed results are already saved.

`generate_vectors.py` emits 18 restricted cases (three formats, six trajectory
points), with full layers, 8 independently checked cells each, post-write epochs,
exact persistent masks and final integer scores/actions. `check_vectors.py`
replays all saved integer arrays exactly. All vectors and weight-derived arrays
remain in ignored `artifacts/p07_cartpole/`; only hashes/errors are tracked.

The scheduled golden and its E01-compatible host adapter are
`model_export/cartpole/{fixed_point.py,fixed_deployment.py}`. Synthetic tests
need no upstream weights and are added to smoke CI. Physical bus, MAC lanes,
banking, wall-clock deadlines, RTL and full-horizon quantized qualification are later
decisions. No hardware performance or full-horizon quantized reliability is
claimed from these software measurements.
