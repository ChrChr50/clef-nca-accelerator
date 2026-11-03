"""Audit logical convolution weight sharing and actual row request spacing.

Public synthetic coefficients only. This measures the existing component; it
does not implement a shared line buffer, physical ROM or generation scheduler.
"""
from pathlib import Path
import json
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from model_export.cartpole.freeze import sha256


def bench(sw,ww,aw,fraction):
    return f'''`timescale 1ns/1ps
module tb;
 reg clk=0;always #5 clk=~clk;
 reg rst=1,cv=0,cb=0,cc=0,rv=0;
 reg [10:0]ca=0;reg signed [{aw-1}:0]cd=0;
 wire cr,configured,error,ready,valid;wire[20:0]tag;
 wire[32*20*{sw}-1:0]data;
 wire[31:0]active,asat,ysat;
 integer i,tick=0,requests=0,responses=0,previous=-1,interval_seen=0;
 nca_row_stage #(.INPUTS(54),.OUTPUTS(20),.LANES(32),.STATE_W({sw}),
 .WEIGHT_W({ww}),.ACC_W({aw}),.FRACTION({fraction})) dut
 (.clk(clk),.rst(rst),.cfg_valid(cv),.cfg_bias(cb),.cfg_commit(cc),.cfg_addr(ca),.cfg_data(cd),
 .cfg_ready(cr),.configured(configured),.config_error(error),.req_valid(rv),.req_ready(ready),
 .req_tag(21'd0),.req_values({32*54*sw}'d0),.resp_valid(valid),.resp_ready(1'b1),
 .resp_tag(tag),.resp_values(data),.active_cycles(active),.accumulator_saturations(asat),.output_saturations(ysat));
 genvar g;
 generate for(g=0;g<32;g=g+1)begin: checks
  always @(posedge clk) if(!rst && dut.calculating_row)
   if(dut.arithmetic[g].coefficient !== (dut.output_slot*54+dut.input_feature_index))
    $fatal(1,"convolution coefficient sequence differs lane=%0d",g);
 end endgenerate
 always @(posedge clk) begin
  tick=tick+1;
  if(!rst && rv && ready)begin
   if(previous>=0)begin
    if(interval_seen!=0 && tick-previous!=interval_seen) $fatal(1,"variable request spacing");
    interval_seen=tick-previous;
   end
   previous=tick;requests=requests+1;
  end
  if(!rst && valid)begin
   if(data!==0 || active!==1080 || asat!==0 || ysat!==0) $fatal(1,"arithmetic/output mismatch");
   responses=responses+1;
   if(responses==3)begin
    $display("TRANSCRIPT_AUDIT_PASS state_bits={sw} shared_logical_coefficient=1 active_cycles=%0d request_interval=%0d",active,interval_seen);
    $finish;
   end
  end
 end
 initial begin
  repeat(2)@(negedge clk);rst=0;
  for(i=0;i<1080;i=i+1)begin @(negedge clk);cv=1;cb=0;ca=i;cd=i;end
  for(i=0;i<20;i=i+1)begin @(negedge clk);cv=1;cb=1;ca=i;cd=0;end
  @(negedge clk);cv=0;cc=1;
  @(negedge clk);cc=0;rv=1;
 end
 initial begin #1000000;$fatal(1,"watchdog");end
endmodule
'''


def main():
    compiler,sim=shutil.which("iverilog"),shutil.which("vvp")
    if not compiler or not sim:raise SystemExit("Icarus/vvp required")
    sources=[ROOT/"rtl/core/nca_round_sat.sv",ROOT/"rtl/core/nca_row_stage.sv"]
    report={"scope":"logical coefficient sequence and unstalled request interval; no physical synthesis or full-pipeline proof",
            "sources":{p.relative_to(ROOT).as_posix():sha256(p) for p in sources},"cases":[]}
    for sw,ww,aw,fraction in ((16,16,48,12),(32,24,62,22)):
        folder=ROOT/f"artifacts/row_stage/transcript_audit/state{sw}"
        folder.mkdir(parents=True,exist_ok=True)
        (folder/"tb.sv").write_text(bench(sw,ww,aw,fraction))
        commands=[[compiler,"-g2012","-Wall","-s","tb","-o","sim.vvp",*map(str,sources),"tb.sv"],[sim,"sim.vvp"]]
        for index,command in enumerate(commands):
            proc=subprocess.run(command,cwd=folder,capture_output=True,text=True,timeout=60)
            output=proc.stdout+proc.stderr
            (folder/f"command{index}.log").write_text(output)
            if proc.returncode:raise RuntimeError(output)
        if "TRANSCRIPT_AUDIT_PASS" not in output:raise AssertionError(output)
        line=next(line for line in output.splitlines() if line.startswith("TRANSCRIPT_AUDIT_PASS"))
        fields=dict(token.split("=",1) for token in line.split()[1:])
        report["cases"].append({**{k:int(v) for k,v in fields.items()},"simulation":"PASS","commands":commands})
        print(line,flush=True)
    (ROOT/"artifacts/row_stage/transcript_audit/result.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")


if __name__=="__main__":main()
