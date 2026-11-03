"""Exhaustive synthetic shared-window address/padding test at both widths."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from model_export.cartpole.freeze import sha256

BENCH=r'''
module tb;
parameter SW=32;
reg clk=0;always #5 clk=~clk;
reg rst=1,clear=0,load=0;reg [4:0] row=0,center=0;reg [2:0] beat=0;
reg [24*SW-1:0] data=0;reg [31:0] term=0;
wire [32*SW-1:0] operands;wire ready;
nca_row_window #(.STATE_W(SW)) dut(clk,rst,clear,load,row,beat,data,center,term,operands,ready);
integer r,b,c,ch,t,rr,cc,want,checks;
task fill(input integer number);
begin
 for(b=0;b<8;b=b+1) begin
  @(negedge clk);load=1;row=number;beat=b;
  for(c=0;c<4;c=c+1) for(ch=0;ch<6;ch=ch+1)
   data[(c*6+ch)*SW +: SW]=1+number*192+(b*4+c)*6+ch;
 end
 @(negedge clk);load=0;
end endtask
initial begin
 checks=0;repeat(2) @(negedge clk);rst=0;
 #1;if(ready) $fatal(1,"invalid rows visible");
 fill(0);fill(1);
 for(r=0;r<32;r=r+1) begin
  center=r;#1;if(!ready) $fatal(1,"missing valid window %0d",r);
  for(t=0;t<54;t=t+1) begin
   term=t;#1;
   rr=r+t/18-1;ch=t%6;
   for(c=0;c<32;c=c+1) begin
    cc=c+(t/6)%3-1;
    want=rr<0 || rr>=32 || cc<0 || cc>=32 ? 0 : 1+rr*192+cc*6+ch;
    if(operands[c*SW +: SW]!==want) $fatal(1,"window r=%0d c=%0d term=%0d got=%0d want=%0d",r,c,t,operands[c*SW +: SW],want);
    checks=checks+1;
   end
  end
  if(r<30) fill(r+2);
 end
 @(negedge clk);clear=1;@(negedge clk);clear=0;
 #1;if(ready) $fatal(1,"stale window after invalidate");
 $display("window PASS SW=%0d comparisons=%0d rows_loaded=32",SW,checks);$finish;
end
endmodule
'''

def main():
    source=ROOT/'rtl/core/nca_row_window.sv'
    report={'source_sha256':sha256(source),'cases':[]}
    for width in (16,32):
        folder=ROOT/f'artifacts/row_pipeline/window{width}'
        folder.mkdir(parents=True,exist_ok=True)
        (folder/'tb.sv').write_text(BENCH)
        commands=[[shutil.which('iverilog'),'-g2012','-s','tb',f'-Ptb.SW={width}','-o','sim.vvp',str(source),'tb.sv'],
                  [shutil.which('vvp'),'sim.vvp']]
        for i,command in enumerate(commands):
            p=subprocess.run(command,cwd=folder,capture_output=True,text=True,timeout=60)
            output=p.stdout+p.stderr
            (folder/f'command{i}.log').write_text(output)
            if p.returncode: raise RuntimeError(output)
        if 'window PASS' not in output: raise AssertionError('no pass')
        print(output,flush=True)
        report['cases'].append({'width':width,'comparisons':55296,'commands':commands,'result':'PASS'})
    (ROOT/'artifacts/row_pipeline/window.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
