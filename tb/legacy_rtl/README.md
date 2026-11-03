# Historical RTL test fixtures

These six modules are retired from the accelerator's production RTL hierarchy:

- `nca_local_rule.sv`: earlier folded cell engine.
- `nca_mac_stream.sv`, `nca_guard_add.sv`, `nca_word_pack.sv`,
  `nca_event_counter.sv`, `nca_elastic_word.sv`: earlier standalone primitives.

Only the P08/P09 historical test runners explicitly compile these fixtures.
Do not include this directory in accelerator synthesis source lists. The current
production hierarchy consists of the five files in `rtl/core/` and is described
in `docs/architecture/ROW_PIPELINE_EPOCH_CORE.md`.

Original fixture contents are preserved, including comments and names, so old
implementation evidence remains attributable. The user's comment removal and
readability cleanup applies to current production RTL, not these archived test
fixtures. The shared `nca_round_sat.sv` remains in production and is also compiled
by the historical tests.
