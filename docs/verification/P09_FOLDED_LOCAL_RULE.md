# P09 folded local rule — 2026-10-08

Status: **Implemented; HDL/synthesis verification pending, not fully complete**.
P08 remains pending; no earlier stage was relabeled complete. Stop before P10.
Proposed ADR-0014 and `P09_G5_COMPUTE_PACKET.md` supply the compute portion of
G5, not an accepted architecture or a final P10 gate decision.

Implemented portable `rtl/core/nca_local_rule.sv` with lane parameter, sequential
configuration validation, packed patch request/delta result, 54/20/30 fan-in
loops, 20/30/6 channel loops, exact accepted signed arithmetic and per-layer
trace/saturation events. Neighborhood acquisition, residual/mask/clamp, epochs,
RNG, readout and physical grid/bus remain outside this component. Existing P08
requantizer is reused without editing its source. See the compute packet for
configuration/reset/trace contracts, packing and full memory-demand estimates.

`tb/p09_local_rule/{support.py,run.py,test_support.py}` provides independent
Python-int cell calculations, synthetic and restricted parameter images,
two's-complement encoding/decoding and hash/round-trip checks, plus self-checking
generated HDL benches for lanes 1/2/3/4, bubbles, stalls, output backpressure,
invalid loads, loops, trace boundaries and reset. All generated arrays/images
and learned literals are in ignored local `artifacts/p09_local_rule/`.

## Observations and commands

Python commands use `.venv-p05/Scripts/python.exe` (3.12.14, locked NumPy 2.3.5).

| Command | Actual result |
|---|---|
| `-m unittest tb.p09_local_rule.test_support -v` initial | 4/4 PASS, 0.298 s |
| Same after adding residual/post-write boundary test | 5/5 PASS, 0.373 s |
| `tb/p09_local_rule/run.py --generate-only` | PASS: six synthetic cells, 336 layer accumulator/output pairs, image round-trip and bounds |
| `tb/p09_local_rule/run.py --generate-only --restricted` | PASS: all six accepted vector hashes, 48 scalar cells, 2,688 layer pairs; actual model2 bounds 58/57/57 bits |
| `-c` subprocess invocation of `tb/p09_local_rule/run.py` | **Exit 2 observed**; iverilog/vvp absent; simulation NOT RUN |
| Combined P09/P08/fixed/accepted/export unittest modules, before boundary test | 23/23 PASS, 1.287 s |
| `-m unittest tb.p09_local_rule.test_support tb.p08_primitives.test_vectors model_export.cartpole.test_fixed_point model_export.cartpole.test_accepted_arithmetic model_export.cartpole.test_export_local -q` final | 24/24 PASS, 1.271 s |
| `-m unittest discover -s sw/cartpole/tests -q` | 12/12 PASS, 1.834 s |
| `-m unittest discover -s reference/original_nca/tests -q` | 17/17 PASS, 0.220 s |
| `experiments/p07_cartpole/check_vectors.py` | PASS, 18 saved complete layer/epoch/readout cases including six accepted fidelity32 |
| `reference/original_nca/tools/verify_upstream.py --upstream self-organized-control` | PASS; pinned revision, 13 artifact hashes, three checkpoint operator/plant rollouts |
| `scripts/run_smoke.py` | PASS; 16 scaffold files/20 directories, 28 governed hashes, dependency contract and oracle firewall |
| `-m compileall -q tb/p09_local_rule` / `git diff --check` | PASS |
| `git check-ignore` for restricted kernels.mem, biases.mem and tb.sv | All ignored |

53 final Python regression tests passed across combined/host/reference suites.
Scalar equality/image checks are genuine software evidence, **not RTL equality**.
The candidate structural active-cycle counts (1/2/3/4 lanes: 1,862/932/640/492)
are computed from the implemented loops; no cycle, fit, DSP, Fmax or power
measurement is claimed. Parameter storage is 48,112 raw bits; actual inference
of behavioral arrays and lane read ports remains untested. Full-horizon fixed
and FPGA control reliability remain unqualified.

Local tool discovery again found no Icarus/vvp, Verilator or Yosys on PATH.
Configured Quartus is not installed. No tool installation, hosted CI, push,
commit, P10 implementation or P08 repair/acceptance occurred. CI now contains
rights-safe synthetic P09 checks after its Icarus setup, but has not been run.
Normal execution helper failed before command execution; reviewed direct shell
execution worked. Existing dirty-worktree changes were preserved. Accepted
manifests/golden/package sources were unchanged, so governance remains 28 hashes.

## Reproduction / remaining requirements

With Icarus/vvp available, run `python tb/p09_local_rule/run.py` and locally
`python tb/p09_local_rule/run.py --restricted`; inspect real logs and fix/retest
any HDL defects. Complete P08 verification separately rather than fabricating
a pass. Actual synthesis is still needed to compare G5 alternatives. Keep
restricted images/fixtures local; do not upload them as CI artifacts. P09 stays
verification-pending until required HDL checks pass. **No P10 authorization.**
