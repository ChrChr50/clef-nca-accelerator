# Clef-NCA: A Tapeout-Oriented Neural Cellular Automata Accelerator for Robust CartPole Control

> Historical-scope notice (2026-10-06): retained for provenance, not the active forward implementation plan. ADR-0007 and docs/architecture/EMBODIED_NCA_VISION.md supersede task-specific choices. Original-reference evidence and dated experimental decisions remain preserved; no new embodied acceptance or model freeze is implied.

## Preliminary semester project proposal and staged research trajectory

**Working project name:** Clef-NCA  
**Guaranteed baseline deliverable:** A synthesizable, fixed-point neural cellular automata (NCA) inference accelerator demonstrated in closed-loop CartPole control on an FPGA.  
**Tapeout-oriented target:** Take the same verified core through an ASIC RTL-to-GDSII flow; actual MPW submission remains conditional on course infrastructure, funding, and shuttle dates.  
**Long-term trajectory:** Extend the same cellular substrate with locally maintained connectivity, plasticity, viability, and role migration to test progressively stronger forms of self-maintaining organization and, eventually, the full Clef autopoiesis hypothesis.

---

## 1. Executive decision

The closest documented starting point is Alexandre Variengien et al.'s 2021 CartPole neural cellular automaton, *Towards Self-organized Control: Using Neural Cellular Automata to Robustly Control a Cart-pole Agent*. It is unusually well matched to this project because it combines:

- a two-dimensional cellular substrate;
- a shared local neural update rule;
- recurrent distributed state rather than a conventional feed-forward policy graph;
- a reinforcement-learning control task;
- explicit input and output cells embedded in the grid;
- reported tolerance to cell-state damage, update noise, and some input deletion; and
- public source code, a notebook, and pretrained models.

The paper's reference implementation uses a 32 x 32 grid, six state channels per cell, eight input cells carrying four redundant CartPole observations, two output cells encoding action values, 20 learned 3 x 3 x 6 perception filters, a 30-unit hidden layer, and 1,854 learned parameters shared across all cells. Each cell is selected for update with probability 0.5, and the NCA evolves for 50--60 cellular steps before each environment action. Training is external: Deep Q-learning, Adam, and backpropagation through time optimize the shared local rule in software. These details come directly from the [paper](https://arxiv.org/html/2106.15240) and its [public repository](https://github.com/aVariengien/self-organized-control).

No located prior work supplies the exact intersection of this controller with a reusable digital NCA accelerator. The nearest hardware companion is Paluch et al.'s 2024 FPGA implementation of ordinary neural controllers for physical CartPole and F1TENTH systems. It demonstrates the surrounding engineering pattern—train off-chip, quantize, implement the controller in programmable logic, measure latency and power, and close the loop with a physical plant—but it does not implement a cellular controller. Their CartPole controller reportedly reaches 1 kHz closed-loop control, with a 91-cycle, 3.64 microsecond estimated compute latency on their selected FPGA design. It is therefore a useful hardware methodology and comparison point, not the proposed design itself: [paper](https://arxiv.org/html/2407.08681v1), [hardware repository](https://github.com/SensorsINI/Neural-Control-Tools).

The recommended semester project is consequently:

> **Reproduce, quantize, architect, implement, verify, and characterize a reusable FPGA/ASIC accelerator for the Variengien CartPole NCA; then use its fault-injection and parameterization hooks as the controlled experimental chassis for later Clef extensions.**

This is the best compromise between a guaranteed conventional ECE deliverable and a faithful path toward the larger research program.

---

## 2. Claim discipline

This proposal deliberately separates what the semester baseline establishes from what later Clef experiments may test.

### 2.1 What the baseline is

The baseline is a hardware implementation of an externally trained, fixed shared local rule operating over a recurrent spatial state. It is a real digital controller, not merely an animation of one: the FPGA state and arithmetic causally generate the CartPole actions in closed loop.

It is also a bio-inspired cellular system with developmental-looking transients and recovery behavior. The original paper reports stable control beyond 10,000 simulation steps and recovery under several perturbations. Its strongest damage results, however, must be interpreted in light of its training procedure: half of the sampled NCA grids were damaged during training. Uniformly distributed damage and input deletion supplied more novel tests, but robustness was uneven across deleted inputs.

### 2.2 What the baseline is not

The baseline is not, by itself:

- autopoietic;
- closed to efficient cause (CEC);
- an `(F, A)` or `(M, R)` realization;
- self-manufacturing at either the transistor or organizational level;
- online self-training;
- open-ended evolution;
- evidence for Medium or Strong Rosen; or
- evidence that its functional semantics escape every fixed computable description.

Its weights, cell types, neighborhood, boundary rule, channel meanings, I/O locations, reward, and training algorithm are externally fixed. The system can recover a learned spatial regime after state damage, but persistence or regeneration under a fixed update rule is weaker than autopoiesis. In the project's standing hierarchy:

> **emergence < adaptation < autopoietic organization < evidence relevant to Medium Rosen.**

Later experiments must earn each step rather than rename the baseline.

### 2.3 Terminology correction: stochastic updates are not clockless RTL

The source paper says that independent 0.5-probability cell updates discourage reliance on globally synchronized cell updates. In a conventional FPGA realization, this will be implemented as a synchronous, seeded update-enable mask. It reproduces the relevant transition semantics but is not a physically asynchronous or clockless fabric. A genuinely asynchronous implementation is a separate architectural investigation and is not required for the semester deliverable.

### 2.4 Tapeout wording

The committed deliverable is **tapeout-oriented** or **tapeout-ready**: clean synthesizable RTL, verification, constraints, synthesis, place-and-route, timing closure, power estimation, DRC/LVS where the chosen educational flow permits it, and a GDSII artifact. Submission to an MPW shuttle is a stretch deliverable because foundry access, dates, funding, packaging, and board bring-up are external dependencies.

---

## 3. Research objective

### 3.1 Primary objective

Design and evaluate a parameterized digital accelerator that executes a learned local NCA rule over a two-dimensional state grid and uses the resulting recurrent dynamics to control CartPole.

The project must demonstrate a complete algorithm-to-silicon workflow:

1. reproduce the reference software behavior;
2. define a fixed-point numerical contract;
3. derive a cycle-accurate hardware architecture;
4. implement and verify synthesizable RTL;
5. run closed-loop hardware-in-the-loop control;
6. characterize robustness, throughput, latency, resource use, and energy; and
7. complete an ASIC implementation flow to a tapeout-ready macro.

### 3.2 Core research questions

**RQ1 — Fidelity:** Can a quantized hardware NCA preserve the control performance and characteristic perturbation response of the floating-point reference?

**RQ2 — Architecture:** Which mixture of spatial parallelism and temporal folding gives the best area/latency/energy tradeoff for repeated local-rule execution?

**RQ3 — Locality:** How much of the NCA's nominal spatial locality survives physical implementation once state memories, neighborhood reads, shared weights, and arithmetic reuse are included?

**RQ4 — Sparse activity:** Can the stochastic update mask be exploited as clock-enable, operand-isolation, or skipped-work sparsity without changing seeded transition semantics?

**RQ5 — Robustness cost:** What hardware overhead is required to preserve control under cell-state corruption, disabled cells, broken neighborhood links, or missing inputs?

**RQ6 — Extension readiness:** Can the baseline datapath and state organization expose edge and cell metadata without requiring a redesign when later adding local plasticity and viability dynamics?

### 3.3 Hypotheses

- A fixed-point NCA can retain acceptable CartPole control after quantization-aware retraining or calibrated post-training quantization.
- A folded accelerator with a banked grid memory and several parallel MAC lanes will be substantially more feasible for a semester FPGA and small ASIC macro than one complete neural cell engine per logical grid location.
- Seeded mask replay will permit bit-exact software/RTL equivalence while update sparsity reduces switching activity and, when scheduling allows, executed work.
- Fault tolerance will not be free: some robustness comes from distributed dynamics, but redundancy, state capacity, and recovery iterations consume area, time, or energy and must be measured against a conventional controller.

---

## 4. Scope contract

The project is divided into three nested completion levels. Each level is independently defensible; later levels do not invalidate an earlier deliverable.

### Level A — Guaranteed semester deliverable

Level A is the minimum successful project and must be protected from scope creep.

- Reproduce at least one released/pretrained CartPole NCA in software.
- Freeze a precise operator graph from the actual implementation rather than reconstructing it from prose alone.
- Build a bit-accurate fixed-point reference model.
- Implement a parameterized NCA inference core in SystemVerilog.
- Verify cellular-step output against the reference model using deterministic masks and stored trace vectors.
- Synthesize the core for the available FPGA and report clock frequency, LUTs, flip-flops, block RAMs, DSPs, cycle counts, and estimated power.
- Demonstrate the FPGA controlling a host-simulated CartPole environment. Real-time wall-clock operation is a target; functionally closed-loop slowed-time operation remains an acceptable fallback if the selected device cannot meet the full 32 x 32, 50--60-step deadline.
- Implement repeatable state, input, and cell-disable fault injection.
- Compare float software, quantized software, and RTL/FPGA behavior.

### Level B — Strong semester/thesis deliverable

- Complete design-space exploration over numerical width, MAC-lane count, memory banking, and optional active-cell skipping.
- Compare against a compact conventional MLP/DQN controller under the same CartPole task and implementation assumptions.
- Measure board-level latency and power where instrumentation permits.
- Take the NCA core through an open or university-supported RTL-to-GDSII flow with timing closure and physical-design reports.
- Release reproducible scripts, tests, traces, trained weights, and documentation where licensing permits.

### Level C — Clef research extensions

- Add locally stored connection state and eligibility/plasticity variables.
- Add a distributed viability signal coupled to environmental performance.
- Permit link loss, restoration, and context-sensitive routing.
- Test migration of causal roles after damage or environmental remapping.
- Introduce reciprocal maintenance relations between distinct functional coalitions.
- Only after intervention evidence supports it, evaluate claims of organizational closure or CEC.

Level C is not required to pass the semester project. It is the reason the Level A architecture is parameterized rather than a one-off NCA datapath.

---

## 5. Reference workload and reproducibility contract

### 5.1 Reference model

The authoritative workload is the source repository corresponding to Variengien et al., pinned to an exact commit. Before RTL begins, the project will record:

- repository commit hash;
- software environment and dependency versions;
- pretrained checkpoint identity and checksum;
- exact tensor shapes, padding, boundary behavior, activation functions, biases, residual update, clamping, and cell-type write protections;
- input normalization constants;
- grid initialization distribution;
- PRNG and update-mask behavior;
- the number of NCA steps per environment action;
- output scaling and action selection;
- the modified CartPole reward and termination rules; and
- deterministic evaluation seeds.

The paper is sufficiently precise to select the project, but not sufficient to write equivalent RTL safely. In particular, its stated layer dimensions and total parameter count should be reconciled against the executable graph before estimating exact operations, storage, or multiplier count.

### 5.2 Software reproduction gate

RTL work begins only after the following gate is met:

- the reference checkpoint runs locally;
- nominal closed-loop score is reproduced within a predeclared statistical tolerance;
- at least one published perturbation condition is qualitatively reproduced;
- per-step tensors can be exported as golden traces; and
- the code/repository license has been checked before redistributing derived source or weights.

If the old software stack cannot be reproduced quickly, the fallback is to reimplement the published operator in a current framework and train a compatible model. The fallback changes the claim from exact reproduction to architectural replication and will be stated as such.

### 5.3 Numerical conversion

The project will sweep signed fixed-point formats rather than choose one informally. Candidate formats should include 8-, 12-, and 16-bit state/weight representations with wider accumulators. The flow is:

1. collect state, weight, activation, and accumulator distributions;
2. establish saturation and rounding rules;
3. evaluate post-training quantization;
4. use quantization-aware retraining if necessary;
5. lock a single bit-exact format for RTL; and
6. test long recurrent rollouts for drift, overflow, limit cycles, and control failure.

Long-horizon equivalence matters more here than one-step mean-squared error because small numerical deviations are repeatedly fed back through both the NCA and the controlled environment.

---

## 6. Proposed hardware architecture

### 6.1 Architectural principle

The first implementation will be a **folded cellular engine**: logical cells remain spatially arranged and communicate only through their local neighborhood, while a smaller number of physical processing lanes time-multiplexes the shared local rule. This preserves the model's causal transition structure without attempting to instantiate thousands of complete neural update networks.

The distinction is important:

- **logical topology:** a 2-D grid with local neighborhoods;
- **physical microarchitecture:** banked memory, schedulers, and reusable MAC lanes;
- **model semantics:** one old grid state produces one new grid state under a specified mask;
- **implementation schedule:** an engineering choice that must not change those semantics.

### 6.2 Top-level blocks

```text
Host / plant interface
        |
Observation encoder ---- Configuration/status bus
        |                         |
        v                         v
  Input-cell writer       Control and step sequencer
        |                         |
        +----------+--------------+
                   v
          Banked state memory A
                   |
         Neighborhood window unit
                   |
          Parallel MAC-lane array <---- Weight/bias ROM
                   |
       Activation, residual, saturation
                   |
          Update-mask / fault gate <---- Seeded PRNG + fault CSR
                   |
          Banked state memory B
                   |
              A/B swap
                   |
          Output-cell reader
                   |
          Action / Q-value result
```

### 6.3 State memory

Two logical state buffers implement Jacobi-style step semantics: all updates at NCA step `k+1` read the completed state at step `k`. Ping-pong buffering avoids read-after-write order dependence.

The memory subsystem stores `rows x columns x channels` state values. It should be parameterized for smaller test grids and the 32 x 32 reference grid. Banking must permit the neighborhood unit to sustain the selected cell issue rate without silently converting the local stencil into a memory bottleneck.

For an FPGA, block RAM or distributed RAM selection is part of the design-space exploration. For ASIC, the interface should permit either inferred SRAM macros or a register-file fallback in the educational flow.

### 6.4 Neighborhood window unit

For each scheduled logical cell, the window unit emits the required 3 x 3 x 6 neighborhood in the exact reference order. It handles:

- zero or reference-matched boundary padding;
- cell coordinates and row transitions;
- fixed input-cell fields;
- optional disabled-cell/disabled-edge masks; and
- deterministic handling of output cells.

A streaming line-buffer architecture is attractive for dense raster sweeps. Direct banked random access is more flexible for sparse masked-cell scheduling and later dynamic connectivity. The semester design should begin with dense raster order plus write suppression; skipped-compute scheduling is an optimization evaluated only after correctness.

### 6.5 Local-rule engine

The local-rule engine implements the frozen learned operator:

1. local perception over the 3 x 3 neighborhood;
2. hidden affine layer;
3. reference activation function;
4. output affine layer;
5. residual state update;
6. saturation/rounding; and
7. protection or overwrite rules for fixed input-cell channels.

Weights are shared across all cells and stored once in ROM or preloadable RAM. A parameterized MAC array exposes the principal PPA tradeoff:

- few lanes: low area, high sweep latency;
- many lanes: high area, low latency;
- intermediate lane count: likely semester optimum.

The initial design target should sweep 8, 16, 32, and 64 MAC lanes if the device permits. No performance number should be promised until the exact executable graph and target clock are frozen. A useful first-order workload estimate is:

```text
cell updates per action ~= rows * columns * NCA_steps * update_probability
MACs per action         ~= cell updates per action * MACs per cell update
```

For the published 32 x 32 grid, 50--60 NCA steps, and 0.5 update probability, this is tens of thousands of selected cell updates per CartPole action. It makes folding necessary and places MAC-lane count, memory bandwidth, and control interval at the center of the design.

### 6.6 Update mask and deterministic replay

A seeded LFSR or counter-based PRNG generates the per-cell update enable. Required operating modes are:

- `REFERENCE_MASK`: consume a stored software-generated mask for bit-exact trace testing;
- `SEEDED_MASK`: generate a repeatable on-chip pseudo-random mask;
- `ALL_UPDATE`: update every eligible cell for debug and characterization; and
- `EXTERNAL_MASK`: accept experiment-controlled masks for fault and scheduling studies.

Masking first suppresses writes. Operand isolation and full computation skipping are later power/performance optimizations and must be checked for identical visible behavior.

### 6.7 Control and interfaces

The core should have a narrow, conventional integration shell:

- memory-mapped configuration/status registers, preferably AXI-Lite or a simple bus with an AXI-Lite wrapper;
- streaming or register writes for four normalized observations;
- a `start_action` command specifying the number of NCA iterations and seed;
- two output action values plus chosen-action status;
- interrupt or `done` signaling;
- counters for cycles, selected cells, skipped cells, saturation events, and faults; and
- debug access to state-memory regions.

The host computer initially integrates the plant. It sends observations, waits for an accelerator action, advances CartPole, and returns the next observation. This cleanly isolates the accelerator's computation from the environment while retaining a genuine closed causal loop.

### 6.8 Fault-injection fabric

Fault injection is a first-class baseline feature because robustness is both scientifically relevant and architecturally differentiating. It must support:

- corrupting a rectangular or circular region of writable cell state;
- replacing state with zero, uniform pseudo-random values, or a fixed pattern;
- disabling selected cells;
- suppressing selected directional neighbor contributions;
- removing or replacing selected inputs; and
- recording the exact injection time, seed, location, and duration.

Fault controls are externally commanded in Level A. That is an experimental instrument, not endogenous repair.

### 6.9 Extension fields reserved for Clef

The baseline state-memory address map and neighborhood packet should reserve optional fields for:

- edge weight or conductance `w`;
- edge existence/availability `g`;
- eligibility/plasticity trace `e`;
- local resource or viability variable `q`;
- local threshold/homeostatic parameter `h` or `theta`; and
- role/activity metadata used only for observation, not for externally assigning function.

These fields may be compiled out in Level A. Reserving interfaces does not claim they already produce organization; it prevents the later experiments from requiring a new accelerator chassis.

---

## 7. Closed-loop experiment design

### 7.1 Nominal protocol

For each seeded episode:

1. initialize the CartPole state and NCA grid;
2. write the four normalized observations into the eight designated input cells;
3. execute the configured number of NCA steps;
4. read the two output-cell values;
5. apply the argmax left/right action;
6. advance the environment;
7. retain the NCA grid state across control actions; and
8. continue until termination or the declared horizon.

The environment must duplicate the reference paper's modified reward for reproduction results. A separate standard Gymnasium CartPole protocol may be added for comparability, but results from the two reward functions must never be mixed.

### 7.2 Perturbation matrix

Each controller/precision/architecture point will be evaluated under:

- no perturbation;
- one-time localized state damage;
- periodic localized damage;
- spatially distributed damage;
- random cell disablement at increasing fractions;
- broken directional links at increasing fractions;
- deletion of each redundant input individually;
- deletion of both copies of one observation;
- observation bias, quantization, and delay; and
- CartPole parameter changes such as pole mass, pole length, force magnitude, and friction when supported by the environment.

Not every condition is expected to be survivable. The purpose is to obtain degradation and recovery curves, not select only favorable demonstrations.

### 7.3 Metrics

**Functional metrics**

- episode return and survival length;
- success/failure rate across seeds;
- cart-position and pole-angle error;
- action disagreement versus the floating-point model;
- time or NCA steps to recover after perturbation;
- retained performance as a function of damaged fraction; and
- long-run state saturation or numerical divergence.

**Hardware metrics**

- cycles per selected cell update;
- cycles per grid step and CartPole action;
- maximum clock frequency;
- control decisions per second;
- LUT, flip-flop, BRAM/SRAM, and DSP/multiplier use;
- FPGA measured or tool-estimated power;
- ASIC area, critical path, and estimated dynamic/leakage power;
- energy per cell update, grid step, and control decision; and
- fault-support overhead relative to the same core with instrumentation removed.

**Joint metrics**

- energy per successful control second;
- area-energy-delay versus control score;
- robustness per unit area/energy; and
- performance retained per disabled cell or link.

### 7.4 Required comparisons

At minimum:

1. original floating-point NCA software;
2. bit-accurate quantized NCA software;
3. RTL simulation;
4. FPGA NCA; and
5. a compact conventional MLP/DQN controller with comparable nominal task performance.

The conventional controller prevents a misleading conclusion in which the NCA is called efficient solely because FPGA inference is fast. A fair evaluation asks what the cellular recurrent substrate costs and what robustness or adaptability it buys.

The Paluch et al. accelerator is a literature comparator, not necessarily an apples-to-apples benchmark: its controller, training objective, plant, hardware, and numerical format differ. Its value is to show that a complete hardware CartPole control loop and disciplined latency/power reporting are realistic.

---

## 8. Verification plan

### 8.1 Unit verification

- fixed-point multiplier, accumulator, rounding, and saturation;
- activation approximation;
- PRNG sequence and mask threshold;
- neighborhood ordering and boundary padding;
- input-cell write protection;
- ping-pong memory swap;
- fault-mask addressing; and
- output readout and argmax.

### 8.2 Differential verification

A cycle-accurate software model will consume the same state, weights, observations, mask bits, and faults as RTL. Automated tests will compare:

- local-rule intermediates;
- a single cell update;
- a complete grid step;
- 50--60 recurrent steps;
- multiple environment actions; and
- long closed-loop traces.

Comparison is bit-exact after quantization. Floating-point comparison uses declared error and policy-agreement tolerances.

### 8.3 Assertions and coverage

SystemVerilog assertions should check:

- no write to protected channels except through the input interface;
- no read/write bank alias during a grid step;
- correct cell and step counts;
- valid memory addresses at boundaries;
- stable configuration while busy;
- completion within a derived cycle bound; and
- deterministic replay for a fixed seed.

Coverage should cross boundary class, cell type, update enable, saturation, fault mode, and memory-bank transitions.

### 8.4 Hardware validation

FPGA tests should include known-answer traces, prolonged grid evolution, closed-loop CartPole, deliberate damage, and repeated runs under identical seeds. On-chip logic analysis or trace buffers should capture representative internal state without making full-grid continuous readback a performance requirement.

---

## 9. PPA design-space exploration

The exploration should prioritize architectural questions that are both publishable and useful for conventional hardware roles.

### 9.1 Parallelism and folding

Sweep physical MAC lanes and, if practical, parallel logical-cell issue. Report the Pareto frontier rather than declaring one configuration universally optimal.

### 9.2 State storage and locality

Compare feasible banking and buffering strategies. Quantify memory energy and stalls; do not infer physical locality merely from the mathematical stencil.

### 9.3 Precision

Sweep state, weight, and accumulator widths. Recurrent control quality, recovery, and numerical stability are co-equal constraints with area.

### 9.4 Activity sparsity

Separate three cases:

- masked write only;
- operand isolation/clock enables;
- skipped scheduling of non-updated cells.

Measure whether power savings justify the PRNG, scheduler, and irregular access overhead.

### 9.5 Multirate and reduced computation

Explore fixed versus variable NCA iterations per action only after reproducing the 50--60-step baseline. Early-exit or convergence detection is a stretch optimization and must not be confused with the source algorithm.

### 9.6 Fault-tolerance tax

Report fault-injection, metadata, spare capacity, and recovery-time overhead. The engineering question is not just whether distributed dynamics survive damage, but whether their total silicon cost is competitive with simpler redundancy schemes.

---

## 10. Semester execution plan

This schedule assumes a 15-week semester and intentionally front-loads reproducibility and numerical risk.

| Weeks | Work package | Exit criterion |
|---|---|---|
| 1--2 | Pin source, recreate environment, run pretrained model, inspect exact operator | Deterministic software run and saved golden traces |
| 3--4 | Fixed-point study and quantization | Chosen numerical format meets declared control/trace tolerance |
| 5 | Cycle/bit-accurate architecture model | Model matches quantized software across unit and rollout tests |
| 6--8 | RTL state memory, neighborhood unit, local-rule engine, controller | Complete grid steps match golden vectors |
| 9 | PRNG/masks, input/output interface, instrumentation, faults | Reproducible multi-step RTL traces under nominal and fault modes |
| 10 | FPGA synthesis and timing iteration | Bitstream runs known-answer test; resource/timing report captured |
| 11 | Host link and closed-loop CartPole | FPGA-generated actions control the environment |
| 12 | Robustness experiments | Seeded degradation/recovery data collected |
| 13 | PPA parameter sweep and conventional-controller comparison | Pareto data and comparison plots complete |
| 14 | ASIC synthesis/place-and-route | Timing/area/power reports; GDSII if flow supports it |
| 15 | Reproducibility freeze, report, demonstration | Tagged repository, final report, demo, and artifact manifest |

### 10.1 Scope freeze dates

- End of week 2: reference implementation and semantics frozen.
- End of week 4: precision frozen for the primary RTL configuration.
- End of week 6: no new baseline features; only completion and debug.
- End of week 10: Level A takes priority over every Clef extension.
- Level C work begins only after FPGA closed-loop control is demonstrated.

---

## 11. Deliverables and acceptance criteria

### D1. Reproducible reference package

- environment lockfile/container recipe;
- pinned source/checkpoint metadata;
- model/operator specification;
- golden test vectors; and
- nominal plus perturbation reproduction report.

**Accepted when:** another machine can regenerate at least the declared nominal result and the vectors used by RTL tests.

### D2. Fixed-point model

- numerical-format report;
- bit-accurate implementation; and
- long-rollout error/control comparison.

**Accepted when:** the quantized model meets a predefined policy agreement and CartPole performance threshold across a fixed seed set.

### D3. Synthesizable RTL accelerator

- parameterized SystemVerilog;
- configuration and host interface;
- deterministic mask modes;
- counters and fault injection; and
- simulation testbench.

**Accepted when:** all required golden traces match bit-for-bit and synthesis completes without inferred unintended latches or unresolved timing paths.

### D4. FPGA demonstration

- bitstream;
- host control program;
- closed-loop CartPole demonstration; and
- measured cycles and device utilization.

**Accepted when:** the hardware performs repeated closed-loop episodes and its outputs agree with the quantized reference for deterministic replay.

### D5. Evaluation report

- nominal performance;
- perturbation matrix;
- PPA sweeps;
- conventional-controller comparison; and
- explicit limitations.

**Accepted when:** all plots are generated by checked-in scripts from archived raw data.

### D6. ASIC/tapeout package

- synthesis and timing constraints;
- lint and CDC reports as applicable;
- gate-level or post-layout verification;
- place-and-route reports;
- area/power/timing summary; and
- GDSII plus DRC/LVS evidence if available in the selected flow.

**Accepted when:** the design reaches the highest documented closure stage supported by the course/PDK, with any remaining foundry-dependent steps identified.

---

## 12. Risk register and fallbacks

| Risk | Early indicator | Mitigation | Guaranteed fallback |
|---|---|---|---|
| Reference repository no longer runs | Dependency failures in week 1 | Containerize legacy stack; use released checkpoint | Reimplement operator and retrain, clearly labeled replication |
| Parameter-count/operator ambiguity | Paper dimensions do not match graph | Treat executable graph as implementation authority; document discrepancy | Freeze a functionally verified compatible operator |
| Quantization destabilizes recurrence | Long rollout diverges despite low one-step error | Wider state/accumulator; QAT; saturation study | Use 16-bit or mixed precision |
| Full 32 x 32 controller misses real-time | Cycle model exceeds control interval | More lanes, higher clock, skip masked cells, fewer verified iterations if retrained | Slowed-time closed-loop demo plus measured accelerator throughput |
| FPGA resource exhaustion | Early synthesis exceeds BRAM/DSP/LUT budget | Fold more heavily; use shared activation/MAC resources | Smaller grid/model trained on same task while retaining parameterized 32 x 32 simulation |
| Host communication dominates latency | Interface profiling shows idle accelerator | Batch/debug protocol first; DMA/streaming only if needed | Report compute latency separately and run functional HIL |
| ASIC memories unavailable | PDK flow lacks SRAM macros | Abstract memory wrappers | Register-file/synthesized-memory demonstrator on reduced configuration |
| Actual shuttle unavailable | No funded slot or deadline mismatch | Finish all pre-submission artifacts | Tapeout-ready GDSII and signoff report, not fabricated silicon |
| Clef extensions threaten schedule | Baseline not closed by week 10 | Enforce scope gate | Defer all Level C work |

---

## 13. Staged extension from NCA accelerator to Clef testbed

The extension path is designed as controlled ablation, with the original fixed-rule NCA always retained as Mode 0.

### Mode 0 — Fixed-rule NCA baseline

- shared fixed learned update rule;
- fixed local neighborhood;
- externally designated I/O cells;
- retained recurrent grid state;
- stochastic update mask; and
- externally injected faults.

This demonstrates emergence, distributed recurrence, and some robustness. It does not demonstrate endogenous functional organization.

### Mode 1 — Locally plastic cellular network

Add per-edge `w` and eligibility `e`, updated only from local pre/post state, local modulatory variables, and neighboring signals. Keep topology `g` fixed initially.

Questions:

- Can the controller adapt online to changed plant parameters or sensor mappings?
- Do local changes preserve function after damage better than the fixed NCA?
- What PPA and energy overhead does plastic state impose?

This may demonstrate adaptation. Plasticity alone is not autopoiesis.

### Mode 2 — Viability-coupled maintenance and dynamic connectivity

Add local resource/viability `q` and dynamic connection availability `g`. Successful action affects environmental feedback, which changes local viability; viability in turn gates state retention, communication, repair, or plasticity. Links and active regions must decay or become unavailable without continued maintenance.

Questions:

- Does behavior maintain the material/causal conditions that enable that behavior?
- After damage, does the system recruit idle cells or alternate links rather than merely relax under a fixed map?
- Are the maintaining relations reciprocally dependent under interventions?

This is a candidate experiment for self-maintaining organization, not proof by construction.

### Mode 3 — Role migration and closure experiments

Remove permanent semantic identity from ordinary cells. Permit input mediation, action production, routing, repair, and plasticity support to migrate among physical regions subject to the fixed external transducer boundary.

Use interventions to identify candidate functional coalitions `C_A`, `C_B`, and `C_C` and test whether each coalition's causal capacity is maintained by processes generated by others:

```text
C_A -> environmental action -> viability conditions maintaining C_B
C_B -> plasticity/connectivity conditions maintaining C_C
C_C -> organization/recruitment conditions maintaining C_A
```

The arrows must denote maintenance of causal capacity, not temporal co-activation. A successful claim requires counterfactual necessity, recovery, reciprocal dependence, and exclusion of a hidden external maintainer.

### Mode 4 — Medium Rosen empirical program

Only after a credible Mode 3 result should the project address the standing Medium Rosen claim:

> Microstate evolution may be computable while no single fixed computable model exhaustively captures the system's historically constituted functional-entailment semantics.

The empirical program would seek persistent failure of frozen functional models under endogenous role creation and intervention, while microstate prediction remains intact. No finite collection of failed probes proves non-computability. The hardware can, at most, provide increasingly stringent evidence that fixed externally chosen semantic decompositions lose explanatory and engineering sufficiency.

This preserves the project's central philosophical ambition without making it a premise of the accelerator design.

---

## 14. Novelty statement

The safe novelty claim for the semester proposal is:

> A parameterized, fault-injectable FPGA/ASIC architecture and evaluation methodology for recurrent neural cellular automata used in closed-loop control, demonstrated on a published CartPole NCA and designed to support later local-plasticity and viability-coupled extensions.

Potentially novel components include:

- hardware scheduling for recurrent NCA control rather than one-shot image morphogenesis;
- joint PPA/control/robustness evaluation;
- deterministic replay of stochastic cellular updates across software and RTL;
- comparison of write masking, operand isolation, and true skipped-work execution;
- link-level fault injection and recovery characterization; and
- a common hardware chassis supporting fixed NCA, local plasticity, dynamic connectivity, and viability-coupled modes.

These are proposal claims pending a formal prior-art review. The proposal should not claim to be the first FPGA CA, first hardware neural controller, first NCA, or first robust distributed controller.

---

## 15. Why this is a strong conventional engineering project

Even if none of the Clef extensions succeeds, the work demonstrates:

- translation of a nonstandard learned algorithm into a precise hardware specification;
- fixed-point and recurrent numerical analysis;
- memory banking and stencil dataflow;
- configurable parallel MAC architecture;
- RTL design, assertions, and differential verification;
- FPGA integration and hardware/software co-design;
- embedded closed-loop control;
- fault injection and reliability evaluation;
- quantitative PPA design-space exploration; and
- ASIC synthesis, timing closure, and physical design.

The advisor/recruiter version of the project can therefore be stated without Rosenian prerequisites:

> “I built and physically characterized a configurable neural cellular automata accelerator for robust real-time control, verified it against a published reference model, and evaluated the cost of distributed recovery under hardware faults.”

The research version adds:

> “The accelerator is deliberately structured as a controlled experimental platform for testing whether local plasticity and viability-coupled maintenance can produce stronger forms of self-maintaining functional organization.”

Both descriptions are true at their respective stages.

---

## 16. Recommended advisor pitch

> This semester I propose to implement a hardware accelerator for a published neural cellular automaton that controls CartPole. The reference system is a 32 x 32 recurrent grid whose cells share a learned local update rule; it has public code and reported robustness to state damage, noise, and some sensor deletion. I will reproduce and quantize the model, build a parameterized fixed-point SystemVerilog accelerator, close the control loop with a host CartPole environment on FPGA, evaluate latency, resources, power, and fault recovery, and take the core through an ASIC physical-design flow. This gives a complete and independently valuable accelerator project. The same architecture will reserve optional local edge, plasticity, and viability state so a later phase can compare the fixed NCA against progressively more self-maintaining cellular organizations. I will not claim that the baseline is autopoietic; that remains a hypothesis to be tested through explicit interventions in the extension modes.

---

## 17. Immediate next actions

1. Pin and execute the public NCA repository; record commit, model checkpoint, environment, and license status.
2. Export one-cell, one-step, and 60-step golden traces including mask bits.
3. Reconcile the published 1,854-parameter statement with the executable operator graph.
4. Define the target FPGA, toolchain, available DSP/BRAM budget, host interface, and ASIC/PDK flow.
5. Build a spreadsheet or script-level cycle/resource model for MAC-lane and memory-bank sweeps.
6. Set numerical and control acceptance thresholds before quantization.
7. Implement fixed-point arithmetic and a single-cell update engine before building the grid scheduler.
8. Hold all endogenous plasticity and viability features until the Level A FPGA loop passes.

---

## 18. Primary sources

1. A. Variengien, S. Pontes-Filho, T. E. Glover, and S. Nichele, “Towards Self-organized Control: Using Neural Cellular Automata to Robustly Control a Cart-pole Agent,” 2021. [Paper](https://arxiv.org/html/2106.15240) · [Code and pretrained models](https://github.com/aVariengien/self-organized-control)
2. M. Paluch et al., “FPGA Hardware Neural Control of CartPole and F1TENTH Race Car,” 2024. [Paper](https://arxiv.org/html/2407.08681v1) · [Hardware repository](https://github.com/SensorsINI/Neural-Control-Tools)

---

## 19. Bottom line

The CartPole NCA is the correct preliminary project because it is close enough to Clef to preserve the cellular, local, recurrent, damage-tolerant research direction, yet conventional enough to guarantee a real accelerator deliverable. The semester work should succeed or fail on clear hardware and control metrics—not on whether Rosen's strongest claims are settled. Its deepest value is architectural continuity: the same verified cellular engine can become the control case against which later plastic, viability-coupled, role-migrating, and candidate-CEC systems are tested.
