# NCA accelerator: active benchmark and long-term vision

Updated 2026-10-07. ADR-0008 records the user's accepted benchmark choice: the same CartPole task as the original reference paper/executable. ADR-0007's embodied-control motivation remains, but its earlier assumption that the first FPGA demonstration must use a newly selected distributed physical plant is superseded by this choice. The implementation status governs actual implementation status; the audited background governs Clef's conceptual distinctions.

## Accepted scope hierarchy

1. One-semester baseline: a portable fixed-weight NCA FPGA accelerator controlling the reference paper's simulated CartPole.
2. Preserve the original executable NCA/plant behavior as the software authority. Optimize arithmetic, scheduling, storage and transport with measured evidence; preserve deterministic replay and exact fixed-point golden equivalence.
3. After the verified baseline FPGA design, implement the custom balancing surface and EvoGym Balancer-v0 as separate extension benchmarks. These test distributed sensing/actuation, localized disturbances, body/surface scaling and event-based control more directly.
4. Explore separately authorized ASIC synthesis/physical design. Fabrication is gated by actual PDK/SRAM/funding/shuttle access.
5. Pursue full Clef's actual internally maintained efficient-causal organization in separately authorized experiments. The fixed NCA baseline is a controlled ancestor, not approximate autopoiesis or proof of CEC/Medium Rosen.

The semester endpoint remains FPGA control of a simulated physical plant; no physical robot is required. Exact due date/remaining weeks are not supplied. CartPole selection does not demonstrate body-wide spatial locality or universal superiority over CPU/GPU/TPU.

## Implementation status

The reference and numerical contracts are complete. P08 portable primitives and
P09 folded local-rule RTL are implemented with HDL verification pending. The
full grid scheduler, integrated core and FPGA demonstration remain incomplete.
See [implementation status](../STATUS.md) for the current evidence boundaries.

## Reference authority and non-negotiable distinctions

Use reference/original_nca/operator_manifest.json, cartpole.py, core.py, provenance/checkpoint identities, discrepancies and golden tests; do not replace the plant with stock Gymnasium CartPole or the browser-demo transition.

The original executable uses a 32×32×6 grid, a shared 1,916-parameter local neural graph, four observations duplicated across eight input sites, two score readouts, 50–59 internal steps per action and stochastic cell masks. Source-aligned plant integration/reward/horizon and state rewrite order matter. The raw output hidden-channel accumulation is not silently clipped.

P03 is complete as an executable reproduction with empirical limitations. The full paper statistics were not reproduced; missing historical seeds/checkpoint/table facts remain missing. Episode-grid reset is a paper/harness discrepancy; ADR-0009 chooses fresh seeded deployment episodes without claiming historical equivalence. The 30,000-step long-duration study is a declared diagnostic, not the released environment's default horizon.

Upstream checkpoint/source redistribution remains restricted by the existing incomplete licensing record. ADR-0009 permits local-only use of pinned model2 from the ignored clone; weights and derived images must not be committed/shared/shipped without explicit rights determination. Candidate identity and primary operational protocol are accepted G3E decisions; P06 recorded 6/10, with subsequent explicit freeze by ADR-0011. Fidelity32 numerical semantics are accepted by ADR-0012; the original float inference remains unclipped.

## Baseline acceptance and sparse/event design

The FPGA performs learned NCA inference/action selection; the host supplies the declared CartPole observation and applies resulting forces. No task-solving policy is supplied by the host. State persists between actions; startup, episode, controller and fault resets are declared separately.

The first FPGA realization must implement the accepted reference policy/plant contract, numeric contract, replay, bounded scheduling/transport, control-quality evidence and reproducible resource/timing reports. A folded engine can now be the first complete CartPole FPGA demonstration; it is not presented as having validated distributed body control.

Keep event-capable scheduling, masks, queue/ownership interfaces and instrumentation in the architecture where justified. Exact-preserving work avoidance (e.g. skipping irrelevant masked arithmetic while retaining clears/clamps/markers) is evaluated separately from state-change-triggered sleeping. Merely observing a mask or clock enable is not measured work savings. Prove equivalence for actual skipping, including finite-value behavior, RNG draw assignment and all affected writes.

Behavior-changing event gating is a separate variant, not a silent modification of “the same reference NCA.” G3E must distinguish reference-faithful acceptance from any semester event-variant commitment. Queue/deadline/overload tests apply to the actual admitted workload/protocol; a native distributed event-control claim requires extension evidence, not CartPole alone. Do not let an unvalidated event-policy redesign block faithful hardware by pretending it is needed to reproduce the paper.

P07's scheduled bit-accurate model includes arithmetic, masking, I/O rewrite, observation timing, commits, readout, RNG boundaries and reset. Tests distinguish model/control, quantization, arithmetic, temporal/scheduler, interface and physical failures.

## Post-FPGA benchmark extensions

X01: custom actuated balancing/manipulation surface. Define and validate the plant, local sensor/actuator boundary, surface coupling/contact simplifications and independent competent controller before NCA training. Begin with one object and a bounded task. Do not assume a passive fixed bowl proves useful closed-loop control or that local inputs imply locally restricted computation.

X02: EvoGym Balancer-v0. Reuse the documented simulator with one fixed morphology; define a physically motivated local-sensing adapter rather than silently passing whole-body state. Establish NCA competence and declared event semantics. Morphology search and broader task suites are optional later scope.

Both are authorized as planned extensions after the verified CartPole FPGA design, not as tasks to execute now. They have separate plant/policy/event manifests and acceptance gates. Their order, exact physical model/body, training method and budgets remain future human choices; neither assumes unchanged CartPole weights will solve a new plant. They are conventional controls, not full Clef. They need not wait for ASIC fabrication and are not required to finish the one-semester baseline.

## Architecture, comparisons and Clef continuity

Separate replaceable neural arithmetic, scheduler, state ownership, transducers and non-organizing trace/intervention hooks. Isolate FPGA/ASIC primitives. Use appropriate actual CDC; do not invent clock domains or call halo versioning cache coherence without such a protocol.

Compare the same frozen NCA in software and FPGA, folded/patch variants where implemented, competent conventional controllers with equal sensor/actuator access, and explicitly distinct dense/event policies where approved. Report latency/jitter/deadline misses, work executed/skipped, traffic/queue pressure, quality/stability/recovery, resource/Fmax and measured versus estimated power. Count or disclose host/transport and training/inference costs consistently. GPU/TPU comparisons require actual access or are clearly literature-only.

Later Clef still requires runtime coalitions that causally maintain/reconstruct one another's capacities; no privileged role tags or external scripted organizing/repair. CEC and Medium Rosen remain separate; no finite hardware benchmark establishes the universal semantic-noncomputability conjecture. Consult the supplied relational-biology sources before mathematical objections.

## Milestones

M0 accepted CartPole choice (complete) → M1 deployment contract/checkpoint readiness (E01/E02) → M2 model/numeric freeze (P06/P07) → M3 verified RTL (P08–P12) → M4 FPGA CartPole loop (P13/P14) → M5 measured baseline report/release. X01/X02 are post-FPGA extensions; ASIC and full Clef are separately gated. Dates await the actual due date; keep verification/bring-up contingency.
