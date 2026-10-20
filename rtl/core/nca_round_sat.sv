// Signed nearest-even requantization. ReLU precedes rounding and clipping.
module nca_round_sat #(
    parameter integer IN_W=62, OUT_W=32, SHIFT=22
) (
    input wire signed [IN_W-1:0] value,
    input wire relu,
    output reg signed [OUT_W-1:0] result,
    output reg saturated
);
    localparam signed [IN_W:0] HI = ({{IN_W{1'b0}},1'b1} << (OUT_W-1))-1;
    localparam signed [IN_W:0] LO = -({{IN_W{1'b0}},1'b1} << (OUT_W-1));
    localparam [IN_W:0] REM_MASK = ({{IN_W{1'b0}},1'b1} << SHIFT)-1;
    localparam [IN_W:0] HALF = ({{IN_W{1'b0}},1'b1} << (SHIFT>0 ? SHIFT-1 : 0));
    reg signed [IN_W:0] wide, quotient, rounded;
    reg [IN_W:0] remainder;
    always @* begin
        wide = {value[IN_W-1],value};
        if (relu && wide < 0) wide = 0;
        quotient = wide >>> SHIFT;
        remainder = $unsigned(wide) & REM_MASK;
        rounded = quotient;
        if (SHIFT>0 && ((remainder>HALF) || ((remainder==HALF) && quotient[0])))
            rounded = quotient + {{IN_W{1'b0}},1'b1};
        saturated = 1'b0;
        if (rounded>HI) begin result=HI[OUT_W-1:0]; saturated=1'b1; end
        else if (rounded<LO) begin result=LO[OUT_W-1:0]; saturated=1'b1; end
        else result=rounded[OUT_W-1:0];
    end
`ifndef SYNTHESIS
    initial begin
        assert (IN_W>=OUT_W && OUT_W>=2 && SHIFT>=0 && SHIFT<IN_W)
            else $fatal(1,"invalid requantization parameters");
    end
`endif
endmodule
