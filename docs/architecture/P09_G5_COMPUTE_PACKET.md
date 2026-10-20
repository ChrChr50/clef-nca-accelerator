# P09 local-rule engine / preliminary G5 compute packet

2026-10-08. **Implemented, HDL verification pending. G5 is not accepted.**
P08 remains verification-pending. This packet supplies compute alternatives only;
final lanes/storage/partition/bus/RNG/clocks wait for the P10 G5 packet and user.

## Exact component boundary

`rtl/core/nca_local_rule.sv` accepts a single packed 54-word zero-padded
neighborhood and returns **delta**, six signed state-format words. It implements
learned 3x3 6->20/ReLU, 1x1 20->30/ReLU, 1x1 30->6 linear, exactly 1,860
products and 56 bias additions per cell. ReLU precedes signed shift-22 ties-even
requantization. Complete 56-bit products extend to 62-bit partial sums; bias
enters only the last fan-in term in a 63-bit guarded sum, then clips to 62.
The actual loaded model2 analytical full-state bounds are 58/57/57 signed bits.

The component acquires **no** grid neighbors itself. The caller forms patch
index `(kernel_row*3+kernel_col)*6+channel` using old-epoch words and zeros for
out-of-grid sites. Patch word zero occupies the least significant 32 bits.
Result channel zero similarly occupies the least significant 32 bits. Padding
and corner/edge order are checked by the harness against P07. Grid RAM/halos,
logical masks/RNG, residual, clamps, markers, epoch commits, readout and physical
transport remain outside P09. A Python boundary probe verifies delta is added
once, then post-writes applied once, for mask-zero/one and input/output/ordinary
cells against `FixedNCA.step`; this is not an RTL integration pass.

## Request/result, configuration and trace

Single clock, synchronous active-high reset. `request_valid && request_ready`
latches all patch words; no further input stability is needed after acceptance.
Only one request is active; result/delta remain stable under result backpressure.
`run_enable=0` pauses compute loops without advancing terms/groups/layers/cycles.
Result retirement may occur while compute is disabled. There is deliberately a
one-cycle request bubble after a pending result retires. Reset aborts work,
clears validity/counters and invalidates parameter configuration; it does not
clear the physical parameter arrays, whose stale contents cannot be used.

Load parameters sequentially, **1,860 kernel words then 56 bias words**; no
request is admitted until all load transactions are valid. `load_ready` denotes
transport acceptance; `load_error` pulses when address/order/sign-extension is
invalid and config progress does not advance. Kernels are signed 24-bit values
sign-extended to a 62-bit load word; biases are signed 62-bit words. Incorrect
ordering/noncanonical kernel extension is tested. Configuration is locked after
completion and during requests/results; reloading requires explicit reset. This
is a verification/compute seam, not a final bus configuration protocol.

Kernel address: layer offsets `[0,1080,1680]` plus `input_index*outputs+output`.
Bias offsets `[0,20,50]`. All layers traverse fan-in in source row/column/channel
order. Output-channel groups are parallelized; tail lanes are invalid and must
be ignored. `trace_valid` is a **one-clock event**, not a backpressured stream;
`trace_keep` identifies valid lane accumulators/activations/saturation flags.
Consumers must capture the event rather than count held payloads every clock.
Separate accumulator/layer diagnostic flags preserve golden labels. Full
controller counters and activity/skipping accounting remain integration work.

## Images, rights and observed checks

`tb/p09_local_rule/support.py` quantizes through validated `accepted_format()`
and unchanged `FixedNCA`. It emits local `kernels.mem` (24 bits, six hex digits)
and `biases.mem` (62 bits, sixteen hex digits, top two padding bits zero), two's
complement ASCII, with layer/input/output flattening above. Decoder rejects
nonzero padding/out-of-width inputs. Both images round-trip exactly and hashes
are recorded in ignored `images.json`/`result.json`. Raw packed parameter demand
is **48,112 bits**; text/container sizes are not hardware RAM widths.

Local model2 image hashes:

- kernels: `38155228bcf9cc56edcb483c619e0a054036c0f591558f3d7699ad0ce0038ec2`
- biases: `2e327263cf03475eded2244ba952658275d99c9ee3a04b0ab26d43f24b1669a0`

Checkpoint blob is the unchanged frozen model2 hash; upstream revision/13
artifact hashes/three released operator/plant rollouts were verified. All learned
images and generated benches are ignored/local, never embedded in tracked RTL
or CI. A private GitHub repository does not waive the rights boundary.

Scalar/P07 evidence: six public synthetic cells (corners/edge/interior), 336
accumulator/output pairs; all six accepted fidelity32 snapshots with eight cells
each, **48 cells / 2,688 accumulator/output pairs**. All compare exactly to saved
layer arrays and independent scalar cells. Generated HDL benches cover lanes
1/2/3/4, fan-in/output loops, parameter loading, valid bubbles, compute stalls,
result backpressure and reset. These benches are **not executed** locally.

## G5 compute alternatives

| Option | Structural enabled cycles/cell | Storage/read implications | Main risk |
|---|---:|---|---|
| A: 1 output MAC lane | 1,862 | One coefficient read/term; 62-bit sum lane | Lowest nominal throughput |
| B: 2 lanes | 932 | Two coefficient reads/term; broadcast input | Extra DSP/read-port/banking cost |
| C: 4 lanes | 492 | Four coefficient reads/term; tails for 30/6 outputs | Wider fanout/ports and uncertain fit/Fmax |

Three lanes (640 structural cycles) are also in the harness to exercise tails.
Counts derive from `sum(ceil(outputs/lanes)*fan_in)+2` inter-layer copy cycles,
excluding request/retirement bubbles, configuration, acquisition, stalls and
whole-grid control. **No RTL-cycle measurement or speedup/PPA claim** follows.
The bench asserts these counts when a simulator is available. Active logical
MACs stay 1,860; inactive tail lanes can create additional physical switching.
No work-skipping or power benefit has been measured.

The source uses behavioral parameter arrays with simultaneous per-lane reads;
actual RAM mapping/replication/banking is not selected or proven. Scratch stores
54 input words +30 output words =2,688 bits, plus 62*LANES sum bits, 192 result
bits and optional trace/control storage. This is a source-level demand count,
not synthesized resources. No DSP packing is assumed for 32x24 multiplication.

Recommendation: retain A as the low-complexity provisional reference and compare
B/C after simulation and synthesis; **do not accept a final lane count yet**.
P10 must combine real fit/timing/read-bandwidth with state ownership, wrapper,
RNG/replay and semester schedule. More lanes may reduce compute cycles but
cost memory ports/timing margin; one lane may be sufficient for step-synchronized
simulation, which has no accepted 20 ms wall-clock deadline. No purchase decision
or DE1-SoC fit claim is made.

Portable SystemVerilog/replaceable delta seams retain FPGA/ASIC independence and
later extension compatibility. Folding preserves the original local graph when
old-neighborhood acquisition is correct; no patch mesh or Clef closure claim
is introduced. All options remain conventional fixed-weight accelerators.

## Stop and prerequisites

Proposed ADR-0014 remains unaccepted. P09 is not fully verified/complete: Icarus,
vvp, Verilator and Yosys remain absent, and P08 verification is pending. Run
`python tb/p09_local_rule/run.py` and `--restricted` with actual HDL tools,
repair/retest real defects, then obtain actual synthesis evidence. CI synthetic
steps are prepared but not pushed/run. **No P10 or final G5 decision is started.**
