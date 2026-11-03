# Row-pipeline continuation: G4 return packet

Date: 2026-10-28. Status: **at G4; numerical replacement unaccepted**.

ADR-0015 accepts the user's implementation direction and source corrections. The imported spec has been turned into a corrected implementation contract, a separate numerical candidate, and tested reversible row-stage/storage RTL components. Full architecture/controller implementation stops here because a new control-quality tradeoff was measured. This is not a claim that the entire spec or P10–P14 are complete.

## Decision

Select the response to row16's earlier control failure: retain fidelity32 for the row implementation (recommended), authorize a predeclared new 16-bit quantization experiment, or explicitly accept the measured row16 limitation. Proposed ADR-0016 records options, schedule/portability consequences and recommendation. No new human choice is presumed from the earlier delegation of implementation details.

## Numerical evidence

Same frozen model2 and original graph, same source plant/episode protocol, 50–59 steps, source I/O ordering, independent persistent grids/plants and identical logical mask/count draws. Python 3.12.14 and NumPy 2.3.5. Candidate format was declared before the runs and not tuned on the results.

| Seed | Role | Screen cap | Float / fidelity32 / row16 survived cap | First row16 action difference from float |
|---|---|---:|---|---|
| 10 | Reused calibration | 128 | Yes / yes / yes | 67, identical current observation |
| 12 | Reused calibration | 128 | Yes / yes / yes | None within cap |
| 40 | New validation | 256 | Yes / yes / yes | None within cap |
| 41 | New validation | 256 | Yes / yes / yes | 101, identical current observation |

All screen saturation counts are zero. Fidelity32 matches all screen float actions. These are censored screens, not full-episode wins. Kernel quantization clips no weights, and full-valid-state accumulator bounds require 32/31/31 signed bits for the actual row16 coefficients, within 48 allocated bits. This safety proof does not establish recurrent policy stability.

The longer campaign uses the same four seeds, explicitly disclosing screen reuse. It stopped on new numerical evidence:

| Seed | Float actions saved | fidelity32 actions saved | row16 actions saved | State at stop |
|---|---:|---:|---:|---|
| 10 | 2272 | 2272 | 2272 | All censored/alive |
| 12 | 1312 | 1312 | 1312 | All censored/alive |
| 40 | 1328 | 1328 | 1328 | All censored/alive |
| 41 | 1488 | 1488 | **1150** | row16 terminal, pole-angle limit; comparators censored/alive |

No row16 saturation is recorded in these saved long checkpoints. The seed-41 failure occurs before the original source horizon; therefore the environment's episode cap does not explain it. Changed precision changed the decisions and trajectory. This is evidence of an earlier failure in one paired case, not an estimated population failure rate or proof that every 16-bit format is unsuitable. The three live/censored candidate runs do not cancel the recorded failure.

All comparison processes were explicitly stopped at the gate. Checkpoints every 16 completed logical actions preserve grids, plants, source RNG state, counters and identities under ignored `artifacts/row16_validation/long/`. No background training or automation is running. `gate_summary.json` is a safe, hashed aggregate snapshot; `long_summary.json` was not fabricated as complete.

## Concrete implementation and verification

- `ROW_PIPELINE_IMPLEMENTATION_CONTRACT.md` corrects the original spec without editing its 529-line imported snapshot. The source-faithful three corrections, count range, ties, parameter count, Q-format widths and ROM layout are explicit.
- `row16_candidate.py` reuses the immutable/reference-bound golden; it does not change the accepted manifest. Output-major ROM conversion is independently round-tripped; signed hex export is confined to ignored artifacts.
- Six checkpoint-derived candidate vector cases include all layer accumulators/outputs, complete post-write state, eight independent scalar cells each, persistent epochs 1/2/59 and readout/action. Generation and replay pass. All 18 old P07 cases still replay exactly.
- `nca_row_stage.sv` provides testable portable whole-row arithmetic under both precisions. Eight configurations / 24 rows / **11904 output-word comparisons** pass independent scalar expectations, tags, saturation counts, input capture, backpressure, incomplete configuration rejection and reset abort. Simulated enabled cycles are 1080/800/720 for 32/24/8 lanes; the seven-lane final-stage tail measures 840.
- `nca_banked_state.sv` provides portable single-grid storage. At both widths, all 6144 scalar locations, concurrent distinct-address transfers, collision blocking/retry, response tags and reset-without-RAM-clear tests pass.
- These prototypes do not contain the complete line-buffer/generation scheduler, recurrent postwrite/readout controller, autonomous RNG or UART. The convolution stage test supplies explicit patches; final shared-window implementation and physical ROM/activation ports still need work. No FPGA fit, Fmax or power claim follows.

## Existing RTL verification advanced

Installed Icarus in ignored `artifacts/toolchain/iverilog/` and recorded its version: `12.0 (devel) (s20150603-1539-g2693dd32b)`. The distributor's v12-20220611 installer SHA-256 is `A614057374DFAED5DA0FE454CDEB410E54981FD85DBD28BD472F4CCB765DEB84`. Source: [Icarus Windows distributor](https://bleyer.org/icarus/), linked from the upstream installation guidance. Install exit 0; no reboot. Installer/uninstall metadata and the install log remain local; binaries are not committed.

Both synthetic and restricted P08 benches now pass locally. Both synthetic and restricted P09 benches pass with lanes 1/2/3/4; restricted coverage includes all six accepted fidelity32 vector cases and 48 scalar cells / 2688 layer pairs per lane configuration. Earlier normal-sandbox native compiler calls returned -1 without diagnostic output; reviewed execution outside those process restrictions passed. No RTL arithmetic fix was required for those existing modules. Synthesis remains unrun.

## Commands and results

Use `.venv-p05/Scripts/python.exe` for Python. For HDL commands prepend the local Icarus `bin` directory to this process's PATH. Full commands/logs are in ignored artifact reports.

| Command | Observed result |
|---|---|
| Existing P09/P08/fixed/accepted/export unit modules plus `test_row16_candidate` | 31/31 pass, 1.518 s; initial existing-test temp permission errors resolved by using a writable artifact temp directory |
| Original-reference, CartPole deployment, historical Hanoi and historical training discoveries | 70/70 pass, 13.874 s; exhaustive 29520 states / 177120 actions retained |
| `-m unittest model_export.cartpole.test_exact_blas -v` | 3/3 pass, 0.727 s; optional backend not used in primary campaigns |
| `-m unittest experiments.row16_validation.test_resume -v` | 1/1 pass, 26.867 s; interrupted/restored versus uninterrupted numerical state/plant/RNG/count equality |
| `experiments/row16_validation/vectors.py` / `--check` | Six new cases generated and replay pass; local ROM layout round-trip |
| `experiments/p07_cartpole/check_vectors.py` | All 18 existing complete cases pass |
| `tb/p08_primitives/run.py` / `--restricted` | Both HDL simulations pass |
| `tb/p09_local_rule/run.py` / `--restricted` | Both HDL suites pass, lanes 1/2/3/4 |
| `tb/row_stage/run.py` | Eight HDL configurations / 24 rows pass |
| `tb/row_stage/memory.py` | Both widths pass complete mapping/concurrency/collision tests |
| `scripts/run_smoke.py` | Scaffold, pinned runtime and oracle firewall pass |
| Python compileall for new candidate/experiment/bench files | Pass |

105 unit tests passed across the recorded suites; HDL/vector runs are additional. The first resume fixture terminated before its intended action-16 checkpoint, so the test was corrected to widen the **unit-only** synthetic plant limits. Qualification/evaluation plant limits never changed.

Final consolidated run after the workspace/routing changes: all **105 tests passed in 41.557 s**, using unittest loading of the eight arithmetic/support/candidate/resume modules and four reference/deployment/historical discovery suites. Upstream verification passed the pinned revision, 13 artifact hashes and three checkpoint operator/CartPole rollouts. Both accepted manifest loaders validate unchanged; all 31 protected hashes validate. Imported spec SHA-256 remains unchanged. `git diff --check` passed, with existing line-ending normalization notices only. A final process query confirmed zero remaining task comparison processes. Tool binaries, learned images and progress states are ignored.

CI was extended with rights-safe candidate, resume, row-stage and memory tests; the updated workflow was not pushed or dispatched in this task. The original reference, bound accepted arithmetic, weights and old empirical results were preserved. Implementation-package routing is explicitly updated for this authorization and its integrity manifest refreshed; it does not authorize advancing past this newly reached gate.

## Next readiness

The subsequent user-requested diagnosis and hardware-cost analysis is in `docs/verification/ROW16_DIAGNOSIS_AND_PRECISION_COST.md`. It adds exact saved-case replay, input/history interventions and sourced logical/DSP cost estimates without accepting this gate or resuming qualification. New evidence identifies a changed decision already at action 101, grid-history dependence in late responses and an already inevitable one-step terminal transition at 1150. It does not turn those probes into population control-quality or physical-fit evidence.

The row arithmetic and banked storage components are usable test prototypes. P08/P09 existing HDL gaps are closed locally; synthesis and final row-architecture signoff remain pending. P10 scheduler proof and G5, P11 complete core, P12 integrated co-simulation and P13/P14 board/control signoff remain incomplete. On disposition, continue from these files rather than redo P03 or restart Hanoi. No commit/push, weight publication or model training occurred.
