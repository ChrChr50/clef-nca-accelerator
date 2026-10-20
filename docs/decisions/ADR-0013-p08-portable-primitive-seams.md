# ADR-0013: P08 portable primitive seams

- Status: **Proposed — implementation record pending HDL verification**
- Proposed: 2026-10-07
- Stage: P08; no new human gate; G5 remains unselected
- Supersedes: None
- Related requirements: P08-001 through P08-006

## Context and scoped choice

The user authorized only P08. ADR-0012 fixes fidelity32 and P07 supplies the
integer authority. Final lane count, memory partition, bus, RNG and clocks
must not be decided by introducing an oversized foundation framework.

Implement separate arithmetic, sign-extension and diagnostic primitives with
a reusable single-lane dot-product stream and one-entry same-clock elastic
transport. The single-lane primitive is a reusable block, not a selected
accelerator parallelism. Synchronous reset cancels partial/pending primitive
transactions. Saturation flags travel with results; counters advance only on
consumer acceptance and saturate with sticky overflow. This transaction seam
is independent of plant/controller/epoch reset semantics.

Alternatives for later integration include combinational unrolled MAC arrays,
multiple instances of the stream, or a pipelined folded engine; choose at G5
with fit/timing/ownership evidence. RAM request tags, queue depths and CDC
are deferred until there is an actual selected interface requiring them.

## Consequences and evidence boundary

Portable SystemVerilog contains no vendor primitives or model weights. Synthetic
vectors are rights-safe; checkpoint-derived verification benches remain ignored
and local. Python scalar/P07 consistency checks pass, but local HDL tools are
absent: simulation, assertions, synthesis and vendor/open-flow correlation
remain unrun. This record is not human acceptance, G5 approval or an RTL pass.
See `P08_PRIMITIVE_INTERFACES.md` and the implementation status for exact evidence and commands.

No model behavior, numeric format, memory ownership or Clef closure claim changes.
Stop after P08; do not implement P09 automatically.
