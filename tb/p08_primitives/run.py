"""Rights-safe P08 vector generation and Icarus reproducibility entry point.

Generated testbenches/logs live only in ignored artifacts, including when
--restricted selects accepted checkpoint-derived P07 comparison cases.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from model_export.cartpole.accepted_arithmetic import accepted_format, load_accepted_arithmetic
from model_export.cartpole.freeze import load_frozen, sha256
from model_export.cartpole.fixed_point import FixedNCA, round_shift, scalar_cell_delta
from model_export.cartpole.test_fixed_point import fixture

SOURCES = [ROOT/'rtl/core'/f'nca_{name}.sv' for name in
           ('round_sat','guard_add','word_pack','event_counter','elastic_word','mac_stream')]


def clipped(value, width):
    lo, hi = -(1 << (width-1)), (1 << (width-1))-1
    return max(lo,min(hi,value)), int(value<lo or value>hi)


def rounded(value, shift=22, relu=False):
    value = max(0,value) if relu else value
    q,r = divmod(value,1 << shift)
    return q+int(2*r>(1 << shift) or (2*r==(1 << shift) and q%2))


def literal(value, width):
    return f"{width}'sh{value & ((1<<width)-1):0{(width+3)//4}x}"


def cases(restricted=False):
    fmt=accepted_format()
    rng=np.random.RandomState(808)
    values=[-(1<<61),(1<<61)-1,0,1,-1]
    for q in (-2147483649,-2147483648,-3,-2,-1,0,1,2,3,2147483647,2147483648):
        for offset in (-1,0,1):
            values.append((q<<22)+(1<<21)+offset)
    values += [int(v) for v in rng.randint(-(1<<61),1<<61,256,dtype=np.int64)]
    rounds=[]
    for relu in (False,True):
        for v in values:
            expect=clipped(rounded(v,relu=relu),32)
            golden=clipped(int(round_shift([max(0,v) if relu else v],22)[0]),32)
            assert expect==golden
            rounds.append((v,int(relu),*expect))
    extremes=[-(1<<31),(1<<31)-1,-1,0,1,1<<24]
    adds=[(a,b,en,*clipped(a+(b if en else 0),32))
          for a in extremes for b in extremes for en in (0,1)]
    packs=[(v,v,1) for v in extremes]
    packs += [(0,1<<31,0),(0,-(1<<31)-1,0),(0,1<<32,0)]
    macs=[]
    for n in (1,20,30,54):
        for sign in (-1,1):
            terms=[(-(1<<31),sign*((1<<23)-1))]*n
            bias=(1<<61)-1 if sign<0 else -(1<<61)
            macs.append((terms,bias,*clipped(sum(a*b for a,b in terms)+bias,62)))
        terms=[(int(rng.randint(-(1<<31),1<<31)),int(rng.randint(-(1<<23),1<<23))) for _ in range(n)]
        macs.append((terms,123,*clipped(sum(a*b for a,b in terms)+123,62)))
    model=FixedNCA(fixture(),fmt)
    grid=rng.randint(-(1<<31),1<<31,(1,32,32,6),dtype=np.int64)
    groups=[(model,grid,[(0,0),(31,31),(16,16)],None)]
    bindings=[]
    if restricted:
        from reference.original_nca.core import load_tfjs_weights
        base=ROOT/'self-organized-control/demo/models/model2'
        model=FixedNCA(load_tfjs_weights(base/'model.json',base/'group1-shard1of1.bin'),fmt)
        for case in load_accepted_arithmetic()['verification_vectors']:
            path=ROOT/case['restricted_vector_path']
            if sha256(path)!=case['sha256']: raise ValueError('restricted vector hash mismatch')
            with np.load(path,allow_pickle=False) as saved:
                groups.append((model,saved['old_grid'].copy(),[tuple(map(int,c)) for c in saved['cells']],
                               saved['cell_delta'].copy()))
            bindings.append({'path':case['restricted_vector_path'],'sha256':case['sha256']})
    for model,grid,coords,saved_delta in groups:
        delta,trace=model.delta(grid,True)
        for ci,(row,col) in enumerate(coords):
            np.testing.assert_array_equal(delta[0,row,col],scalar_cell_delta(model,grid,row,col))
            if saved_delta is not None: np.testing.assert_array_equal(delta[0,row,col],saved_delta[ci])
            values=[]
            for kr in range(3):
                for kc in range(3):
                    rr,cc=row+kr-1,col+kc-1
                    values.extend([int(grid[0,rr,cc,c]) if 0<=rr<32 and 0<=cc<32 else 0 for c in range(6)])
            for layer in range(3):
                matrix=model.kernels[layer].reshape(len(values),-1)
                next_values=[]
                for out in range(matrix.shape[1]):
                    terms=[(v,int(matrix[i,out])) for i,v in enumerate(values)]
                    bias=int(model.biases[layer][out])
                    acc,sat=clipped(sum(a*b for a,b in terms)+bias,62)
                    assert acc==int(trace[f'layer{layer}_accumulator'][0,row,col,out])
                    y,ysat=clipped(rounded(acc,relu=layer<2),32)
                    assert y==int(trace[f'layer{layer}_output'][0,row,col,out])
                    macs.append((terms,bias,acc,sat))
                    rounds.append((acc,int(layer<2),y,ysat))
                    next_values.append(y)
                values=next_values
    return rounds,adds,packs,macs,bindings


HEADER = r'''
module tb;
reg clk=0; always #5 clk=~clk;
reg rst=1;
reg signed [61:0] rv; reg relu; wire signed [31:0] ry; wire rs;
nca_round_sat rounder(rv,relu,ry,rs);
reg signed [31:0] a,b; reg en; wire signed [31:0] ay; wire asat;
nca_guard_add adder(a,b,en,ay,asat);
reg signed [31:0] pw; reg signed [63:0] pc; wire signed [63:0] pe;
wire signed [31:0] po; wire pv;
nca_word_pack packer(pw,pc,pe,po,pv);
reg iv=0,first=0,last=0,ready=0; wire ir,ov;
reg signed [31:0] x; reg signed [23:0] w; reg signed [61:0] bias;
wire signed [61:0] acc; wire ms;
nca_mac_stream mac(clk,rst,iv,first,last,ready,ir,x,w,bias,ov,acc,ms);
wire [31:0] count; wire counter_overflow;
nca_event_counter ctr(clk,rst,ov&&ready,ms,count,counter_overflow);
reg cf=0,ce=0; wire [1:0] small_count; wire small_overflow;
nca_event_counter #(.W(2)) small_ctr(clk,rst,cf,ce,small_count,small_overflow);
reg ev=0,er=0; reg [31:0] ed=0; wire ei,eo; wire [31:0] eq;
nca_elastic_word elastic(clk,rst,ev,er,ei,ed,eo,eq);
integer expected_count=0;
task round_case(input signed [61:0] v,input r,input signed [31:0] y,input s);
begin rv=v; relu=r; #1; if (ry!==y || rs!==s) $fatal(1,"round mismatch"); end endtask
task add_case(input signed [31:0] aa,bb,input e,input signed [31:0] y,input s);
begin a=aa;b=bb;en=e;#1;if(ay!==y || asat!==s) $fatal(1,"guard-add mismatch");end endtask
task pack_case(input signed [31:0] ww,input signed [63:0] cc,input valid_word);
begin pw=ww;pc=cc;#1;if(pe!==$signed(ww) || po!==cc[31:0] || pv!==valid_word) $fatal(1,"packing mismatch");end endtask
task term(input signed [31:0] xx,input signed [23:0] ww,input f,l,input signed [61:0] bb);
begin
 @(negedge clk); iv=1;x=xx;w=ww;first=f;last=l;bias=bb;
 if (!ir) $fatal(1,"unexpected input backpressure");
 @(posedge clk); #1; @(negedge clk); iv=0;
 // Valid bubbles must not reapply the previous product.
 @(posedge clk); #1;
end endtask
task finish(input signed [61:0] expected,input sat);
integer j;
begin
 if(!ov || acc!==expected || ms!==sat) $fatal(1,"MAC mismatch");
 @(negedge clk);iv=1;first=1;last=1;x=123;w=-77;bias=999;
 for(j=0;j<3;j=j+1) begin
   @(posedge clk);#1;
   if(!ov || acc!==expected || ms!==sat || ir || count!==expected_count)
     $fatal(1,"stall stability/count mismatch");
 end
 @(negedge clk); ready=1;iv=0;
 @(posedge clk);#1;expected_count=expected_count+sat;
 if(ov || count!==expected_count) $fatal(1,"accepted saturation count mismatch");
 @(negedge clk); ready=0;
end endtask
initial begin
 rv=0;relu=0;a=0;b=0;en=0;pw=0;pc=0;x=0;w=0;bias=0;
 repeat(2) @(posedge clk); #1;
 if(ov || eo || count || counter_overflow) $fatal(1,"reset mismatch");
 @(negedge clk);rst=0;
'''

FOOTER = r'''
 // MAC can retire/replace its result in one cycle without losing either word.
 term(32'sd2,24'sd3,1,1,62'sd7);
 @(negedge clk);ready=1;iv=1;first=1;last=1;x=-2;w=3;bias=7;
 @(posedge clk);#1;
 if(!ov || acc!==62'sd1 || ms || count!==expected_count) $fatal(1,"MAC simultaneous retire/replace");
 @(negedge clk);ready=0;iv=0;
 finish(62'sd1,0);
 // One-entry transport empty/full/stall/simultaneous replacement.
 @(negedge clk);ev=1;ed=32'hdeadbeef;er=0;
 @(posedge clk);#1;if(!eo || eq!==32'hdeadbeef || ei) $fatal(1,"elastic fill");
 @(negedge clk);ed=32'habcdef01;
 repeat(3) begin @(posedge clk);#1;if(eq!==32'hdeadbeef || ei) $fatal(1,"elastic stalled");end
 @(negedge clk);er=1;
 @(posedge clk);#1;if(!eo || eq!==32'habcdef01) $fatal(1,"elastic simultaneous replacement");
 @(negedge clk);ev=0;
 @(posedge clk);#1;if(eo || !ei) $fatal(1,"elastic drain");
 // Counter saturation and overflow sticky policy.
 @(negedge clk);cf=1;ce=1;
 repeat(4) @(posedge clk);#1;
 if(small_count!==3 || !small_overflow) $fatal(1,"counter wrap");
 @(negedge clk);cf=0;
 repeat(2) @(posedge clk);#1;
 if(small_count!==3) $fatal(1,"counter stall");
 // Reset cancels a partial transaction and pending transport/output state.
 term(32'sd17,24'sd19,1,0,62'sd0);
 @(negedge clk);rst=1;
 @(posedge clk);#1;
 if(ov || eo || count || counter_overflow || small_count || small_overflow || ir || ei)
   $fatal(1,"reset cancellation");
 @(negedge clk);rst=0;
 term(32'sd2,24'sd3,1,1,62'sd7); expected_count=0;
 finish(62'sd13,0);
 $display("P08 RTL primitive simulation: PASS");$finish;
end
initial begin #20000000; $fatal(1,"testbench timeout"); end
endmodule
'''


def generate(restricted=False):
    rounds,adds,packs,macs,bindings=cases(restricted)
    lines=[HEADER]
    for v,r,y,s in rounds: lines.append(f'round_case({literal(v,62)},{r},{literal(y,32)},{s});')
    for a,b,e,y,s in adds: lines.append(f'add_case({literal(a,32)},{literal(b,32)},{e},{literal(y,32)},{s});')
    for w,c,v in packs: lines.append(f'pack_case({literal(w,32)},{literal(c,64)},{v});')
    for terms,bias,acc,sat in macs:
        for i,(x,w) in enumerate(terms):
            lines.append(f'term({literal(x,32)},{literal(w,24)},{int(i==0)},{int(i==len(terms)-1)},{literal(bias,62)});')
        lines.append(f'finish({literal(acc,62)},{sat});')
    lines.append(FOOTER)
    return '\n'.join(lines),{'round_cases':len(rounds),'guard_add_cases':len(adds),
                            'packing_cases':len(packs),'mac_transactions':len(macs),
                            'mac_terms':sum(len(t) for t,_,_,_ in macs),'restricted_bindings':bindings}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--generate-only',action='store_true')
    parser.add_argument('--restricted',action='store_true')
    args=parser.parse_args()
    load_frozen();load_accepted_arithmetic()
    directory=ROOT/'artifacts/p08_primitives'/('restricted' if args.restricted else 'synthetic')
    directory.mkdir(parents=True,exist_ok=True)
    text,report=generate(args.restricted)
    bench=directory/'tb.sv';bench.write_text(text,encoding='utf-8')
    report.update(schema_version=1,python=sys.version,seed=808,arithmetic='fidelity32',
                  source_sha256={p.relative_to(ROOT).as_posix():sha256(p) for p in SOURCES},
                  generator_sha256=sha256(Path(__file__)),
                  testbench_sha256=hashlib.sha256(text.encode()).hexdigest(),
                  simulation='NOT RUN',synthesis='NOT RUN')
    rc=0
    if not args.generate_only:
        compiler,runner=shutil.which('iverilog'),shutil.which('vvp')
        if not compiler or not runner:
            report['tool_limitation']='iverilog/vvp unavailable on PATH';rc=2
        else:
            version=subprocess.run([compiler,'-V'],capture_output=True,text=True)
            report['iverilog_version']=version.stdout+version.stderr
            commands=[[compiler,'-g2012','-Wall','-s','tb','-o',str(directory/'sim.vvp'),
                       *map(str,SOURCES),str(bench)],[runner,str(directory/'sim.vvp')]]
            report['commands']=commands
            for index,cmd in enumerate(commands):
                proc=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
                (directory/f'command{index}.log').write_text(proc.stdout+proc.stderr)
                if proc.returncode:
                    rc=proc.returncode;report['simulation']='FAIL';break
            else:
                if 'P08 RTL primitive simulation: PASS' not in proc.stdout:
                    rc=1;report['simulation']='FAIL (missing completion marker)'
                else: report['simulation']='PASS'
    (directory/'result.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps(report,indent=2,sort_keys=True))
    return rc


if __name__=='__main__':
    raise SystemExit(main())
