# P06 accepted model2 qualification

This is the **pre-registered** source-default float qualification from
ADR-0009, not retraining or a paper-table reproduction. The versioned
protocol is `sw/cartpole/qualification.v1.json`. Run locally with:

```text
.venv-p05\Scripts\python.exe -u experiments/p06_cartpole/run_qualification.py
```

The runner first verifies the ignored upstream revision, 13 artifact hashes
and three fixed-checkpoint goldens, then checks the model2 weight-blob hash.
It runs seeds 10–19 exactly once each via the E01 `CartPoleHost` and
`ReferenceController` seam. Per seed, `RandomState(seed)` first supplies the
source plant's four reset draws, then one `randint(50,60)` and contiguous
per-epoch/per-cell update-mask draws per action. The initial NCA grid comes
from the separate `seeded_initial_grid(seed ^ 0x5A17)` stream; it persists
across actions but resets at the next episode. No noise, damage, input
deletion or within-episode reinitialization is applied.

Completed records append to `results.jsonl`; when all ten are present the
runner writes `summary.json`. The threshold is >=8/10 balanced completions
at action 10,001 **and** pinned-golden pass. A process interruption leaves
an ignored, atomic progress snapshot under `artifacts/p06_cartpole/progress/`;
rerun the same command to resume. Missing episodes are incomplete, not
failed or passed. Do not delete/reseed/pool attempts to change the result.
The result records contain hashes, counts and scores only, never checkpoint
bytes or full NCA grids.

These records apply to the declared Python/NumPy runtime and logical draw
assignment. A SHA-256 of mask hashes verifies a recorded sequence; it does
not replace the generator/seed mapping needed to reconstruct masks. No
hardware-quality, 20 ms real-time or statistical population claim follows.
