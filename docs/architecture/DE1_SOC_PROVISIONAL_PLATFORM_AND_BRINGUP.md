# DE1-SoC Provisional Platform and Bring-Up Guide

- Decision date: 2026-09-17
- Decision scope: accepted G1 platform, toolchain, portability, repository, and initial licensing policy
- Initial role: provisional baseline development and synthesis platform
- Final baseline board lock: before P13 platform integration
- Full Clef physical-platform decision: G8/P18

## Decision

Use the school-provided Terasic DE1-SoC as the provisional development platform for the conventional fixed-weight NCA baseline. Do not purchase a larger FPGA or design a multi-board system until measured model, synthesis, timing, memory-bandwidth, or experimental evidence justifies doing so.

This is a real working-platform commitment, not a promise that DE1-SoC is the final board. P02 may pin a Cyclone V/Quartus-capable workflow, and P09-P10 may synthesize against the DE1-SoC device. The technology-independent core must remain portable. The final board must be confirmed or changed before P13 adds board-specific wrappers, constraints, HPS integration, debug IP, and software.

The initial hardware budget is $0: use the lab board and do not purchase an upgrade without a later evidence-backed decision. No-cost proprietary Quartus is accepted because it is the authoritative supported backend for the chosen Cyclone V device. Paid proprietary tools are not authorized. The repository will be private initially. Original project material remains all rights reserved during private development until a later institutional/provenance/claim review authorizes publication and a license.

## Why this decision supersedes buying for the worst case

The exact NCA operator graph, grid, channel count, numerical widths, epoch count, MAC parallelism, and state-memory organization do not yet exist as frozen executable contracts. A large board selected against hypothetical maxima would purchase unused risk insurance before the dominant resource demands are known.

The DE1-SoC is available in the school lab, has no initial hardware cost, has local instructional support, and contains both programmable logic and a Linux-capable hard processor. It therefore supports the required baseline split: the HPS or another host runs the accepted plant simulation or interfaces to spatial sensors/actuators, while the FPGA evaluates persistent recurrent NCA control and schedules sparse/event work.

The cost-saving decision is safe only if the project preserves portability and treats later capacity decisions as measured engineering gates rather than silently shrinking the scientific contract to fit the board.

## Hardware baseline

The board uses the Cyclone V SE `5CSEMA5F31C6N`. Relevant resources are:

| Resource | Available |
|---|---:|
| Programmable logic | 85K logic elements / 32,070 ALMs |
| Registers | 128,300 |
| M10K block memory | 397 blocks / 3,970 Kbit |
| MLAB memory | 480 Kbit |
| Total advertised embedded memory | 4,450 Kbit |
| Variable-precision DSP blocks | 87 |
| Independent 18x18 multipliers | 174 |
| HPS | Dual-core 800 MHz Arm Cortex-A9 |
| HPS memory | 1 GB DDR3 |
| FPGA-attached memory | 64 MB SDRAM, 16-bit interface |
| Host and debug I/O | 1 GbE, USB host, USB-UART, onboard USB-Blaster II |
| Removable storage | HPS microSD socket |

Sources: [Terasic DE1-SoC specifications](https://www.terasic.com.tw/cgi-bin/page/archive.pl?Language=English&No=836&PartNo=2), [Cyclone V FPGA and SoC FPGA product table](https://docs.altera.com/api/khub/documents/s60vJiu_kjIh2yag_Ea_yg/content), and the user-supplied `DE1-SoC_User_manualv.1.2.2_revE.pdf` described below.

The board is materially smaller than KV260. That principally affects how many MAC lanes and spatial tiles can be active simultaneously; it does not by itself prevent a folded, low-bit NCA baseline.

## Governing board manual and revision control

The supplied manual is **DE1-SoC User Manual v1.2.2 for board revision E**, dated April 2, 2015:

- Local source: `C:\Users\skywa\Downloads\DE1-SoC_User_manualv.1.2.2_revE.pdf`
- Size: 11,024,450 bytes
- Pages: 115
- SHA-256: `BC78872EDAF95A96E5876172A20EA14EEB01BC736CB01857FBE496FE6EDF348E`
- Repository treatment: referenced but not copied into the repository

Use this as the controlling hardware manual only if the checked-out lab board is revision E. The board-revision marking and the manual must match before using revision-sensitive pin assignments, CD demonstrations, or nonvolatile programming procedures. If the lab provides another revision, obtain its matching manual from the [Terasic DE1-SoC resources page](https://www.terasic.com.tw/cgi-bin/page/archive.pl?CategoryNo=165&Language=English&No=836&PartNo=4) and record a new checksum.

The rev. E manual confirms:

- USB-Blaster II programming uses Type-A to Type-B USB at connector J13.
- HPS serial UART uses Type-A to Mini-B USB at connector J4.
- SW10 is on the bottom of the board and selects `MSEL[4:0]`.
- Default Active Serial boot is `10010`; Linux FPGA-manager programming is documented as `01010`; the supplied U-Boot/LXDE/framebuffer SD-image path uses `00000`.
- JTAG `.sof` programming is volatile; Active Serial `.jic` programming changes nonvolatile configuration storage.
- The HPS-to-FPGA example uses an `.rbf` FPGA image and the lightweight HPS-to-FPGA bridge.

The manual sometimes refers to the configuration device as EPCS128 and once uses EPCQ wording in the factory-demo section. This guide therefore uses the neutral term **configuration flash** unless quoting a specific manual procedure. Initial checkout must not write or erase it.

## Software support and version policy

Cyclone V remains supported by Quartus Prime Lite 25.1, including compilation, simulation, timing analysis, programming, and Cyclone V device files. Lite is free and does not require a license file. Signal Tap and in-system probes provide the vendor debug lane.

Sources: [Quartus Prime Lite 25.1 download and Cyclone V support](https://www.altera.com/downloads/fpga-development-tools/quartus-prime-lite-edition-design-software-version-25-1-windows), [25.1std device-support status](https://docs.altera.com/r/docs/683593/25.1std/quartus-prime-standard-and-lite-editions-version-25.1std-software-and-device-support-release-notes/device-support-and-pin-out-status), and [Quartus licensing](https://docs.altera.com/r/docs/683472/26.1/altera-fpga-software-installation-and-licensing/licensing-altera-fpga-software).

Do not assume that every old Terasic or Cornell demonstration migrates unchanged to the newest Quartus release. The attached rev. E manual's examples specify Quartus II/Nios II/SoC EDS 13.1; Terasic's rev. F/G CD targets Quartus 16.0; its rev. H CD targets 20.1.1; and Cornell's published HPS instructions use a 2016 Linux image. These old versions describe the example environment, not an instruction to install obsolete software blindly. P02 must record the exact board revision, lab image, Quartus version, USB-Blaster driver, Platform Designer/Qsys version, compiler, and checksums actually used. Prefer the lab's known-good HPS image for initial bring-up, then test migration to a supported Quartus release deliberately rather than mixing generations accidentally.

Cornell's established model is Linux on the Arm HPS talking to custom FPGA hardware through Qsys/Platform Designer and memory-mapped bridges. That model matches the planned NCA host/accelerator boundary. Source: [Cornell ECE5760 DE1-SoC HPS Linux notes](https://people.ece.cornell.edu/land/courses/ece5760/DE1_SOC/HPS_peripherials/linux_index.html).

## What is committed and what is deferred

### Committed now

- DE1-SoC/Cyclone V is the first synthesis and laboratory target.
- Quartus is the authoritative FPGA implementation backend for this target.
- The HPS/Linux path is the preferred local host path, subject to lab access and image verification.
- The reusable core stays portable SystemVerilog.
- The same core sources must remain consumable by Quartus and the open Yosys/OpenROAD ASIC exploration lane.
- Avalon, HPS bridges, clocks, resets, memories, pins, and Signal Tap remain outside the core in wrappers.
- The baseline will first explore folding and parameterized MAC-lane counts rather than assume full spatial replication.

### Deferred

- Whether DE1-SoC is the final P13-P14 baseline demonstration board.
- Whether a larger single FPGA is necessary.
- Whether more than one DE1-SoC is useful.
- The physical tile/patch count and final platform for full Clef; G8/P18 decides this from an accepted experiment specification.
- Any purchase or multi-board interconnect design.

## Capacity evidence to collect at every stage

| Stage | Record | Decision relevance |
|---|---|---|
| P02 | Board revision, lab availability, Quartus/driver/image versions, access rules, reproducible tool invocation | Confirms that the nominal platform is actually usable and reproducible |
| P03 | Exact operator graph, tensor shapes, grid dimensions, channels, epoch count | Establishes the computation that hardware must implement |
| E00-E02/P06 | Accepted plant/I/O, event load and bursts, deadlines, model identity, persistence/reset, rule dimensions | Prevents choosing hardware for a model that was not accepted |
| P07 | State/weight/accumulator widths, saturation rates, action agreement, fixed-point memory footprint | Converts model size into real DSP and memory demand |
| P08 | Primitive inference reports for multipliers, accumulators, saturation, and inferred memories | Confirms Quartus maps portable RTL as intended |
| P09 | ALM/register/DSP use, Fmax, worst slack, cycles per local rule, results across `MAC_LANES` | Primary compute-capacity checkpoint |
| P10/G5 | Local state/halo footprint, memory ports, event queues/high-water load, patch links, worst-case service/overload and clock domains | Primary board-retention or upgrade checkpoint |
| P11-P12 | Complete decision latency, trace-buffer demand, deterministic replay, exact co-simulation | Shows whether the verified core meets the baseline contract before wrappers |
| Before P13 | Post-fit headroom, timing margin, expected debug overhead, HPS/FPGA bandwidth, lab access continuity | Final baseline board lock or superseding ADR |
| P13-P14/G6 | Actual hardware timing, throughput, host-transfer latency, reliability, and repeatability | Physical signoff evidence |
| P15 | Pareto sweep of lanes, precision, buffering, frequency, latency, and energy estimates | Determines whether optimization is preferable to migration |
| P18/G8 | Required simultaneous tiles/patches, locality, event/synchrony protocol, intervention bandwidth | Selects the physical platform for full Clef rather than inheriting the baseline board by default |

Every synthesis checkpoint must retain the exact device, Quartus version, project seed, clock constraints, parameter manifest, and concise reports. Do not compare percentages from unlike FPGA families without also comparing actual operations, memory organization, timing, and throughput.

## Upgrade decision policy

Use these as engineering review bands, not as substitutes for measured signoff:

### Continue on DE1-SoC

- The accepted design meets timing with useful margin.
- No critical resource is above roughly 65% after place and route.
- State and weight memories map predictably without excessive HPS or SDRAM traffic.
- Expected Signal Tap/debug logic and future interface wrappers still have room.
- Decision latency satisfies the accepted baseline experiment.

### Optimize and re-measure

- Any critical resource is approximately 65-80%.
- Timing passes but has little margin or is highly seed-sensitive.
- Folding, memory packing, or neighborhood/compute overlap can plausibly recover margin without changing numerical behavior.
- Debug instrumentation fits only selectively.

Optimization may change lane count, pipeline depth, memory packing, or scheduling. It must not silently change the accepted operator graph, fixed-point semantics, or scientific test contract.

### Prepare a board-upgrade ADR

- Any critical resource remains above roughly 80% after reasonable optimization.
- Place and route fails or timing cannot meet the accepted G5 target.
- Ping-pong state, weights, or necessary trace buffers cannot fit with safe memory-port behavior.
- External-memory traffic makes deterministic decision latency unacceptable.
- Required verification/debug logic cannot coexist with the accelerator.
- The board is unavailable often enough to threaten reproducibility or schedule.
- The accepted full-Clef G8 experiment requires more simultaneously physical local engines, link state, or intervention bandwidth than the DE1-SoC can support.

At an upgrade gate, compare at least: a larger single FPGA, a reduced-parallelism implementation that preserves behavior, and a multi-board design. Choose from measured bottlenecks, not vendor headline metrics.

## Multi-board DE1-SoC policy

Multiple boards are not a transparent replacement for one larger FPGA. They are attractive for independent experiment replication or parameter sweeps. Partitioning one NCA or Clef mesh across boards additionally requires:

- an explicit partition and halo/boundary-state protocol;
- deterministic ordering and synchronization;
- bounded link latency and buffering;
- replayable failure and packet-loss behavior;
- measurement of communication versus computation time; and
- treatment of the physical inter-board boundary in Clef locality and intervention claims.

Gigabit Ethernet is suitable for early orchestration and independent workers but may be too latent for fine-grained synchronous neighbor exchange. GPIO-based links can reduce protocol overhead but add signal-integrity, clock-domain, pin-budget, and custom-board risks. Do not begin a cluster design until a single-board report identifies the specific resource or throughput bottleneck.

## Acquisition and first-use checklist

The following sequence is deliberately non-destructive. Use volatile JTAG programming before writing configuration flash.

### Before collecting the board

1. Ask the lab manager for the exact board revision, asset/serial identifier, checkout duration, allowed storage location, and whether overnight or unattended runs are permitted.
2. Ask which Quartus version, USB-Blaster driver, DE1-SoC CD/BSP, microSD image, serial-terminal settings, and HPS compiler environment the lab supports.
3. Ask whether the board must be returned with its factory configuration-flash image, original microSD contents, network configuration, and switch settings restored.
4. Ask whether administrator rights are available for drivers and whether the lab provides a workstation. Do not assume a personal Windows installation can access the board.
5. Obtain the lab's networking rules. Cornell's published notes require assigned wired-network parameters in its lab and warn against improvising DHCP/MAC settings.

### Inventory at checkout

6. With power disconnected, place the board on an ESD-safe, nonconductive surface and inspect both sides for bent pins, damaged connectors, loose heatsinks, contamination, or conductive debris.
7. Photograph the top, bottom, board-revision marking, asset label, and all switch positions before changing anything.
8. Confirm the loan includes or identify replacements for:
   - DE1-SoC board;
   - regulated 12 V DC adapter approved by the lab;
   - USB Type-A to Type-B data cable for USB-Blaster II connector J13;
   - USB Type-A to Mini-B data cable for HPS UART connector J4;
   - a known-good microSD card/image if HPS Linux will be used; and
   - Ethernet cable if permitted by the lab.
9. Record the markings on the power adapter and do not substitute a supply based only on connector fit. The manual specifies a 12 V DC input.
10. Record the FPGA part as `5CSEMA5F31C6N` and the board revision. If the board is rev. E, verify the attached manual against the checksum above and use rev. E CD/reference files. The Terasic resource page separates rev. B, C/D, E, F/G, and H materials.

### Factory power-on acceptance

11. Keep power off while inspecting SW10/MSEL on the bottom of the board. Record its original position. In the rev. E manual, `SW10.1..5` defaults to ON, OFF, ON, ON, OFF, where ON is `0`; this produces Active Serial `MSEL[4:0] = 10010`. Do not change it merely to begin testing.
12. Connect J13 to the host with the Type-B USB cable. Connect the approved 12 V supply, then turn on the board.
13. Observe the factory configuration. The attached rev. E manual expects changing seven-segment characters and blinking red LEDs. Record a short video or log the observed behavior. Failure here should be reported to the lab before custom programming.
14. If authorized, run the lab's known-good factory or board-test package. Test at minimum the 50 MHz clock, LEDs/buttons, USB-Blaster detection, and FPGA SDRAM. The manual's RTL SDRAM demonstration takes about eight seconds and reports pass/fail on LEDs.

### Host-tool and JTAG acceptance

15. Install or select the approved Quartus release and Cyclone V device support. Install the USB-Blaster II driver if the workstation does not already have it.
16. With the board powered and J13 connected, use Quartus Programmer Auto Detect or the command-line JTAG inventory. Record the detected chain and save a screenshot/text log. The manual expects both the FPGA and HPS devices in the JTAG chain.
17. Compile or use a known-good minimal LED design for the exact device and board revision. Program its `.sof` through JTAG only. Verify the expected LED behavior.
18. Power-cycle the board and verify that the volatile JTAG image disappears and the factory configuration-flash image returns. Do not create or program a `.jic`, erase configuration flash, or alter the factory nonvolatile image during initial acceptance.

### HPS/Linux acceptance

19. Back up or checksum the supplied microSD image before modifying it. Keep a restorable original.
20. With power off, set SW10/MSEL exactly as required by the supplied image. The attached rev. E manual documents `00000` for its U-Boot/LXDE/framebuffer SD images and `01010` for Linux FPGA-manager configuration. Its later combined HPS/FPGA example also mentions `01110`, so use only the value required by the exact lab image and procedure. Never move SW10 while powered.
21. Insert the microSD card and connect J4 to the host with the Mini-B data cable. Configure the serial terminal using the lab image's documented settings; do not guess from an unrelated BSP.
22. Connect Ethernet only after applying the lab's assigned MAC/IP policy. Keep the serial console available even when using SSH.
23. Power on, capture the complete boot log, log in using credentials supplied by the lab, and immediately replace or disable documented default credentials if the lab permits.
24. Record `uname`, distribution/build identity, compiler version, storage layout, network configuration, and available FPGA-manager interfaces. Shut Linux down cleanly before removing power.

### HPS-to-FPGA path acceptance

25. Run a known-good HPS-only hello/LED test to verify Linux, UART, and native HPS GPIO.
26. Run the lab's known-good HPS-to-FPGA bridge example. The rev. E manual's example loads `soc_system_dc.rbf` with `hps_config_fpga` and accesses FPGA peripherals through the lightweight HPS-to-FPGA bridge. Cornell's model uses Linux memory mapping to reach FPGA registers; invalid or absent bridge addresses can hang the bus and crash Linux, so first use only the address map generated with the exact FPGA image.
27. Verify a minimal control/status register exchange through the lightweight HPS-to-FPGA bridge, then verify a small block transfer or memory test through the intended data path.
28. Record the FPGA image checksum, Platform Designer address map, HPS executable checksum, observed register values, transfer result, and reboot/recovery procedure.

### Project handoff after acceptance

29. Create a board inventory record containing photographs, revision, asset ID, cable/supply inventory, switch settings, tool and driver versions, SD-image checksum, factory-test result, JTAG result, Linux boot result, and HPS-FPGA bridge result.
30. Restore any lab-required default network, switch, microSD, and configuration-flash state after each session.
31. Store generated bitstreams, reports, and logs under the later P13-P14 artifact policy; never commit proprietary vendor files, credentials, or an unlicensed lab image.
32. Until P13, use the board only for platform familiarization and accepted smoke tests. Do not call the NCA hardware brought up before bit-exact P12 regressions and staged P13-P14 self-tests exist.

## Safety and common failure controls

- Change SW10/MSEL only while power is off, and photograph the original setting.
- Do not place the exposed board on metal or an antistatic bag's conductive exterior.
- Use data-capable USB cables; charge-only cables can masquerade as driver failures.
- Distinguish J13 USB-Blaster from J4 USB-UART.
- Do not write or erase configuration flash during initial checkout; JTAG `.sof` programming is volatile and recoverable.
- Do not use an old default-root Linux image on an unrestricted network.
- Shut Linux down cleanly before removing power to reduce microSD corruption.
- Keep an original SD-image backup and exact checksum.
- Treat a bridge-address mismatch as capable of hanging the HPS; pair every userspace binary with its exact FPGA address-map manifest.
- Preserve the factory/demo recovery files appropriate to the actual board revision.

## Decision record relationship

This guide supplies the operational detail for `ADR-0001`. If measured evidence later requires a different board, create a superseding ADR that cites the relevant synthesis, timing, memory, throughput, access, or G8 experimental evidence. Do not rewrite this historical decision or silently reduce the accepted model to avoid an upgrade.
