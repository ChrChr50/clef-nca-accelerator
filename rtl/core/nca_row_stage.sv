module nca_row_stage #(
    parameter integer CELLS=32, INPUTS=20, OUTPUTS=30, LANES=24,
    parameter integer STATE_W=16, WEIGHT_W=16, ACC_W=48, FRACTION=12, USE_RELU=1,
    parameter integer TAG_W=21, STREAM_INPUT=0, MASK_SKIP=0, USE_STEP_ENABLE=0,
    parameter integer CFG_ADDR_W=$clog2(INPUTS*OUTPUTS+OUTPUTS)
) (
    input wire clk, rst,
    input wire cfg_valid, cfg_bias, cfg_commit,
    input wire [CFG_ADDR_W-1:0] cfg_addr,
    input wire signed [ACC_W-1:0] cfg_data,
    output wire cfg_ready,
    output reg configured, config_error,
    input wire req_valid,
    output wire req_ready,
    input wire [TAG_W-1:0] req_tag,
    input wire [CELLS*INPUTS*STATE_W-1:0] req_values,
    input wire [LANES*STATE_W-1:0] stream_values,
    input wire [CELLS-1:0] req_mask,
    input wire step_enable,
    output wire [31:0] operand_term, operand_slot,
    output reg resp_valid,
    input wire resp_ready,
    output reg [TAG_W-1:0] resp_tag,
    output reg [CELLS*OUTPUTS*STATE_W-1:0] resp_values,
    output reg [CELLS-1:0] resp_mask,
    output reg [31:0] active_cycles, accumulator_saturations, output_saturations, issued_macs
);
    localparam integer ROW_OUTPUT_WORDS=CELLS*OUTPUTS;
    localparam integer OUTPUTS_PER_LANE=(ROW_OUTPUT_WORDS+LANES-1)/LANES;
    localparam integer PRODUCT_BITS=STATE_W+WEIGHT_W;
    localparam integer DOT_PRODUCT_BITS=PRODUCT_BITS+$clog2(INPUTS);
    localparam integer GUARDED_ACCUMULATOR_BITS=(ACC_W>DOT_PRODUCT_BITS ? ACC_W : DOT_PRODUCT_BITS)+1;
    localparam signed [GUARDED_ACCUMULATOR_BITS-1:0] ACCUMULATOR_MAX=( {{(GUARDED_ACCUMULATOR_BITS-1){1'b0}},
        1'b1} << (ACC_W-1))-1;
    localparam signed [GUARDED_ACCUMULATOR_BITS-1:0] ACCUMULATOR_MIN=-( {{(GUARDED_ACCUMULATOR_BITS-1){1'b0}},
        1'b1} << (ACC_W-1));
    reg signed [WEIGHT_W-1:0] kernel_weights [0:INPUTS*OUTPUTS-1];
    reg signed [ACC_W-1:0] neuron_biases [0:OUTPUTS-1];
    reg [INPUTS*OUTPUTS+OUTPUTS-1:0] coefficient_loaded;
    wire [LANES*STATE_W-1:0] lane_input_values;
    reg signed [GUARDED_ACCUMULATOR_BITS-1:0] lane_accumulators [0:LANES-1];
    reg calculating_row;
    integer input_feature_index, output_slot, lane_index;
    wire [LANES-1:0] lane_has_output, lane_updates_enabled, accumulator_overflow, activation_overflow;
    wire signed [GUARDED_ACCUMULATOR_BITS-1:0] accumulated_product [0:LANES-1];
    wire signed [STATE_W-1:0] quantized_activation [0:LANES-1];
    integer accumulator_overflow_count, activation_overflow_count, active_lane_count;
    wire clock_enabled=!USE_STEP_ENABLE || step_enable;
    assign operand_term=input_feature_index;
    assign operand_slot=output_slot;

    assign cfg_ready=!rst && !configured && !calculating_row && !resp_valid && !req_valid;
    assign req_ready=!rst && clock_enabled && configured && !calculating_row && (!resp_valid || resp_ready)
                     && !cfg_valid && !cfg_commit;

    genvar input_lane;
    generate if (!STREAM_INPUT) begin: captured
        reg [STATE_W-1:0] captured_features [0:CELLS*INPUTS-1];
        always @(posedge clk) begin
            if (rst) begin
                for(integer feature_word=0;feature_word<CELLS*INPUTS;
                    feature_word=feature_word+1) captured_features[feature_word]<=0;
            end else if (req_valid && req_ready) begin
                for(integer feature_word=0;feature_word<CELLS*INPUTS;
                    feature_word=feature_word+1) captured_features[feature_word]<=req_values[feature_word*STATE_W
                    +: STATE_W];
            end
        end
        for(input_lane=0;input_lane<LANES;input_lane=input_lane+1) begin: read_words
            wire [31:0] cell_index=(input_lane*OUTPUTS_PER_LANE+output_slot)/OUTPUTS;
            assign lane_input_values[input_lane*STATE_W
                +: STATE_W]=captured_features[cell_index*INPUTS+input_feature_index];
        end
    end else begin: streamed
        assign lane_input_values=stream_values;
    end endgenerate

    wire signed [WEIGHT_W-1:0] shared_weight [0:2];
    wire signed [ACC_W-1:0] shared_bias [0:2];
    genvar broadcast_group;
    generate for (broadcast_group=0;broadcast_group<3;broadcast_group=broadcast_group+1) begin: broadcasts
        if (CELLS==32 && INPUTS==20 && OUTPUTS==30 && LANES==24) begin: dense_one
            wire [31:0] output_neuron=(output_slot+10*broadcast_group)%30;
            assign shared_weight[broadcast_group]=kernel_weights[output_neuron*INPUTS+input_feature_index];
            assign shared_bias[broadcast_group]=neuron_biases[output_neuron];
        end else if (broadcast_group==0 && ((INPUTS==54 && OUTPUTS==20 && LANES==CELLS) ||
                                       (CELLS==32 && INPUTS==30 && OUTPUTS==6 && LANES==8))) begin: common
            wire [31:0] output_neuron=output_slot%OUTPUTS;
            assign shared_weight[broadcast_group]=kernel_weights[output_neuron*INPUTS+input_feature_index];
            assign shared_bias[broadcast_group]=neuron_biases[output_neuron];
        end else begin: unused_group
            assign shared_weight[broadcast_group]=0;
            assign shared_bias[broadcast_group]=0;
        end
    end endgenerate

    genvar mac_lane;
    generate for (mac_lane=0;mac_lane<LANES;mac_lane=mac_lane+1) begin: arithmetic
        wire [31:0] output_word_index=mac_lane*OUTPUTS_PER_LANE+output_slot;
        wire [31:0] cell_index=output_word_index/OUTPUTS;
        wire [31:0] output_neuron=output_word_index%OUTPUTS;
        assign lane_has_output[mac_lane]=output_word_index<ROW_OUTPUT_WORDS;
        assign lane_updates_enabled[mac_lane]=lane_has_output[mac_lane] && (!MASK_SKIP || resp_mask[cell_index]);
        wire signed [STATE_W-1:0] selected_operand=$signed(lane_input_values[mac_lane*STATE_W +: STATE_W]);
        wire signed [STATE_W-1:0] operand=lane_updates_enabled[mac_lane] ? selected_operand : {STATE_W{1'b0}};
        wire signed [WEIGHT_W-1:0] raw_coefficient;
        wire signed [ACC_W-1:0] raw_bias;
        if (CELLS==32 && INPUTS==20 && OUTPUTS==30 && LANES==24) begin: grouped_read
            assign raw_coefficient=shared_weight[mac_lane%3];
            assign raw_bias=shared_bias[mac_lane%3];
        end else if ((INPUTS==54 && OUTPUTS==20 && LANES==CELLS) ||
                     (CELLS==32 && INPUTS==30 && OUTPUTS==6 && LANES==8)) begin: broadcast_read
            assign raw_coefficient=shared_weight[0];
            assign raw_bias=shared_bias[0];
        end else begin: generic_read
            assign raw_coefficient=lane_has_output[mac_lane]
                ? kernel_weights[output_neuron*INPUTS+input_feature_index] : {WEIGHT_W{1'b0}};
            assign raw_bias=lane_has_output[mac_lane] ? neuron_biases[output_neuron] : {ACC_W{1'b0}};
        end
        wire signed [WEIGHT_W-1:0] coefficient=lane_updates_enabled[mac_lane] ? raw_coefficient : {WEIGHT_W{1'b0}};
        wire signed [PRODUCT_BITS-1:0] product=operand*coefficient;
        wire signed [GUARDED_ACCUMULATOR_BITS-1:0] extended_product={{(GUARDED_ACCUMULATOR_BITS-PRODUCT_BITS){product[PRODUCT_BITS-1]}},product};
        wire signed [ACC_W-1:0] selected_bias=lane_updates_enabled[mac_lane] ? raw_bias : {ACC_W{1'b0}};
        wire signed [GUARDED_ACCUMULATOR_BITS-1:0] extended_bias={{(GUARDED_ACCUMULATOR_BITS-ACC_W){selected_bias[ACC_W-1]}},selected_bias};
        assign accumulated_product[mac_lane]=lane_accumulators[mac_lane]+extended_product;
        wire signed [GUARDED_ACCUMULATOR_BITS-1:0] final_sum=accumulated_product[mac_lane]+extended_bias;
        assign accumulator_overflow[mac_lane]=lane_updates_enabled[mac_lane] && (final_sum>ACCUMULATOR_MAX
            || final_sum<ACCUMULATOR_MIN);
        wire signed [ACC_W-1:0] clipped_acc=final_sum>ACCUMULATOR_MAX ? ACCUMULATOR_MAX[ACC_W-1:0] :
            final_sum<ACCUMULATOR_MIN ? ACCUMULATOR_MIN[ACC_W-1:0] : final_sum[ACC_W-1:0];
        nca_round_sat #(.IN_W(ACC_W),.OUT_W(STATE_W),.SHIFT(FRACTION)) requantize (
            .value(clipped_acc),.relu(USE_RELU!=0),.result(quantized_activation[mac_lane]),
                .saturated(activation_overflow[mac_lane]));
    end endgenerate

    always @* begin
        accumulator_overflow_count=0;
        activation_overflow_count=0;
        active_lane_count=0;
        for (integer counted_lane=0;counted_lane<LANES;
            counted_lane=counted_lane+1) if (lane_updates_enabled[counted_lane]) begin
            active_lane_count=active_lane_count+1;
            accumulator_overflow_count=accumulator_overflow_count+accumulator_overflow[counted_lane];
            activation_overflow_count=activation_overflow_count+activation_overflow[counted_lane];
        end
    end

    always @(posedge clk) begin
        if (rst) begin
            calculating_row<=0;
            resp_valid<=0;
            configured<=0;
            config_error<=0;
            coefficient_loaded<=0;
            input_feature_index<=0;
            output_slot<=0;
            resp_values<=0;
            resp_tag<=0;
            resp_mask<=0;
            issued_macs<=0;
            active_cycles<=0;
            accumulator_saturations<=0;
            output_saturations<=0;
            for (lane_index=0;lane_index<LANES;lane_index=lane_index+1) lane_accumulators[lane_index]<=0;
        end else begin
            if (resp_valid && resp_ready && clock_enabled) resp_valid<=0;
            if (cfg_ready && cfg_valid) begin
                configured<=0;
                if (cfg_bias && cfg_addr<OUTPUTS) begin
                    neuron_biases[cfg_addr]<=cfg_data;
                    coefficient_loaded[INPUTS*OUTPUTS+cfg_addr]<=1;
                end else if (!cfg_bias && cfg_addr<INPUTS*OUTPUTS) begin
                    kernel_weights[cfg_addr]<=cfg_data[WEIGHT_W-1:0];
                    coefficient_loaded[cfg_addr]<=1;
                end else config_error<=1;
            end else if (cfg_ready && cfg_commit) begin
                configured<=&coefficient_loaded;
                if (!(&coefficient_loaded)) config_error<=1;
            end
            if (req_valid && req_ready) begin
                resp_tag<=req_tag;
                resp_values<=0;
                resp_mask<=req_mask;
                issued_macs<=0;
                calculating_row<=1;
                input_feature_index<=0;
                output_slot<=0;
                active_cycles<=0;
                accumulator_saturations<=0;
                output_saturations<=0;
                for (lane_index=0;lane_index<LANES;lane_index=lane_index+1) lane_accumulators[lane_index]<=0;
            end else if (calculating_row && clock_enabled) begin
                issued_macs<=issued_macs+active_lane_count;
                active_cycles<=active_cycles+1;
                if (input_feature_index==INPUTS-1) begin
                    accumulator_saturations<=accumulator_saturations+accumulator_overflow_count;
                    output_saturations<=output_saturations+activation_overflow_count;
                    for (lane_index=0;lane_index<LANES;lane_index=lane_index+1) begin
                        if (lane_has_output[lane_index]) resp_values[(lane_index*OUTPUTS_PER_LANE+output_slot)*STATE_W +: STATE_W]<=quantized_activation[lane_index];
                        lane_accumulators[lane_index]<=0;
                    end
                    input_feature_index<=0;
                    if (output_slot==OUTPUTS_PER_LANE-1) begin calculating_row<=0;
                    resp_valid<=1;
                    end
                    else output_slot<=output_slot+1;
                end else begin
                    for (lane_index=0;lane_index<LANES;lane_index=lane_index+1)
                        if (lane_updates_enabled[lane_index]) lane_accumulators[lane_index]<=accumulated_product[lane_index];
                    input_feature_index<=input_feature_index+1;
                end
            end
        end
    end
`ifndef SYNTHESIS
    initial begin
        assert (CELLS>0 && INPUTS>0 && OUTPUTS>0 && LANES>0 && LANES<=ROW_OUTPUT_WORDS)
            else $fatal(1,"invalid row geometry");
        assert (STATE_W>=2 && WEIGHT_W>=2 && ACC_W>=PRODUCT_BITS && FRACTION>0 && FRACTION<ACC_W)
            else $fatal(1,"invalid row arithmetic widths");
    end
`endif
endmodule
