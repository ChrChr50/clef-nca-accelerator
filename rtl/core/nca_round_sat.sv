module nca_round_sat #(
    parameter integer IN_W=62, OUT_W=32, SHIFT=22
) (
    input wire signed [IN_W-1:0] value,
    input wire relu,
    output reg signed [OUT_W-1:0] result,
    output reg saturated
);
    localparam signed [IN_W:0] output_maximum = ({{IN_W{1'b0}},1'b1} << (OUT_W-1))-1;
    localparam signed [IN_W:0] output_minimum = -({{IN_W{1'b0}},1'b1} << (OUT_W-1));
    localparam [IN_W:0] discarded_bit_mask = ({{IN_W{1'b0}},1'b1} << SHIFT)-1;
    localparam [IN_W:0] rounding_halfway = ({{IN_W{1'b0}},1'b1} << (SHIFT>0 ? SHIFT-1 : 0));
    reg signed [IN_W:0] extended_value, shifted_value, rounded_value;
    reg [IN_W:0] discarded_bits;
    always @* begin
        extended_value = {value[IN_W-1],value};
        if (relu && extended_value < 0) extended_value = 0;
        shifted_value = extended_value >>> SHIFT;
        discarded_bits = $unsigned(extended_value) & discarded_bit_mask;
        rounded_value = shifted_value;
        if (SHIFT>0 && ((discarded_bits>rounding_halfway) || ((discarded_bits==rounding_halfway) && shifted_value[0])))
            rounded_value = shifted_value + {{IN_W{1'b0}},1'b1};
        saturated = 1'b0;
        if (rounded_value>output_maximum) begin result=output_maximum[OUT_W-1:0];
        saturated=1'b1;
        end
        else if (rounded_value<output_minimum) begin result=output_minimum[OUT_W-1:0];
        saturated=1'b1;
        end
        else result=rounded_value[OUT_W-1:0];
    end
`ifndef SYNTHESIS
    initial begin
        assert (IN_W>=OUT_W && OUT_W>=2 && SHIFT>=0 && SHIFT<IN_W)
            else $fatal(1,"invalid requantization parameters");
    end
`endif
endmodule
