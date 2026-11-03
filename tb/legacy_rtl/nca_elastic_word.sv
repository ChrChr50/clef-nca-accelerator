// Single-clock one-entry ready/valid register; not a CDC or grid memory.
module nca_elastic_word #(parameter integer W=32) (
    input wire clk, rst, in_valid, out_ready,
    output wire in_ready,
    input wire [W-1:0] in_data,
    output reg out_valid,
    output reg [W-1:0] out_data
);
    assign in_ready = !rst && (!out_valid || out_ready);
    always @(posedge clk) begin
        if (rst) begin out_valid<=0; out_data<=0; end
        else if (in_ready) begin
            out_valid<=in_valid;
            if (in_valid) out_data<=in_data;
        end
    end
endmodule
