# ADR-0015: Row-pipeline implementation direction and reference corrections

- Status: **Accepted for implementation direction and validation**
- Accepted: 2026-10-28
- Decider: User, with implementation details delegated to the agent
- Stage/gate: P07 extension, then P08–P14 in dependency order; stop at unresolved human gates
- Supersedes: Imported revision 1.0 wording where it conflicts with the original executable; no accepted numerical manifest is superseded by this ADR

## Decision and authorization

The user supplied `docs/architecture/NCA_DE1_SOC_RTL_ARCHITECTURE_SPEC.md`, then chose the more reference-faithful behavior for observation injection, mandatory postwrites despite zero masks, and output-channel increments. The user delegated unresolved hardware choices and, after discussing ordinary stage registers and predictable handoffs, authorized implementation, retroactive changes/tests, ledger/traceability updates and stopping at human gates.

Select a synchronous row pipeline, all 32 columns crossing stage boundaries together, initial MAC allocation 32/24/8, one persistent grid with safe in-place writes, three old-state row buffers, and no cross-epoch overlap. Ordinary producer working/output registers plus consumer input registers provide the required intermediate capacity; do not add redundant FIFOs or a second pair of buffers around them. Whole-row ready/valid and clock enables handle exceptional stalls. A producer must not overwrite a value until its consumer has captured it or completed its final read. Fixed nominal latencies do not waive ownership assertions.

Prefer four banks of 256 96-bit cell words for a 16-bit grid, eight transfer beats per logical row, subject to actual inference and timing. Keep banking replaceable behind a logical row interface. Retain explicit memory arbitration, tagged conservative old-row release and an owned pending delta row. Compare achieved timing/resource use against the nominal schedule; lane count and clock are targets until measured.

Keep technology dependencies in wrappers, exact replay injection/readback, a source-compatible autonomous RNG/sampler for primary fidelity, mask clock enables with mandatory postwrites, and framed UART with one outstanding decision, duplicate suppression and explicit recovery. The physical board path must be confirmed before board signoff. See the reconciliation report section 12 for implementation details and evidence requirements.

## Reference behavior retained

Keep the unchanged frozen model2, original graph and 1,916 parameters. Use 50–59 epochs, lowest-index ties, raw random initialization, learned update from the existing grid followed by source clears/markers/observation writes. Output channels 4/5 receive +1 each epoch even with zero masks; the learned update may counteract it. The host scales float32 observations exactly once at the declared frontend boundary. No training or weight replacement is selected.

## Numerical gate

16/F10 state, 16/F12 weights and 48/F22 bias/accumulators are the requested candidate, **with validation**. This preference is not evidence that control performance passes. ADR-0012/fidelity32 and `arithmetic.accepted.v1.json` remain the accepted numerical authority until a separate evidence-bearing superseding decision. Add candidate artifacts separately; do not rewrite the original P07 evidence or its bound source files. If testing reveals a new quality/capacity tradeoff, return to the human gate with measurements and options rather than silently accepting an inferior controller or retraining.

## Scope and consequences

This authorization permits related implementation work in order and preserves stage gates; it does not mark P08–P14 complete, resolve unmeasured G5/G6 evidence, start historical Hanoi training, authorize weight redistribution, or establish FPGA fit/Fmax/power. Fixed-point equivalence, numerical control quality and physical implementation are separate evidence obligations. Full Clef and ASIC endpoint choices remain later work.
