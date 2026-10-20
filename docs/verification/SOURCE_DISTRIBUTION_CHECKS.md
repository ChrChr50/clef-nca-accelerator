# Source distribution verification — 2026-10-20

The source distribution retains the controller implementation, technical
contracts, experiment measurements and reproducibility entry points.

## Behavior preservation

- All 82 retained Python/SystemVerilog implementation and test source files in
  reference, deployment, export, RTL, testbench, training and experiment trees
  are byte-identical to the pre-publication workspace.
- 94 local unit tests passed both before and after packaging. The committed
  archive also passed the same 94 tests, smoke checks, accepted-manifest
  validation and synthetic testbench generation.
- The existing empirical runner produced exactly equal reports before and
  after packaging for model2, 15 conditions, one seed and a two-action cap.
  This is a behavior-preservation smoke check, not control qualification.
- A machine-specific source-module path in parity metadata was made
  repository-relative. All measurements remain unchanged. Dependent model
  freeze and arithmetic artifact hashes were refreshed; all other contract
  values and selected verification-vector identities remain unchanged.
- JSON/JSONL evidence and the two hash-bound acceptance decisions preserve
  their serialized bytes across Git checkouts.

## Hosted verification

[GitHub Actions run 39435847067](https://github.com/ChrChr50/clef-nca-accelerator/actions/runs/39435847067)
completed successfully for commit
`8491a5a84acc42a26dc857d69ef51d21da892d50`.
The workflow includes Python regressions and synthetic P08/P09 Icarus
compile/simulation commands. Earlier stage reports correctly record that
local HDL execution was unavailable when those stages were implemented.

This new synthetic result does not establish checkpoint-derived HDL signoff,
synthesis, measured cycles, board fit, Fmax, power, a complete grid scheduler
or closed-loop FPGA operation. Those remain unverified. Model2's original
6/10 qualification and the bounded scope of fidelity32 quality evidence are
unchanged.
