# From the Python CartPole NCA to `nca_local_rule.sv`

2026-10-30 location update: this is a historical explanation of the earlier
folded engine. Its unchanged source now lives at `tb/legacy_rtl/nca_local_rule.sv`;
the five other retired primitives listed below also moved into `tb/legacy_rtl/`.
The current accelerator uses the row pipeline documented in
`docs/architecture/ROW_PIPELINE_EPOCH_CORE.md`. Historical line-by-line text below
is preserved; the active `nca_round_sat.sv` has subsequently been renamed internally.

This is an explanation of the inspected 133-line source in
`rtl/core/nca_local_rule.sv`, as read on 2026-10-08. It does not change the RTL.
Line numbers refer to that source, not this document. Read the two side by side.

The source authority is `reference/original_nca/core.py:CanonicalNCA.local_delta`.
The hardware numerical authority is the validated `fidelity32` contract in
`sw/cartpole/arithmetic.accepted.v1.json` and
`model_export/cartpole/fixed_point.py`. The local rule evaluates frozen released
model2's learned parameters; it does not train them.

## 1. Where this component sits in the system

The Python algorithm has a grid of 32 x 32 cells, with six state values per cell.
For one cell `(r,c)`, gather its 3 x 3 neighborhood: nine cells times six channels
is **54 scalar values**. The same learned rule is applied wherever the cell is.

```text
Old grid snapshot, outside this module
        |
        | gather one 3 x 3 x 6 patch; substitute zeros outside grid
        v
patch_words: 54 state-format values
        |
        | kernels + biases are the shared trained rule
        v
54 inputs -> 20 learned features -> ReLU
20 features -> 30 learned features -> ReLU
30 features -> 6 linear delta values
        |
        v
delta_words: proposed change to this cell's six state channels
        |
        | outside this module:
        v
apply cell's random mask -> add delta to old cell -> clear/rewrite I/O
        |
        v
commit new grid; repeat for 50-59 NCA epochs per CartPole decision
        |
        v
read output-cell channel 0 at (13,16) and (17,16), choose argmax
        |
        v
CartPole host applies left/right force and returns next four observations
```

The current module implements the middle three neural layers for **one patch
request**. It has no grid RAM, grid coordinates, neighborhood-fetch logic,
stochastic mask, residual addition, I/O rewrite, epoch loop, action argmax, or
CartPole simulator. Those are integration responsibilities outside its ports.
The eventual grid controller can reuse this engine for every cell, always
obtaining patches from the same old-epoch snapshot. This preserves synchronous
NCA semantics even if cells are physically serviced one after another.

Three different kinds of time are involved:

1. **FPGA clock:** this module uses many clock edges to finish a cell's rule.
2. **NCA epoch:** all 1,024 cells' proposals/updates are computed and committed.
3. **CartPole step:** after 50-59 NCA epochs, select a force and advance the plant.

`run_enable` pauses the first of these. It is not the NCA's random cell-update
mask and does not select how many NCA epochs a CartPole decision receives.

## 2. The mathematical and Python mapping

Let `x[t]` be the flattened neighborhood, with
`t = (kernel_row * 3 + kernel_column) * 6 + channel`.
The kernel row and column each run 0 through 2; channel runs 0 through 5.
Thus `x[0..5]` is the upper-left neighbor, and `x[24..29]` is the center cell.
The caller must supply zeros for any neighbor outside the grid.

Ignoring quantization for a moment, the same math as Python is:

```text
h0[o] = ReLU(sum(t=0..53, x[t]  * W0[t,o]) + b0[o]), o=0..19
h1[o] = ReLU(sum(t=0..19, h0[t] * W1[t,o]) + b1[o]), o=0..29
dx[o] =      sum(t=0..29, h1[t] * W2[t,o]) + b2[o],  o=0..5
```

| Python object/operation | Hardware object/operation |
|---|---|
| Grid neighborhood used by `conv2d_same` | Caller-packed `patch_words`, then `inputs[0..53]` |
| `w.conv0_kernel`, `w.conv1_kernel`, `w.conv2_kernel` | Three successive regions of `kernels` |
| `w.conv0_bias`, `w.conv1_bias`, `w.conv2_bias` | Three successive regions of `biases` |
| A filter's dot product | `product`, `sums`, `partial`; repeat over `term_index` |
| Bias addition | `selected_bias` and `biased`; latch it only at the final term |
| First `relu(...)` | `nca_round_sat` with `layer=0`, so its `relu` input is true |
| Second `relu(...)` | Same circuit with `layer=1` |
| Intermediate `x` with 20 or 30 features | `scratch`, then copied back into `inputs` |
| Final linear `conv1x1` | Same circuit with `layer=2`, so ReLU is disabled |
| One cell of the returned `local_delta(grid)` array | Six packed values in `delta_words` |
| Returning a completed result to the caller | `result_valid` / `result_ready` handshake |
| Python execution order and loop indices | `mode`, `layer`, `term_index`, `output_base` and related counters |

The 20 and 30 features are temporary neural activations. They do not create
20- or 30-channel persistent grids. `scratch` is reused between cells and
layers; it is not the NCA's recurrent memory.

### Where the 1,916 parameters live

| Layer | Input count (`fan`) | Output count (`outputs`) | Kernel array addresses | Bias array addresses |
|---|---:|---:|---|---|
| 0: 3 x 3 x 6 -> 20 | 54 | 20 | 0-1079, 1,080 values | 0-19, 20 values |
| 1: 20 -> 30 | 20 | 30 | 1080-1679, 600 values | 20-49, 30 values |
| 2: 30 -> 6 | 30 | 6 | 1680-1859, 180 values | 50-55, 6 values |

There are 1,860 kernels and 56 biases: **1,916 learned scalar parameters**.
The original paper's stated 1,854 differs from the executable graph's 1,916.
This implementation follows the executable graph.

For a particular input term and output feature, the hardware address is:

```text
kernel_base + term_index * outputs + output_base + lane_number
```

This stores each input term's coefficients for all output features consecutively.
For example, layer-0 kernel addresses 0-19 are input term 0's weights for all
20 features; addresses 20-39 are input term 1's weights. A single filter's 54
weights are therefore strided through this array, not a contiguous 54-word block.

### Fixed-point numbers versus the Python float32 rule

| Hardware value | Stored integer `q` means | Signed width |
|---|---|---:|
| `inputs`, `scratch`, `activated`, `delta_words` | real value = `q / 2^24` | 32 bits |
| `kernels`, `coefficient` | real value = `q / 2^22` | 24 bits |
| Products | real value = `q / 2^46` | 56 bits |
| `biases`, `sums`, `clipped` | real value = `q / 2^46` | 62 bits |
| `partial`, `biased` | same scale, with an extra guard bit | 63 bits |

The bias is quantized at product scale so it can be added directly. After
the completed dot product and bias, apply ReLU in layers 0/1, round the integer
division by `2^22` to nearest with ties to an even result, then saturate to
the signed 32-bit state/activation range. The third layer does the same
conversion with no ReLU.

That is the accepted P07 approximation of the float32 rule, not bit-identical
float32 arithmetic. The original float inference has no [-5,5] clipping.
Here, saturation prevents numeric wrap at the declared integer widths; the
32/F24 state range is approximately [-128,128), not [-5,5]. The six returned
values are still deltas, not already-updated cell state.

## 3. Small SystemVerilog dictionary

- `wire`: a signal driven by combinational logic or another module. A wire
  does not by itself hold a value between clocks.
- `reg`: a procedural variable. Here most declarations are clocked storage,
  but the word alone does not guarantee physical RAM or a particular FPGA primitive.
- `signed [31:0]`: a 32-bit two's-complement number; bit 31 is its sign.
- `integer`: a 32-bit signed control/index variable here; it does not mean
  the neural network uses integer-valued semantic features.
- `assign`: continuous combinational wiring; it is not a CPU instruction.
- `always @(posedge clk)`: evaluate this clocked block on every rising edge.
- `<=` in that block: a nonblocking register assignment. Right-hand sides see
  the pre-edge values; register updates take effect together afterward.
- `if`, `for`: describe control/multiple assignments in the circuit; a `for`
  inside a clock block does not inherently spend one clock per loop iteration.
- `[i*32+:32]`: select 32 bits starting at bit `i*32`. Packed word 0 occupies
  the lowest 32 bits. This carries a list of scalar words, not a grid coordinate.
- `{...}` and `{{N{sign}},word}`: concatenate bits and replicate a sign bit
  to widen a signed number without changing its numeric value.
- `generate`: construct repeated hardware at elaboration, before operation.
  It is not a runtime loop over grid cells.

## 4. Every line of `nca_local_rule.sv`

### Lines 1-23: declare the one-cell engine's ports

| Line | Source item | Mapping and purpose |
|---:|---|---|
| 1 | Comment: folded local delta engine | States the boundary: evaluate the shared learned neural rule. Grid, mask, residual and I/O rewrite belong outside. |
| 2 | `module nca_local_rule #(parameter integer LANES=1)` | Defines the hardware function. `LANES` is how many output features are evaluated in parallel, default one. It changes physical parallelism, not the learned layer sizes. |
| 3 | `clk, rst, run_enable` | Hardware clock; synchronous active-high reset; compute pause/enable. `rst` resets this engine/configuration, not the CartPole plant or full grid. `run_enable` is distinct from stochastic NCA firing. |
| 4 | `load_valid, load_bias` | Parameter-loading request. `load_valid` says a word is offered; `load_bias` selects the bias array rather than the kernel array. These replace software loading of the six weight tensors. |
| 5 | `[10:0] load_address` | An 11-bit index large enough for kernel addresses 0-1859. Bias addresses are separately numbered 0-55. It is not a cell address. |
| 6 | `signed [61:0] load_word` | Common 62-bit parameter input. A kernel is its canonical sign-extended 24-bit value; a bias uses all 62 bits. |
| 7 | `load_ready` | Indicates the engine can accept a load transaction this clock. Both valid and ready must be true. This is transport control, not learning. |
| 8 | `load_error` | One-clock indication that an accepted load had wrong ordering, address or kernel sign extension. Invalid loading does not advance configuration. |
| 9 | `request_valid` | Caller offers one neighborhood for neural evaluation. |
| 10 | `[54*32-1:0] patch_words` | Packed 1,728-bit neighborhood: 54 signed 32-bit state words. These are the 3 x 3 x 6 inputs to the first layer. The bus itself is unsigned; individual slices are stored in signed `inputs`. |
| 11 | `request_ready` | Indicates the one-cell request can be accepted. Prevents two overlapping patches from corrupting shared scratch/accumulators. |
| 12 | `result_ready` | Caller says it can receive the completed six-value delta. |
| 13 | `result_valid` | Indicates `delta_words` is complete; remains asserted until the caller accepts it. |
| 14 | `[6*32-1:0] delta_words` | Packed 192-bit result. Word 0 is delta for state channel 0, through word 5 for channel 5. These are not six environment actions; CartPole still has two action readout cells. |
| 15 | `trace_valid` | One-clock event indicating completed layer-output diagnostics. Trace is not backpressured like the delta result. |
| 16 | `[1:0] trace_layer` | Identifies which neural layer, 0/1/2, produced that trace. |
| 17 | `[5:0] trace_base` | First output-feature index in the traced group, not a row/column. Six bits cover indices 0-29. |
| 18 | `[LANES-1:0] trace_keep` | One valid bit per physical lane. Tail lanes beyond the layer's output count must be ignored. |
| 19 | `[LANES*62-1:0] trace_acc` | Packed completed bias-inclusive, saturated 62-bit dot products, before ReLU/requantization. Mirrors golden layer accumulator arrays. |
| 20 | `[LANES*32-1:0] trace_output` | Packed completed 32-bit feature/delta values after ReLU where applicable and requantization. Mirrors golden layer output arrays. |
| 21 | `trace_acc_sat, trace_layer_sat` | Per-lane flags for accumulator saturation and subsequent activation/output saturation. They diagnose integer arithmetic and do not become neural features. |
| 22 | `[31:0] active_cycles` | Hardware compute-cycle counter for this cell request. It counts enabled MAC/ADVANCE cycles, not 50-59 NCA epochs or CartPole steps. |
| 23 | `);` | Ends the port list. No arithmetic is performed by this punctuation. |

### Lines 24-40: storage, indices and number limits

| Line | Source item | Mapping and purpose |
|---:|---|---|
| 24 | `localparam IDLE=0, MAC=1, ADVANCE=2` | Three hardware control states: waiting, multiply/accumulate, and moving one completed layer's activations into the next layer's inputs. |
| 25 | `[1:0] mode, layer` | `mode` holds the control state; `layer` holds neural layer index 0/1/2. Two bits suffice for each. |
| 26 | `fan, outputs, kernel_base, bias_base, term_index, output_base` | `fan`: current dot-product length 54/20/30. `outputs`: current feature count 20/30/6. Bases choose weight/bias regions. `term_index` chooses the current input term. `output_base` chooses the first feature in the current lane group. |
| 27 | `integer config_count` | Counts successfully loaded parameter words across kernels then biases, 0 through 1916. |
| 28 | `reg configured` | True only after the complete trained rule has loaded. Prevents inference using an incomplete/stale rule. |
| 29 | `signed [23:0] kernels [0:1859]` | The 1,860 learned connection weights, shared across cell requests. This is parameter storage, separate from grid state. Actual synthesis into RAM/registers and read-port implementation remain to be measured. |
| 30 | `signed [61:0] biases [0:55]` | The 56 learned feature biases: 20 + 30 + 6. These complete the 1,916-parameter rule. |
| 31 | `signed [31:0] inputs [0:53]` | Working input vector. Initially the 54 neighborhood values; later the first 20 or 30 words hold intermediate features. It is one request's local scratch, not the 32 x 32 grid. |
| 32 | `signed [31:0] scratch [0:29]` | Space for all outputs of either hidden layer: first 20, then 30. Reused between layers/cells. |
| 33 | `signed [61:0] sums [0:LANES-1]` | One running dot-product sum for each physical output lane. Begins at zero for each output feature. |
| 34 | `lane_live, acc_sat, act_sat` | Lane validity; combinational accumulator-bound flag; output-round/saturation flag. Each vector has one bit per lane. |
| 35 | `signed [61:0] clipped [0:LANES-1]` | Completed dot product plus bias constrained to the 62-bit accumulator range. This is still product/bias scale F46. |
| 36 | `signed [31:0] activated [0:LANES-1]` | Feature value after the first/second-layer ReLU or third-layer linear conversion, rounding and saturation. |
| 37 | `signed [62:0] partial [0:LANES-1]` | Extra-wide temporary sum of the saved accumulator and the current product. The extra bit exposes overflow. |
| 38 | `signed [62:0] biased [0:LANES-1]` | Extra-wide `partial + selected_bias`. Combinational throughout MAC; used as a completed feature only on the last input term. |
| 39 | `HI={2'b00,{61{1'b1}}}` | Largest signed 62-bit value, `2^61-1`, represented safely in a 63-bit comparison word. Not a learned threshold. |
| 40 | `LO={2'b11,{61{1'b0}}}` | Smallest signed 62-bit value, `-2^61`, represented in 63 bits. Not the paper's training [-5,5] limit. |

### Lines 41-60: handshake wires and arithmetic lanes

| Line | Source item | Mapping and purpose |
|---:|---|---|
| 41 | `assign load_ready = ...` | Admit parameter words only out of reset, while idle, with no pending result, until all 1916 have loaded. Parameter replacement requires reset. |
| 42 | `assign request_ready = ...` | Admit a patch only when compute is enabled, rule fully configured, idle, no unconsumed result, and no offered parameter load. Gives loading priority and avoids resource conflicts. |
| 43 | `genvar l` | Elaboration-time index for constructing arithmetic lanes. It is not a grid-cell number or runtime loop counter. |
| 44 | `generate for(l=0; l<LANES; ...) begin: lane` | Replicates the following dot-product arithmetic once per output lane. Each lane evaluates a different output feature using the same input term. |
| 45 | `lane_live[l] = output_base+l<outputs` | Enables only real feature indices. With four lanes and six final outputs, the group starting at output 4 has two live lanes. |
| 46 | `coefficient = (mode==MAC && lane_live[l]) ?` | Select the learned kernel value only during active MAC mode and for a real output. |
| 47 | `kernels[kernel_base+term_index*outputs+output_base+l] : 24'sd0` | Completes the weight lookup: layer region + input-term row + output feature. Idle/tail lanes receive zero coefficient. This chooses one of a filter's learned weights for the current multiplication. |
| 48 | `sx={{24{inputs[term_index][31]}},inputs[term_index]}` | Widen the current signed 32-bit input to 56 bits by sign extension. Preserves the number; performs no scaling/rounding. |
| 49 | `sw={{32{coefficient[23]}},coefficient}` | Widen the signed 24-bit weight to 56 bits. Preserves the number. |
| 50 | `product=sx*sw` | Compute one learned connection's contribution. The original 32-bit times 24-bit operands have an exact signed 56-bit product, despite the sign-extended operands. No per-product rounding occurs. |
| 51 | `extended_product={{6{product[55]}},product}` | Sign-extend the product to the 62-bit accumulator format. Still F46. |
| 52 | `partial[l] = $signed({sums[l][61],sums[l]})+` | Widen the running sum to 63 bits and start adding the current product. |
| 53 | `$signed({extended_product[61],extended_product})` | Complete that guarded signed addition. `partial` is the next dot-product subtotal without bias. |
| 54 | `selected_bias = (mode==MAC && lane_live[l]) ?` | Select this feature's learned bias only for a live MAC lane. |
| 55 | `biases[bias_base+output_base+l] : 62'sd0` | Bias index depends on layer and output feature, never on `term_index`. There is one bias per output feature. |
| 56 | `biased[l] = partial[l]+...selected_bias...` | Form the candidate completed dot product with its bias in a 63-bit guarded sum. Because only the final term latches this path, bias is added once, not once per input term. |
| 57 | `acc_sat[l] = biased[l]>HI || biased[l]<LO` | Test whether the completed bias-inclusive result exceeds signed 62-bit limits. |
| 58 | `clipped[l] = ...` | Saturate high/low or retain the low 62 bits when in range. Implements the accepted golden's accumulator saturation boundary. |
| 59 | `nca_round_sat requant(clipped[l],layer!=2,activated[l],act_sat[l])` | Instantiate the reusable numeric converter. Positional ports are value, ReLU enable, output, saturation flag. Defaults are IN_W=62, OUT_W=32, SHIFT=22. ReLU is true for layers 0/1 and false for layer 2. |
| 60 | `end endgenerate` | End each lane's construction and the generate block. All lane combinational circuits exist at once. |

### Lines 61-86: clocked reset and trained-parameter loading

| Line | Source item | Mapping and purpose |
|---:|---|---|
| 61 | `integer i` | Procedural index used to clear/copy multiple storage entries or lane results. It is not trained state and does not select a CartPole action. |
| 62 | `always @(posedge clk)` | Defines the engine's clocked state transitions. Arithmetic wires above continuously respond to current stored values. |
| 63 | `if(rst) begin` | Enter synchronous reset on the rising edge with reset high. |
| 64 | `mode<=IDLE; layer<=0; fan<=54; outputs<=20; kernel_base<=0; bias_base<=0` | Establish the first-layer control parameters while idle. No neighborhood has yet been accepted. |
| 65 | `term_index<=0; output_base<=0; config_count<=0; configured<=0` | Reset traversal counters and invalidate the loaded rule. The parameter arrays themselves are not cleared; configuration must be fully reloaded before inference. |
| 66 | `result_valid<=0; delta_words<=0; trace_valid<=0; trace_keep<=0` | Clear pending delta and trace validity/payload. These are engine outputs, not grid or plant reset. |
| 67 | `load_error<=0` | Clear the load-error pulse. |
| 68 | `trace_layer<=0; trace_base<=0; trace_acc<=0; trace_output<=0` | Initialize trace metadata and data. |
| 69 | `trace_acc_sat<=0; trace_layer_sat<=0; active_cycles<=0` | Clear numerical trace flags and per-request compute-cycle count. |
| 70 | `for ... sums[i]<=0` | Clear every physical lane's accumulator together at this clock edge. This loop does not take LANES clocks. |
| 71 | `for ... inputs[i]<=0` | Clear the 54-word working input vector. No grid-memory operation occurs here. |
| 72 | `for ... scratch[i]<=0` | Clear the 30-word temporary activation vector. |
| 73 | `end else begin` | Normal clocked operation when reset is low. |
| 74 | `trace_valid<=0` | Default to no trace event on this clock; line 96 overrides it when an output group finishes. This ensures a one-clock pulse even during compute pauses. |
| 75 | `load_error<=0` | Default to no load-error event; line 85 overrides it for an invalid accepted load. |
| 76 | `if(result_valid && result_ready) result_valid<=0` | Retire the completed delta when the caller accepts it. This works even with `run_enable=0`. Data remains stored; validity determines whether it is a new result. |
| 77 | `if(load_valid && load_ready) begin` | Process one accepted parameter transaction. |
| 78 | Comment: sequential complete configuration | Specifies the load protocol: all 1860 kernels, then all 56 biases. This storage layout differs from interleaving each software kernel/bias tensor in a file, while preserving their meanings. |
| 79 | `config_count<1860 && !load_bias && load_address==config_count &&` | During the kernel portion, require kernel selection and the exact next kernel index. Prevents missing/reordered coefficients. |
| 80 | `load_word==$signed({{38{load_word[23]}},load_word[23:0]})` | Require a valid sign-extended signed 24-bit kernel value on the 62-bit load port. Rejects an out-of-range word instead of silently truncating it. |
| 81 | `kernels[load_address]<=load_word[23:0]; config_count<=config_count+1` | Store one quantized learned weight and advance load progress. This assignment is configuration, not backpropagation or an online weight update. |
| 82 | `else if(config_count>=1860 && load_bias && load_address==config_count-1860)` | After kernels, require bias mode and sequential local bias addresses 0-55. |
| 83 | `biases[load_address]<=load_word; config_count<=config_count+1` | Store one quantized learned bias and advance progress. |
| 84 | `if(config_count==1915) configured<=1` | The last bias completes all 1916 parameters. Due to nonblocking semantics, the test sees the count before this edge's increment. |
| 85 | `else load_error<=1` | Reject an accepted word that matches neither valid loading case. Stored arrays/count are unchanged for that word. |
| 86 | `end` | End parameter-loading handling. |

### Lines 87-114: accept a cell patch and evaluate each layer's output groups

| Line | Source item | Mapping and purpose |
|---:|---|---|
| 87 | `if(request_valid && request_ready) begin` | Start a new cell-local neural evaluation on an accepted neighborhood. |
| 88 | `for ... inputs[i]<=patch_words[i*32+:32]` | Copy all 54 packed words into signed working inputs on this edge. The caller may change the patch bus after acceptance. The 54 assignments are simultaneous captures, not 54 compute clocks. |
| 89 | `for ... sums[i]<=0` | Start each lane's first output dot product at zero. |
| 90 | `layer<=0; fan<=54; outputs<=20; kernel_base<=0; bias_base<=0` | Select the first convolution's graph sizes and parameter regions. |
| 91 | `term_index<=0; output_base<=0; mode<=MAC; active_cycles<=0` | Start with input term 0 and output features 0 through LANES-1; enter arithmetic mode and reset this request's cycle count. |
| 92 | `end else if(run_enable && mode!=IDLE) begin` | If no new request started, advance an ongoing computation only when enabled. Pausing preserves indices, sums and layer state. |
| 93 | `active_cycles<=active_cycles+1` | Count this enabled compute clock, including inter-layer ADVANCE clocks. The counter is an ordinary 32-bit wrapping increment, not the saturating `nca_event_counter` primitive. |
| 94 | `if(mode==MAC) begin` | Evaluate the active output group's next dot-product term. |
| 95 | `if(term_index==fan-1) begin` | This is the final input contribution for each lane's current output feature. First layer final index 53; second 19; third 29. The combinational `partial` already includes that final contribution. |
| 96 | `trace_valid<=1; trace_layer<=layer; trace_base<=output_base` | Announce this completed output group and identify its neural layer/feature base. |
| 97 | `trace_keep<=lane_live; trace_acc_sat<=acc_sat & lane_live` | Mark real features and suppress accumulator flags from unused tail lanes. |
| 98 | `trace_layer_sat<=act_sat & lane_live` | Suppress requantization/output flags from unused tail lanes. |
| 99 | `for(i=0;i<LANES;i=i+1) begin` | Commit all lane results together. Physical lane parallelism is distinct from NCA cell parallelism. |
| 100 | `trace_acc[...]<=clipped[i]; trace_output[...]<=activated[i]; sums[i]<=0` | Capture golden-comparable preactivation/output values and reset sums for the next group. The trace payload can include tail-lane entries; use `trace_keep`. |
| 101 | `if(lane_live[i]) begin` | Only actual layer outputs may write neural result storage. |
| 102 | `if(layer==2) delta_words[(output_base+i)*32+:32]<=activated[i]` | Final layer: write this output to its corresponding six-channel delta slot. This is the final linear neural output for that state channel. |
| 103 | `else scratch[output_base+i]<=activated[i]` | Hidden layers: save this feature for the next layer's input vector. |
| 104 | `end` | End live-lane guard. |
| 105 | `end` | End simultaneous lane-result writes. |
| 106 | `term_index<=0` | Next output group starts at input term 0 again, because every output has its own full dot product. |
| 107 | `if(output_base+LANES>=outputs) begin` | Determine whether this group finishes the whole current layer, including a partially filled tail group. |
| 108 | `if(layer==2) begin mode<=IDLE; result_valid<=1; end` | All six final deltas are complete: return to idle and offer one complete cell result. The final delta writes from line 102 become visible on this same edge. |
| 109 | `else mode<=ADVANCE` | A hidden layer is complete: schedule the one-clock transfer to the next layer. |
| 110 | `end else output_base<=output_base+LANES` | If more features remain in this layer, select the next output group. No grid-cell movement happens here. |
| 111 | `end else begin` | Handle an input term before the final dot-product contribution. |
| 112 | `for ... sums[i]<=partial[i][61:0]` | Save the product-inclusive subtotal without bias for each lane. Retaining 62 bits is exact under the proven partial-sum bounds; simulation assertions check this assumption. It is not arbitrary rounding. |
| 113 | `term_index<=term_index+1` | Advance to the next neighborhood scalar or previous-layer feature, reusing the same arithmetic lane(s). This is the temporal folding of a software dot product. |
| 114 | `end` | End final-term versus intermediate-term decision. |

### Lines 115-133: layer transitions and simulation checks

| Line | Source item | Mapping and purpose |
|---:|---|---|
| 115 | `end else begin` | The other reachable active mode is ADVANCE: move completed hidden activations to next-layer inputs. |
| 116 | `for(i=0;i<30;i=i+1) inputs[i]<=scratch[i]` | Copy scratch into the reusable input vector in one clock. After layer 0 only the first 20 entries are consumed; after layer 1 all 30 are consumed. Stale unused entries therefore do not affect a dot product. |
| 117 | `layer<=layer+1; output_base<=0` | Move to the next neural layer and its first output group. Right-hand-side tests below still see the old layer index on this edge. |
| 118 | `if(layer==0) begin fan<=20; outputs<=30; kernel_base<=1080; bias_base<=20; end` | After finishing first layer, configure the 20 -> 30 pointwise layer and its weight/bias offsets. |
| 119 | `else begin fan<=30; outputs<=6; kernel_base<=1680; bias_base<=50; end` | After finishing second layer, configure the 30 -> 6 final linear layer and its offsets. |
| 120 | `mode<=MAC` | Resume dot products next enabled clock. `term_index` and sums were already reset on completion of the preceding group. |
| 121 | `end` | End ADVANCE handling. |
| 122 | `end` | End enabled active-computation handling. |
| 123 | `end` | End normal non-reset operation. |
| 124 | `end` | End the clocked block. |
| 125 | `` `ifndef SYNTHESIS `` | Begin simulation checks normally omitted when synthesis defines `SYNTHESIS`. These checks are not learned computation. |
| 126 | `initial assert(LANES>=1 && LANES<=30) else $fatal(...)` | At simulation startup, reject an invalid physical lane count. Thirty is the largest layer-output count. |
| 127 | `always @(posedge clk) if(!rst && mode==MAC && run_enable) begin` | On enabled MAC clocks, verify arithmetic assumptions using pre-edge register values. |
| 128 | `for(integer j=0;j<LANES;j=j+1)` | `j` is a simulation assertion index over hardware lanes; distinct from elaboration index `l` and procedural write index `i`. |
| 129 | `if(lane_live[j]) assert(partial[j]<=HI && partial[j]>=LO)` | Each real lane's subtotal must fit 62 signed bits before line 112 stores it. This protects the exact-product/partial-sum contract. |
| 130 | `else $fatal(1,"unproved partial accumulator overflow")` | The `else` belongs to the assertion's failure action: stop simulation if the asserted partial-sum bound fails. It does not terminate on every inactive lane. |
| 131 | `end` | End the assertion block. |
| 132 | `` `endif `` | End simulation-only checks. |
| 133 | `endmodule` | End the module definition. |

## 5. What an actual request does, clock by clock

For default `LANES=1`, suppose the caller has already loaded the rule and
gathered one cell's old-grid patch.

1. On a rising edge with `request_valid && request_ready`, the 54 patch words
   are captured. The engine selects layer 0, output feature 0, input term 0.
2. On the next enabled edge, save `x[0]*W0[0,0]` in `sums[0]`.
3. On the next, save that sum plus `x[1]*W0[1,0]`. Continue through term 52.
4. At term 53, form the last product, add the saved sum and the one bias,
   then apply ReLU, rounding and saturation. Save feature 0 in `scratch[0]`.
   Reset the sum and input-term index; select output feature 1.
5. Repeat until all 20 features are in scratch: 20 x 54 = 1,080 MAC clocks.
6. One ADVANCE clock copies those features into `inputs`; select layer 1.
7. Compute 30 dot products of 20 terms, with bias and ReLU: 600 MAC clocks.
8. One ADVANCE clock copies the 30 features into `inputs`; select layer 2.
9. Compute six dot products of 30 terms, with bias and no ReLU: 180 clocks.
10. The last edge completes all six delta words and raises `result_valid`.
    The result stays available until `result_ready` accepts it. The receiver
    then applies the cell mask/residual and post-writes elsewhere in the system.

The source therefore implies **1,862 enabled compute clocks per cell** with
one lane: 1,080 + 600 + 180 + two layer-transfer clocks. This excludes initial
request capture, configuration, neighborhood acquisition, result-retirement
bubbles and any pauses. It is a structural count, not a measured FPGA latency.

With four lanes, each input term is broadcast to four different output-feature
dot products. Output counts remain 20,30,6; groups become 5,8,2, including tails.
The corresponding structural count is 5*54 + 8*20 + 2*30 + 2 = 492 enabled
clocks. `LANES=4` does not evaluate four grid cells or four NCA epochs at once.

### A numeric example for one term

Take input 0.5 and kernel weight 0.25, with other dot-product contributions
zero and bias 0.125. These are invented teaching values, not model2 weights.

```text
input integer       = 0.5   * 2^24 = 8,388,608
coefficient integer = 0.25  * 2^22 = 1,048,576
product integer     =                  8,796,093,022,208  (F46)
bias integer        = 0.125 * 2^46 =    8,796,093,022,208
completed sum       =                 17,592,186,044,416
ReLU               = unchanged, because it is positive
requantize          = sum / 2^22 = 4,194,304             (F24)
decoded feature     = 4,194,304 / 2^24 = 0.25
```

`sums` preserves partial contributions until the entire dot product finishes.
`scratch` preserves that final feature until the next layer consumes it.
Only the eventual six-channel grid, outside this engine, persists between
NCA epochs and CartPole decisions.

## 6. The other files under `rtl`

| File | Algorithm or hardware role |
|---|---|
| `core/nca_round_sat.sv` | ReLU when enabled, signed shift-22 nearest-even conversion, and output saturation. Directly instantiated by `nca_local_rule`. |
| `core/nca_mac_stream.sv` | Separate reusable stream MAC primitive: exact products/subtotals and final-term bias. The current local-rule module implements its own per-lane arithmetic rather than instantiating this module. |
| `core/nca_guard_add.sv` | Guarded signed add/saturation useful for `old_cell + masked_delta` and marker additions. It is not yet wired into the local-rule module. |
| `core/nca_elastic_word.sv` | One-entry single-clock ready/valid buffer. Helps transport values during stalls; not the NCA grid memory or a clock-domain-crossing FIFO. |
| `core/nca_event_counter.sv` | Saturating diagnostic event counter. Does not implement event-triggered NCA learning/scheduling; its `fire` is a count-acceptance condition. |
| `core/nca_word_pack.sv` | Sign extension/validation between hardware words and wider comparison containers. Helps compare with NumPy int64 goldens; does not select the physical FPGA bus format. |
| `core/README.md` | Describes the primitives/local-rule boundary and verification status. |
| `wrappers/fpga/README.md` | Specifies where vendor memories, clocks, buses, DSP bindings and debug blocks must be isolated. No wrapper implementation is supplied here yet. |
| `wrappers/asic/README.md` | Specifies where technology-specific SRAM/clock/power/PDK wrappers belong. No ASIC implementation is supplied here yet. |

## 7. Fidelity and evidence boundaries

The three layer sizes, activations, biases, parameter count and neighborhood
ordering correspond to the published executable CartPole rule. The physical
reuse of arithmetic lanes adds control signals, addresses and scratch storage;
these are implementation mechanisms rather than extra learned features.

Two qualifications matter for reading this as software-to-hardware conversion:

1. The numbers use accepted fixed-point arithmetic, with explicit rounding and
   saturation. This is an approximation of float32, tested against an accepted
   integer golden; it is not a claim that the paper specifies these widths.
2. The engine trusts the caller's old-grid patch and zero padding. It cannot
   enforce full synchronous grid evolution by itself. Full controller
   equivalence requires correct grid storage, masks, residual, I/O rewrite,
   epoch commits and final action readout around this component.

The current implementation status reports Python scalar/image checks and generated testbenches,
while actual P08/P09 HDL compilation, simulation and synthesis remain pending.
This explanation inspects source intent; it does not certify synthesized
resource mapping, timing or complete FPGA CartPole behavior.
