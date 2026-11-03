# Portable SystemVerilog core

The current accelerator epoch hierarchy contains exactly five modules:

| File | Role |
|---|---|
| `nca_epoch_core.sv` | Top-level pipeline, memory arbitration, old-row release, source postwrites and complete epoch commit |
| `nca_banked_state.sv` | Four-bank persistent grid |
| `nca_row_window.sv` | Three shared old-row buffers and zero-padded neighborhood selectors |
| `nca_row_stage.sv` | Convolution, Dense 1 and Dense 2 arithmetic instances, coefficient sharing and ready/valid ownership |
| `nca_round_sat.sv` | ReLU, nearest-even rounding and signed saturation |

`files.f` is the production source list, with paths relative to the repository
root. Accepted fidelity32 remains the default. Architecture and interface details
are in `docs/architecture/ROW_PIPELINE_EPOCH_CORE.md`; verification is under
`tb/row_pipeline/` and `tb/row_stage/`.

The earlier folded local-rule engine and five standalone primitives moved to
`tb/legacy_rtl/`. They are test fixtures for historical P08/P09 regressions and
are not production synthesis inputs. Their original bytes are preserved.

The 2026-10-30 readability cleanup removes comments from production RTL and
replaces abbreviated internal names with descriptive names. Public module,
parameter and port names remain stable. See
`docs/verification/RTL_CLEANUP_RENAME_MAP.json` for the mapping and
`docs/verification/RTL_CLEANUP_2026_10_30.md` for actual checks.

The implementation is still an epoch engine. G5 physical acceptance, the full
action controller, autonomous RNG, transport, FPGA wrappers and board evidence
remain outstanding. No fit/Fmax/power result follows from simulation.
