// P09 reversible folded local delta engine. No grid/RNG/mask/residual/IO.
module nca_local_rule #(parameter integer LANES=1) (
    input wire clk, rst, run_enable,
    input wire load_valid, load_bias,
    input wire [10:0] load_address,
    input wire signed [61:0] load_word,
    output wire load_ready,
    output reg load_error,
    input wire request_valid,
    input wire [54*32-1:0] patch_words,
    output wire request_ready,
    input wire result_ready,
    output reg result_valid,
    output reg [6*32-1:0] delta_words,
    output reg trace_valid,
    output reg [1:0] trace_layer,
    output reg [5:0] trace_base,
    output reg [LANES-1:0] trace_keep,
    output reg [LANES*62-1:0] trace_acc,
    output reg [LANES*32-1:0] trace_output,
    output reg [LANES-1:0] trace_acc_sat, trace_layer_sat,
    output reg [31:0] active_cycles
);
    localparam IDLE=0, MAC=1, ADVANCE=2;
    reg [1:0] mode, layer;
    integer fan, outputs, kernel_base, bias_base, term_index, output_base;
    integer config_count;
    reg configured;
    reg signed [23:0] kernels [0:1859];
    reg signed [61:0] biases [0:55];
    reg signed [31:0] inputs [0:53];
    reg signed [31:0] scratch [0:29];
    reg signed [61:0] sums [0:LANES-1];
    wire [LANES-1:0] lane_live, acc_sat, act_sat;
    wire signed [61:0] clipped [0:LANES-1];
    wire signed [31:0] activated [0:LANES-1];
    wire signed [62:0] partial [0:LANES-1];
    wire signed [62:0] biased [0:LANES-1];
    localparam signed [62:0] HI={2'b00,{61{1'b1}}};
    localparam signed [62:0] LO={2'b11,{61{1'b0}}};
    assign load_ready = !rst && mode==IDLE && !result_valid && config_count<1916;
    assign request_ready = !rst && run_enable && configured && mode==IDLE && !result_valid && !load_valid;
    genvar l;
    generate for(l=0;l<LANES;l=l+1) begin: lane
        assign lane_live[l] = output_base+l<outputs;
        wire signed [23:0] coefficient = (mode==MAC && lane_live[l]) ?
            kernels[kernel_base+term_index*outputs+output_base+l] : 24'sd0;
        wire signed [55:0] sx={{24{inputs[term_index][31]}},inputs[term_index]};
        wire signed [55:0] sw={{32{coefficient[23]}},coefficient};
        wire signed [55:0] product=sx*sw;
        wire signed [61:0] extended_product={{6{product[55]}},product};
        assign partial[l] = $signed({sums[l][61],sums[l]})+
            $signed({extended_product[61],extended_product});
        wire signed [61:0] selected_bias = (mode==MAC && lane_live[l]) ?
            biases[bias_base+output_base+l] : 62'sd0;
        assign biased[l] = partial[l]+$signed({selected_bias[61],selected_bias});
        assign acc_sat[l] = biased[l]>HI || biased[l]<LO;
        assign clipped[l] = biased[l]>HI ? HI[61:0] : biased[l]<LO ? LO[61:0] : biased[l][61:0];
        nca_round_sat requant(clipped[l],layer!=2,activated[l],act_sat[l]);
    end endgenerate
    integer i;
    always @(posedge clk) begin
        if(rst) begin
            mode<=IDLE;layer<=0;fan<=54;outputs<=20;kernel_base<=0;bias_base<=0;
            term_index<=0;output_base<=0;config_count<=0;configured<=0;
            result_valid<=0;delta_words<=0;trace_valid<=0;trace_keep<=0;
            load_error<=0;
            trace_layer<=0;trace_base<=0;trace_acc<=0;trace_output<=0;
            trace_acc_sat<=0;trace_layer_sat<=0;active_cycles<=0;
            for(i=0;i<LANES;i=i+1) sums[i]<=0;
            for(i=0;i<54;i=i+1) inputs[i]<=0;
            for(i=0;i<30;i=i+1) scratch[i]<=0;
        end else begin
            trace_valid<=0;
            load_error<=0;
            if(result_valid && result_ready) result_valid<=0;
            if(load_valid && load_ready) begin
                // Sequential complete configuration, kernel words then biases.
                if(config_count<1860 && !load_bias && load_address==config_count &&
                   load_word==$signed({{38{load_word[23]}},load_word[23:0]})) begin
                    kernels[load_address]<=load_word[23:0]; config_count<=config_count+1;
                end else if(config_count>=1860 && load_bias && load_address==config_count-1860) begin
                    biases[load_address]<=load_word;config_count<=config_count+1;
                    if(config_count==1915) configured<=1;
                end else load_error<=1;
            end
            if(request_valid && request_ready) begin
                for(i=0;i<54;i=i+1) inputs[i]<=patch_words[i*32+:32];
                for(i=0;i<LANES;i=i+1) sums[i]<=0;
                layer<=0;fan<=54;outputs<=20;kernel_base<=0;bias_base<=0;
                term_index<=0;output_base<=0;mode<=MAC;active_cycles<=0;
            end else if(run_enable && mode!=IDLE) begin
                active_cycles<=active_cycles+1;
                if(mode==MAC) begin
                    if(term_index==fan-1) begin
                        trace_valid<=1;trace_layer<=layer;trace_base<=output_base;
                        trace_keep<=lane_live;trace_acc_sat<=acc_sat & lane_live;
                        trace_layer_sat<=act_sat & lane_live;
                        for(i=0;i<LANES;i=i+1) begin
                            trace_acc[i*62+:62]<=clipped[i];trace_output[i*32+:32]<=activated[i];sums[i]<=0;
                            if(lane_live[i]) begin
                                if(layer==2) delta_words[(output_base+i)*32+:32]<=activated[i];
                                else scratch[output_base+i]<=activated[i];
                            end
                        end
                        term_index<=0;
                        if(output_base+LANES>=outputs) begin
                            if(layer==2) begin mode<=IDLE;result_valid<=1;end
                            else mode<=ADVANCE;
                        end else output_base<=output_base+LANES;
                    end else begin
                        for(i=0;i<LANES;i=i+1) sums[i]<=partial[i][61:0];
                        term_index<=term_index+1;
                    end
                end else begin
                    for(i=0;i<30;i=i+1) inputs[i]<=scratch[i];
                    layer<=layer+1;output_base<=0;
                    if(layer==0) begin fan<=20;outputs<=30;kernel_base<=1080;bias_base<=20;end
                    else begin fan<=30;outputs<=6;kernel_base<=1680;bias_base<=50;end
                    mode<=MAC;
                end
            end
        end
    end
`ifndef SYNTHESIS
    initial assert(LANES>=1 && LANES<=30) else $fatal(1,"invalid lane count");
    always @(posedge clk) if(!rst && mode==MAC && run_enable) begin
        for(integer j=0;j<LANES;j=j+1)
            if(lane_live[j]) assert(partial[j]<=HI && partial[j]>=LO)
                else $fatal(1,"unproved partial accumulator overflow");
    end
`endif
endmodule
