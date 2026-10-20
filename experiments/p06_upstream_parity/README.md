# P06 diagnostic: direct upstream Python comparison

This is a seed-12 comparison after the failed P06 qualification. It is not a
replacement qualification, model freeze, training run, or new numerical contract.

The worker imports the unchanged `NeuralCA` and `CartPoleEnvContiReward` classes
from the ignored, pinned `self-organized-control` clone. It loads the released
model2 tensors independently from their TFJS manifest. The source's random
uniform mask draw is intercepted at runtime and supplied with 0.25/0.75 values
encoding the caller's exact mask. Source files and learned weights are unchanged.
No NumPy/P03 inference or plant function executes in the upstream worker.

Use notebook/checkpoint coordinates (5,12), not the discrepant DQN constructor's
(5,13). Apply the accepted E01 float32 observation and scaling boundary to both
arms. This tests the source operator under the accepted deployment protocol;
it does not recreate the whole historical DQN test harness, float64 scaling,
cross-episode pool behavior, optional reinitialization, or original TF runtime.

Both arms start from exactly the P06 seed-12 plant/grid and consume identical
50–59 schedules and masks from the original P06 NumPy runtime. Each has its own
persistent grid and plant. Before the first differing action their physical
observations are identical; afterward their plants evolve independently.
Continue each arm until its own source termination, bounded at 10,001 actions.
An identical-input single-step model2 probe and bitwise I/O-mask comparison
precede the episode. Tiny differences between TensorFlow and NumPy are recorded,
not immediately labeled semantic defects. The old per-step `2e-5` tolerance is
reported as a diagnostic, not promoted to a long-recurrence error guarantee.

Upstream environment: Python 3.11.9, TensorFlow/Intel 2.15.1, Keras 2.15.0,
NumPy 1.26.4, Gym 0.23.1; full installed lock is `upstream-runtime.lock`.
TensorFlow oneDNN is disabled; inter/intra-op threads are 1. This is an explicitly
declared modern execution of source code, not the unavailable historical lock.
Local environment remains Python 3.12.14/NumPy 2.3.5 from `.venv-p05`.

```powershell
python -m venv .venv-p06-parity
.venv-p06-parity/Scripts/python.exe -m pip install -r experiments/p06_upstream_parity/upstream-runtime.lock
.venv-p05/Scripts/python.exe reference/original_nca/tools/verify_upstream.py --upstream self-organized-control
.venv-p05/Scripts/python.exe -u experiments/p06_upstream_parity/run.py
```

The runner resumes from ignored `artifacts/p06_upstream_parity/results_progress.npz`
every 25 moves. Full grids/first-disagreement snapshots stay ignored. Safe per-move
metrics are retained locally in ignored `results/comparisons.jsonl`; the compact
`results/summary.json` records hashes, runtimes, counts and first differences.
The local arm must reproduce the existing P06 seed-12 result and
endpoint identities; this prevents runtime changes being mistaken for a replay.
Interrupted runs remain incomplete. Results cannot identify population reliability
or establish the paper's 100-run table from one diagnostic seed.
