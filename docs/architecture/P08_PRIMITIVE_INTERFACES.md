# P08 portable primitive interfaces

Authority: accepted ADR-0012, validated accepted arithmetic/freeze manifests,
and the unchanged P07 integer golden. P08 has no new human gate. Final lanes,
banking, bus, RNG and clocks remain G5 decisions. These building blocks neither
implement the complete local graph (P09) nor a grid scheduler (P10/P11).

## Arithmetic and boundaries

- `nca_round_sat`: combinational signed 62-bit accumulator to signed 32-bit
  activation, optional ReLU before shift-22 nearest-even rounding, then
  saturation. Negative ties use arithmetic quotient and nonnegative remainder;
  neither arithmetic shift alone nor floating-point division is the rule.
- `nca_guard_add`: combinational signed 33-bit sum of two 32-bit words followed
  by signed state saturation. `enable_rhs=0` suppresses only the delta term;
  it does **not** implement or suppress global clears/input/output post-writes.
  A marker increment supplies the state word `32'sh01000000` (1<<24).
- `nca_mac_stream`: reusable sequential dot-product primitive. Signed 32x24
  multiplication produces the complete 56-bit product, explicitly sign-extended
  to 62 bits. Partial sums contain products only; final accepted term adds bias
  once in a signed 63-bit guard domain before accumulator saturation. ReLU and
  requantization are outside this primitive. Accepted fan-ins 54/20/30 fit;
  MAX_TERMS=54 and ACC_W>=PROD_W+clog2(MAX_TERMS) conservatively prove generic
  partial sums do not wrap. Assertions reject malformed first/last sequences
  and excess terms. Arbitrary synthetic biases can saturate the final guard sum;
  frozen weights' tighter bounds remain the P07 authority.
- `nca_word_pack`: sign-extension and validated narrowing for 64-bit comparison
  containers, not a physical bus format. A bad container is flagged; consumers
  must reject `unpack_valid=0`, never use its truncated `word_out`. State RAM
  still has 32-bit words. Software little-endian int64 hash normalization remains
  distinct from raw 32-bit dumps; P08 adds no RAM dump/hash engine.

Parameterization supports verification/reuse, not an alternative deployment.
The instantiated/tested primary widths are 32/24/62 and SHIFT=22. Products,
guard sums and signed constants have explicit widths. No vendor primitives,
learned literals, teacher policy, plasticity or event-gated model variant exists.

## Ready/valid and diagnostics

All sequential primitives use one clock and synchronous active-high reset.
`fire=in_valid && in_ready` is the sole acceptance event. MAC `first` starts
one transaction and `last` closes it; a one-term transaction has both set.
Bias is sampled only on `last`. Inputs must stay stable while valid is stalled.
Output data, saturation flag and valid remain stable until output acceptance.
MAC may retire an old output while accepting the next transaction's first term.
Reset aborts partial/pending transactions and clears output validity. No hidden
retry, controller reset or epoch behavior is introduced.

`nca_elastic_word` is a one-entry same-clock transport register: it accepts into
empty storage, holds under backpressure, and supports simultaneous retire/replace.
It is not a FIFO queue, CDC, RAM or selected host transport. No CDC primitive is
needed before an actual cross-domain G5/P13 contract exists.

Combinational saturation flags are **level results**, not clock events. Bind
`nca_event_counter.fire` to the consuming transaction's acceptance and its
`event_in` to that transaction's saturation flag. The default unsigned 32-bit
counter saturates at all-ones, with sticky overflow on the next event; reset
clears both. Never count a held flag once per stalled cycle. Integrators must
provide separate counters for each golden diagnostic label (accumulator/layer,
residual/marker, etc.); P08 demonstrates accumulator-output counting only and
does not implement full NCA counter aggregation or initialization diagnostics.

## Abstract memory integration contract (not a chosen implementation)

Future engines supply ordered state/weight words to the MAC handshake and
consume its result through the requantizer/transport register. A memory adapter
must retain requests until accepted and return associated words without
reordering or mixing transactions; RAM latency/banking/ports belong to G5.
The future grid interface must distinguish old-epoch read ownership from
new-epoch writes and prohibit visibility before commit. P08 deliberately
allocates no RAM, halos, epoch barrier, queue, RNG, address layout or bus tags:
inventing those would prematurely implement P09/P10. This contract supplies the
primitive seams while keeping actual storage/transport wrappers replaceable.

## Verification entry point and rights

Run `python tb/p08_primitives/run.py` with Icarus `iverilog` and `vvp` on PATH.
It validates authority, generates synthetic accepted-width tests in ignored
`artifacts/p08_primitives/synthetic/`, compiles SystemVerilog with assertions,
executes it, and records tool version, commands and source/testbench hashes.
Missing tools exit 2 with **NOT RUN**, not a simulation pass.

`--generate-only` checks scalar/P07 correspondence and emits the bench without
claiming RTL execution. `--restricted` additionally verifies six accepted NPZ
hashes and generates MAC/layer tests for eight saved cells per case, including
corners and I/O cells. These testbench literals are checkpoint-derived and must
remain local/ignored. They are not production ROM images. Whole epochs,
readouts, reset/stalls and memory schedules still require later integration.

CI uses only the synthetic lane. Current local HDL simulation/synthesis and
Quartus/Yosys portability remain unrun until actual tools execute. Python vector
tests, static review or prior P07 replay cannot replace that evidence.
