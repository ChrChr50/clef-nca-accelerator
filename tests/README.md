# Project regression tests

The retired folded engine and five standalone primitives are in `tb/legacy_rtl/`;
P08/P09 tests explicitly compile those historical fixtures. The production source
list is `rtl/core/files.f`. `tb/rtl_cleanup/check_refactor.py` compares current
production tokens with the ignored saved sources using the published rename map;
`tb/rtl_cleanup/run_regressions.py` records component/historical regression logs.

`tb/row_pipeline/window.py` checks every shared-window address and boundary at
both widths. `tb/row_pipeline/run.py --jobs 4` checks synthetic full-grid replay
with mask skipping on/off at both widths. Add `--restricted --format fidelity32
--jobs 2` for locally hash-checked frozen model2 replay; generated images and
checkpoints remain ignored. These test epochs, not a complete board controller.

scripts/run_smoke.py checks scaffold, governance integrity and the historical oracle firewall. Numerical reference tests live beside their models/environments; HDL verification belongs in tb/.

Retain original NCA and historical Hanoi/P05 regressions. New embodied plant, event semantics, overload and persistent-control tests are added in E01–P12 as authorized; historical passing tests do not establish the new benchmark.
