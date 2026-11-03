# ADR-0018 — G5 row-pipeline physical disposition

Date: 2026-10-30

Status: **Proposed / unaccepted.** This is not numerical acceptance or G5 signoff.

## Proposed decision

Retain accepted fidelity32 and proceed to targeted synthesis/inference of the
functionally tested shared-row epoch pipeline. Keep 32/24/8 lanes and four cyclic
cell-word banks provisional until actual RAM/DSP/ALM and timing evidence exists.
Use source-exact host replay/observation conversion for initial integration,
while retaining the separately required source-compatible autonomous RNG and
controller/transport decisions as explicit G5 obligations.

The detailed options, logical storage accounting, replay and transport boundary,
consequences, evidence and next stop are in
`docs/architecture/P10_G5_ROW_PIPELINE_PACKET.md`.

## Acceptance conditions

Inspect exact functional evidence and actual target mapping/timing before freezing
the final architecture. A functional epoch simulation cannot prove DE1-SoC fit
or physical coefficient sharing. Select an explicit host/FPGA draw/conversion
boundary and physical transport, configuration/reset protocol and service model
before the complete deployment controller is finalized. Return with measured
alternatives if resources or timing fail. Do not accept row16's quality loss,
change frozen weights, or resume historical training implicitly.
