"""Full-grid bank mapping and collision arbitration HDL test, synthetic only."""
from pathlib import Path
import json
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from model_export.cartpole.freeze import sha256


def bench(width):
    return f'''`timescale 1ns/1ps
module tb;
 localparam SW={width}; localparam BW=4*6*SW;
 reg clk=0;always #5 clk=~clk;
 reg rst=1,wv=0,rv=0;reg[4:0]wr=0,rr=0;reg[2:0]wb=0,rb=0;
 reg[BW-1:0]wd=0;wire ready,valid;wire[4:0]orow;wire[2:0]obeat;wire[BW-1:0]od;
 reg[BW-1:0]scoreboard[0:255];integer r,b,k,address;
 nca_banked_state #(.STATE_W(SW)) dut(.clk(clk),.rst(rst),.wr_valid(wv),.wr_row(wr),.wr_beat(wb),.wr_data(wd),
 .rd_valid(rv),.rd_ready(ready),.rd_row(rr),.rd_beat(rb),.resp_valid(valid),.resp_row(orow),.resp_beat(obeat),.resp_data(od));
 task check_read(input integer row,input integer beat);
 begin
  @(negedge clk);wv=0;rv=1;rr=row;rb=beat;
  @(posedge clk);#1;
  if(!valid || od!==scoreboard[row*8+beat] || orow!==row || obeat!==beat)
   $fatal(1,"bank mapping mismatch row=%0d beat=%0d",row,beat);
 end endtask
 initial begin
  repeat(2) @(negedge clk);rst=0;
  // Unique words per row, column and channel; all 6144 scalar locations covered.
  for(r=0;r<32;r=r+1) for(b=0;b<8;b=b+1) begin
   @(negedge clk);wv=1;wr=r;wb=b;
   for(k=0;k<24;k=k+1) wd[k*SW +: SW]=((r*32+b*4+k/6)*6+k%6)*37+16'h8a31;
   scoreboard[r*8+b]=wd;
  end
  @(negedge clk);wv=0;
  for(r=0;r<32;r=r+1) for(b=0;b<8;b=b+1) check_read(r,b);
  // Simultaneous reads/writes to distinct locations remain legal.
  for(address=0;address<256;address=address+1) begin
   @(negedge clk);rv=1;wv=1;rr=address/8;rb=address%8;
   wr=((address+128)%256)/8;wb=(address+128)%8;wd=~scoreboard[(address+128)%256];
   if(!ready) $fatal(1,"unrelated operation stalled");
   @(posedge clk);#1;
   if(!valid || od!==scoreboard[address]) $fatal(1,"dual-port comparison failed");
   scoreboard[(address+128)%256]=wd;
  end
  // Same-address read never depends on vendor read-during-write behavior.
  @(negedge clk);rr=5;rb=3;wr=5;wb=3;rv=1;wv=1;wd='1;
  #1;if(ready) $fatal(1,"collision not blocked");
  @(posedge clk);#1;if(valid) $fatal(1,"collision produced a response");
  scoreboard[5*8+3]=wd;
  @(negedge clk);wv=0;
  @(posedge clk);#1;
  if(!valid || od!==scoreboard[5*8+3]) $fatal(1,"collision retry failed");
  for(r=0;r<32;r=r+1) for(b=0;b<8;b=b+1) check_read(r,b);
  @(negedge clk);rst=1;wv=0;rv=0;
  @(posedge clk);#1;if(valid) $fatal(1,"reset response invalidation failed");
  @(negedge clk);rst=0;
  check_read(5,3); // contents intentionally survive reset; controller must invalidate its state separately.
  $display("banked state PASS: SW=%0d all 6144 scalars, concurrent accesses and collision retry",SW);$finish;
 end
 initial begin #1000000;$fatal(1,"watchdog");end
endmodule
'''


def main():
    compiler,sim=shutil.which("iverilog"),shutil.which("vvp")
    if not compiler or not sim:
        raise SystemExit("Icarus required")
    source=ROOT/"rtl/core/nca_banked_state.sv"
    report={"source_sha256":sha256(source),"scope":"storage mapping only; no generation scheduler/FPGA fit", "cases":[]}
    for width in (16,32):
        folder=ROOT/f"artifacts/row_stage/memory{width}"
        folder.mkdir(parents=True,exist_ok=True)
        (folder/"tb.sv").write_text(bench(width))
        commands=[[compiler,"-g2012","-Wall","-s","tb","-o","sim.vvp",str(source),"tb.sv"],[sim,"sim.vvp"]]
        for index,command in enumerate(commands):
            proc=subprocess.run(command,cwd=folder,text=True,capture_output=True,timeout=60)
            output=proc.stdout+proc.stderr
            (folder/f"command{index}.log").write_text(output)
            if proc.returncode:raise RuntimeError(output)
        if "banked state PASS" not in output:raise AssertionError(output)
        print(output.strip(),flush=True)
        report["cases"].append({"state_bits":width,"simulation":"PASS","scalar_locations":6144,"commands":commands})
    (ROOT/"artifacts/row_stage/memory_result.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")


if __name__=="__main__":main()
