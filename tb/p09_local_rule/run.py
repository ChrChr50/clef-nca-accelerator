"""Generate local parameter images/benches, then explicitly run or defer HDL."""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tb.p09_local_rule.support import fixtures,write_images,active_cycles
from tb.p08_primitives.run import literal
from model_export.cartpole.freeze import sha256


HEADER=r'''
module tb;
parameter LANES=1;
reg clk=0;always #5 clk=~clk;
reg rst=1,en=1,lv=0,lb=0,qv=0,rr=0;
reg [10:0] la=0;reg signed [61:0] lw=0;wire lr,le,qr,rv;
reg [54*32-1:0] patch=0;wire [6*32-1:0] delta;
wire tv;wire [1:0] tl;wire [5:0] tb;
wire [LANES-1:0] keep,asat,ysat;
wire [LANES*62-1:0] ta;wire [LANES*32-1:0] ty;wire [31:0] cycles;
nca_local_rule #(.LANES(LANES)) dut(clk,rst,en,lv,lb,la,lw,lr,le,qv,patch,qr,rr,rv,delta,
    tv,tl,tb,keep,ta,ty,asat,ysat,cycles);
reg signed [23:0] km[0:1859];reg signed [61:0] bm[0:55];
reg signed [61:0] ea[0:55];reg signed [31:0] ey[0:55];
reg es[0:55],eys[0:55];reg [6*32-1:0] expected_delta;
reg checking=0;integer seen=0;
integer lane,index,j,elapsed;
always @(posedge clk) begin
 #1;
 if(tv) begin
   if(!checking) $fatal(1,"unexpected trace");
   for(integer l=0;l<LANES;l=l+1) if(keep[l]) begin
     integer k;
     k=(tl==0 ? 0 : tl==1 ? 20 : 50)+tb+l;
     if($signed(ta[l*62+:62])!==ea[k] || $signed(ty[l*32+:32])!==ey[k] ||
        asat[l]!==es[k] || ysat[l]!==eys[k]) $fatal(1,"layer boundary mismatch");
     seen=seen+1;
   end
 end
end
task configure;
begin
 for(j=0;j<1916;j=j+1) begin
   @(negedge clk);lv=1;lb=(j>=1860);la=(j<1860 ? j : j-1860);
   lw=(j<1860 ? $signed(km[j]) : bm[j-1860]);
   if(!lr) $fatal(1,"configuration backpressure");
   @(posedge clk);#2;if(le) $fatal(1,"valid config rejected");
   @(negedge clk);lv=0; // bubble prevents stale load being counted twice
   @(posedge clk);#2;
 end
 if(!qr || lr) $fatal(1,"incomplete/non-atomic configuration");
end endtask
task run_case;
integer wall, expected_cycles;
reg [6*32-1:0] held;
begin
 expected_cycles=((20+LANES-1)/LANES)*54+((30+LANES-1)/LANES)*20+((6+LANES-1)/LANES)*30+2;
 seen=0;checking=1;wall=0;
 @(negedge clk);qv=1;en=1;
 if(!qr) $fatal(1,"request not ready");
 @(posedge clk);#2;
 @(negedge clk);qv=0;patch=0;
 while(!rv) begin
   // Stalls are physical only, do not advance fan-in/output/layer loops.
   en=(wall%7!=2 && wall%7!=3);
   @(posedge clk);#2;
   wall=wall+1;
   if(lr || qr) $fatal(1,"parameter/request access while busy");
   if(wall>10000) $fatal(1,"no forward progress");
   @(negedge clk);
 end
 if(delta!==expected_delta || seen!=56 || cycles!==expected_cycles)
   $fatal(1,"delta/trace/cycle mismatch");
 held=delta;en=1;checking=0;
 repeat(4) begin @(posedge clk);#2;if(!rv || delta!==held || lr || qr) $fatal(1,"result backpressure");end
 @(negedge clk);rr=1;
 @(posedge clk);#2;if(rv) $fatal(1,"result not retired");
 @(negedge clk);rr=0;
end endtask
initial begin
 $readmemh("kernels.mem",km);$readmemh("biases.mem",bm);
 repeat(2) @(posedge clk);#2;
 if(qr || lr || rv) $fatal(1,"reset interface");
 @(negedge clk);rst=0;
 if(qr) $fatal(1,"unconfigured request accepted");
 // Invalid ordering and kernel sign extension must not advance config.
 @(negedge clk);lv=1;la=1;lw=0;
 @(posedge clk);#2;if(!le) $fatal(1,"wrong-address config not rejected");
 @(negedge clk);la=0;lw=62'sh0000000001000000;
 @(posedge clk);#2;if(!le) $fatal(1,"bad sign extension not rejected");
 @(negedge clk);lv=0;
 configure;
'''

FOOTER=r'''
 // Reset aborts an in-progress request and invalidates configuration.
 @(negedge clk);qv=1;patch=0;
 @(posedge clk);#2;
 @(negedge clk);qv=0;
 repeat(3) @(posedge clk);
 @(negedge clk);rst=1;
 @(posedge clk);#2;if(rv || qr || tv || cycles) $fatal(1,"reset cancellation");
 @(negedge clk);rst=0;
 if(qr) $fatal(1,"reset reused stale configuration");
 $display("P09 local-rule RTL: PASS lanes=%0d",LANES);$finish;
end
initial begin #5000000;$fatal(1,"timeout");end
endmodule
'''


def generate(cases):
    lines=[HEADER]
    for p,delta,trace in cases:
        for layer,out,acc,value,sat,ysat in trace:
            k=(0,20,50)[layer]+out
            lines.append(f'ea[{k}]={literal(acc,62)};ey[{k}]={literal(value,32)};es[{k}]={sat};eys[{k}]={ysat};')
        packed=sum((int(v)&((1<<32)-1))<<(i*32) for i,v in enumerate(p))
        result=sum((int(v)&((1<<32)-1))<<(i*32) for i,v in enumerate(delta))
        lines.append(f'patch={literal(packed,54*32)};expected_delta={literal(result,6*32)};run_case;')
    lines.append(FOOTER)
    return '\n'.join(lines)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--generate-only',action='store_true')
    parser.add_argument('--restricted',action='store_true')
    args=parser.parse_args()
    model,cases,bindings=fixtures(args.restricted)
    folder=ROOT/'artifacts/p09_local_rule'/('restricted' if args.restricted else 'synthetic')
    images=write_images(model,folder)
    bench=folder/'tb.sv';bench.write_text(generate(cases))
    sources=[ROOT/'rtl/core/nca_round_sat.sv',ROOT/'rtl/core/nca_local_rule.sv']
    report={'schema_version':1,'arithmetic':model.fmt.manifest(),'python':sys.version,
            'cases':len(cases),'layer_output_comparisons':len(cases)*56,
            'images':images,'bounds':model.bounds,'accepted_vectors':bindings,
            'source_sha256':{p.relative_to(ROOT).as_posix():sha256(p) for p in sources},
            'bench_sha256':sha256(bench),'generator_sha256':sha256(Path(__file__)),
            'support_sha256':sha256(Path(__file__).with_name('support.py')),
            'lane_alternatives':{str(n):{'structural_active_cycles':active_cycles(n),'rtl_cycles_measured':False} for n in (1,2,3,4)},
            'simulation':'NOT RUN','synthesis':'NOT RUN','final_G5_choice':None}
    rc=0
    if not args.generate_only:
        compiler,sim=shutil.which('iverilog'),shutil.which('vvp')
        if not compiler or not sim: report['tool_limitation']='iverilog/vvp absent';rc=2
        else:
            proc=subprocess.run([compiler,'-V'],capture_output=True,text=True)
            report['iverilog_version']=proc.stdout+proc.stderr;report['commands']=[]
            for lanes in (1,2,3,4):
                cmds=[[compiler,'-g2012','-Wall','-s','tb',f'-Ptb.LANES={lanes}',
                       '-o',f'sim{lanes}.vvp',*map(str,sources),str(bench)],
                      [sim,f'sim{lanes}.vvp']]
                for index,cmd in enumerate(cmds):
                    report['commands'].append(cmd)
                    proc=subprocess.run(cmd,cwd=folder,capture_output=True,text=True,timeout=60)
                    (folder/f'lanes{lanes}_{index}.log').write_text(proc.stdout+proc.stderr)
                    if proc.returncode: rc=proc.returncode;break
                if rc: break
                if f'P09 local-rule RTL: PASS lanes={lanes}' not in proc.stdout:rc=1;break
            report['simulation']='FAIL' if rc else 'PASS (lanes 1/2/3/4)'
    (folder/'result.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps(report,indent=2,sort_keys=True));return rc


if __name__=='__main__':raise SystemExit(main())
