# E00/G2E: benchmark comparison for the one-semester embodied NCA accelerator

> Historical decision packet. On 2026-10-07 the user selected reference-paper CartPole, with custom surface and EvoGym as post-FPGA extensions (accepted ADR-0008). The recommendation and pending-choice statements below describe the earlier comparison, not active implementation authority. Use ../STATUS.md to resume.

Date: 2026-10-06. Status: decision packet, awaiting user selection. Sources inspected online on this date; no candidate installed, trained, timed or profiled locally. Feasibility/risk rankings below are engineering judgments, not measurements.

## Confirmed scope and decision

The user wants comparison → user selection → replacement of the active Hanoi benchmark. The endpoint is a real FPGA controlling a simulated physical plant, within one semester. A physical robot/apparatus is not required. Exact due date, remaining weeks and available training compute are not established.

Select one primary workload, not three parallel projects. A benchmark choice does not automatically accept its default observation interface, a new neural operator, a spiking model, exact grid size, event threshold or timing budget. Those require executable contracts and later gates. Original CartPole reproduction and historical Hanoi work remain controls/provenance, not new-target completion.

## Side-by-side comparison

| Option | Existing documented foundation | Strength for this project | Principal additional work/risk |
|---|---|---|---|
| A. Modular soft-robot locomotion | Published embodied NCA/SNCA controllers, experiment code and a simulated voxel robot | Strongest direct prior art for local sensors, neighbor communication and distributed actuators | Java simulation/training integration, provenance/licensing audit, different controller graph; continuous motion need not be sparse |
| B. EvoGym Balancer-v0 | Established soft-body plant and RL tooling | Practical stationary-control task with a grid of actuators; potential quiet/disturbance contrast | New NCA policy and declared local sensor/event adapter; default observations are not a distributed interface |
| C. Event-camera mobile-robot following | SEBVS event emulation and published simulated control | Strongest direct event-input demonstration; queue/burst/latency work | ROS/Gazebo integration, policy reconstruction/access, new NCA policy; actuator locality is weaker |

“Strongest” and “practical” are relative judgments under the confirmed scope. None establishes a successful event-driven FPGA NCA in this repository, nor guarantees a speedup over CPU/GPU/TPU.

## A. Published modular soft-robot locomotion

### What is already established

Nadizar et al. study simulated robots composed of deformable voxels. Each local controller uses its own sensors and neighbor messages to produce local actuation. The paper compares conventional neural controllers with a spiking NCA formulation, using fixed optimized synaptic parameters. This is direct embodied-control prior art rather than an NCA used only to grow a robot's shape. [Paper](https://arxiv.org/html/2204.02099v1), [project](https://giorgia-nadizar.github.io/VSRCollectiveControlViaSNCA/).

### What our project would add

Choose one fixed morphology and flat-terrain locomotion first. Retain a conventional shared-weight NCA variant as the closest continuation of the MAC-based baseline, unless the user explicitly accepts a spiking-rule fork. Build exact software/export/fixed-point/RTL models, local state/message storage, event admission and measured work skipping; then test limited terrain/disturbance and sensor/link-loss variants.

Spiking is not synonymous with freely sleeping hardware: the published model uses discrete-time neuron updates, leak and threshold dynamics. Any event-only realization needs equivalent or separately validated maintenance semantics. Its conventional ANN and spiking models are not drop-in copies of the original CartPole operator. [Paper](https://arxiv.org/html/2204.02099v1).

### Reproducibility and semester risks

The authors' repository supplies Java simulator and evolutionary-optimization components. Its Starter demonstration uses non-optimized robots moving downhill, so simply running that demo would not establish learned control. Controller reproduction/export, dependency compatibility and usable learned-model artifacts need an early audit. A complete code/dependency license grant was not established from the reviewed root listing; inspect provenance before copying or redistributing source/artifacts. [Code](https://github.com/giorgia-nadizar/VSRCollectiveControlViaSNCA).

This option gives the strongest documented embodied-NCA foundation but introduces an additional simulation stack and controller-graph change. It supports later Clef locality, resource and damage studies; it does not itself instantiate autopoiesis.

## B. EvoGym Balancer-v0

### What is already established

The documented task starts a voxel robot on a narrow pole and asks it to remain balanced. Balancer-v1 additionally requires jumping onto the pole; that is excluded from the proposed minimum scope. [Task documentation](https://evolutiongym.github.io/all-tasks/misc.html).

EvoGym provides the simulator, Gym-style interface and optimization examples; its main repository uses an MIT license. The documented packaged Python support is 3.7–3.10, so compatibility with this repository's Python 3.12 numerical reference must be checked rather than assumed. A separate host-simulation environment is an option, not an already implemented integration. [Repository](https://github.com/EvolutionGym/evogym), [license](https://github.com/EvolutionGym/evogym/blob/main/LICENSE).

### What our project would add

Use one small fixed body initially; do not co-optimize morphology. Expose declared local deformation/contact/motion observations where the simulator supports them, and map local actuator commands to its existing action vector. The reviewed balancing code returns orientation and whole-body relative positions by default: that is not automatically the local sensor contract Clef's engineering baseline seeks. New sensing must be documented, physically motivated and shared by comparison controllers. [Environment source](https://github.com/EvolutionGym/evogym/blob/main/evogym/envs/balance.py).

Train an ordinary fixed-weight NCA for balance, then introduce sensor-change/neighbor-change events and maintenance timers as an explicit policy variant. Compare quiet balance, localized perturbations and dense disturbances. Stationary operation offers a plausible sparse-load regime, but its actual event fraction and necessary maintenance rate must be measured. The simulator's ordinary periodic interface does not natively provide our event-driven controller.

### Reproducibility and semester risks

The documented plant and permissively licensed code reduce environment-development uncertainty. They do not prove NCA learnability or event-gating stability. A software competence/load gate must precede hardware freeze. Floating-point physics replay requires pinned versions and declared tolerances; bit-exact FPGA/controller replay uses saved sensor/event traces, not an unsupported cross-platform physics bit-identity claim.

This option preserves the ordinary neural-MAC direction and provides distributed actuation and scaling/damage experiments. It is not the proposal's custom actuated balancing surface, and it does not require designing a new physical plant from scratch.

## C. Event-camera robot following using SEBVS

### What is already established

SEBVS describes synthetic event generation in a ROS/Gazebo setting and simulated mobile-robot object following. Its published controller is transformer-based and trained by behavior cloning, not an NCA. Its reported policy uses accumulated event/RGB representations; that is not evidence of our proposed raw-event work scheduler. [Project and architecture](https://eventbasedvision.github.io/SEBVS/).

### What our project would add

Use one simple scene and robot, feeding bounded-resolution event locations/timestamps/polarities into persistent NCA state and reading steering/speed commands. Compare event-rate bursts, quiet inputs, moving targets, occlusion and control delays. An event packet interface is a good vehicle for queues, backpressure, scheduling, CDC and sensor-to-actuator latency tests. Timer/maintenance service remains necessary where the recurrent controller requires it.

### Reproducibility and semester risks

The reviewed repository's public tree principally supplies the event emulator. Its documented setup uses Ubuntu 22.04, ROS 2 Humble and Python 3.10; dataset access is linked through a request form. The README declares CC BY-SA 4.0. Complete runnable policy/task/checkpoint access and dependency rights must be audited; do not assume the emulator alone reproduces the paper's controller. [Repository](https://github.com/eventbasedvision/SEBVS).

Camera pixels give spatial sensing, but steering/speed remain a small centralized actuator output. This is less direct evidence for a body-wide local sensor/actuator mesh than the voxel options. Rendering, perception and middleware can dominate a one-semester project. No simulator/emulator costs should disappear from end-to-end comparison accounting.

## Recommendation — not selection

For the ordinary fixed-weight NCA/MAC accelerator trajectory in one semester, recommend **B: EvoGym Balancer-v0**, subject to early installation, sensing and software-control checks. It supplies a documented plant without committing the baseline to a new spiking datapath or a perception/middleware-heavy stack. This is a risk judgment, not a claim that training will succeed.

Choose A instead if the priority is reproducing the most directly documented embodied cellular controller and accepting the Java/provenance/controller-graph work. Choose C if demonstrating raw event-sensor processing is more important than distributed body actuation and the added stack is acceptable.

The custom balancing-surface idea remains a future candidate. Inventing its dynamics, validating its physics and establishing a working NCA at the same time adds research uncertainty; it is not silently selected as the baseline. Tactile manipulation was also screened ([Tactile Gym](https://github.com/yijionglin/tactile_gym_2)), but is outside this bounded three-option decision packet because it adds contact/perception integration without an established NCA policy in the reviewed sources.

## Proposed minimum and acceptance dimensions

Common minimum: one plant/task, one fixed body/scene, fixed deployment weights, persistent state, replayable spatial observations/actions, genuine event work avoidance with maintenance, portable synthesizable core, actual FPGA closed loop, and a bounded comparison report. No physical apparatus, morphology search, multi-task curriculum, online learning or CEC proof is required this semester.

Propose evaluating control against a competent conventional controller with the same sensing/actuation/delay boundary, and comparing the identical frozen NCA on CPU versus FPGA. Also retain dense and event NCA variants. Define per-task quality/stability thresholds after selection rather than imposing an arbitrary common success percentage on unlike tasks. Evaluate success/control duration or locomotion/tracking quality, jitter/deadline misses, event fraction, work skipped, traffic, queue high-water/overflow, resource fit and measured versus estimated power.

A plant simulator stays on the host; the FPGA produces the learned actions. The simulator, safety boundary or conventional baseline must not secretly supply the desired control policy to the NCA. Damage recovery or successful control is not CEC evidence.

## One-semester dependency plan

1. Select one option and perform a bounded provenance/install/replay/competence check. If it fails, return to a decision gate before hardware freeze.
2. Freeze plant/local-I/O/event semantics and policy; quantize against long-trajectory control tests.
3. Verify portable arithmetic and folded engine, then integrate the event scheduler/local state and counters.
4. Complete exact co-simulation, FPGA transport and simulated closed loop; exercise overload and quiet-maintenance behavior.
5. Measure a limited architecture comparison and produce the reviewed baseline release/report.

Allocate time from the actual remaining semester, reserving bring-up/regression/report contingency. No fabricated weekly dates or training duration estimates are supplied. ASIC fabrication and full Clef follow separately; if ASIC synthesis fits, record it as an achieved stretch result.

## Gate and next action

Proposed ADR-0008 remains unaccepted. User must select A, B or C (or request a different comparison). After selection, update the active benchmark contract and task-specific stage inputs, then implement E01/E02 as requested. No candidate source was cloned or installed, no policy trained, and no environment/RTL code changed during this comparison.
