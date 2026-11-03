# Shared-row epoch RTL verification — 2026-10-30

Result: **PASS for the measured functional scope; G5 remains unaccepted.**
This implements the previously missing transcript frontend/pipeline/scheduler.
It does not establish FPGA fit, achieved clock, power, a complete action
controller, or a change in the frozen model's policy performance.

## Implemented scope

- `nca_row_window.sv`: three tagged old rows, common term decode, zero padding
  and scalar-per-column operand selections; no 32×54 captured convolution patch.
- `nca_row_stage.sv`: streaming/captured input alternatives, explicit shared
  coefficient reads, optional mask gating and clock enable, ordinary captured
  dense inputs and stable tagged producer results. Default standalone behavior
  remains compatible with the existing tests.
- `nca_epoch_core.sv`: connected convolution/Dense 1/Dense 2 pipeline,
  single-grid read arbitration, conservative old-row release, owned delta and
  old-center-row writeback, source postwrites and complete epoch barrier.
  Fidelity32 is default; row16 is a comparison parameterization.

See `docs/architecture/ROW_PIPELINE_EPOCH_CORE.md` for the exact interface,
ownership, counters, limitations and architecture map.

## Reproduction

Use `.venv-p05/Scripts/python.exe` (Python 3.12.14, NumPy 2.3.5), with the local
`artifacts/toolchain/iverilog/bin` on PATH. The observed tool is Icarus 12.0
development revision `s20150603-1539-g2693dd32b`; executable/version hashes are
in `artifacts/row_pipeline/evidence.json`. Native tool execution used reviewed
execution because this Windows sandbox previously failed to launch the toolchain.

| Command after the Python prefix | Observed result |
|---|---|
| `tb/row_pipeline/window.py` | Both widths PASS; 55,296 address/padding comparisons per width, all 32 loaded rows and invalidate behavior |
| `tb/row_pipeline/run.py --jobs 4` | Four synthetic configurations PASS: fidelity32/row16 × mask skipping off/on, three persistent epochs each |
| `tb/row_pipeline/run.py --restricted --format fidelity32 --jobs 2` | Both accepted-width frozen-model2 configurations PASS, three persistent epochs each; checkpoint/freeze/arithmetic identities validated |
| `tb/row_pipeline/collect_evidence.py` | PASS: source identities current; 18 epochs, 110,592 final-grid comparisons and 1,032,192 layer-output comparisons |
| `tb/row_stage/run.py` | Eight configurations, 24 rows, 11,904 output comparisons PASS; both widths and seven-lane tail variant |
| `tb/row_stage/memory.py` | Both widths/all 6,144 scalar locations each PASS; concurrency and collision retry |
| `tb/row_stage/audit_transcripts.py` | Both widths PASS: common coefficient values, 1080 active cycles and 1081 accepted-request interval |
| `-m unittest tb.p09_local_rule.test_support tb.p08_primitives.test_vectors model_export.cartpole.test_fixed_point model_export.cartpole.test_accepted_arithmetic model_export.cartpole.test_export_local model_export.cartpole.test_row16_candidate -q` | 31 tests PASS |
| `-m unittest discover -s reference/original_nca/tests -q` | 17 tests PASS |
| `-m unittest discover -s sw/cartpole/tests -q` | 12 tests PASS |
| `-m unittest discover -s reference/hanoi/tests -q` | 11 tests PASS; exhaustive 29,520 state/goal cases and 177,120 actions |
| `-m unittest discover -s training/hanoi_nca/tests -q` | 30 retained regression tests PASS; no historical training campaign resumed |
| `-m unittest model_export.cartpole.test_exact_blas experiments.row16_validation.test_resume -q` | Four tests PASS, including the bounded synthetic resume fixture |
| `experiments/p07_cartpole/check_vectors.py` | 18 complete saved P07 cases PASS |
| `reference/original_nca/tools/verify_upstream.py --upstream self-organized-control` | Revision, 13 artifact hashes and three checkpoint operator/CartPole rollouts PASS |
| `scripts/run_smoke.py` | Scaffold/reproducibility/governance/oracle firewall PASS |
| `-m compileall -q tb/row_pipeline` / `git diff --check` | PASS; pre-existing line-ending notices only |

The final Python regression total is **105**. For tests using temporary files,
set `TMP` and `TEMP` to the existing workspace `artifacts/testtmp` directory.
Initial executions using sandbox-generated Windows temp locations failed with
permission errors; reruns with the workspace temp directory passed. These were
filesystem failures, not numerical test failures. An initial generated-bench
syntax error (missing whitespace between case entries) was fixed before replay.
Initial full-grid simulation hit a 300-second timeout; three later profiling runs were deliberately stopped
while changing equivalent wide-vector storage to narrow word addressing and
running the final independent configurations concurrently. None is counted as
a pass. The completed final matrix uses a 900-second per-command limit;
observed per-case wall times were approximately 245–493 seconds under concurrent
load. Logs, generated benches, input hashes and source/tool identities are local.

## Measured behavior

All six configurations execute mixed, zero and full masks with changing
observations and persistent state. Seed 528 generates a mixed mask with 480 active
cells. Tests compare each completed row's three layer outputs with the unchanged
P07 integer golden and read every final grid word after each epoch. Inactive
learned outputs are zero in skip mode, while mandatory source postwrites remain.
Signed extrema exercise residual/marker saturation. Tests check their separate
counts, one commit per row, all 256 frontend reads, 256 writeback reads and 256
grid writes per epoch, reset invalidation and real overlapping stage activity.
The enabled-stage overlap monitor records 73,407 clocks across each three-epoch
test. Assertions guard old-row overwrite, epoch tags and committed-row reads.

Every completed epoch took **43,326 simulated clocks** under the fixed
16-enabled/3-paused-clock pattern. This is not an unstalled throughput number,
Fmax, wall-clock controller latency, or a universal liveness proof. Forward
progress is observed under that admitted stall schedule. With skipping off,
each epoch executes 1,904,640 MACs. With skipping on, mixed/zero/full masks execute
892,800 / 0 / 1,904,640 MACs. The schedule length is unchanged; no measured
energy saving follows from the work counter.

The shared coefficient accesses are explicit at source level. Actual memory
replication, ports, multiplier decomposition and placement require synthesis.
Counters are per transaction; lifetime counters belong in the later controller.
The 16-bit epoch tag wraps modulo 65,536 with no cross-epoch overlap; it is not
a globally unique lifetime trace identifier.

## Retention and stop

Restricted checkpoint-derived images, expected vectors, benches and logs stay
under ignored `artifacts/row_pipeline/`. The evidence collector hashes them
there without publishing the weights. The original reference, imported spec,
accepted numerical manifest/golden and all 31 protected package identities remain
unchanged. Existing staged publication changes are preserved; no commit, push,
hosted CI, synthesis, training or qualification campaign was dispatched.

The synthetic replay matrix is added as a separate CI job with a 20-minute
timeout; that new hosted job has not been executed here. Stop at proposed
ADR-0018/G5. An action-level 50–59-epoch sequencer, RNG/draw assignment,
integer readout/argmax, transport/recovery and board evidence remain outstanding.
