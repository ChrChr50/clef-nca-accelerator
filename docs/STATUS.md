# Implementation status

2026-10-30: the audited transcript recommendations now have a functionally
verified shared-row epoch pipeline. See
`verification/ROW_PIPELINE_EPOCH_RTL_2026_10_30.md`: 18 persistent synthetic and
model2 epochs pass exact layer/final-grid comparison. ADR-0017 authorizes this
width-independent work with fidelity32 default. **Stopped at G5**, proposed
ADR-0018; final physical mapping and complete action/RNG/transport controller
remain outstanding. Row16's numerical replacement remains unaccepted. The dated
October 28 prototype-only description below is superseded for this architecture
scope; its measured numerical failure remains unchanged.

This document summarizes the existing implementation and evidence. Detailed
measurements remain in the verification reports and experiment results.

2026-10-28 continuation is **stopped at a new G4 numerical decision**. ADR-0015 accepts the row-pipeline implementation direction; row16 is not accepted arithmetic. It failed seed 41 at action 1150 while float/fidelity32 remained alive through 1488 saved actions. ADR-0016 and `architecture/ROW_PIPELINE_G4_RETURN_PACKET.md` contain options and evidence. Existing P08/P09 synthetic and restricted HDL now pass locally; parameterized row-stage and banked-storage prototypes also pass. The complete scheduler/controller and FPGA implementation remain incomplete.

| Area | Status | Evidence / boundary |
|---|---|---|
| Original NCA/CartPole reproduction (P03) | Complete with stated empirical limitations | `reference/original_nca/`; P03 verification reports; paper statistics not fully reproduced |
| Historical Hanoi environment/training (P04/P05) | Environment complete; training forward path superseded | Retained code, tests and negative findings; no accepted Hanoi model freeze |
| CartPole deployment (E00–E02) | Complete | `sw/cartpole/` interface/replay and host/controller tests |
| Model2 qualification/freeze (P06) | Model frozen by ADR-0011 despite failed original qualification | 6/10 horizon completions versus original 8/10 condition; evidence unchanged |
| Integer golden (P07) | fidelity32 accepted by ADR-0012 | Bounded integer/float comparisons; full-horizon fixed quality unverified |
| Portable primitives (P08) | Implemented; synthetic and checkpoint-derived HDL pass locally | Synthesis audit unrun |
| Folded local-rule engine (P09) | Implemented; synthetic and checkpoint-derived HDL pass locally | Connected row-stage epoch candidate also passes; synthesis/physical mapping pending |
| Grid memory/scheduler and integrated core (P10–P12) | Shared-row single-grid epoch pipeline verified; at G5 | Full action/RNG/transport controller incomplete; physical evidence and ADR-0018 acceptance pending |
| Board integration/demonstration (P13/P14) | Not implemented | No measured fit, Fmax, power or closed-loop FPGA result |
| ASIC and further embodied/Clef extensions | Later research | Separate evidence and design decisions required |

## Accepted baseline

- Same modified CartPole plant as the source, with four observations and two actions.
- 32×32×6 recurrent grid; 1,916 fixed shared parameters; 50–59 epochs per action.
- Fresh seeded grid per episode, persistent between actions; primary mode has no
  damage, update noise or random in-episode grid reset.
- fidelity32: state/activations 32/F24, weights 24/F22, accumulator/bias 62/F46,
  exact bias-last MAC, nearest-ties-even requantization and signed saturation.
- Old-grid reads and full epoch commit; source I/O rewrite and integer action
  selection must be preserved by subsequent hardware integration.
- Step-synchronized host simulation. The simulated 20 ms timestep is not an
  accepted 20 ms wall-clock deadline.

## Evidence interpretation

The float qualification result remains 6/10. Numerical acceptance does not
establish full-horizon fixed-point reliability, board competence or a hardware
performance advantage. Python comparisons and generated HDL benches do not
establish an RTL simulation pass. Passing synthetic cases does not establish
checkpoint-dependent hardware signoff.

The newer [source-distribution checks](verification/SOURCE_DISTRIBUTION_CHECKS.md)
record successful synthetic Icarus execution in hosted CI. This does not mark
all original P08/P09 acceptance requirements complete.

Technical requirements are mapped in
[requirements traceability](requirements/REQUIREMENTS_TRACEABILITY.md).
Architecture choices and acceptance scope are recorded in
[design decisions](decisions/README.md).
