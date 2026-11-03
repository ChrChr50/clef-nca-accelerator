module nca_banked_state #(
    parameter integer ROWS=32, COLS=32, CHANNELS=6, STATE_W=16, BANKS=4,
    parameter integer ROW_W=$clog2(ROWS), BEAT_W=$clog2(COLS/BANKS)
) (
    input wire clk, rst,
    input wire wr_valid,
    input wire [ROW_W-1:0] wr_row,
    input wire [BEAT_W-1:0] wr_beat,
    input wire [BANKS*CHANNELS*STATE_W-1:0] wr_data,
    input wire rd_valid,
    output wire rd_ready,
    input wire [ROW_W-1:0] rd_row,
    input wire [BEAT_W-1:0] rd_beat,
    output reg resp_valid,
    output reg [ROW_W-1:0] resp_row,
    output reg [BEAT_W-1:0] resp_beat,
    output reg [BANKS*CHANNELS*STATE_W-1:0] resp_data
);
    localparam integer CELL_BITS=CHANNELS*STATE_W;
    localparam integer ROW_BEATS=COLS/BANKS;
    localparam integer WORDS_PER_BANK=ROWS*ROW_BEATS;
    wire same_address_collision=wr_valid && wr_row==rd_row && wr_beat==rd_beat;
    assign rd_ready=!rst && !same_address_collision;
    genvar bank_index;
    generate for (bank_index=0;bank_index<BANKS;bank_index=bank_index+1) begin: banks
        reg [CELL_BITS-1:0] cell_words [0:WORDS_PER_BANK-1];
        always @(posedge clk) begin
            if (!rst) begin
                if (wr_valid) cell_words[wr_row*ROW_BEATS+wr_beat]<=wr_data[bank_index*CELL_BITS +: CELL_BITS];
                if (rd_valid && rd_ready)
                    resp_data[bank_index*CELL_BITS +: CELL_BITS]<=cell_words[rd_row*ROW_BEATS+rd_beat];
            end
        end
    end endgenerate
    always @(posedge clk) begin
        if (rst) begin resp_valid<=0;
        resp_row<=0;
        resp_beat<=0;
        end
        else begin
            resp_valid<=rd_valid && rd_ready;
            if (rd_valid && rd_ready) begin resp_row<=rd_row;
            resp_beat<=rd_beat;
            end
        end
    end
`ifndef SYNTHESIS
    initial begin
        assert (ROWS>1 && COLS>1 && CHANNELS>0 && STATE_W>=2 && BANKS>0 && COLS%BANKS==0 && ROW_BEATS>1)
            else $fatal(1,"invalid banked-state geometry");
    end
    always @(posedge clk) if (!rst) begin
        if (wr_valid) assert (wr_row<ROWS && wr_beat<ROW_BEATS) else $fatal(1,"invalid write address");
        if (rd_valid) assert (rd_row<ROWS && rd_beat<ROW_BEATS) else $fatal(1,"invalid read address");
    end
`endif
endmodule
