# Requirements-to-Evidence Traceability

This matrix maps governing requirements to implementation artifacts and observed evidence. A requirement marked `Recorded` is captured but not yet implemented or verified. Only measured or directly inspected evidence may advance a requirement to `Verified`.

Scope precedence (2026-10-07): accepted ADR-0008 selects reference-paper CartPole first, with custom surface/EvoGym test extensions after the verified FPGA baseline. The active vision and resumption plan supersede earlier distributed-plant-first requirements. P00–P05 tables retain dated historical evidence; Hanoi requirements are not current deployment requirements. Original P03 evidence is reused with its limits, not relabeled as FPGA verification.

## Row-pipeline continuation — 2026-10-28

ADR-0015 records the user's accepted direction and reference-faithful corrections. Imported specification revision 1.0 is preserved; the reconciliation report identifies necessary corrections. Numerical acceptance and hardware evidence remain distinct.

| ID | Requirement | Artifact/evidence | Status |
|---|---|---|---|
| ROW-001 | Preserve post-update observation injection, mandatory postwrites on zero masks, output channels 4/5 increments and lowest-index ties. | Immutable original operator; ADR-0015; candidate regressions; 2026-10-30 full-grid epoch HDL replay | Postwrites verified in epoch RTL; action-controller integer tie/readout implementation remains pending |
| ROW-002 | Validate 16/F10 state, 16/F12 kernels and 48/F22 accumulators before replacing accepted fidelity32. | Protocol; screen/gate summaries; candidate bounds; proposed ADR-0016 | At G4: seed-41 candidate fails at 1150 versus comparators alive at 1488; replacement unaccepted |
| ROW-003 | Exact independent scalar/vector equality, output-major ROM round-trip, signed extrema, saturation and bounds. | Seven candidate tests; six complete checkpoint cases, 48 independent scalar cells, exact persistent replay and ignored signed ROMs | Verified for measured candidate operators/layout; not policy acceptance |
| ROW-004 | Predeclared paired recurrent comparison with seeds, masks, persistent grids, failures/censoring and resumable state. | Four completed screens; deliberately incomplete long campaign at G4; resume equivalence unit test; safe gate summary | Verified as executed/reported; full-horizon campaign incomplete |
| ROW-005 | Row lockstep, correct stage-register ownership, one grid, safe old-row release and stall-independent logical draws. | Eight row-stage HDL configurations; both banked widths; ADR-0017; `nca_epoch_core.sv` and 18 persistent epoch replays | Functional generation safety/barriers and progress verified under tested stalls with supplied masks; autonomous draw generator and physical mapping pending |
| ROW-006 | Measure actual RAM/DSP mapping, ports, recurrence timing and end-to-end protocol rather than treating projections as results. | ADR-0015; future P09/P10/P13 evidence | Recorded |
| ROW-007 | Diagnose the saved numerical failure with reproducible bounded replay and causal probes; distinguish logical precision cost from physical synthesis. | `ROW16_DIAGNOSIS_AND_PRECISION_COST.md`; seed41 first-divergence, input/history probes and exact recorded-action/terminal-grid replay; `hardware_tradeoff.json` | Diagnostic evidence obtained; no new numerical acceptance, population qualification or physical mapping |
| ROW-008 | Match transcript operand delivery: shared old rows, shared offset/channel decode, scalar-per-lane input and common convolution coefficient stream; distinguish logical sharing from physical ROM mapping. | `nca_row_window.sv`; streamed row-stage branch; exhaustive window tests and `ROW_PIPELINE_EPOCH_RTL_2026_10_30.md` | Three-row/shared-decode frontend and explicit coefficient broadcasts functionally verified; physical ROM mapping unverified |
| ROW-009 | Measure row request interval separately from active cycles and preserve old-generation reads through write grants/snapshots. | Component 1080 active / 1081 request interval; guarded single-grid scheduler; 43,326 clocks per epoch under fixed test stalls | Integrated old-generation safety, all row commits, transfer counts and tested progress verified; no unstalled/Fmax/board throughput claim |
| ROW-010 | Connect row stages with actual overlap, exact mask MAC gating and mandatory source postwrites while preserving accepted arithmetic. | Six full-grid configurations, 18 epochs; 110,592 grid and 1,032,192 layer comparisons; local hash-bound reports; proposed ADR-0018/G5 | Verified for tested functional scope; fidelity32 remains accepted, row16 quality loss unresolved; full action/RNG/transport controller and physical G5 evidence pending |
| ROW-011 | Remove unused production RTL and improve active-source readability without changing behavior or losing historical regression evidence. | Five-file `rtl/core/files.f`; six byte-preserved fixtures in `tb/legacy_rtl/`; 165 identifier renames; 7,175-token check; `RTL_CLEANUP_2026_10_30.md`; fresh 18-epoch matrix and 105 Python regressions | Verified: active RTL comment-free, public interfaces unchanged, all 150 golden/input files unchanged, historical tests runnable; G5 status unchanged |

No existing verified requirement is widened to the new numerical or row-pipeline implementation without new evidence. Historical Hanoi, original-reference and existing accepted numerical results are preserved.

2026-10-28 verification addendum: existing P08/P09 synthetic **and restricted** HDL entry points passed locally with Icarus. This advances the existing arithmetic requirements' HDL scope; it does not establish synthesis, full controller or board signoff. See the row-pipeline G4 packet for exact commands, 105 passing unit tests, source identities and limitations. New CI commands were added but not dispatched.

## Status vocabulary

| Status | Meaning |
|---|---|
| Recorded | Requirement is captured and awaits its implementation stage. |
| In progress | Implementation exists but required evidence is incomplete. |
| Verified | Required evidence exists and has passed the stated check. |
| Blocked | A named dependency prevents progress. |
| Not applicable | The requirement does not apply to the referenced stage/artifact. |

## Scientific and claim requirements

| ID | Requirement | Source | Planned stage(s) | Evidence | Status |
|---|---|---|---|---|---|
| SCI-002 | Treat the FPGA as substrate; any future organism is the changing runtime organization of participating tiles, links, processes, and capacities. | Architecture invariants 1; active vision | P18–P23 | Implementation status project guardrails | Recorded |
| SCI-006 | Report only the strongest demonstrated rung of the claim ladder; do not collapse adjacent levels. | Architecture invariants, Claim ladder; active vision | P18–P23 | Future experiment/release reports | Recorded |
| SCI-007 | Preserve the project's stated claim before evaluating it; state mathematical/evidential objections separately. | active vision | All claim-bearing stages | Future documentation review | Recorded |

## Baseline architecture and verification requirements

| ID | Requirement | Source | Planned stage(s) | Evidence | Status |
|---|---|---|---|---|---|
| BASE-001 | Reference CartPole host supplies four observations; FPGA performs persistent NCA control with two actions and accepted source-aligned protocol. | ADR-0008; active vision | E01–E02, P11, P13–P14 | E01 versioned interface and direct P03-backed wrapper parity; hardware evidence pending | Verified for E01 software boundary; FPGA pending |
| BASE-002 | Hidden state persists between control decisions; plant, episode, controller and recovery resets are distinct. | Active vision; invariants | E01–E02, P06–P07, P11–P12 | E01 explicit controller/plant construction and reset-separation test; recovery protocol later | Verified for E01 separation; deployment recovery policy pending |
| BASE-003 | Preserve accepted causal scheduling: old/new epoch separation for synchronous models, declared order/version/ownership for asynchronous models; no silent raster bias. | Active vision; invariants | E02, P06–P07, P10–P12 | Future assertions and equivalence tests | Recorded |
| BASE-004 | The bit-accurate fixed-point model is the golden RTL specification, with exact agreement at declared boundaries. | Architecture invariants, Baseline 4 | P07–P12 | Future bit-exact regression reports | Recorded |
| BASE-005 | Stochastic schedules are reproducible under fixed seeds or supplied mask traces. | Architecture invariants, Baseline 5 | P03, P06–P07, P11–P12 | Future deterministic replay tests | Recorded |

## Clef accommodation requirements

| ID | Requirement | Source | Planned stage(s) | Evidence | Status |
|---|---|---|---|---|---|
| ACC-001 | Keep local transition arithmetic replaceable behind an interface. | Architecture invariants, Clef accommodation 1 | P09 onward | Future interface ADR and RTL | Recorded |
| ACC-002 | Keep scheduling separate from transition meaning. | Architecture invariants, Clef accommodation 2 | P10–P12, P18–P21 | Future architecture/specification evidence | Recorded |
| ACC-003 | Keep environment transducers separate from internal functional organization. | Architecture invariants, Clef accommodation 3 | P11, P13, P18–P22 | Future boundary/interface tests | Recorded |
| ACC-004 | Provide trace, snapshot, deterministic replay, and intervention hooks that observe/perturb but do not organize or repair the system. | Architecture invariants, Clef accommodation 4; audit §§8, 18 | P11–P14, P19–P22 | Future access-control review and intervention tests | Recorded |
| ACC-005 | Do not assume dynamic Clef topology requires FPGA partial reconfiguration; runtime state may directly gate causal paths. | Architecture invariants, Clef accommodation 5; audit §16.3 | P01, P18–P21 | `docs/architecture/P01_G1_PLATFORM_TOOLCHAIN_PACKET.md`, section “Why Clef runtime topology does not require FPGA partial reconfiguration”; later RTL tests remain required | Verified for P01 decision scope |
| ACC-006 | Compare folded execution with patch-local memories and neighbor exchange in the baseline; preserve locally causal propagation for later Clef. | Active vision; project invariants | P10–P15, P18–P23 | Future G5/G8 decisions, locality tests and PPA reports | Recorded |

## Active embodied/event requirements

| ID | Requirement | Stage(s) | Required evidence | Status |
|---|---|---|---|---|
| EMB-001 | Compare benchmarks before human selection; user selected reference CartPole, custom surface/EvoGym post-FPGA. | E00/G2E | Comparison/history; accepted ADR-0008, 2026-10-07 | Verified for selection/sequence, not deployment readiness |
| EMB-002 | Current CartPole plant/I/O contract reuses original units, timing, sites, limits, reset semantics; extension local I/O is separate. | E01/P06; X01/X02 | E01 versioned interface/replay manifests, source-bound wrapper and seven tests; later extension contracts separate | Verified for E01 CartPole; extensions/P06 pending |
| EMB-003 | Competent offline-trained fixed-weight policy on held-out and long-duration control scenarios. | E02/G3E/P06 | P03 long-duration evidence; P06 records; accepted ADR-0011 freeze | Model2 reached 6/10, below original 8/10; user accepts unchanged weights as engineering baseline. Stronger control competence is not retrospectively claimed. |
| EMB-004 | Reference-faithful folded CartPole may complete first FPGA baseline; prove/account equivalent skipping, label changed event variants; distributed event claims require extensions. | E02, P11–P15; X01/X02 | E02 G3E packet and accepted ADR-0009 distinguish exact-preserving optimization from changed event gating | Boundary accepted; work/energy equivalence not measured |
| EMB-005 | Original synchronous mask/step semantics remain primary; event triggers/maintenance/sleeping are explicitly accepted distinct variants where changed. | E02/P06–P12; X01/X02 | E02 packet and accepted ADR-0009; P03/E01 exact/replay tests | Reference semantics accepted/verified in software; changed event variants unaccepted |
| EMB-006 | Bounded queues, coalescing/dedup, backpressure/overflow, fairness, load envelope and deadline policy. | P07–P14 | Boundary/overload/assertion tests and measured latency/queue pressure | Recorded |
| EMB-007 | Patch memory ownership/versioned halos and commit prevent stale/mixed state; concurrency does not silently change semantics. | P10–P12 | Protocol tests/assertions and G5 decision | Recorded |
| EMB-008 | RNG follows logical identities; stalled hardware replay preserves the frozen model. | P06–P12 | Deterministic differential replay under stalls | Recorded |
| EMB-009 | Genuine CDC/reset crossings isolated and tested; no assumed cache coherence from halo exchange. | P08/P13 | Clock/reset map, CDC protocol tests and actual constraints/reports | Recorded |
| EMB-010 | Fair identical-NCA and conventional-control comparisons; GPU/TPU claims limited by access and sourced/measured evidence. | E02/P15 | Equal sensing/load/deadline/quality accounting; uncertainty and repeatability | Recorded |
| EMB-011 | Report latency/jitter/misses, active fraction/events, bytes/links, resources/Fmax, stability/recovery, power provenance and energy/control second. | P14–P15 | Saved measured reports with host/transport inclusion policy | Recorded |
| EMB-012 | Semester endpoint is FPGA with simulated physical plant; one semester, no physical apparatus required. Exact due date remains open; ASIC fabrication is separately gated. | E00/G2E, G7 | User clarification and ADR-0007 addendum, 2026-10-06 | Verified for endpoint/one-semester decision; dated schedule and ASIC target pending |
| EMB-013 | Preserve immutable original and historical Hanoi evidence; no false new-target completion. | Migration/all stages | Historical snapshots; `docs/verification/2026_10_06_SCOPE_MIGRATION.md`; 58 historical tests and governance checks passed | Verified for this documentation migration only |
| EMB-014 | Portable RTL, replaceable rule/scheduler/transducers and non-organizing trace hooks support later Clef without baseline closure claims. | P08–P18 | Interface review and later intervention controls | Recorded |

## Selected CartPole resumption requirements

| ID | Requirement | Stage(s) | Evidence | Status |
|---|---|---|---|---|
| CART-001 | Current task is original-reference CartPole, not stock Gym defaults or Hanoi. | E00/E01/P06 | ADR-0008; immutable operator/plant and resumption plan | Verified for selection; deployment pending |
| CART-002 | Reuse P03; consolidate E01 separately; do not restart old Hanoi P05 or retrain without measured need/authorization. | E01/E02 | E01 deployment/replay manifests; E02 packet reuses P03 long records and reruns preservation regressions; accepted ADR-0009 | Verified through E02/G3E; no retraining authorized |
| CART-003 | Checkpoint, reset gap, horizon/protocol, control thresholds and simulated versus wall-clock timing are explicit G3E choices. | E02/G3E/P06 | ADR-0009, P06 results, accepted ADR-0011, resolved freeze | User explicitly freezes current weights despite 6/10 result; original protocol retained. Hardware timing unmeasured. |
| CART-004 | Local checkpoint verification does not authorize weight redistribution/export; retain provenance/rights boundary. | E02/P06 | P03 verifier PASS for revision, 13 hashes and 3 goldens; PROVENANCE.md; accepted ADR-0009 local-only restriction | Local-only use accepted; export rights unresolved, no shared weight image authorized |
| CART-005 | Custom surface/EvoGym extensions follow verified FPGA baseline and have separate plant/model/event gates; no automatic weight transfer. | X01/X02 | ADR-0008; extension prompts | Verified for planned sequence, not implementation |
| CART-006 | Control/hardware evidence does not imply body-wide event scaling, CEC or Medium Rosen; preserve original/full-Clef distinctions. | All claim-bearing stages | Active vision and future bounded reports/interventions | Recorded |

## E01 CartPole consolidation requirements

| ID | Requirement | Evidence | Status |
|---|---|---|---|
| E01-001 | Reuse the immutable P03 operator and modified CartPole plant without duplicating physics or selecting a checkpoint. | `sw/cartpole/deployment.py`, `interface.v1.json`, source SHA-256 binding and direct-step parity test | Verified |
| E01-002 | Express four observations/eight scaled sites, two actions, 50–59 epochs, masks, I/O order and persistent state in a host-neutral contract. | `interface.v1.json`; all-site, marker and parity tests | Verified |
| E01-003 | Define deterministic replay with explicit initial state, grid, ordered draws, hashes and declared arithmetic comparison boundary. | `replay.v1.json`; two-decision identical-trace/noise test | Verified for E01 float harness; deployed RNG and P07 fixed-point pending |
| E01-004 | Keep terminal reward/horizon, plant/controller resets, diagnostic horizon and wall-clock pacing distinct. | Source plant plus E01 manifest/doc; terminal-horizon and reset-separation tests | Verified for E01 structural contract; G3E policy choices pending |
| E01-005 | Map existing versus missing evidence, retain historical tests/firewall and stop before training, model freeze, RTL or extensions. | `E01_CARTPOLE_DEPLOYMENT_AND_REPLAY.md`; implementation status command/results; clean immutable-reference scope check | Verified |

## E02 CartPole readiness and G3E requirements

| ID | Requirement | Evidence | Status |
|---|---|---|---|
| E02-001 | Verify the ignored pinned upstream source and all released checkpoint identities without copying weights. | `verify_upstream.py` pass: revision, 13 hashes, three checkpoint goldens; checkpoint hash manifest | Verified locally; redistribution unresolved |
| E02-002 | Compare model1/model2/model3 under a declared common software-control protocol, preserving censoring and small-sample limits. | P03 long-duration raw JSONL and E02 side-by-side packet, seeds 0–2 | Verified as candidate comparison, not held-out reliability |
| E02-003 | Expose source versus extended horizon, episode-grid reset discrepancy, noise/damage/deletion conditions, timing and prospective thresholds for G3E. | E02 G3E packet; accepted ADR-0009 | G3E protocol accepted; prospective ten-seed qualification unrun |
| E02-004 | Bound numerical and rights claims: no inferred clamp, no silent weight export, full dynamic profiling at P07. | Weight extrema observed for all three checkpoints; P03 operator/provenance; E02 packet | Finite weights verified; recurrent state range and export grant unresolved |
| E02-005 | Separate reference-faithful execution and proved exact-preserving work avoidance from behavior-changing event variants. | E02 event-boundary analysis; accepted ADR-0009 | Boundary accepted; no skipping implementation or changed event variant accepted |
| E02-006 | Reuse regression evidence, preserve historical assets, stop at G3E without training or P06. | E02 implementation status command/results, P03/E01 and historical P04/P05 tests, smoke/firewall, scope check; G3E acceptance entry | E02/G3E completed at its date; P06 later attempted and returned after failed gate |

## P06 conditional CartPole freeze requirements

| ID | Requirement | Evidence | Status |
|---|---|---|---|
| P06-001 | Verify pinned ignored model2 source/blob and fixed-checkpoint goldens before qualification or export. | P03 verifier, accepted ADR-0009, `qualification.v1.json`, P06 implementation status | Verified locally; redistribution unresolved |
| P06-002 | Predeclare and run exactly seeds 10–19 through the E01 host/controller with fresh grids, source horizon, accepted mask/schedule RNG and no primary perturbation. | Versioned qualification manifest/harness, direct P03-operator prefix parity test, ten completed per-seed JSONL records | Verified as executed; result 6/10 |
| P06-003 | Original condition: freeze only after >=8/10 and pinned goldens, otherwise return to G3E. | ADR-0009; original failed summary; accepted superseding ADR-0011 | Historical gate failed 6/10. User explicitly supersedes its pre-freeze condition; no retry, retraining or retrospective pass. |
| P06-004 | Resolve versioned checkpoint, graph, plant, interface, replay, RNG and reset/horizon contract without modifying E01/P03 historical assets. | `sw/cartpole/deployment.freeze.v1.json`; `model_export/cartpole/freeze.py`; accepted ADR-0011 | Verified: explicit-decision freeze, source/episode bindings and unchanged historical assets |
| P06-005 | Keep restricted weights/derived images ignored/local; validate regeneration/export round-trip and hash without tracked tensor leakage. | Ignored 7,664-byte export; six-tensor bitwise round-trip; pinned blob hash; legacy/fake authority refusal tests | Verified local export under explicit accepted freeze; redistribution remains unresolved |
| P06-006 | Add fast E01/P06 tests to CI without licensed weights, preserve original/historical regressions and firewall, and stop before P07/RTL/event variants. | Updated smoke workflow, local regression/smoke results, final P06 implementation status | Verified locally; hosted CI not run; stopped before P07 |
| P06-007 | Perform the user-authorized paired comparison of a failed P06 seed against independent execution of the pinned upstream Python operator with identical weights, initial state and masks. | `experiments/p06_upstream_parity/`; `docs/verification/P06_UPSTREAM_PARITY.md`; compact summary and local traces | Verified for seed 12: identical 1,334 actions, score and plant endpoint; all decision-grid errors within P03 tolerance. Modern TensorFlow runtime and accepted deployment protocol; historical paper statistics and other seeds remain unverified. No freeze-gate change. |

## P07 numerical profiling and scheduled golden requirements

| ID | Requirement | Evidence | Status |
|---|---|---|---|
| P07-001 | Start from an accepted resolved weight/episode freeze and declare calibration versus acceptance before numeric tuning. | Accepted ADR-0011; resolved freeze; `experiments/p07_cartpole/protocol.v1.json` | Verified; reused 10/12 calibration, new 20/21 bounded acceptance; no format tuning on results |
| P07-002 | Profile weights/biases, layer preactivations, delta, residual, state, input scales, markers and score margins through the primary horizon; do not infer state bounds from weights. | `float_profile.json`; P07 verification report | Verified: 10,001 actions/544,994 epochs, exact P06 match; state/delta/residual each epoch, preactivations sampled every 64 epochs; stress separately labeled |
| P07-003 | Implement explicit signed widths/scales, bias/accumulation order, ReLU, residual, rounding/saturation/overflow and analytical accumulator bounds. | `fixed_point.py`; accepted arithmetic manifest/ADR-0012; synthetic tests and analytical bounds | Verified; user accepted fidelity32 at G4. Alternatives preserved. |
| P07-004 | Preserve old-grid epochs, held pre-action inputs, source post-writes, supplied logical masks, persistence and tie behavior through one E01 quantization boundary. | Scheduled controller; `fixed_deployment.py`; scalar cells, service permutations, zero-mask/persistence/E01 tests | Verified functional schedule; physical lanes/bus/RNG/clock remain G5 |
| P07-005 | Save layer/cell/post-write/readout vectors and first differences without exposing checkpoint-derived fixtures. | Ignored 18-case vectors, safe `vectors_manifest.json`; `check_vectors.py` | Verified: exact full-array replay and 144 independent scalar cells; arrays remain ignored/local |
| P07-006 | Measure float/fixed numerical drift, action/score differences and runtime separately from baseline policy failure; disclose caps and reuse. | `evaluation_summary.json`; first-difference diagnostics; P07 report | Verified bounded comparison; balanced24/fidelity32 exact 2/2 new 256-action traces; compact18 has changes. No full-horizon quantized quality claim. |
| P07-007 | Prepare G4 alternatives and obtain explicit acceptance before selecting arithmetic; stop before RTL. | G4 packet; accepted ADR-0012; `arithmetic.accepted.v1.json` | G4 complete: fidelity32 and bounded quality scope accepted 2026-10-07. Full-horizon quantized quality unverified; P08 unstarted. |
| P08-001 | Use read-only accepted model2/fidelity32 authority; explicit 32/24/62-bit signed arithmetic, full product and bias-last sums. | `rtl/core/nca_mac_stream.sv`; P08 interfaces/report; manifest validators | RTL implemented; scalar/vector correspondence passed; HDL execution pending |
| P08-002 | ReLU before signed ties-even shift-22 requantization, 33-bit residual/marker guard and counted signed saturation. | `nca_round_sat.sv`, `nca_guard_add.sv`; 756 synthetic rounding/72 add cases plus accepted local layer tests | Expectations checked against P07; RTL simulation unrun |
| P08-003 | Treat int64 as comparison containers; validate packing and sign extension without choosing a bus. | `nca_word_pack.sv`; nine packing cases; interface contract | Implemented/testbench prepared; HDL execution pending |
| P08-004 | Ready/valid reset/stall behavior and once-per-acceptance saturation counters with explicit overflow policy. | `nca_mac_stream.sv`, `nca_elastic_word.sv`, `nca_event_counter.sv`; temporal bench, proposed ADR-0013 | Prepared; temporal/assertion simulation unrun; no G5/CDC choice |
| P08-005 | Reproducible synthetic and restricted-vector verification; no learned literals/images committed. | `tb/p08_primitives/run.py`, `test_vectors.py`; ignored generated benches and six accepted hashes | 3 Python tests pass; 48 restricted scalar cells checked; ignored-path check passes; no RTL pass claimed |
| P08-006 | Portable core and abstract memory/transport seams; preserve governance, firewall and later-stage boundary. | P08 interfaces/report, proposed ADR-0013; smoke CI synthetic simulation entry | Smoke/28 governed hashes/firewall pass; Quartus/Yosys and hosted CI unrun; P09 not started |
| P09-001 | Implement accepted fidelity32 three-layer local rule with exact signed MAC/bias/ReLU/rounding and scalar/layer boundaries. | `nca_local_rule.sv`; P09 support/bench/report | Implemented; 48 restricted scalar cells and 2,688 layer pairs pass in Python; RTL unrun |
| P09-002 | Generate quantized local kernel/bias images from validated frozen tensors; declare encoding/order/hashes and verify round-trip/analytical bounds. | P09 support, ignored `images.json`, G5 compute packet | PASS, 1,860/56 words, 48,112 bits, model2 bounds 58/57/57; all images ignored/local |
| P09-003 | Test all six accepted fidelity32 snapshots, padding/channel order, loop boundaries, stalls/reset/bias/configuration and lane alternatives. | P09 scalar tests and generated lane 1/2/3/4 benches | Software comparisons pass; HDL temporal/arithmetic execution pending |
| P09-004 | Return delta only; keep neighborhood/RNG/epoch/residual/clamps outside compute and test composition once. | Engine interface, packet, delta boundary unit test | Python composition matches P07 mask/IO/post-writes; no full RTL integration claim |
| P09-005 | Provide G5 compute options and actual evidence without silently selecting final lanes/storage or inventing speedup. | G5 compute packet; proposed ADR-0014; structural cycles 1,862/932/492 | Preliminary options; actual cycles/synthesis/fit/PPA unrun; final decision deferred to P10 |
| P09-006 | Preserve portable/rights/governance/firewall boundaries and stop before P10. | P09 report/implementation status; ignored images; smoke/provenance checks; CI entry | 53 final Python regressions and 18 P07 replays pass; no push/hosted CI/P10; P09 verification pending |

## P00 evidence summary (historical)

P00 establishes documentation evidence only. No entry above should be read as evidence that an NCA or Clef mechanism exists. The only fully verified items are the bootstrap/process requirements and the absence of out-of-stage accelerator implementation in P00.

## P01 gate requirements

| ID | Requirement | Source | Evidence | Status |
|---|---|---|---|---|
| P01-001 | Compare two or three current FPGA/toolchain stacks using primary-source evidence for logic, DSP, memory, host connectivity, debug, cost, and availability. | stage specifications, P01; G1 table | `docs/architecture/P01_G1_PLATFORM_TOOLCHAIN_PACKET.md`, Shortlist and stack sections | Verified |
| P01-002 | Compare open and vendor verification/synthesis options. | stage specifications, P01 | G1 packet, Verification and synthesis comparison | Verified |
| P01-003 | Preserve a path to portable SystemVerilog and ASIC synthesis. | stage specifications, P01; BASE-006 | G1 packet and accepted ADR-0001: SystemVerilog core consumed by Quartus and Yosys/OpenROAD with vendor/PDK/memory wrappers isolated | Verified at accepted-policy level; implementation awaits P02 onward |
| P01-006 | Do not purchase hardware, create external accounts, or commit to a platform before the human choice. | stage specifications, P01 | Implementation status scope audit and ADR decision chronology | Verified; platform commitment followed explicit user authorization |
| P01-007 | After platform authorization, record the school-provided DE1-SoC, $0 initial hardware spend, and no-cost Quartus as provisional policy; preserve a portable core and defer upgrade until measured evidence justifies it. | User G1 platform decision; BASE-006; BASE-008 | `docs/architecture/DE1_SOC_PROVISIONAL_PLATFORM_AND_BRINGUP.md`; `ADR-0001` decision and validation sections | Verified at planning/decision level; implementation evidence awaits P02-P14 |
| P01-008 | Define what capacity evidence is collected, when the board is re-evaluated, and how a larger FPGA or cluster is considered without silently weakening the accepted model. | User G1 platform decision; stage gates G5, G6, G8 | DE1-SoC guide, “Capacity evidence,” “Upgrade decision policy,” and “Multi-board DE1-SoC policy” | Verified at planning level |
| P01-009 | Provide a safe, revision-aware, non-destructive DE1-SoC acquisition and initial bring-up procedure. | User request; supplied rev. E manual v1.2.2; Terasic resources; Cornell lab workflow | DE1-SoC guide, “Governing board manual,” “Acquisition and first-use checklist,” and “Safety and common failure controls”; supplied PDF SHA-256 `BC78872EDAF95A96E5876172A20EA14EEB01BC736CB01857FBE496FE6EDF348E` | Verified as documented procedure; physical execution awaits board access |
| P01-010 | Complete G1 with a private-first repository, SystemVerilog core, Quartus FPGA backend, open ASIC compatibility lane, and an explicit initial license posture. | User G1 acceptance | Accepted `ADR-0001`; G1 packet outcome; implementation status | Verified; P01 complete |

## P02 scaffold requirements

| ID | Requirement | Source | Evidence | Status |
|---|---|---|---|---|
| P02-001 | Create the repository scaffold without adding an NCA model or RTL behavior. | stage specifications, P02 | `scripts/check_scaffold.py`; local smoke output; zero `.sv`/`.svh` files | Verified |
| P02-002 | Preserve the private-first, all-rights-reserved G1 decision. | Accepted ADR-0001 | `LICENSE`; `config/toolchains.toml`; `.gitignore`; repository README; private `ChrChr50/clef-nca-accelerator` remote | Verified |
| P02-004 | Add dependency locking, formatting/lint configuration, and reproducibility checks. | stage specifications, P02 | `requirements/ci.lock`; `pyproject.toml`; `.editorconfig`; `.verible-verilog-format`; `scripts/check_reproducibility.py` | Verified for the zero-dependency P02 environment |
| P02-005 | Add smoke CI using the same reproducible entry point as local checks. | stage specifications, P02 | `.github/workflows/smoke.yml`; `scripts/run_smoke.py`; local smoke gate; GitHub Actions run `35280904093` | Verified locally and on hosted Ubuntu CI |
| P02-006 | Isolate portable core, FPGA technology, ASIC technology, board, and flow boundaries. | stage specifications, P02; BASE-006 | Canonical `reference/`, `training/`, `model_export/`, `rtl/`, `tb/`, `sw/`, `boards/`, `flows/`, `experiments/`, and `docs/` layout; `config/toolchains.toml` | Verified structurally |
| P02-008 | Create the private GitHub repository only when authenticated authorization/tooling is available; otherwise provide one missing external step. | stage specifications, P02 | Authenticated creation of private `ChrChr50/clef-nca-accelerator`; tracked remote branch; hosted run `35280904093` | Verified |

## P03 original-NCA reproduction requirements

| ID | Requirement | Source | Evidence | Status |
|---|---|---|---|---|
| P03-001 | Preserve an isolated original-paper Python reference before any task adaptation. | P03 reference specification | `reference/original_nca/`; manifest test rejects task-specific content | Verified |
| P03-002 | Pin authoritative source revision, dependencies, environment, seeds, checkpoints, and license; record unavailable data. | P03 reference specification | `provenance.json`, `environment.lock.json`, `checkpoint_hashes.json`, `PROVENANCE.md` | Verified; historical dependency versions/seeds and complete license grant explicitly unavailable |
| P03-003 | Match local update, full step, readout, fixed-checkpoint CartPole rollout, persistence/reset, damage, and stochastic behavior at declared comparison points. | P03 reference specification; user acceptance audit | Exact Windows hashes in `golden_vectors.json`; full-array cross-platform vectors in `golden_arrays.npz`; `test_core.py`; `verify_upstream.py`; exact report; independent TensorFlow.js 3.7.0 comparison | Verified: exact hashes on the declared Windows arithmetic runtime; complete-array Windows/Linux comparisons and cross-backend errors use the declared `2e-5` tolerance |
| P03-004 | Attempt empirical longevity, noise, deletion, and damage reproduction with distributions/tolerances. | P03 reference specification; paper Tables 1-2 | `run_empirical.py`; `empirical_results.json`; `P03_EMPIRICAL_REPRODUCTION.md`; `experiments/p03_long_duration/`; `P03_LONG_DURATION_CONTINUATION.md` | Verified as an attempted reconstruction: 30,000-action extended horizon, all six principal conditions and position deletion measured, 10 seeds for uniform-damage/deletion arms; one baseline episode censored and several means remain far from the paper, so 100-run empirical equivalence is not claimed |
| P03-005 | Reproduce documented curriculum, pool behavior, reset operator, and 50-60 recurrent schedule where executable evidence confirms them. | P03 reference specification | `training_contract.py`; named persistence/reinitialization and curriculum tests; manifest training/schedule sections | Verified; executable range is 50-59; cross-episode evaluation reset remains an explicit upstream ambiguity |
| P03-006 | Resolve all paper/executable operator and semantic discrepancies. | P03 reference specification | `DISCREPANCIES.md`; `operator_manifest.json` | Verified; unresolved historical facts remain labeled gaps |
| P03-007 | Retain a reproducible environment lock and CI test path. | P03 reference specification | `requirements/original_nca.lock`, `requirements/ci.lock`, workflow, `environment.lock.json` | Verified for clean-room environment; historical environment unavailable |
| P03-008 | Preserve upstream license boundaries and do not silently redistribute ambiguous artifacts. | P02 retention policy; P03 reference specification | `.gitignore`; provenance license record; upstream verifier reads local clone | Verified |
| P03-009 | Prepare G2 with immutable original contract and explicit six-action, bounded variable-disk differences. | G2 table; P03 reference specification | G2 decision record; accepted ADR-0002; user acceptance on 2026-09-19 | Verified; G2 accepted with recommended Option A |
| P03-010 | Do not begin P04 or task-specific training before G2 acceptance. | P03 reference specification | Scope audit; no adapter/environment/oracle/training artifacts | Verified |

## P04 Hanoi environment and oracle requirements

| ID | Requirement | Source | Evidence | Status |
|---|---|---|---|---|
| P04-001 | Implement the accepted canonical `N_MAX=8` state, exact 36-value observation order, all goals, and six ordered unmasked actions. | stage specifications, P04; ADR-0002 | `reference/hanoi/environment.py`; `environment_manifest.json`; environment and exhaustive tests | Verified |
| P04-002 | Make illegal actions deterministic no-ops with separately reported legality, independent of reward/target shaping. | stage specifications, P04 | `transition`; `StepResult`; no reward API; directed and exhaustive tests | Verified |
| P04-003 | Provide reproducible reset, terminal, move-budget, serialization, and state-hash behavior without selecting G3 policy. | stage specifications, P04; P05 G3 boundary | SHA-256 counter reset; canonical snapshot/state JSON; hash goldens; episode tests; caller-supplied budget | Verified |
| P04-004 | Implement an independent optimal-distance and complete optimal-action-set oracle for training/evaluation only. | stage specifications, P04 | `reference/hanoi/oracle.py`; reverse BFS plus independent recurrence | Verified |
| P04-005 | Exhaust all `3^8` states for every goal, all smaller sizes, all actions, legality, inverse consistency, distance monotonicity, ambiguity, and `2^n-1` standard bounds. | stage specifications, P04 | `test_oracle_exhaustive.py`; 29,520 states; 177,120 actions; P04 evidence report | Verified |
| P04-006 | Prevent oracle modules, tables, distances, and traces from entering model export or synthesized RTL artifacts. | stage specifications, P04; BASE-007 | `scripts/check_oracle_firewall.py`; positive repository scan; deliberate contaminated-fixture rejection; smoke/CI integration | Verified for current repository and build inputs |
| P04-007 | Preserve the immutable P03 reproduction and do not begin Hanoi training. | P03 downstream contract; stage specifications, P04 | P03 regression; scope audit; no training/model/RTL behavior added | Verified |

## P05 software controls, training, and G3 requirements

| ID | Requirement | Source | Evidence | Status |
|---|---|---|---|---|
| P05-001 | Preserve the immutable original reference and derive a separate Hanoi adapter/model using the exact 1,916-parameter local graph unless evidence and a human decision authorize a separate fork. | stage specifications, P05; ADR-0002; ADR-0004 | V1 `training/hanoi_nca/{adapter.py,model.py,runtime.py}` remains regression-tested; accepted experimental v2 files are separate and use 2,338 parameters; no diff under `reference/original_nca/` | Verified for v1 and authorized v2 separation; no v2 performance freeze |
| P05-002 | Use P04 as the sole transition authority and prevent oracle/target/reward data from entering deployable model/export paths. | P04 downstream contract; BASE-007 | `run_experiment.py` calls `HanoiEnv`; expanded firewall; AST import test; no training environment duplicate | Verified |
| P05-003 | Define/test fixed mappings for 36 inputs and six outputs, including collisions, distance, bias, and full index mapping. | stage specifications, P05 | `layout_v1.json` and `layout_v2.json`; `layout.py`; contract tests; P05 and P05 v2 verification reports | Verified for both P05 layouts |
| P05-004 | Build a canonical 29,520-case corpus with complete-set targets, terminal treatment, hash identities, coverage, and leakage-safe partitions. | stage specifications, P05 | `dataset.py`; `experiments/p05/dataset_manifest.json`; corpus test | Verified |
| P05-005 | Explicitly measure and propose normalization, redundancy, score/target scaling, terminal treatment, reward, illegal feedback/loss, budget, recurrent steps, and marker behavior. | G3 requirements | Difference manifest; G3 packet; results budget and 59-step marker probes | Verified as measured proposal; G3 not accepted |
| P05-006 | Implement a conventional control on the identical 36-value/six-action contract. | stage specifications, P05 | `control.py`; checkpoint/results; 99.962% train, 60.559% seen-n test, 33/72 closed-loop completions | Verified |
| P05-007 | Separately measure adapter/operator regression, six-output signal curriculum, complete-set imitation, coherent persistent-state DAgger, and optional RL disposition. | stage specifications, P05 | P05 tests; curves and DAgger failure records in `results.json`; RL explicitly not attempted because reward is deferred | Verified as attempted/measured; DAgger failed numerically and rolled back |
| P05-008 | Compare independent-grid sampling with coherent paired trajectories and keep hidden state persistent between moves. | stage specifications, P05 | `run_experiment.py`; 72 episodes for each mode; per-episode records and summaries | Verified; both modes completed 13/72 in the retained run |
| P05-009 | Record seeds, environments, exact datasets, hashes, pools, schedules, curves, failures, legality, completion/truncation, margins, and stratified results. | stage specifications, P05 | `experiments/p05/{results.json,dataset_manifest.json,episode_records.json}`; dependency lock; verification report | Verified |
| P05-010 | Re-run P03 and P04 regressions and retain the oracle firewall throughout P05. | stage specifications, P05 | V2 continuation: 17 P03, 11 exhaustive P04, 18 P05 tests; smoke and firewall passed | Verified |
| P05-011 | Establish learnability before hardware work without mislabeling random resampling as generalization. | stage specifications, P05 | Conventional/NCA split metrics; `P05_HYPOTHESIS_A.md`; `P05_V2_RELATIONAL_NCA.md`; coherent trajectories and bounded v2 soak | In progress: v2 inference is bounded but held-out action accuracy is 25/194 and closed-loop completion 1/12; robust Hanoi competence remains unestablished |
| P05-012 | Prepare G3 with complete differences, host feedback boundary, and a freeze-eligible first model; stop before P06. | stage specifications, P05 | Proposed ADR-0003; accepted experimental ADR-0004; updated G3 packet; no P06 artifacts | At G3; neither v1 nor v2 is functionally freeze-eligible; final G3 choice remains open |
| P05-013 | Implement the user-authorized v2 structural experiment separately, verify its bounded eight-channel operator and measure policy behavior without changing the accepted logical interface. | User authorization 2026-09-29; ADR-0004 | `training/hanoi_nca/{layout_v2.json,v2_model.py,v2_adapter.py,v2_runtime.py,run_v2.py,difference_manifest_v2.json}`; six v2 tests; `experiments/p05_v2/`; `P05_V2_RELATIONAL_NCA.md` | Verified as implementation and measured negative policy experiment; no functional freeze |
| P05-014 | Test the v2 teaching-bottleneck hypothesis with a paper-mechanics warm-up, persistent grid pool, original recurrent schedule, long oracle-supervised action phase, and resumable evidence. | User authorization 2026-09-29; P05 experiment specification | `training/hanoi_nca/run_v2_paper_flow.py`; deterministic resume tests; `docs/verification/P05_V2_PAPER_TEACHING_CONTINUATION.md` | Negative and stopped: fresh warm-up outputs saturated at -5; imitation loss ln(6) with zero gradient; bulky data replaced by user request |
| P05-015 | Repair the measured warm-up zero-output/saturation failure with a gated, variance-calibrated spatial curriculum and separate stable numerical experiments, while preserving P04 and the G3 boundary. | User authorization 2026-09-30; P05 experiment specification; ADR-0005 | `training/hanoi_nca/{run_v3_teaching.py,v3_runtime.py,v4_runtime.py,layout_v6.json}`; `test_v3_teaching.py`; `P05_V3_GATED_TEACHING_CONTINUATION.md`; retained 36-input warm-up seed | Measured: 14 inaccessible v2 inputs fixed; spaced v6 layout passed relay, broadcast, combination, routing, legality; two-disk imitation failed at fresh/persistent 0.4375/0.479167 vs 0.85; no model freeze |
| P05-016 | Test whether supervised six-action progress, separate legality semantics, coherent state/grid trajectories, and distinct-state validation repair the imitation bottleneck before changing spatial topology. | User authorization 2026-09-30; proposed ADR-0006 | `training/hanoi_nca/run_v7_teaching.py`; `test_v7_teaching.py`; `experiments/p05_v7_stopped/`; `P05_BASELINE_REVERSION_AND_ARCHITECTURE_OPTIONS.md` | Stopped by user-requested architecture-first reversion at 4,250 updates; latest fresh/coherent action accuracy 0/0.375, no gate or closed-loop success; prior v6 source configuration active, exact old trained weights unavailable |
