"""Synthetic row-stage HDL tests for both accepted and candidate arithmetic.

No original checkpoint is used. Artifacts include reproducible commands, hashes,
expected words and simulator logs. This verifies a stage, not a full controller.
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import numpy as np
from model_export.cartpole.fixed_point import FixedNCA, Format
from model_export.cartpole.row16_candidate import EXPECTED
from model_export.cartpole.test_fixed_point import fixture
from model_export.cartpole.freeze import sha256


def hex_file(path, values, width):
    path.write_text("".join(f"{int(v)&((1<<width)-1):0{(width+3)//4}x}\n" for v in np.asarray(values).flat))


def scalar_row(inputs, kernel, bias, fmt, relu):
    result = []
    acc_sats, out_sats = 0,0
    alo,ahi = -(1<<(fmt.accumulator_bits-1)),(1<<(fmt.accumulator_bits-1))-1
    ylo,yhi = -(1<<(fmt.state_bits-1)),(1<<(fmt.state_bits-1))-1
    for cell in inputs:
        for column in range(kernel.shape[1]):
            acc = sum(int(x)*int(w) for x,w in zip(cell,kernel[:,column],strict=True))+int(bias[column])
            acc_sats += int(acc<alo or acc>ahi)
            acc = min(ahi,max(alo,acc))
            acc = max(0,acc) if relu else acc
            q,r = divmod(acc,1<<fmt.weight_fraction)
            q += int(2*r>(1<<fmt.weight_fraction) or (2*r==(1<<fmt.weight_fraction) and q%2))
            out_sats += int(q<ylo or q>yhi)
            result.append(min(yhi,max(ylo,q)))
    return np.asarray(result,np.int64),acc_sats,out_sats


def bench(inputs,outputs,lanes,fmt,counts,cases=3):
    return f'''`timescale 1ns/1ps
module tb;
 localparam SW={fmt.state_bits}, AW={fmt.accumulator_bits}, WW={fmt.weight_bits};
 localparam NI={inputs}, NO={outputs}, NL={lanes}, CW=$clog2(NI*NO+NO);
 reg clk=0; always #5 clk=~clk;
 reg rst=1,cv=0,cb=0,cc=0,rv=0,rr=0;
 reg [CW-1:0] ca=0; reg signed [AW-1:0] cd=0;
 wire cr,configured,error,ready,valid;
 reg [20:0] tag=0; wire [20:0] out_tag;
 reg [32*NI*SW-1:0] values=0; wire [32*NO*SW-1:0] result;
 wire [31:0] cycles,asat,ysat;
 reg [WW-1:0] k[0:NI*NO-1]; reg [AW-1:0] b[0:NO-1];
 reg [SW-1:0] x[0:32*NI-1], y[0:32*NO-1];
 reg [32*NO*SW-1:0] expected; integer i,j,elapsed;
 nca_row_stage #(.INPUTS(NI),.OUTPUTS(NO),.LANES(NL),.STATE_W(SW),.WEIGHT_W(WW),
 .ACC_W(AW),.FRACTION({fmt.weight_fraction}),.USE_RELU({int(outputs!=6)})) dut
 (.clk(clk),.rst(rst),.cfg_valid(cv),.cfg_bias(cb),.cfg_commit(cc),.cfg_addr(ca),.cfg_data(cd),
 .cfg_ready(cr),.configured(configured),.config_error(error),.req_valid(rv),.req_ready(ready),
 .req_tag(tag),.req_values(values),.resp_valid(valid),.resp_ready(rr),.resp_tag(out_tag),
 .resp_values(result),.active_cycles(cycles),.accumulator_saturations(asat),.output_saturations(ysat));
 task configure;
 begin
  $readmemh("kernel.hex",k); $readmemh("bias.hex",b);
  for(i=0;i<NI*NO;i=i+1) begin
   @(negedge clk); cv=1;cb=0;ca=i;cd=$signed(k[i]);
  end
  for(i=0;i<NO;i=i+1) begin
   @(negedge clk);cv=1;cb=1;ca=i;cd=$signed(b[i]);
  end
  @(negedge clk);cv=0;cc=1;
  @(negedge clk);cc=0;
  if(!configured || error) $fatal(1,"configuration failed");
 end endtask
 task run_case(input integer number,input integer expected_acc_sats,input integer expected_out_sats);
 begin
  $readmemh($sformatf("input%0d.hex",number),x);
  $readmemh($sformatf("output%0d.hex",number),y);
  for(j=0;j<32*NI;j=j+1) values[j*SW +: SW]=x[j];
  for(j=0;j<32*NO;j=j+1) expected[j*SW +: SW]=y[j];
  @(negedge clk);tag=number+21'h12340;rv=1;
  if(!ready) $fatal(1,"unexpected request stall");
  @(posedge clk);#1;
  @(negedge clk);rv=0;values='1;tag=0;elapsed=0;
  while(!valid) begin
   @(posedge clk);#1;elapsed=elapsed+1;
   if(elapsed>NI*((32*NO+NL-1)/NL)+2) $fatal(1,"stage timeout");
  end
  if(result!==expected) $fatal(1,"row result mismatch case=%0d",number);
  if(out_tag!==number+21'h12340) $fatal(1,"tag mismatch");
  if(cycles!==NI*((32*NO+NL-1)/NL) || elapsed!==cycles) $fatal(1,"cycle count mismatch %0d",cycles);
  if(asat!==expected_acc_sats || ysat!==expected_out_sats) $fatal(1,"counter mismatch %0d %0d",asat,ysat);
  repeat(7) begin
   @(posedge clk);#1;
   if(!valid || result!==expected || ready) $fatal(1,"backpressure ownership failure");
  end
  @(negedge clk);rr=1;
  @(posedge clk);#1;if(valid) $fatal(1,"response not consumed");
  @(negedge clk);rr=0;
 end endtask
 initial begin
  repeat(2) @(negedge clk);rst=0;
  cc=1;@(negedge clk);cc=0;
  if(configured || !error || ready) $fatal(1,"incomplete configuration accepted");
  rst=1;@(negedge clk);rst=0;
  configure;
  {''.join(f'run_case({n},{counts[n][0]},{counts[n][1]});' for n in range(cases))}
  // An interrupted calculation must not produce a response or retain configuration.
  @(negedge clk);rv=1;
  @(negedge clk);rv=0;
  repeat(3) @(negedge clk);rst=1;
  @(negedge clk);rst=0;
  repeat(3) @(negedge clk);
  if(valid || configured || ready) $fatal(1,"reset did not invalidate transaction");
  $display("row stage PASS: NI=%0d NO=%0d lanes=%0d SW=%0d cycles=%0d",NI,NO,NL,SW,NI*((32*NO+NL-1)/NL));
  $finish;
 end
 initial begin #2000000;$fatal(1,"watchdog");end
endmodule
'''


def main():
    compiler,simulator = shutil.which("iverilog"),shutil.which("vvp")
    if not compiler or not simulator:
        raise SystemExit("iverilog/vvp required; no simulation claimed")
    sources = [ROOT / "rtl/core/nca_round_sat.sv",ROOT / "rtl/core/nca_row_stage.sv"]
    report = {"stage":"P09 row-stage candidate prototype; not a complete core or G5 acceptance",
              "sources":{p.relative_to(ROOT).as_posix():sha256(p) for p in sources},"cases":[]}
    for fmt in (EXPECTED,Format("fidelity32",32,24,24,22,62)):
        model = FixedNCA(fixture(),fmt)
        rng = np.random.RandomState(914)
        for layer,lanes in ((0,32),(1,24),(2,8),(2,7)):
            kernel = model.kernels[layer].reshape(-1,model.kernels[layer].shape[-1])
            ni,no = kernel.shape
            folder = ROOT / f"artifacts/row_stage/{fmt.name}_layer{layer}_lanes{lanes}"
            folder.mkdir(parents=True,exist_ok=True)
            hex_file(folder / "kernel.hex",kernel.T,fmt.weight_bits)
            hex_file(folder / "bias.hex",model.biases[layer],fmt.accumulator_bits)
            counts=[]
            for number in range(3):
                inputs = rng.randint(-(1<<(fmt.state_bits-1)),1<<(fmt.state_bits-1),(32,ni),dtype=np.int64)
                outputs,a,y = scalar_row(inputs,kernel,model.biases[layer],fmt,layer<2)
                hex_file(folder / f"input{number}.hex",inputs,fmt.state_bits)
                hex_file(folder / f"output{number}.hex",outputs,fmt.state_bits)
                counts.append((a,y))
            (folder / "tb.sv").write_text(bench(ni,no,lanes,fmt,counts))
            commands=[[compiler,"-g2012","-Wall","-s","tb","-o","sim.vvp",*map(str,sources),"tb.sv"],
                      [simulator,"sim.vvp"]]
            logs=[]
            for number,command in enumerate(commands):
                proc = subprocess.run(command,cwd=folder,capture_output=True,text=True,timeout=120)
                output = proc.stdout+proc.stderr
                (folder / f"command{number}.log").write_text(output)
                logs.append(output)
                if proc.returncode:
                    raise RuntimeError(f"row stage failed: {folder.name}: {output[-2000:]}")
            if "row stage PASS" not in logs[-1]:
                raise AssertionError("simulator did not report a pass")
            item={"format":fmt.name,"layer":layer,"lanes":lanes,"commands":commands,
                  "simulation":"PASS","rows":3,"word_comparisons":3*32*no,
                  "active_cycles_per_row":ni*((32*no+lanes-1)//lanes),"stdout":logs[-1].strip()}
            report["cases"].append(item)
            print(item["stdout"],flush=True)
    report["simulation"]="PASS"
    (ROOT / "artifacts/row_stage/result.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("Row-stage HDL PASS: 8 configurations, 24 rows",flush=True)


if __name__=="__main__":
    main()
