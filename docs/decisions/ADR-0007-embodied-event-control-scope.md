# ADR-0007: Embodied sparse/event-based NCA control scope

- Status: Accepted for scope migration; benchmark and implementation forks remain open
- Accepted: 2026-10-06
- Decider: User
- Stage: Cross-stage documentation migration; next active stage E00
- Supersedes: ADR-0002's Hanoi derivative task/interface requirement only; the immutable original NCA remains accepted
- Related: EMBODIED_NCA_VISION.md; active implementation program and implementation status
- Superseded in part: accepted ADR-0008, 2026-10-07, selects reference CartPole first and defers custom surface/EvoGym to post-FPGA extensions; long-term embodied/event motivation remains.

## Evidence and decision

The user requested retroactive alignment of documentation, plans and stages with an embodied NCA FPGA accelerator baseline for sparse/event-based autonomous robotic workloads, rather than Tower of Hanoi. The user separately chose “Compare benchmarks before selecting one.”

Adopt this engineering scope. Preserve original NCA reproduction and all Hanoi code, tests, reports, experiments and provenance as historical assets. Do not reinterpret completed historical tests as evidence for the new plant or event model. Historical P05 experiments do not constitute a successful model freeze.

Introduce E00–E02 as explicit bridge stages for benchmark selection, environment/replay, and software control/event semantics. Reuse future P06–P23 identifiers with revised prompts, not historical task-specific constants. G2E and G3E are new decisions; old G2/G3 decisions cannot authorize them.

## Alternatives and consequences

Continuing Hanoi fails the new objective. Silently choosing the proposal's balancing surface would bypass the requested benchmark comparison. Erasing/relabeling earlier work destroys evidence. The accepted migration updates operative routing and preserves history.

No particular benchmark, physical apparatus, sensor mapping, action encoding, clock topology, event threshold, patch geometry, numeric format, deadline, or performance improvement is accepted by this ADR. Those require the designated gates. The initial DE1-SoC/private/portable policy remains; fit and I/O must be reassessed for the selected workload.

A dense folded implementation is an intermediate verification checkpoint. Completion of the revised baseline requires sparse/event-based FPGA control evidence. ASIC fabrication and actual CEC are not semester promises.

## Validation

### User clarification — 2026-10-06

The user confirmed the sequence: provide benchmark comparisons, let the user select, then replace the Hanoi benchmark. The user also accepted FPGA control of a simulated physical plant as the semester endpoint and specified one semester. No physical apparatus is required. Benchmark choice remains open; “one semester” does not supply an absolute due date or remaining week count. This clarification does not authorize new task-specific code/training before selection.

Documentation/governance checks and unchanged historical regression results are recorded in the scope-migration implementation status entry. No model, environment, RTL or board implementation was changed by this decision.
