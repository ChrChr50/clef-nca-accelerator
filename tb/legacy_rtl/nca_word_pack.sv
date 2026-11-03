// Comparison-container normalization, NOT a selected G5 wire format.
module nca_word_pack #(parameter integer W=32, CONTAINER_W=64) (
    input wire signed [W-1:0] word_in,
    input wire signed [CONTAINER_W-1:0] container_in,
    output wire signed [CONTAINER_W-1:0] container_out,
    output wire signed [W-1:0] word_out,
    output wire unpack_valid
);
    assign container_out = {{(CONTAINER_W-W){word_in[W-1]}},word_in};
    assign word_out = container_in[W-1:0];
    assign unpack_valid = container_in == $signed({{(CONTAINER_W-W){container_in[W-1]}},container_in[W-1:0]});
`ifndef SYNTHESIS
    initial assert (W>=2 && CONTAINER_W>=W) else $fatal(1,"invalid packing widths");
`endif
endmodule
