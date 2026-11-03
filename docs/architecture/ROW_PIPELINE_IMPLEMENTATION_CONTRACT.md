# Row pipeline implementation contract — 2026-10-28

This addendum binds the imported revision 1.0 and follow-up user choices to the existing repository. ADR-0015 accepts the direction; the numerical replacement and measured hardware gates remain evidence-bearing decisions. The original imported document is preserved byte-for-byte. Use this addendum wherever its corrections conflict with revision 1.0.

## Numerical identity and status

The requested row16 candidate is signed state/activation 16/F10, weight 16/F12 and bias/accumulator 48/F22. Products retain all 32 bits. MACs accumulate exactly and add bias last; complete accumulators saturate at their declared width, layers 0/1 apply ReLU, then nearest-ties-even shift by 12 and counted signed state saturation. Residual and output-marker additions use signed guard bits and saturate separately. Do not silently substitute Q-format nomenclature, arithmetic shifts, wrap, early truncation or a different bias/activation order.

`experiments/row16_validation/protocol.v1.json` declares the candidate experiment. `model_export/cartpole/row16_candidate.py` validates frozen weight identity and provides output-major ROM repacking/round-trip. The existing accepted fidelity32 loader/manifest/golden remain unchanged and separately validated. Candidate vectors and tensor-derived images stay ignored/local.

## Original operator corrections

1. Use the 1,916-parameter graph with all 56 biases, original coordinates/scales, zero SAME padding and existing checkpoint identity.
2. Use 50–59 recurrent epochs per action, one boolean update bit per cell shared across channels, raw random initial grid and persistent state between actions.
3. All learned deltas consume the old generation. The new observation is held in a separate observation register and is injected **after** each learned/masked update, including the first epoch. Never preload it into the grid before that first epoch.
4. After residual: clear channels 2/3 globally, clear all active input-cell channels, apply source marker template, scatter scaled observations. Inputs become `[scaled observation,1,1,0,1,1]` at the declared fixed-point scale.
5. Output channel 3 becomes one; output channels 4/5 receive **+1 each epoch**, even under zero masks. Their learned deltas can counteract the increment. Masking never suppresses mandatory postwrites.
6. Read integer scores from channel 0 at the two source output sites after the final committed epoch; action 0 wins ties. Host telemetry conversion occurs after action selection.
7. Preserve source float64 plant → float32 observation → float32 scale multiplication once → declared quantization. Physical placement of this frontend must pass bit-exact conversion tests.

Replace the imported inactive-cell assertion with: zero mask suppresses the learned residual contribution, and final cell state equals the source postwrite transformation of its old state. Replace immutable-identifier assertions with explicit source clear/reassert rules. `6144` counts scalars; the grid has `1024` cells.

## Stage storage and handoff

Convolution produces a complete row of 32×20 values, Dense 1 produces 32×30, Dense 2 produces 32×6. Capture a producer's completed row into the consumer's ordinary input registers at a whole-row ready/valid handshake. Those registers remain stable while the consumer uses them. Producer result registers can then accumulate the next row. Do not add a redundant pair of transfer buffers around those registers.

Nominal arithmetic stage latencies are 1080/800/720 enabled cycles. Convolution's next complete row arrives 1080 cycles after the last, so Dense 1 normally has 280 cycles of slack. Fixed scheduling allows predictable transfers; ready/valid still handles resource stalls. Requests and responses include row/generation tags. A producer may not overwrite unconsumed results. Stage counters/accumulators and tag/data validity advance together under clock enables.

`rtl/core/nca_row_stage.sv` is the initial **reversible arithmetic prototype**, verified independently under both arithmetic formats. Its general lane schedule is:

`dest = lane * ceil(32 * outputs / lanes) + slot`, `cell = dest / outputs`, `neuron = dest % outputs`, inner loop over input features.

With 32/24/8 lanes this yields the exact proposed 1080/800/720 enabled-cycle counts. A seven-lane final-stage variant tests non-divisible tails. Configuration is complete only after every kernel/bias word loads and an explicit commit occurs. Reset invalidates configuration and pending work. Requests capture inputs, outputs hold under backpressure, and result words/counters/tags are tested.

The prototype's convolution input is an explicitly assembled 54-value patch per cell for arithmetic testing. It is **not** the final memory architecture: final convolution must consume the stable shared three-row/window interface without needlessly replicating 54-word patch storage in each column. No complete grid scheduler, UART controller, autonomous RNG or FPGA fit is implied by the row-stage prototype. Its programmable coefficient access also needs physical port/ROM mapping work before G5 signoff.

## In-place state and memory direction

Keep one complete grid. At candidate precision, use four banks, each 256×96 bits: bank `column mod 4`, address `8*row + floor(column/4)`. Assemble/commit a logical row in eight beats. Parameterize state width behind the wrapper. Actual M10K packing/port mapping must be measured; logical capacity is not a fit report.

Three tagged old-state line buffers preserve radius-one neighborhoods. Conservatively release old row r after the convolution consumer for r+1 completes; last-row release follows its own final convolution. Write only after old-row release and valid matching dense output. Memory arbitration and pending-row ownership must remain live under backpressure. Do not expose partial epochs or launch the next epoch until all rows commit and the pipeline drains.

## RNG, diagnostics and transport

Exact supplied initial grids, epoch counts and masks are required in replay mode. Primary autonomous randomness must implement or demonstrate equivalence to the source generator/sampler and logical draw assignment. xorshift is an optional separately evaluated replacement, never a source-equivalence assertion based only on average activity. Draws cannot depend on stalls or active-lane count.

Mask clock enables may reduce physical work while mandatory postwrites still occur. Report executed-work saturation counts separately if skipped logical operations would otherwise contribute diagnostic counts. Use 64-bit lifetime cycle/work counters or explicit overflow flags, plus bounded per-transaction counters. Fault/reset during partial in-place commit invalidates state until explicit initialization.

Keep the imported CRC-framed UART behind a byte interface and a verified board wrapper. Specify little-endian signed payload fields, sessions, sequence wrap, duplicate response caching, busy rejection, timeouts and bounded lengths. Verification mode includes fragmented exact-grid/mask load/readback and forced epoch count. No accepted physical path or wire-level signoff is inferred from the E01 Python interface.

## Completion boundary

The implementation must remain divided into numerical qualification, stage arithmetic, state/scheduler proof, integrated epoch/controller, transport, physical mapping and board-control evidence. Update the ledger and traceability only for tests actually run. Accepted implementation preferences do not substitute for G4/G5/G6 evidence; new measured tradeoffs return to the relevant human gate. Do not declare the full imported spec implemented from passing one row-stage bench.
