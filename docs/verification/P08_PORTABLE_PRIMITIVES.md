# P08 portable primitives — 2026-10-07

Status: **Implemented; HDL verification pending, not fully complete**.
No P09 execution or G5 decision. The recorded missing-tool
fallback preserves real RTL/tests and records unrun checks rather than claiming
an HDL pass. Accepted manifests were validated read-only and remain unchanged.

## Artifacts

Six SystemVerilog modules under `rtl/core/` implement requantization/ReLU,
guarded residual/marker addition, explicit full signed products and bias-last
streamed MACs, container packing, acceptance-counted saturation diagnostics and
one-entry elastic transport. Interfaces and abstract memory obligations are in
`docs/architecture/P08_PRIMITIVE_INTERFACES.md`; proposed ADR-0013 records the
seams without accepting final lane count, memory, bus, RNG or clocks.

`tb/p08_primitives/run.py` generates a deterministic self-checking SystemVerilog
bench (seed 808), verifies scalar expectations against the existing P07 golden,
and can compile/run Icarus. Assertions cover parameter/protocol/fan-in constraints;
the bench covers rounding/extrema, ReLU, sign extension, saturation, valid bubbles,
input/output stalls, reset cancellation, simultaneous retirement/replacement and
counter overflow. These temporal/assertion checks are **prepared but unrun**.

Public synthetic coverage: 756 requantizations, 72 guarded additions, nine
packing checks, 180 MAC transactions/5,895 products, fan-ins 1/20/30/54.
The independent Python scalar cell implementation agrees at two corners and
one interior synthetic cell, including all three layers.

Restricted coverage additionally binds all six accepted P07 NPZ hashes and
eight independently checked cells per case (48 cells): 3,444 requantizations,
2,868 MAC transactions/95,175 products total, plus the public primitive tests.
Generation checks each accumulator/layer output and saved delta, but does not
constitute RTL simulation, a full epoch test or production integer ROM export.
All generated checkpoint-derived literals remain in ignored local artifacts.

## Commands and observations

Python is `.venv-p05/Scripts/python.exe`, 3.12.14; NumPy 2.3.5 remains locked.

| Command | Observed result |
|---|---|
| Read-only `load_frozen()` / `load_accepted_arithmetic()` | PASS; explicit model2 freeze / accepted-G4-fidelity32 |
| `-m unittest tb.p08_primitives.test_vectors -v` (first run) | 2 pass, 1 fail: synthetic bias signs caused cancellation rather than saturation; corrected test vectors |
| Same P08 tests after correction | 3/3 PASS, 0.234 s |
| `-m unittest tb.p08_primitives.test_vectors model_export.cartpole.test_fixed_point model_export.cartpole.test_accepted_arithmetic model_export.cartpole.test_export_local -v` | 19/19 PASS, 0.797 s |
| `-m unittest discover -s sw/cartpole/tests -q` | 12/12 PASS, 0.988 s |
| `-m unittest discover -s reference/original_nca/tests -q` | 17/17 PASS, 0.147 s |
| `experiments/p07_cartpole/check_vectors.py` | PASS; 18 complete P07 layer/epoch/readout replays, six accepted fidelity32 |
| `tb/p08_primitives/run.py --generate-only` | PASS; synthetic bench emitted; simulation NOT RUN |
| `tb/p08_primitives/run.py --generate-only --restricted` | PASS; six hash-verified local vector bindings and scalar/layer comparisons; simulation NOT RUN |
| `tb/p08_primitives/run.py` | Explicit missing-tool path; program returns 2, simulation NOT RUN (`iverilog/vvp` absent). PowerShell aggregates the failing native command as shell exit 1 |
| `-m compileall -q tb/p08_primitives` / `git diff --check` | PASS |
| `git check-ignore artifacts/p08_primitives/{restricted,synthetic}/tb.sv` (expanded paths) | Both generated benches ignored |

No `iverilog`, `vvp`, Verilator or Yosys was discovered on PATH; configured
verification/Quartus status is tools-not-installed. WSL executable exists but
reports the Windows Subsystem for Linux is not installed. No OS/toolchain
installation, reboot, paid license or external CI run occurred. Smoke CI now
has an explicit Ubuntu Icarus install and synthetic simulation step, but it has
not been pushed/run here and is not evidence of an HDL pass.

The ordinary shell helper failed before execution during setup; reviewed direct
execution worked. No accepted artifact or protected package source was modified,
so no governance hash refresh was needed. Existing dirty-worktree changes were
preserved; original reference and hash-bound integer golden were not edited.

## Remaining acceptance checks / resume only P08

With Icarus `iverilog` and `vvp` available, run `python tb/p08_primitives/run.py`
and locally `python tb/p08_primitives/run.py --restricted`; inspect recorded
versions/logs, repair any actual compile/simulation defects and rerun checks.
Do not reinterpret vector generation as simulation. Then audit synthesis with
the actual Quartus/open tool lane; no inferred resources/Fmax/PPA or portability
pass is recorded now. P08 stays verification-pending until its relevant required
checks pass. No full-horizon fixed/FPGA control reliability is implied.
