# Portable SystemVerilog core

Technology-independent SystemVerilog primitives for accepted fidelity32 now
live here. `nca_round_sat`, `nca_guard_add`, `nca_mac_stream`, `nca_word_pack`,
`nca_event_counter` and `nca_elastic_word` are P08 foundations, not a complete
NCA engine. See `docs/architecture/P08_PRIMITIVE_INTERFACES.md` and
`tb/p08_primitives/`. Quartus/Yosys compatibility is a required verification
target, not yet a measured portability pass. Vendor-specific memories, buses,
debug and clocks remain outside this directory.

P09 adds `nca_local_rule.sv`, a parameterized folded three-layer **delta-only**
engine. Read `docs/architecture/P09_G5_COMPUTE_PACKET.md` and
`tb/p09_local_rule/`; its lane alternatives are not a final G5 choice. P08/P09
HDL simulation and synthesis remain pending; Python/image checks are not RTL
signoff. There is still no grid/epoch/mask/RNG/board controller here.
