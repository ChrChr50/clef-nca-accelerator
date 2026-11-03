# ADR-0017 — Implement the shared-row pipeline without changing arithmetic acceptance

Date: 2026-10-30

Status: **Accepted implementation scope**, by the user's request to implement the
audited transcript recommendations. This does not accept a numerical replacement
or resolve G5 physical architecture signoff.

## Decision

Proceed with portable, width-parameterized architecture work using accepted
ADR-0012 fidelity32 as the default. Keep row16 as a comparison configuration;
ADR-0016's measured quality loss and unaccepted numerical disposition remain.
No qualification/training process or automation resumes.

Implement three tagged shared old-row buffers, common convolution-term decode,
one scalar operand per convolution lane, explicit coefficient broadcasts,
whole-row ready/valid transfers through the three stages, exact mask-based MAC
gating, and a single-grid overwrite scheduler. Use ADR-0015's conservative old-row
release rule. No second full grid or replicated convolution patch registers are
required. Ordinary stage outputs and captured dense inputs remain real storage.

Keep the four cyclic cell-word banks and eight beats per row as a testable
implementation candidate. The current 24-lane Dense 1 mapping has **three** shared
coefficient-address groups per cycle; convolution and Dense 2 each have one.
This is source-level sharing, not proof of a particular mapped ROM/DSP layout.

## Boundary and consequences

The epoch engine accepts an externally supplied cell mask and eight already
scaled/quantized source observations. It performs mandatory postwrites after
the learned update and commits the entire generation before accepting another
epoch. Externally visible initialization/readback occurs while idle. Reset
invalidates configuration and grid validity without resetting the backing RAM.

An action-level 50–59-epoch sequencer, source-compatible autonomous random draws,
framed transport, actual FPGA inference/timing/fit, and end-to-end board control
remain later obligations. They must not be implied by epoch-level equivalence.

Stop at G5 with actual functional evidence and a proposed physical disposition.
Preserve the original reference, imported architecture spec, accepted arithmetic
and hash-bound golden. Update routing/governance to distinguish this newly
authorized architecture work from the still-unaccepted row16 numerical change.
