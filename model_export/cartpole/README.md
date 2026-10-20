# Restricted local CartPole checkpoint regeneration

`export_local.py` is a P06-only local float32 weight serialization and
bitwise round-trip check. It refuses to run until the accepted ten-seed
qualification summary passes, or `--accepted-freeze` validates the explicitly
accepted ADR-0011 resolved manifest. The original failed summary is preserved.
It verifies the pinned upstream clone and
model2 SHA-256, then writes only inside ignored `artifacts/`. No weight
tensor, `.mem`/`.hex`, image, literal fixture or device bitstream belongs
in Git or a shared bundle without an explicit rights determination.

The checked-in manifest can reference weight identities and safe
regeneration instructions. It must not embed values. This float32 local
export is not a quantized memory format or a hardware-ready image. P07/G4 has
accepted fidelity32 with bounded measured evidence. The synthetic
unit test exercises serialization without requiring licensed checkpoints.

`fixed_point.py` is P07's scheduled integer golden. Accepted ADR-0012 selects
fidelity32 via `sw/cartpole/arithmetic.accepted.v1.json`; `accepted_arithmetic.py`
validates its format, evidence and bound hashes. `test_fixed_point.py` uses public synthetic weights for exact
rounding, bounds, overflow, cell and scheduling checks. P07 protocol, measured
results and restricted vectors are under `experiments/p07_cartpole/`. G4 is
complete; full-horizon fixed-point performance is not yet qualified and P08/RTL
requires a separate explicit request.
