# P01 / G1 Platform and Toolchain Decision Packet

- Prepared: 2026-09-17
- Status: **G1 accepted — P01 complete**
- Stage: P01
- Gate: G1
- Decision record: `docs/decisions/ADR-0001-platform-toolchain-and-repository-policy.md`

## Exact decision

Choose:

1. one primary FPGA board/toolchain stack;
2. a working budget ceiling;
3. whether no-cost proprietary FPGA tools are acceptable;
4. repository visibility for P02; and
5. the repository license policy.

The original packet did not purchase hardware, create an external account or repository, install tools, accept a license, or select a platform. The decision amendment below records the user's subsequent selection without performing any of those external actions.

## Decision amendment — school-provided DE1-SoC

On 2026-09-17, after the original comparison, the user identified a school-provided DE1-SoC and accepted it as the provisional baseline development and synthesis platform. The initial hardware budget is $0, and no-cost proprietary Quartus is allowed as the authoritative Cyclone V backend. Paid tools and later hardware purchases are not authorized. This replaces the recommendation to purchase KV260 before measured need exists.

The DE1-SoC uses Cyclone V SE `5CSEMA5F31C6N` with 85K logic elements, 32,070 ALMs, 87 variable-precision DSP blocks/174 18x18 multipliers, 3,970 Kbit M10K plus 480 Kbit MLAB memory, dual-core Cortex-A9 HPS, 1 GB HPS DDR3, 64 MB FPGA SDRAM, Gigabit Ethernet, USB-UART, and onboard USB-Blaster II. Current Quartus Prime Lite 25.1 provides Cyclone V support without a paid license.

This is a provisional working-platform commitment, not a final capacity claim. P09-P10/G5 synthesis and memory evidence, followed by a pre-P13 review, will determine whether DE1-SoC remains the final baseline board. G8/P18 independently selects the full-Clef physical realization. See `docs/architecture/DE1_SOC_PROVISIONAL_PLATFORM_AND_BRINGUP.md` for the complete rationale, monitoring policy, upgrade triggers, clustering caveats, and acquisition/bring-up procedure.

## Evidence limits

The exact NCA operator graph, fixed-point format, model size, state-grid geometry, and Clef tile microarchitecture are intentionally not frozen until later gates. Therefore, this stage can compare raw capacity and workflow risk, but it cannot certify fit or quote utilization, frequency, latency, or power. Those require measured synthesis after P03–P10. Prices and stock are point-in-time evidence and must be rechecked immediately before purchase.

## Shortlist

| | Stack A — AMD KV260 | Stack B — Digilent Nexys Video | Stack C — Terasic DE10-Nano |
|---|---|---|---|
| Recommendation | **Recommended** | Pure-FPGA fallback | Lowest-cost SoC fallback |
| FPGA | Kria K26 / Zynq UltraScale+ MPSoC | Artix-7 XC7A200T | Cyclone V SoC 5CSEBA6U23I7 |
| Logic | 256K system logic cells | 33,650 slices; four 6-input LUTs and eight FFs per slice | 110K logic elements / 41,910 ALMs |
| DSP | 1,248 slices | 740 slices | 112 variable-precision blocks / 224 18×18 multipliers |
| On-chip block memory | 144 BRAM + 64 UltraRAM blocks | 13 Mbit BRAM | 5,570 Kbit M10K plus 621 Kbit MLAB |
| External memory | 4 GB DDR4 | 512 MB DDR3 | 1 GB DDR3 attached to HPS |
| Host path | Quad-core Arm, Linux, 1 GbE, four USB 3/2 ports | 1 GbE, USB-UART, high-speed USB transfer; optional MicroBlaze | Dual-core Arm HPS, Linux, 1 GbE, USB OTG/UART |
| Programming/debug | Integrated USB JTAG/UART; Vivado ILA/VIO | Onboard USB-JTAG and USB-UART; Vivado ILA/VIO | Onboard USB-Blaster II; Signal Tap and in-system probes |
| Vendor implementation | Vivado 2026.1 BASIC; Kria kit receives CORE voucher | Vivado 2026.1 BASIC | Quartus Prime Lite 25.1std |
| Vendor-tool license | BASIC: $0 annual node-locked license; account/license file required | Same | Lite: $0, no license file |
| Board price evidence | $249 MSRP; power supply sold separately at $25 | $577 direct | $225 direct; $190 academic |
| Availability evidence | AMD page reports 26-week direct lead time, while Mouser showed 233 immediately available; recheck before buying | Digilent offered direct sale; DigiKey showed 87 in stock | Terasic offers direct ordering; explicit live stock count was not exposed in the captured page |
| Principal risk | Largest vendor stack; 2026.1 annual-license workflow; carrier is vision-oriented | Highest board cost; no hard CPU; older 7-series fabric | Much less DSP/on-chip memory headroom; older Cyclone V flow |

Sources: [AMD KV260 product page](https://www.amd.com/en/products/system-on-modules/kria/k26/kv260-vision-starter-kit.html), [AMD K26 specifications](https://www.amd.com/en/products/system-on-modules/kria/k26/k26c-commercial.html), [AMD 2026.1 licensing](https://www.amd.com/en/products/software/adaptive-socs-and-fpgas/vivado/vivado-licensing-options.html), [Digilent Nexys Video](https://digilent.com/shop/nexys-video-amd-artix-7-fpga-trainer-board-for-multimedia-applications/), [Terasic DE10-Nano specifications](https://www.terasic.com.tw/cgi-bin/page/archive.pl?CategoryNo=165&Language=English&No=1046&PartNo=2), [Terasic ordering](https://www.terasic.com.tw/cgi-bin/page/archive.pl?CategoryNo=139&Language=English&No=1046&PartNo=8), and [Cyclone V resource table](https://docs.altera.com/api/khub/documents/s60vJiu_kjIh2yag_Ea_yg/content). Stock was checked against direct distributor pages on the preparation date and is not a purchase guarantee.

## Stack A — AMD KV260 with a portable verification front end

### Components

- **Board:** AMD Kria KV260 Vision AI Starter Kit.
- **Implementation:** Vivado 2026.1 BASIC for synthesis, placement, routing, timing, power estimation, bitstream, and ILA/VIO debug. AMD lists Kria SOMs and Zynq UltraScale+ ZU1–ZU7 in BASIC; the BASIC license is no-cost but annual and requires a generated license file. AMD also states that Kria kits receive a CORE voucher beginning with 2026.1.
- **Host/software:** embedded Linux on the Arm processing system for the Hanoi environment and driver, while the technology-independent NCA core remains entirely in programmable logic.
- **Common verification:** Verilator + cocotb + Python golden models; SymbiYosys where its supported assertion subset is sufficient; Vivado simulation and post-implementation checks as vendor correlation.
- **ASIC portability:** Yosys/OpenROAD smoke synthesis against an open platform early; commercial or shuttle-specific flow deferred to G7.

### Why it is recommended

- It has the largest compute and on-chip-memory headroom of the three candidates and therefore the lowest risk before the model and numerical format are frozen.
- A hard Arm/Linux host and 1 GbE make the baseline host/accelerator split straightforward without placing the Hanoi environment in RTL.
- The same programmable logic can first host a folded NCA engine and later a more spatial tile/patch Clef implementation.
- Integrated JTAG/UART plus Vivado ILA/VIO provide a strong bring-up path.
- At $249 MSRP plus a $25 supply, it is cheaper than the Nexys Video while providing a stronger host and more raw FPGA resources.

### Costs and risks

- Minimum board plus official supply is approximately **$274 before tax/shipping**; cables and microSD media may add modest cost.
- AMD's direct page displayed a 26-week lead time, but a current distributor showed stock. Purchase must use a fresh stock check.
- Vivado is proprietary. Starting in 2026.1 even the free BASIC tier requires a renewable annual license file. The portable core and open regression flow reduce, but do not eliminate, dependence on Vivado for bitstream generation and signoff.
- The K26 on the starter kit is an evaluation/non-production SOM. That is suitable for this project prototype but must not be mistaken for a production deployment module.

## Stack B — Nexys Video for a pure-FPGA development model

### Components

- **Board:** Digilent Nexys Video, Artix-7 XC7A200T.
- **Implementation:** Vivado 2026.1 BASIC, which supports 7-series devices at no cost under the annual license model.
- **Host:** external PC over Ethernet or USB; an optional MicroBlaze may provide board-local orchestration but is not required.
- **Verification/ASIC:** same shared Verilator/cocotb/SymbiYosys and OpenROAD portability lanes as Stack A.

### Advantages

- Pure-FPGA organization avoids the temptation to blur Arm software with the accelerator core.
- 740 DSP slices and 13 Mbit BRAM provide credible baseline capacity and useful later spatial-Clef room.
- Mature board support, onboard USB-JTAG/UART, Ethernet, switches/LEDs/OLED, FMC, and four Pmods provide excellent observability and expansion.

### Costs and risks

- Direct price was **$577**; distributor pricing was higher despite current stock.
- It costs more than KV260 while supplying less raw compute and no hard host CPU.
- It shares Vivado proprietary-tool and annual-license dependence with Stack A.
- Artix-7 is mature rather than current-generation; that is stable for teaching/prototyping but offers less future headroom.

## Stack C — DE10-Nano as the lowest-cost integrated-host option

### Components

- **Board:** Terasic DE10-Nano, Cyclone V SoC 5CSEBA6U23I7.
- **Implementation:** Quartus Prime Lite 25.1std with Cyclone V device support. Altera documents Lite as free with no license file; Signal Tap is included.
- **Host:** board-local dual-core Arm HPS/Linux over the HPS–FPGA bridge.
- **Verification/ASIC:** same portable front end and ASIC smoke flow; Quartus provides vendor correlation and bitstream generation.

### Advantages

- Lowest listed retail cost at **$225** or **$190 academic**.
- Hard Arm/Linux host, 1 GB DDR3, Ethernet, UART, USB OTG, and integrated programmer make closed-loop work practical.
- Quartus Lite does not require a license file, avoiding AMD's annual free-license renewal.
- Selecting it provides a useful non-AMD portability forcing function.

### Costs and risks

- Only 112 variable-precision DSP blocks and 5.57 Mbit M10K memory substantially reduce safety margin before P03/P07/P09 quantify the model.
- Cyclone V is an older family. The current Lite release still supports it, but the project would carry more legacy-flow risk.
- Open nextpnr Cyclone V support is explicitly experimental, so Quartus must be treated as the authoritative FPGA implementation backend.
- Direct-order availability needs confirmation before purchase.

## Open-toolchain FPGA option considered but not shortlisted as the sole board

ULX3S with ECP5-85F provides 84K LUTs, 3,744 Kbit embedded RAM, 156 18×18 multipliers, 32 MB SDRAM, USB-JTAG/serial, and a fully open Yosys + nextpnr + Project Trellis bitstream flow. It is valuable as a later portability target. It is not recommended as the only board because the 85F version was listed at $275 with shipment scheduled for 2026-12-01, lacks onboard Ethernet/hard CPU, and has the least memory/logic headroom. Project Trellis also documents limitations in automatic DSP inference. Sources: [ULX3S](https://radiona.org/ulx3s/), [current order page](https://www.crowdsupply.com/radiona/ulx3s), [Lattice ECP5 resources](https://www.latticesemi.com/en/Products/FPGAandCPLD/ECP5.aspx), and [Project Trellis](https://github.com/YosysHQ/prjtrellis).

## Verification and synthesis comparison

### Shared open verification lane — recommended for every stack

| Tool | Role | Strength | Limitation / control |
|---|---|---|---|
| Verilator 5.052 | Fast SystemVerilog lint and compiled simulation | Portable, fast, coverage and assertion support | Partial SVA/coverage and four-state limitations; correlate critical tests with vendor simulator |
| cocotb 2.0.1 | Python-driven RTL tests and exact comparison with fixed-point model | Same test intent across vendors | Simulator-specific differences remain; pin versions and seeds |
| SymbiYosys | Bounded/unbounded safety proofs and cover traces | Excellent for address, buffer-role, handshake, and invariant proofs | Supports a subset of SVA/SystemVerilog; use small proof harnesses |
| Yosys | Technology-independent synthesis sanity checks and ASIC/open-FPGA front end | Detects portability problems early | Does not replace vendor FPGA synthesis or commercial ASIC signoff |

Primary documentation: [Verilator 5.052](https://verilator.org/guide/latest/overview.html), [Verilator language support](https://verilator.org/guide/latest/languages.html), [cocotb 2.0.1](https://docs.cocotb.org/en/stable/release_notes.html), and [SymbiYosys](https://symbiyosys.readthedocs.io/en/latest/).

### Vendor implementation lane

- **Vivado:** authoritative backend for KV260 and Nexys Video. Provides synthesis, implementation, timing, bitstream, and ILA/VIO. Vivado 2026.1 introduced tiered licensing; BASIC is $0 but needs an annual node-locked license. [AMD licensing FAQ](https://www.amd.com/en/products/software/adaptive-socs-and-fpgas/licensing-faq.html) and [ILA/VIO documentation](https://docs.amd.com/r/en-US/ug896-vivado-ip/Working-with-Debug-IP).
- **Quartus Prime Lite:** authoritative backend for DE10-Nano. Version 25.1std supplies Cyclone V device files; Lite is free without a license file and includes Signal Tap. [Quartus download/device support](https://www.altera.com/downloads/fpga-development-tools/quartus-prime-lite-edition-design-software-version-25-1-windows), [licensing](https://docs.altera.com/r/docs/683472/26.1/altera-fpga-software-installation-and-licensing/quartus-prime-software-license), and [Signal Tap](https://docs.altera.com/r/docs/683552/18.1/intel-quartus-prime-standard-edition-user-guide-debug-tools/signal-tap-logic-analyzer-features-and-benefits).
- **Yosys + nextpnr + Trellis:** authoritative open bitstream lane only for a supported ECP5 board. Upstream nextpnr labels Cyclone V and Xilinx 7-series support experimental, so those backends must not sign off the shortlisted AMD/Altera boards. [nextpnr support matrix](https://github.com/YosysHQ/nextpnr).

### Host observation

The P01 inventory found Git 2.53.0.windows.3, but no `python`, `python3`, Verilator, Yosys, nextpnr-ecp5, Icarus, Vivado, or Quartus executable on `PATH`. This is an observed host state, not evidence that software is absent from every directory. P02 must install and pin the selected stack rather than assume it exists.

## ASIC flow comparison

### Open exploration flow — recommended before G7

- Use Yosys/OpenROAD Flow Scripts in a pinned Linux or WSL2/Docker environment for early portability, area/timing trends, and wrapper discipline.
- OpenROAD Flow Scripts supports public ASAP7, Nangate45, SKY130, GF180, and SG13G2 platforms as well as user-supplied proprietary platforms.
- Use SKY130HD or GF180 only as an exploratory target until G7. The open SKY130 PDK explicitly describes itself as an experimental preview not intended for production.
- Do not treat open-flow DRC/LVS or generated GDS as foundry signoff or tapeout authorization.

Sources: [OpenROAD Flow Scripts](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/master/docs/index.md), [RTL-to-GDS tutorial](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/master/docs/tutorials/FlowTutorial.md), and [SKY130 status](https://skywater-pdk.readthedocs.io/en/main/status.html).

### Commercial/foundry flow — defer selection to G7

- If university or shuttle access exists, evaluate a foundry-supported PDK, standard-cell libraries, SRAM compiler/macros, DFT, and signoff decks with either Synopsys Fusion Compiler/PrimeTime/IC Validator or Cadence Genus/Innovus/Tempus/Pegasus.
- Commercial flows offer broader SystemVerilog, memory, DFT, and foundry-signoff support, but require licenses, NDA-controlled PDK data, trained users, and substantial compute/storage.
- P01 selects only a portability policy: keep synthesizable SystemVerilog and memory/vendor/debug wrappers isolated so either open or commercial ASIC flow remains possible.

Sources: [Synopsys Fusion Compiler](https://www.synopsys.com/implementation-and-signoff/physical-implementation/fusion-compiler.html) and [Cadence Genus](https://www.cadence.com/en_US/home/tools/digital-design-and-signoff/synthesis/genus-synthesis-solution.html).

## Why Clef runtime topology does not require FPGA partial reconfiguration

The planned effective topology can live in ordinary runtime state: an edge-enable `g`, weight `w`, threshold, or route state directly gates or scales local causal propagation on a fixed physical mesh. Updating that state changes the effective causal graph without loading a new FPGA configuration. This is cheaper, faster, easier to replay, and less dependent on vendor configuration infrastructure.

Dynamic Function eXchange/partial reconfiguration remains an optional later engineering experiment for swapping physical regions or substrate mechanisms. It is not a prerequisite for Clef, and relying on externally prepared partial bitstreams could complicate the claim that runtime organization maintains itself. No shortlisted board is chosen for partial-reconfiguration capability at G1.

## Schedule and risk effects

| Choice | Baseline schedule | Later Clef | FPGA portability | ASIC portability |
|---|---|---|---|---|
| A — KV260 | Lowest capacity and host-integration risk; vendor setup still substantial | Best headroom for 64–128 low-bit spatial tiles/patches before folding | Portable core plus AMD wrapper; Vivado backend dependency | Neutral if core avoids AXI/vendor primitives internally |
| B — Nexys Video | Simple pure-FPGA boundary, but external host driver work and higher cost | Good fabric/BRAM; no hard host | Same AMD dependency; mature 7-series | Neutral with wrappers; pure-FPGA boundary is clean |
| C — DE10-Nano | Cheap and integrated, but highest risk of early resource-driven redesign | Most likely to force folding or smaller spatial configuration | Gives useful AMD-independent check; Quartus backend dependency | Neutral with wrappers; older FPGA results may be less predictive |

## Repository and license choices

### Visibility

- **Private during development, public at the signed-off release — recommended.** Reduces accidental release of third-party weights, proprietary reports, or unreviewed claims while allowing a deliberate P17 publication/provenance audit.
- **Public from P02.** Maximizes transparency and collaboration but requires license/provenance hygiene immediately; unfinished scientific claims and large artifacts are visible.
- **Private indefinitely.** Lowest disclosure risk but conflicts with the program's reproducible-release intent unless revisited later.

### License

- **Apache-2.0 for original repository code, RTL, scripts, and documentation — recommended pending institutional review.** It is permissive and includes an explicit contributor patent grant. Third-party assets retain their own licenses and must be isolated with provenance notices. [Official license](https://www.apache.org/licenses/LICENSE-2.0.html).
- **Split policy:** CERN-OHL-P-2.0 for original hardware/RTL, Apache-2.0 for software, and CC-BY-4.0 for documentation. More hardware-specific but increases classification and release overhead.
- **All rights reserved until release review.** Suitable if institutional/IP constraints are unresolved, but blocks normal open reuse and contribution.

This is project planning, not legal advice. Institution, sponsor, employer, or upstream-source obligations take precedence.

## Original recommendation and final accepted decision

The original recommendation was:

- **Stack A: AMD KV260**;
- **budget ceiling: $400 before tax/shipping** for one board, official supply, storage/cables, and contingency;
- **allow no-cost proprietary FPGA tools**, while requiring a portable SystemVerilog core and open verification lane;
- **private repository through baseline signoff**, with planned public release after provenance/claim review; and
- **Apache-2.0** for original work, subject to institutional review and third-party license isolation.

The final accepted decision is:

- school-provided DE1-SoC as the provisional baseline development and synthesis board;
- $0 initial FPGA hardware spending, with upgrade deferred until measured justification;
- no-cost proprietary Quartus accepted as the authoritative Cyclone V implementation backend;
- synthesizable SystemVerilog for the technology-independent core;
- portable-core compatibility with both Quartus and an open Yosys/OpenROAD ASIC exploration lane;
- private GitHub repository initially; and
- all rights reserved during private development, with public release and open licensing deferred to an institutional/provenance/claim review.

This lowers procurement cost and uses local expertise while accepting greater capacity risk and an older vendor stack. Open ASIC compatibility is an early portability requirement, not foundry signoff; G7 still selects the actual ASIC technology and endpoint.

## G1 outcome

G1 was accepted on 2026-09-17. P01 is complete. No branch, external repository, tool installation, purchase, license file, or P02 scaffold was created during P01.
