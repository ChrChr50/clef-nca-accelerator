# Production RTL cleanup — 2026-10-30

User-authorized source maintenance. The accepted fidelity32 arithmetic, model,
public module/parameter/port interfaces, scheduling and G5 status are unchanged.

## Production and historical source layout

`rtl/core/files.f` lists exactly five active modules: epoch core, banked state,
row window, row stage and round/saturate. The following obsolete production
modules were moved to `tb/legacy_rtl/`:

- `nca_local_rule.sv`
- `nca_mac_stream.sv`
- `nca_guard_add.sv`
- `nca_word_pack.sv`
- `nca_event_counter.sv`
- `nca_elastic_word.sv`

These remain byte-identical historical P08/P09 test fixtures. Removing them from
production does not delete the old evidence or disable those regression tests.
Their comments and names are preserved for historical attribution; current
production RTL contains no comments. Historical teaching notes have a location
notice, and current source lists/test runners reference the correct directories.

## Names and source preservation

All five active modules have clearer internal names, totaling 165 identifier
renames. Examples:

| Earlier name | Current name | Module |
|---|---|---|
| `front` | `fetch_state` | Epoch core |
| `wb_sent` | `old_row_beats_requested` | Epoch core |
| `cv` | `convolution_result_valid` | Epoch core |
| `cm` | `convolution_update_mask` | Epoch core |
| `term` | `input_feature_index` | Row arithmetic |
| `slot` | `output_slot` | Row arithmetic |
| `valid` | `buffered_row_valid` | Row window |
| `REM_MASK` | `discarded_bit_mask` | Rounding |

The full mapping is in `RTL_CLEANUP_RENAME_MAP.json`. Formatting changes split
compound statement lines and wrap long lines. Module/parameter/port names stay
stable for existing callers. Assertions, synthesis guards and arithmetic remain.

Pre-cleanup sources and complete epoch evidence are saved under ignored
`artifacts/rtl_cleanup/before/`. The refactor checker compares all **7,175 HDL
tokens** after comment/whitespace removal and the declared identifier mapping;
it rejects any other change. It also verifies byte identity of all six historical
fixtures and checks that retired sources are absent from production.

## Verification — complete

All commands below passed using `.venv-p05/Scripts/python.exe`, Python 3.12.14,
NumPy 2.3.5 and the existing local Icarus 12.0 development toolchain. Native HDL
execution used reviewed execution as in the prior stage; no tool was installed.
Put `artifacts/toolchain/iverilog/bin` on PATH. The regression driver supplies a
workspace-local temporary directory for tests that create files.

| Command after the Python prefix unless shown otherwise | Observed result |
|---|---|
| `tb/rtl_cleanup/check_refactor.py` | PASS: 7,175 tokens, no active RTL comments, exact five-file source list and six byte-identical historical fixtures |
| `iverilog -g2012 -Wall -s nca_epoch_core -f rtl/core/files.f -o artifacts/rtl_cleanup/production.vvp` (native command) | PASS, exit 0; production-only elaboration, not synthesis |
| `tb/rtl_cleanup/run_regressions.py` | All 18 commands PASS; exact subcommands/exit codes in `artifacts/rtl_cleanup/regressions.json` and per-command logs |
| `tb/row_pipeline/run.py --jobs 4` | Four synthetic configurations PASS, both widths and mask modes, three persistent epochs each |
| `tb/row_pipeline/run.py --restricted --format fidelity32 --jobs 2` | Both frozen-model2 accepted-width mask modes PASS, three persistent epochs each |
| `tb/row_pipeline/collect_evidence.py` | PASS: current RTL/source/tool identities, 18 epochs, 110,592 grid and 1,032,192 layer comparisons |
| `tb/rtl_cleanup/collect_evidence.py` | PASS: all 150 generated input/golden hex files unchanged from before cleanup; 31 protected identities unchanged; source/replay/regression evidence bound |
| `-m compileall -q tb/rtl_cleanup tb/row_pipeline tb/row_stage tb/p08_primitives tb/p09_local_rule` | PASS |
| `git diff --check` | PASS; pre-existing line-ending notices only |

The 18-command driver includes the window test (55,296 comparisons per width),
row arithmetic (eight configurations / 24 rows / 11,904 output comparisons),
both memory widths (all 6,144 scalars each), common coefficient/request-spacing
checks, P08/P09 synthetic and checkpoint HDL, 105 retained Python tests, 18 P07
vector cases, upstream revision/13 artifact hashes/three checkpoint rollouts,
and scaffold/reproducibility/oracle-firewall checks. Fixture relocation does not
remove any of these checks. The driver itself is the exact executable command
inventory; its logs are under ignored `artifacts/rtl_cleanup/`.

Measured full-grid behavior remains unchanged: 43,326 clocks per epoch under the
fixed 16-enabled/3-paused test schedule, 256 frontend reads / 256 writeback reads /
256 writes, and 1,904,640 unskipped MACs. Skipped mixed/zero/full cases execute
892,800 / 0 / 1,904,640 MACs. All mandatory postwrites, boundaries, pipeline
overlap, reset and persistent-state checks pass. This is exact functional replay,
not new policy qualification, measured FPGA timing or physical netlist equivalence.

Old reports remain under `artifacts/rtl_cleanup/before/row_pipeline/`; fresh
reports retain new source hashes under `artifacts/row_pipeline/`. The combined
cleanup record is `artifacts/rtl_cleanup/evidence.json`. Checkpoint-derived files
and their backups remain ignored. Current names require the updated hierarchical
test probes; public module/parameter/port interfaces are unchanged.

No commit/push, training, qualification campaign, synthesis, physical acceptance
or controller implementation is part of this maintenance request.
