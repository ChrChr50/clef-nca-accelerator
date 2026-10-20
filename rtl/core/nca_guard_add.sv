// Shared residual/marker primitive: full signed guard sum, then saturation.
module nca_guard_add #(parameter integer W=32) (
    input wire signed [W-1:0] lhs, rhs,
    input wire enable_rhs,
    output reg signed [W-1:0] result,
    output reg saturated
);
    localparam signed [W:0] HI = {2'b00,{(W-1){1'b1}}};
    localparam signed [W:0] LO = {2'b11,{(W-1){1'b0}}};
    reg signed [W:0] sum;
    always @* begin
        sum = $signed({lhs[W-1],lhs});
        if (enable_rhs) sum = sum + $signed({rhs[W-1],rhs});
        saturated=1'b0;
        if (sum>HI) begin result=HI[W-1:0]; saturated=1'b1; end
        else if (sum<LO) begin result=LO[W-1:0]; saturated=1'b1; end
        else result=sum[W-1:0];
    end
`ifndef SYNTHESIS
    initial assert (W>=2) else $fatal(1,"invalid state width");
`endif
endmodule
