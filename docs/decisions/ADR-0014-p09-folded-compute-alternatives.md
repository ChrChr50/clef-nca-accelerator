# ADR-0014: P09 folded compute alternatives

Verification update 2026-10-28: synthetic and checkpoint-derived local HDL execution now passes for all four lane variants. Synthesis remains unrun. ADR-0015 accepts the row-pipeline implementation direction; final G5 signoff remains pending, and ADR-0016 records an earlier numerical G4 return. Older missing-tool language below describes the original proposal date.

- Status: **Proposed — G5 compute portion; not accepted**
- Proposed: 2026-10-08
- Stage/gate: P09; final G5 packet belongs to P10
- Supersedes: None
- Related requirements: P09-001 through P09-006

Accepted fidelity32 fixes arithmetic, not physical lanes or storage. P09 supplies
reversible request/delta RTL and lane configurations 1/2/3/4. Options are one,
two or four output-channel MAC lanes; structural cycle counts are 1,862/932/492,
not simulation measurements. Three-lane tail coverage is retained as a test.

Recommend keeping one lane as the provisional functional reference and deferring
final lane selection until actual simulation, synthesis and P10 memory/ownership
evidence. The alternatives preserve identical products, bias-last accumulation,
rounding and graph; wider read demands and DSP mapping may limit throughput.
No reduced precision, mask skipping, patch mesh, bus/RNG or event variant is
selected. The engine returns delta, not residual or action.

P08/P09 HDL execution remains pending because local tools are absent. The G5
compute packet distinguishes scalar/image evidence from unrun RTL/synthesis.
All learned images are local/ignored. This proposal is not a human decision,
board fit/timing result, ASIC signoff, or Clef causal-closure claim. Stop before
P10; do not treat the default parameter as acceptance of a final architecture.

Evidence/options/consequences: `docs/architecture/P09_G5_COMPUTE_PACKET.md`.
