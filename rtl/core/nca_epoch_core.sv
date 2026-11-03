module nca_epoch_core #(
 parameter integer STATE_W=32, WEIGHT_W=24, ACC_W=62, FRACTION=22,
 parameter integer STATE_FRACTION=24, MASK_SKIP=1,
 parameter integer BW=4*6*STATE_W
)(
 input wire clk,rst,step_enable,
 input wire [1:0] cfg_layer,
 input wire cfg_valid,cfg_bias,cfg_commit,
 input wire [10:0] cfg_addr,
 input wire signed [ACC_W-1:0] cfg_data,
 output wire cfg_ready,configured,config_error,

 input wire host_write,host_read,
 input wire [4:0] host_row,
 input wire [2:0] host_beat,
 input wire [BW-1:0] host_data,
 output wire host_ready,
 output wire host_response,
 output wire [BW-1:0] host_result,
 input wire start_valid,
 output wire start_ready,
 input wire [1023:0] update_mask,
 input wire [8*STATE_W-1:0] observations,
 output reg busy,done,
 output reg row_commit,
 output reg [4:0] committed_row,
 output reg [15:0] epoch,
 output reg [31:0] cycles,issued_macs,frontend_reads,writeback_reads,grid_writes,
 output reg [31:0] residual_saturations,marker_saturations,
 output reg [31:0] accumulator_saturations,output_saturations
);
 localparam integer STATE_BITS=STATE_W;
 localparam integer FETCH_IDLE=0,FETCH_ROWS=1,START_CONVOLUTION=2,WAIT_FOR_CONVOLUTION=3,ALL_ROWS_FETCHED=4;
 localparam integer WRITEBACK_IDLE=0,WAIT_FOR_OLD_ROW_RELEASE=1,READ_OLD_CENTER_ROW=2,COMMIT_ROW=3;
 reg [2:0] fetch_state;
 reg [1:0] writeback_state;
 reg [4:0] convolution_row,next_old_row,writeback_row;
 reg loading_initial_rows;
 reg [3:0] window_beats_requested,window_beats_received,old_row_beats_requested,old_row_beats_received,commit_beat;
 reg [31:0] old_row_released,row_committed;
 reg [5:0] committed_row_count;
 reg [255:0] grid_beat_loaded;
 reg [1023:0] epoch_update_mask;
 reg [8*STATE_BITS-1:0] held_observations;
 reg [32*6*STATE_BITS-1:0] pending_delta_row,writeback_old_row;
 reg [31:0] writeback_update_mask;
 wire epoch_start_accepted=start_valid && start_ready;
 assign start_ready=!rst && !busy && configured && (&grid_beat_loaded) && !host_write && !host_read;
 assign host_ready=!rst && !busy && !start_valid;

 wire [2:0] layer_config_ready,layer_configured,layer_config_error;
 assign configured=&layer_configured;
 assign config_error=|layer_config_error;
 assign cfg_ready=!busy && cfg_layer<3 && layer_config_ready[cfg_layer];
 wire convolution_result_valid,convolution_request_ready,dense1_result_valid,dense1_request_ready,
     dense2_result_valid,writeback_ready;
 wire [20:0] convolution_row_tag,dense1_row_tag,dense2_row_tag;
 wire [32*20*STATE_BITS-1:0] convolution_features;
 wire [32*30*STATE_BITS-1:0] dense1_features;
 wire [32*6*STATE_BITS-1:0] delta_features;
 wire [31:0] convolution_update_mask,dense1_update_mask,dense2_update_mask,convolution_input_index,
     convolution_output_slot;
 wire [31:0] convolution_accumulator_saturations,convolution_output_saturations,dense1_accumulator_saturations,
     dense1_output_saturations,dense2_accumulator_saturations,dense2_output_saturations,convolution_macs,
     dense1_macs,dense2_macs;
 wire [32*STATE_BITS-1:0] neighborhood_values;
 wire neighborhood_ready;
 wire convolution_request_valid=busy && fetch_state==START_CONVOLUTION && neighborhood_ready && step_enable;
 wire dense1_request_valid=convolution_result_valid && step_enable;
 wire dense2_request_valid=dense1_result_valid && step_enable;
 assign writeback_ready=busy && writeback_state==WRITEBACK_IDLE && step_enable;
 wire convolution_result_ready=dense1_request_ready && step_enable;
 wire dense1_result_ready=dense2_request_ready && step_enable;
 wire dense2_request_ready;

 nca_row_stage #(.INPUTS(54),.OUTPUTS(20),.LANES(32),.STATE_W(STATE_BITS),
  .WEIGHT_W(WEIGHT_W),.ACC_W(ACC_W),.FRACTION(FRACTION),.STREAM_INPUT(1),
  .MASK_SKIP(MASK_SKIP),.USE_STEP_ENABLE(1)) convolution (
  .clk(clk),.rst(rst),.cfg_valid(cfg_valid && cfg_layer==0 && !busy),
  .cfg_bias(cfg_bias),.cfg_commit(cfg_commit && cfg_layer==0 && !busy),
  .cfg_addr(cfg_addr),.cfg_data(cfg_data),.cfg_ready(layer_config_ready[0]),.configured(layer_configured[0]),
      .config_error(layer_config_error[0]),
  .req_valid(convolution_request_valid),.req_ready(convolution_request_ready),.req_tag({epoch,convolution_row}),
      .req_values({(32*54*STATE_BITS){1'b0}}),
  .stream_values(neighborhood_values),.req_mask(epoch_update_mask[convolution_row*32 +: 32]),.step_enable(step_enable),
  .operand_term(convolution_input_index),.operand_slot(convolution_output_slot),
      .resp_valid(convolution_result_valid),.resp_ready(convolution_result_ready),
  .resp_tag(convolution_row_tag),.resp_values(convolution_features),.resp_mask(convolution_update_mask),
      .active_cycles(),
  .accumulator_saturations(convolution_accumulator_saturations),.output_saturations(convolution_output_saturations),
      .issued_macs(convolution_macs));
 nca_row_stage #(.INPUTS(20),.OUTPUTS(30),.LANES(24),.STATE_W(STATE_BITS),
  .WEIGHT_W(WEIGHT_W),.ACC_W(ACC_W),.FRACTION(FRACTION),.MASK_SKIP(MASK_SKIP),.USE_STEP_ENABLE(1)) dense_one (
  .clk(clk),.rst(rst),.cfg_valid(cfg_valid && cfg_layer==1 && !busy),
  .cfg_bias(cfg_bias),.cfg_commit(cfg_commit && cfg_layer==1 && !busy),
  .cfg_addr(cfg_addr[9:0]),.cfg_data(cfg_data),.cfg_ready(layer_config_ready[1]),.configured(layer_configured[1]),
      .config_error(layer_config_error[1]),
  .req_valid(dense1_request_valid),.req_ready(dense1_request_ready),.req_tag(convolution_row_tag),
      .req_values(convolution_features),
  .stream_values({(24*STATE_BITS){1'b0}}),.req_mask(convolution_update_mask),.step_enable(step_enable),
      .operand_term(),.operand_slot(),
  .resp_valid(dense1_result_valid),.resp_ready(dense1_result_ready),.resp_tag(dense1_row_tag),
      .resp_values(dense1_features),.resp_mask(dense1_update_mask),.active_cycles(),
  .accumulator_saturations(dense1_accumulator_saturations),.output_saturations(dense1_output_saturations),
      .issued_macs(dense1_macs));
 nca_row_stage #(.INPUTS(30),.OUTPUTS(6),.LANES(8),.STATE_W(STATE_BITS),.USE_RELU(0),
  .WEIGHT_W(WEIGHT_W),.ACC_W(ACC_W),.FRACTION(FRACTION),.MASK_SKIP(MASK_SKIP),.USE_STEP_ENABLE(1)) dense_two (
  .clk(clk),.rst(rst),.cfg_valid(cfg_valid && cfg_layer==2 && !busy),
  .cfg_bias(cfg_bias),.cfg_commit(cfg_commit && cfg_layer==2 && !busy),
  .cfg_addr(cfg_addr[7:0]),.cfg_data(cfg_data),.cfg_ready(layer_config_ready[2]),.configured(layer_configured[2]),
      .config_error(layer_config_error[2]),
  .req_valid(dense2_request_valid),.req_ready(dense2_request_ready),.req_tag(dense1_row_tag),
      .req_values(dense1_features),
  .stream_values({(8*STATE_BITS){1'b0}}),.req_mask(dense1_update_mask),.step_enable(step_enable),.operand_term(),
      .operand_slot(),
  .resp_valid(dense2_result_valid),.resp_ready(writeback_ready),.resp_tag(dense2_row_tag),
      .resp_values(delta_features),.resp_mask(dense2_update_mask),.active_cycles(),
  .accumulator_saturations(dense2_accumulator_saturations),.output_saturations(dense2_output_saturations),
      .issued_macs(dense2_macs));

 wire writeback_read_requested=busy && writeback_state==READ_OLD_CENTER_ROW && old_row_beats_requested<8 && step_enable;
 wire window_read_requested=busy && fetch_state==FETCH_ROWS && window_beats_requested<8 && step_enable;
 wire grid_read_valid=writeback_read_requested || window_read_requested || (host_read && host_ready);
 wire [4:0] grid_read_row=writeback_read_requested ? writeback_row : window_read_requested ? next_old_row : host_row;
 wire [2:0] grid_read_beat=writeback_read_requested ? old_row_beats_requested[2:0] : window_read_requested
     ? window_beats_requested[2:0] : host_beat;
 wire grid_read_ready,grid_response_valid;
 wire [4:0] grid_response_row;
 wire [2:0] grid_response_beat;
 wire [BW-1:0] grid_response_data;
 reg [1:0] pending_read_owner;
 wire commit_write_valid=busy && writeback_state==COMMIT_ROW && step_enable;
 wire grid_write_valid=commit_write_valid || (host_write && host_ready);
 wire [4:0] grid_write_row=commit_write_valid ? writeback_row : host_row;
 wire [2:0] grid_write_beat=commit_write_valid ? commit_beat[2:0] : host_beat;
 wire [BW-1:0] committed_cell_values;
 nca_banked_state #(.STATE_W(STATE_BITS)) grid (
  .clk(clk),.rst(rst),.wr_valid(grid_write_valid),.wr_row(grid_write_row),.wr_beat(grid_write_beat),
  .wr_data(commit_write_valid ? committed_cell_values : host_data),.rd_valid(grid_read_valid),
      .rd_ready(grid_read_ready),
  .rd_row(grid_read_row),.rd_beat(grid_read_beat),.resp_valid(grid_response_valid),.resp_row(grid_response_row),
  .resp_beat(grid_response_beat),.resp_data(grid_response_data));
 assign host_response=grid_response_valid && pending_read_owner==0;
 assign host_result=grid_response_data;
 nca_row_window #(.STATE_W(STATE_BITS)) window (
  .clk(clk),.rst(rst),.clear(epoch_start_accepted),.load_valid(grid_response_valid && pending_read_owner==1),
  .load_row(grid_response_row),.load_beat(grid_response_beat),.load_data(grid_response_data),
      .center_row(convolution_row),
  .term(convolution_input_index),.operands(neighborhood_values),.ready(neighborhood_ready));

 function integer observation_site_index(input integer cell_location);
  case(cell_location)
   378:observation_site_index=0;
   820:observation_site_index=1;
   180:observation_site_index=2;
   614:observation_site_index=3;
   634:observation_site_index=4;
   172:observation_site_index=5;
   812:observation_site_index=6;
   358:observation_site_index=7;
   default:observation_site_index=-1;
  endcase
 endfunction
 localparam signed [STATE_BITS:0] STATE_MAX=( { {(STATE_BITS){1'b0}},1'b1} << (STATE_BITS-1))-1;
 localparam signed [STATE_BITS:0] STATE_MIN=-( { {(STATE_BITS){1'b0}},1'b1} << (STATE_BITS-1));
 localparam signed [STATE_BITS-1:0] FIXED_ONE=1<<STATE_FRACTION;
 wire [23:0] residual_overflow_flags,marker_overflow_flags;
 genvar beat_word;
 generate for(beat_word=0;beat_word<24;beat_word=beat_word+1) begin: postwrite
  wire [31:0] cell_column=commit_beat*4+beat_word/6;
  wire [31:0] channel_word_index=cell_column*6+beat_word%6;
  wire [31:0] cell_location=writeback_row*32+cell_column;
  wire signed [STATE_BITS-1:0] previous_value=writeback_old_row[channel_word_index*STATE_BITS +: STATE_BITS];
  wire signed [STATE_BITS-1:0] masked_delta=writeback_update_mask[cell_column]
      ? $signed(pending_delta_row[channel_word_index*STATE_BITS +: STATE_BITS]) : {STATE_BITS{1'b0}};
  wire signed [STATE_BITS:0] residual_sum=$signed({previous_value[STATE_BITS-1],
      previous_value})+$signed({masked_delta[STATE_BITS-1],masked_delta});
  wire signed [STATE_BITS-1:0] clipped_residual=residual_sum>STATE_MAX ? STATE_MAX[STATE_BITS-1:0]
      : residual_sum<STATE_MIN ? STATE_MIN[STATE_BITS-1:0] : residual_sum[STATE_BITS-1:0];
  assign residual_overflow_flags[beat_word]=residual_sum>STATE_MAX || residual_sum<STATE_MIN;
  wire is_output_cell=cell_location==432 || cell_location==560;
  wire signed [STATE_BITS:0] marker_sum=$signed({clipped_residual[STATE_BITS-1],
      clipped_residual})+$signed({FIXED_ONE[STATE_BITS-1],FIXED_ONE});
  wire signed [STATE_BITS-1:0] clipped_marker=marker_sum>STATE_MAX ? STATE_MAX[STATE_BITS-1:0]
      : marker_sum<STATE_MIN ? STATE_MIN[STATE_BITS-1:0] : marker_sum[STATE_BITS-1:0];
  assign marker_overflow_flags[beat_word]=is_output_cell && beat_word%6>=4 && (marker_sum>STATE_MAX
      || marker_sum<STATE_MIN);
  wire signed [31:0] observation_index=observation_site_index(cell_location);
  wire [STATE_BITS-1:0] rewritten_input_value=beat_word%6==0 ? held_observations[observation_index*STATE_BITS
      +: STATE_BITS] :
      (beat_word%6==1 || beat_word%6==2 || beat_word%6==4 || beat_word%6==5) ? FIXED_ONE : {STATE_BITS{1'b0}};
  assign committed_cell_values[beat_word*STATE_BITS +: STATE_BITS]=observation_index>=0 ? rewritten_input_value :
    is_output_cell && beat_word%6>=4 ? clipped_marker : is_output_cell && beat_word%6==3 ? FIXED_ONE :
    beat_word%6==2 || beat_word%6==3 ? {STATE_BITS{1'b0}} : clipped_residual;
 end endgenerate
 integer beat_residual_saturations,beat_marker_saturations;
 always @* begin
  beat_residual_saturations=0;
  beat_marker_saturations=0;
  for(integer saturation_word=0;saturation_word<24;saturation_word=saturation_word+1) begin
   beat_residual_saturations=beat_residual_saturations+residual_overflow_flags[saturation_word];
   beat_marker_saturations=beat_marker_saturations+marker_overflow_flags[saturation_word];
  end
 end
 always @(posedge clk) begin
  if(rst) begin
   busy<=0;
   done<=0;
   fetch_state<=FETCH_IDLE;
   writeback_state<=WRITEBACK_IDLE;
   grid_beat_loaded<=0;
   epoch<=0;
   pending_read_owner<=0;
   old_row_released<=0;
   row_committed<=0;
   committed_row_count<=0;
   convolution_row<=0;
   next_old_row<=0;
   writeback_row<=0;
   window_beats_requested<=0;
   window_beats_received<=0;
   old_row_beats_requested<=0;
   old_row_beats_received<=0;
   commit_beat<=0;
   loading_initial_rows<=0;
   epoch_update_mask<=0;
   held_observations<=0;
   pending_delta_row<=0;
   writeback_old_row<=0;
   writeback_update_mask<=0;
   row_commit<=0;
   committed_row<=0;
   cycles<=0;
   issued_macs<=0;
   frontend_reads<=0;
   writeback_reads<=0;
   grid_writes<=0;
   residual_saturations<=0;
   marker_saturations<=0;
   accumulator_saturations<=0;
   output_saturations<=0;
  end else begin
   done<=0;
   row_commit<=0;
   if(host_write && host_ready) grid_beat_loaded[host_row*8+host_beat]<=1;
   if(grid_read_valid && grid_read_ready) begin
    pending_read_owner<=writeback_read_requested ? 2 : window_read_requested ? 1 : 0;
    if(writeback_read_requested) begin old_row_beats_requested<=old_row_beats_requested+1;
    writeback_reads<=writeback_reads+1;
    end
    else if(window_read_requested) begin window_beats_requested<=window_beats_requested+1;
    frontend_reads<=frontend_reads+1;
    end
   end

   if(grid_response_valid && pending_read_owner==1) window_beats_received<=window_beats_received+1;
   if(grid_response_valid && pending_read_owner==2) begin
    writeback_old_row[grid_response_beat*BW +: BW]<=grid_response_data;
    old_row_beats_received<=old_row_beats_received+1;
   end
   if(epoch_start_accepted) begin
    busy<=1;
    epoch<=epoch+1;
    fetch_state<=FETCH_ROWS;
    writeback_state<=WRITEBACK_IDLE;
    convolution_row<=0;
    next_old_row<=0;
    loading_initial_rows<=1;
    window_beats_requested<=0;
    window_beats_received<=0;
    committed_row_count<=0;
    old_row_released<=0;
    row_committed<=0;
    epoch_update_mask<=update_mask;
    held_observations<=observations;
    cycles<=0;
    issued_macs<=0;
    frontend_reads<=0;
    writeback_reads<=0;
    grid_writes<=0;
    residual_saturations<=0;
    marker_saturations<=0;
    accumulator_saturations<=0;
    output_saturations<=0;
   end else if(busy) begin
    cycles<=cycles+1;
    if(step_enable) begin
     case(fetch_state)
      FETCH_ROWS:if(window_beats_received==8) begin
       if(loading_initial_rows && next_old_row==0) begin next_old_row<=1;
       window_beats_requested<=0;
       window_beats_received<=0;
       end
       else begin loading_initial_rows<=0;
       fetch_state<=START_CONVOLUTION;
       end
      end
      START_CONVOLUTION:if(convolution_request_valid && convolution_request_ready) fetch_state<=WAIT_FOR_CONVOLUTION;
      WAIT_FOR_CONVOLUTION:if(convolution_result_valid && convolution_row_tag=={epoch,convolution_row}) begin
       if(convolution_row>0) old_row_released[convolution_row-1]<=1;
       if(convolution_row==31) begin old_row_released[31]<=1;
       fetch_state<=ALL_ROWS_FETCHED;
       end
       else begin
        convolution_row<=convolution_row+1;
        if(convolution_row<30) begin next_old_row<=convolution_row+2;
        window_beats_requested<=0;
        window_beats_received<=0;
        fetch_state<=FETCH_ROWS;
        end
        else fetch_state<=START_CONVOLUTION;
       end
      end
      default:begin end
     endcase

     issued_macs<=issued_macs+(convolution_result_valid && convolution_result_ready
         ? convolution_macs:0)+(dense1_result_valid && dense1_result_ready ? dense1_macs:0)+(dense2_result_valid
         && writeback_ready ? dense2_macs:0);
     accumulator_saturations<=accumulator_saturations+(convolution_result_valid && convolution_result_ready
         ? convolution_accumulator_saturations:0)+(dense1_result_valid && dense1_result_ready
         ? dense1_accumulator_saturations:0)+(dense2_result_valid && writeback_ready
         ? dense2_accumulator_saturations:0);
     output_saturations<=output_saturations+(convolution_result_valid && convolution_result_ready
         ? convolution_output_saturations:0)+(dense1_result_valid && dense1_result_ready
         ? dense1_output_saturations:0)+(dense2_result_valid && writeback_ready ? dense2_output_saturations:0);
     case(writeback_state)
      WRITEBACK_IDLE:if(dense2_result_valid && writeback_ready) begin
       pending_delta_row<=delta_features;
       writeback_update_mask<=dense2_update_mask;
       writeback_row<=dense2_row_tag[4:0];
       writeback_state<=WAIT_FOR_OLD_ROW_RELEASE;
      end
      WAIT_FOR_OLD_ROW_RELEASE:if(old_row_released[writeback_row]) begin writeback_state<=READ_OLD_CENTER_ROW;
      old_row_beats_requested<=0;
      old_row_beats_received<=0;
      end
      READ_OLD_CENTER_ROW:if(old_row_beats_received==8) begin writeback_state<=COMMIT_ROW;
      commit_beat<=0;
      end
      COMMIT_ROW:begin
       grid_writes<=grid_writes+1;
       residual_saturations<=residual_saturations+beat_residual_saturations;
       marker_saturations<=marker_saturations+beat_marker_saturations;
       if(commit_beat==7) begin
        row_committed[writeback_row]<=1;
        committed_row_count<=committed_row_count+1;
        row_commit<=1;
        committed_row<=writeback_row;
        writeback_state<=WRITEBACK_IDLE;
       end else commit_beat<=commit_beat+1;
      end
     endcase
     if(committed_row_count==32 && fetch_state==ALL_ROWS_FETCHED && writeback_state==WRITEBACK_IDLE
         && !convolution_result_valid && !dense1_result_valid && !dense2_result_valid) begin
      busy<=0;
      done<=1;
      fetch_state<=FETCH_IDLE;
     end
    end
   end
  end
 end
`ifndef SYNTHESIS
 always @(posedge clk) if(!rst && busy) begin
  if(commit_write_valid) assert(old_row_released[writeback_row] && !row_committed[writeback_row]) else $fatal(1,
      "unsafe old-row overwrite");
  if(grid_read_valid && grid_read_ready) assert(!row_committed[grid_read_row]) else $fatal(1,
      "new generation read as old");
  if(convolution_result_valid) assert(convolution_row_tag[20:5]==epoch) else $fatal(1,"conv epoch tag");
  if(dense1_result_valid) assert(dense1_row_tag[20:5]==epoch) else $fatal(1,"dense epoch tag");
  if(dense2_result_valid) assert(dense2_row_tag[20:5]==epoch) else $fatal(1,"output epoch tag");
  if(convolution_request_valid && convolution_request_ready) assert(neighborhood_ready) else $fatal(1,
      "missing old-row window");
 end
 initial assert(STATE_FRACTION>0 && STATE_FRACTION<STATE_W-1) else $fatal(1,"invalid marker format");
`endif
endmodule
