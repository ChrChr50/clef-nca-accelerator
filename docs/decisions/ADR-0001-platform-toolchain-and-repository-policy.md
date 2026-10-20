# ADR-0001: Primary platform, toolchain, and repository policy

- Status: **Accepted**
- Date: 2026-09-17
- Deciders: User
- Stage: P01
- Human gate: G1
- Supersedes: None
- Superseded by: None
- Related requirements: PROC-002, PROC-005, BASE-006, BASE-008, ACC-005, P01-001 through P01-006

## Context

The project needs an initial FPGA development platform for the conventional fixed-weight NCA baseline while the executable NCA and numerical contract are not yet frozen. It also needs a defined point at which measured evidence can select a larger final baseline board. The decision must preserve portable SystemVerilog, compatibility with the selected FPGA toolchain and an open ASIC flow, and a later independent choice of physical substrate for the spatial Clef tile/patch architecture. This ADR also controls P02 repository visibility and initial licensing posture.

The full sourced comparison and point-in-time availability evidence are in `docs/architecture/P01_G1_PLATFORM_TOOLCHAIN_PACKET.md`.

## Decision drivers

- Enough logic, DSP, and on-chip memory before exact utilization is known.
- Host connectivity that keeps the Hanoi environment outside accelerator RTL.
- Deterministic debug and trace support.
- Current cost and availability.
- Portable SystemVerilog and an open verification lane.
- A credible later spatial Clef path without requiring partial reconfiguration.
- ASIC portability through vendor/memory wrapper isolation.
- Reproducible-release and third-party provenance obligations.

## Options considered

### Option A — AMD KV260 with Vivado BASIC/CORE

Kria K26/Zynq UltraScale+ MPSoC with 256K system logic cells, 1,248 DSP slices, 144 BRAM blocks, 64 UltraRAM blocks, 4 GB DDR4, Arm/Linux, 1 GbE, USB, and integrated JTAG/UART. Board MSRP is $249 and the official supply is $25. Vivado 2026.1 BASIC is no-cost with an annual license; AMD says new Kria kits receive a CORE voucher.

This option has the best compute/memory and host-integration margin at the lowest schedule risk. Its main costs are a large proprietary tool installation and renewable vendor licensing.

### Option B — Digilent Nexys Video with Vivado BASIC

Artix-7 XC7A200T with 33,650 slices, 740 DSP slices, 13 Mbit BRAM, 512 MB DDR3, Ethernet, USB data/UART, and onboard JTAG. Direct price is $577.

This option creates a clean pure-FPGA boundary and strong debug environment, but costs more than KV260, has less raw capacity, and lacks a hard host CPU.

### Option C — Terasic DE10-Nano with Quartus Prime Lite

Cyclone V SoC with 110K logic elements, 112 variable-precision DSP blocks, 5.57 Mbit M10K memory, 1 GB HPS DDR3, Arm/Linux, Ethernet, USB, UART, and onboard USB-Blaster. Direct price is $225 or $190 academic. Quartus Prime Lite is no-cost without a license file and includes Signal Tap.

This option is inexpensive and provides a useful non-AMD portability path, but it has the least DSP/on-chip-memory safety margin among the shortlisted integrated-host boards and uses an older FPGA family.

## Recommendation

The original packet recommended **Option A, AMD KV260**, with:

- a `$400` pre-tax/shipping hardware ceiling;
- no-cost proprietary FPGA tools allowed;
- open Verilator/cocotb/SymbiYosys verification retained as the common lane;
- a private repository through baseline signoff, followed by a deliberate public release review; and
- Apache-2.0 for original code, RTL, scripts, and documentation, subject to institutional review and third-party license isolation.

Runtime topology should use ordinary local state to gate causal paths. FPGA partial reconfiguration is optional and is not part of this platform decision.

## Decision

On 2026-09-17 the user accepted G1 as follows:

- Use the school-provided **Terasic DE1-SoC**, Cyclone V SE `5CSEMA5F31C6N`, as the provisional baseline development and synthesis platform.
- Use Quartus as its authoritative vendor implementation backend while keeping the shared open verification lane and portable SystemVerilog core.
- Set initial FPGA hardware spending to **$0** by using the school board; do not purchase an upgrade without a later evidence-backed decision.
- Allow no-cost proprietary Quartus for synthesis, place and route, timing, programming, and signoff. Paid proprietary tools are not authorized by this decision.
- Use synthesizable **SystemVerilog** for the technology-independent accelerator core.
- Keep the core compatible with both Quartus/Cyclone V and an open Yosys/OpenROAD ASIC exploration flow. Vendor memories, PLLs, HPS/Avalon integration, Signal Tap, PDK cells, and ASIC SRAMs must remain behind wrappers.
- Treat Yosys/OpenROAD compatibility as a portability and early PPA lane, not foundry signoff. The actual ASIC PDK, libraries, SRAM strategy, and signoff endpoint remain deferred to G7.
- Collect model, numerical, synthesis, timing, memory, throughput, debug, and lab-access evidence through P12.
- Confirm DE1-SoC or prepare a superseding board ADR before P13 begins platform-specific integration.
- Defer the physical platform for full Clef to G8/P18; do not assume the baseline board or a multi-board cluster is automatically suitable.
- Create the GitHub repository as **private initially** in P02, subject to the user's separate authorization to perform the external creation step.
- Keep original project material **all rights reserved during private development** because no open-source license was selected. Do not add an open-source license or publish the repository until an institutional, third-party provenance, patent, and claim review approves a release policy.

The detailed monitoring and non-destructive bring-up procedure is in `docs/architecture/DE1_SOC_PROVISIONAL_PLATFORM_AND_BRINGUP.md`.

G1 is complete. This decision authorizes P02 to implement the selected local scaffold and, when the user explicitly requests P02 and the authenticated tooling is available, create a private GitHub repository. It does not itself create a repository, install tools, purchase hardware, or begin P02.

## Consequences

### Positive

- Eliminates initial board cost and uses a platform with local laboratory support.
- Provides a board-local Linux host while preserving a host-neutral accelerator boundary.
- Replaces speculative worst-case provisioning with measured capacity checkpoints.
- Keeps ASIC choice open through portable SystemVerilog, Yosys/OpenROAD checks, and technology wrappers.
- Private-first development reduces accidental publication of third-party assets, unreviewed claims, or institutionally controlled material.

### Negative

- Provides substantially less DSP and embedded-memory headroom than KV260.
- Uses an older Cyclone V family and Quartus/Platform Designer ecosystem.
- Old Terasic and Cornell examples target several different Quartus and Linux generations and may require controlled migration.
- Lab access, permissions, and board availability may constrain schedule and reproducibility.
- A later board change remains possible and becomes expensive if delayed until after P13 wrappers and software.
- Private development delays public collaboration, and all-rights-reserved code cannot be openly reused until a later license decision.
- Passing an open ASIC flow does not establish foundry signoff or guarantee equivalence with a future commercial flow.

### Follow-up obligations

- In P02, record the exact board revision, lab image, supported Quartus/driver versions, and access rules; pin dependencies without committing credentials or license files.
- In P03-P10, measure actual model demand, utilization, timing, memory, and throughput instead of resizing the accepted model to fit silently.
- At G5 and again before P13, apply the monitoring and upgrade policy in the DE1-SoC guide.
- Correlate open simulation against the selected vendor simulator/backend.
- Keep Avalon, HPS bridges, processing-system, debug IP, PLLs, and FPGA memories behind wrappers.
- In P02, use `.sv` for RTL and configure the scaffold so portable-core sources can be consumed by Quartus and Yosys without separate behavioral implementations.
- Do not add a permissive or hardware license in P02; retain all rights until a later accepted release/licensing ADR.
- Revisit repository publication and licensing before external release, with institutional and third-party provenance review.

## Evidence

| Evidence | Source or artifact | Date/version | Result |
|---|---|---|---|
| Full G1 comparison | `docs/architecture/P01_G1_PLATFORM_TOOLCHAIN_PACKET.md` | 2026-09-17 | Three viable stacks compared; Stack A recommended |
| Host tool inventory | P01 command record in implementation status | 2026-09-17 | Only Git found on PATH; HDL/vendor tools not found |
| AMD board and licensing | AMD product/licensing pages linked in G1 packet | Retrieved 2026-09-17 | KV260 $249 MSRP; BASIC $0 annual; Kria supported |
| Alternative boards | Digilent, Terasic, Altera sources linked in G1 packet | Retrieved 2026-09-17 | Resource, debug, price, and tool evidence recorded |
| Open ASIC flow | OpenROAD and SKY130 sources linked in G1 packet | Retrieved 2026-09-17 | Suitable for exploration; not foundry signoff |
| DE1-SoC platform amendment | Terasic manual/specifications, current Altera device/tool support, Cornell lab workflow, and `docs/architecture/DE1_SOC_PROVISIONAL_PLATFORM_AND_BRINGUP.md` | Retrieved 2026-09-17 | Provisional board accepted with explicit upgrade checkpoints |
| User-supplied rev. E manual | `C:\Users\skywa\Downloads\DE1-SoC_User_manualv.1.2.2_revE.pdf`; SHA-256 `BC78872EDAF95A96E5876172A20EA14EEB01BC736CB01857FBE496FE6EDF348E` | v1.2.2, 2015-04-02; inspected 2026-09-17 | Confirmed rev. E connectors, SW10/MSEL modes, volatile JTAG, configuration-flash path, and HPS/FPGA bridge example |

## Validation and rollback

Before platform-specific P13 work, synthesize representative compute and memory structures and compare utilization, timing, memory bandwidth, debug reserve, and decision latency against the frozen P07 numerical contract and accepted G5 architecture. If DE1-SoC cannot meet them with reasonable margin, prepare a superseding ADR; do not silently reduce the model or change numerical behavior.

The decision is inexpensive to reverse through P08 because the core remains portable. Reversal becomes costly after the board wrapper, driver, constraints, debug plan, and physical bring-up package are built.

## Claim discipline

This decision selects engineering substrate and tools only. FPGA capacity, effective topology changes, recurrence, adaptation, or partial-reconfiguration capability do not establish CEC, autopoiesis, or Medium Rosen.
