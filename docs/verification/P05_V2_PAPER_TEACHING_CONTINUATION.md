# P05 v2 paper-teaching continuation

## Scope and pre-registered interpretation

The user authorized a full v2 teaching-flow continuation to test whether the
previous v2 policy failure was caused by an inadequate communication warm-up
and training schedule. This is a separate P05 experiment, not G3 model freeze.
It reuses the accepted v2 adapter, eight-channel model, layout, bounded runtime,
P04 observation/action interface, unmasked readout, and oracle firewall.

`training/hanoi_nca/run_v2_paper_flow.py` restores the original paper's core
*training mechanics*: synthetic `4*mean(inputs)` warm-up at every output,
independently sampled persistent NCA grid pool, occasional worst-grid reset,
stochastic 0.5 fire rate, 50--59 recurrent updates, per-weight-tensor gradient
normalization, Adam at 0.005, and a long supervised phase. The Hanoi action
phase uses training-only complete-set oracle labels and cross entropy, **not**
the paper's CartPole reward, replay memory, or DQN targets. Therefore this is
a paper-mechanics adaptation, not an exact historical training reproduction.
No synthetic observation or oracle action enters the deployment-shaped model.

The pre-registered run uses seed 405, batch 16 in four microbatches, pool 128,
warm-up at least 4,000 and at most 12,000 iterations, with transition after
fresh-grid synthetic validation MSE <= 0.02 at a checkpoint, and then 15,000
Hanoi imitation iterations. Disk-count curriculum exposes n=1..2 for the
first 2,500 imitation updates, then n=1..4, n=1..6, and finally n=1..8.
Checkpoints are atomic every 250 iterations and save weights, optimizer,
grid pool, and both random streams. The first short run stopped at iteration
10 and the full command resumed from that exact checkpoint. A separate
stop/resume regression test checks deterministic continuation.

Interpret results by stage, not as one pass/fail score:

1. If synthetic warm-up never reaches MSE 0.02, this run has **not** ruled out
   the communication-teaching bottleneck, regardless of later action results.
2. If warm-up succeeds but train fresh-grid optimal-action accuracy stays low,
   the action-mapping optimization bottleneck remains. A longer schedule alone
   was insufficient; this does not prove NCA representational impossibility.
3. If train accuracy is high but hash-held-out accuracy is low, the main
   observed limitation is generalization from training identities.
4. If fresh-grid action accuracy is high but persistent closed-loop completion
   is low, diagnose recurrent-state persistence and accumulated policy errors
   separately. Completion, legality, and excess moves are not interchangeable.

The run does not preregister a hardware freeze threshold. G3 remains open.

## Outcome and replacement

The 2026-09-29 full run was stopped by user authorization on 2026-09-30
after a failed warm-up and non-learning imitation continuation. The fixed
fresh-grid validation MSE was 25.5460949 at warm-up iteration 12,000,
versus the 0.02 goal. Direct replay of the warm-up checkpoint gave all six
output scores exactly -5 on all 48 validation examples; a two-example
backward probe gave zero gradients for all six weight/bias tensors. At
imitation iteration 3,000, the sampled cross-entropy was 1.79175949
(`ln(6)`) and the pre-normalization gradient norm was zero. The last
`resume.pt` SHA-256 was
`5a8177bb956bcbd140134cebcd5f4138894b97b015232ed108410c54210b6009`.
These are negative model-training measurements, not a completed policy result.

The user requested a replacement run rather than appending to this run. Its
large resumable checkpoint and logs may therefore be removed after stopping
the process; this concise evidence is retained here. No G3 model freeze is
authorized by this result.

## Commands and historical live state

Executed smoke command in the separate disposable experiment directory:

```text
.venv-p05/Scripts/python.exe training/hanoi_nca/run_v2_paper_flow.py --output experiments/p05_v2_paper_smoke --batch-size 4 --microbatch-size 2 --pool-size 8 --step-min 2 --step-max 3 --warmup-min 2 --warmup-max 2 --imitation-iterations 2 --checkpoint-every 1 --stop-after 2 --eval-cases-per-split 8 --eval-max-n 1
```

The same command without `--stop-after 2` resumed and finished. The two new
unit tests passed. The full run was started with:

```text
.venv-p05/Scripts/python.exe training/hanoi_nca/run_v2_paper_flow.py --output experiments/p05_v2_paper_flow --stop-after 10
.venv-p05/Scripts/python.exe training/hanoi_nca/run_v2_paper_flow.py --output experiments/p05_v2_paper_flow
```

Progress is at `experiments/p05_v2_paper_flow/progress.json`, the full
resume point is `resume.pt`, and stdout/stderr are retained beside it. If the
process is interrupted, rerun the second command with the same configuration.
The final `results.json`, when present, is the experiment result; no result
is inferred from elapsed time or an intermediate loss.

Observed first uninterrupted 250-iteration checkpoint after the resume:
warm-up fresh-grid validation MSE 0.29038 and maximum absolute pool state 5.
This is an early training measurement, not a warm-up pass or failure. The
checkpoint appeared about 3 minutes 40 seconds after the resumed process
started, or approximately 0.92 wall seconds per iteration over that interval;
that rate is not guaranteed across later phases.

Completed regressions while the full run continued: P03 17/17, exhaustive
P04 11/11, P05 20/20 including the two new resume/curriculum tests,
repository smoke, oracle firewall, compileall, and `git diff --check` passed.

Deliberate differences from the paper beyond the necessary six-output Hanoi
adaptation: the v2 input/output coordinates stay fixed, grid damage/noise is
not introduced, the v2 inference/training state clip remains in force, and
supervised optimal-action labels replace DQN rewards. These choices favor a
clean test of whether a more sustained communication curriculum teaches v2;
they do **not** permit an exact-paper-replication claim.

## Measurement caveat

The prior v2 report's 9,261-second elapsed time included an approximately
two-and-a-half-hour gap between checkpoint timestamps, so it must not be used
as CPU throughput. The 10-iteration full-configuration launch took 18.38
seconds including process startup and corpus construction; longer uninterrupted
intervals are needed for a useful throughput estimate. This report will be
updated with measured full-run and regression evidence once available.
