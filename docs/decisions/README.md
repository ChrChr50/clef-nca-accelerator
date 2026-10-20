# Architecture Decision Records

Architecture Decision Records (ADRs) preserve choices that constrain later architecture, portability, numerical behavior, verification, or scientific interpretation.

## Lifecycle

1. Copy `ADR-TEMPLATE.md` to `ADR-NNNN-short-title.md` using the next four-digit number.
2. Use `Proposed` while evidence is being gathered.
3. Human-gate ADRs must remain `Proposed` and must identify their gate until the user explicitly chooses an option.
4. Change the status to `Accepted` only after the authorized decision. Record the decision date and evidence.
5. Use `Superseded by ADR-NNNN` rather than rewriting an accepted decision. Use `Rejected` for considered choices that were explicitly declined.
6. Link the ADR from the relevant implementation status entry and requirements rows.

Do not use an ADR to turn a speculative mechanism or scientific claim into an established result. Evidence and claim level remain separate.

## Index

| ADR | Title | Status | Gate | Stage |
|---|---|---|---|---|
| ADR-0001 | Primary platform, toolchain, and repository policy | Accepted | G1 | P01 |
| ADR-0002 | Immutable original NCA and bounded Hanoi interface | Original reference retained; Hanoi scope superseded by ADR-0007 | Historical G2 | P03 |
| ADR-0003 | Hanoi training and runtime boundary | Historical proposed packet, inactive forward path | Historical G3 | P05 |
| ADR-0004 | P05 v2 relational Hanoi NCA experiment | Accepted for P05 experiment; no model freeze | G3 continuation | P05 |
| ADR-0005 | Gated teaching and smooth-bound experiment | Authorized for reversible P05 experiment; no model freeze | G3 continuation | P05 |
| ADR-0006 | P05 action-value teaching proposal | Historical proposed experiment; no model freeze | Historical G3 | P05 |
| ADR-0007 | Embodied sparse/event control scope | Motivation retained; first benchmark/sequence superseded by ADR-0008 | G3E subsequently accepted in ADR-0009 | Migration/E00 |
| ADR-0008 | Reference CartPole baseline; post-FPGA custom surface/EvoGym | Accepted benchmark/sequence; protocol later set by ADR-0009 | G2E complete; G3E subsequently accepted | E00 |
| ADR-0009 | CartPole checkpoint readiness and event boundary | Accepted conditional model2 protocol; P06 6/10 failed its 8/10 gate | G3E reopened for response | E02/P06 |
| ADR-0010 | Response to failed model2 full-horizon qualification | Proposed; unaccepted | G3E return | P06 |
| ADR-0011 | Freeze released model2 despite preserved qualification limitation | Accepted by explicit user decision; supersedes pre-freeze gate only | G3E resolved | P06/P07 prerequisite |
| ADR-0012 | CartPole fixed-point numerical and quality contract | Accepted fidelity32; bounded quality scope | G4 complete | P07 |
| ADR-0013 | Portable P08 primitive seams and transaction diagnostics | Proposed implementation record; HDL verification pending | None; does not select G5 | P08 |
| ADR-0014 | Folded P09 local-rule compute alternatives | Proposed; HDL/synthesis evidence pending | G5 compute portion; final choice deferred to P10 | P09 |

ADR-0004/0005 remain records of historical experimental authorization, not acceptance of the new benchmark or model. See the active vision and implementation status for current readiness.
