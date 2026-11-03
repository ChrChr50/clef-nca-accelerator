module nca_row_window #(
 parameter integer STATE_W=32, BANKS=4, COLS=32, CHANNELS=6,
 parameter integer BEATS=COLS/BANKS, BEAT_W=$clog2(BEATS)
)(
 input wire clk,rst,clear,
 input wire load_valid,
 input wire [4:0] load_row,
 input wire [BEAT_W-1:0] load_beat,
 input wire [BANKS*CHANNELS*STATE_W-1:0] load_data,
 input wire [4:0] center_row,
 input wire [31:0] term,
 output wire [COLS*STATE_W-1:0] operands,
 output reg ready
);

 reg [STATE_W-1:0] buffered_row_values[0:3*COLS*CHANNELS-1];
 reg [4:0] buffered_row_numbers[0:2];
 reg [2:0] buffered_row_valid;
 integer buffer_slot;
 always @(posedge clk) begin
  if(rst || clear) begin
   buffered_row_valid<=0;
   for(buffer_slot=0;buffer_slot<3;buffer_slot=buffer_slot+1) buffered_row_numbers[buffer_slot]<=0;
  end else if(load_valid) begin
   for(integer loaded_word=0;loaded_word<BANKS*CHANNELS;loaded_word=loaded_word+1)
    buffered_row_values[(load_row%3)*COLS*CHANNELS+load_beat*BANKS*CHANNELS+loaded_word]<=load_data[loaded_word*STATE_W +: STATE_W];
   buffered_row_numbers[load_row%3]<=load_row;
   if(load_beat==0) buffered_row_valid[load_row%3]<=0;
   if(load_beat==BEATS-1) buffered_row_valid[load_row%3]<=1;
  end
 end

 wire signed [31:0] neighbor_row=$signed({1'b0,center_row})+$signed(term/18)-1;
 wire signed [31:0] neighbor_column_offset=$signed((term/6)%3)-1;
 wire [31:0] neighbor_channel=term%6;
 always @* begin
  ready=1;
  for(integer required_row=0;required_row<32;required_row=required_row+1)
   if(required_row+1>=center_row && required_row<=center_row+1)
    if(!buffered_row_valid[required_row%3] || buffered_row_numbers[required_row%3]!=required_row) ready=0;
 end
 genvar grid_column;
 generate for(grid_column=0;grid_column<COLS;grid_column=grid_column+1) begin: columns
  wire signed [31:0] neighbor_column=grid_column+neighbor_column_offset;
  assign operands[grid_column*STATE_W +: STATE_W]=
   neighbor_row<0 || neighbor_row>=32 || neighbor_column<0 || neighbor_column>=COLS || term>=54 ?
   {STATE_W{1'b0}} : buffered_row_values[((neighbor_row%3)*COLS+neighbor_column)*CHANNELS+neighbor_channel];
 end endgenerate
`ifndef SYNTHESIS
 always @(posedge clk) if(!rst && load_valid) begin
  assert(!clear) else $fatal(1,"row load during invalidate");
  if(load_beat!=0) assert(buffered_row_numbers[load_row%3]==load_row)
   else $fatal(1,"unordered row load");
 end
`endif
endmodule
