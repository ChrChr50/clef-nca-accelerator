// One event per accepted transaction, never per stalled clock. Saturates itself.
module nca_event_counter #(parameter integer W=32) (
    input wire clk, rst, fire, event_in,
    output reg [W-1:0] count,
    output reg overflow
);
    always @(posedge clk) begin
        if (rst) begin count<=0; overflow<=0; end
        else if (fire && event_in) begin
            if (&count) overflow<=1;
            else count<=count+{{(W-1){1'b0}},1'b1};
        end
    end
endmodule
