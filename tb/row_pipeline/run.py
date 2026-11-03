"""Exact full-grid epoch pipeline replay. Generated images stay in artifacts/.

Public fixtures by default; --restricted uses the locally pinned checkpoint.
Golden remains the unchanged P07 integer implementation, not this scheduler.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
from model_export.cartpole.fixed_point import FixedNCA, Format
from model_export.cartpole.test_fixed_point import fixture
from model_export.cartpole.row16_candidate import EXPECTED
from model_export.cartpole.freeze import sha256
from tb.row_stage.run import hex_file


def bench(fmt, skip, expected_macs, counts, epochs):
    return f'''`timescale 1ns/1ps
module tb;
localparam SW={fmt.state_bits},WW={fmt.weight_bits},AW={fmt.accumulator_bits},BW=24*SW;
reg clk=0;always #5 clk=~clk;
reg rst=1,en=1,cv=0,cb=0,cc=0,hw=0,hr=0,start=0;
reg [1:0] layer=0;reg [10:0] addr=0;reg signed [AW-1:0] data=0;
reg [4:0] row=0;reg [2:0] beat=0;reg [BW-1:0] hd=0;
reg [1023:0] mask;reg [8*SW-1:0] obs;
wire ready,configured,error,hready,hvalid,sready,busy,done,commit;
wire [BW-1:0] result;wire [4:0] committed_row;wire [15:0] epoch;
wire [31:0] cycles,macs,fr,wr,ww,rs,ms,asat,ysat;
nca_epoch_core #(.STATE_W(SW),.WEIGHT_W(WW),.ACC_W(AW),.FRACTION({fmt.weight_fraction}),
 .STATE_FRACTION({fmt.state_fraction}),.MASK_SKIP({skip})) dut (
 .clk(clk),.rst(rst),.step_enable(en),.cfg_layer(layer),.cfg_valid(cv),.cfg_bias(cb),.cfg_commit(cc),
 .cfg_addr(addr),.cfg_data(data),.cfg_ready(ready),.configured(configured),.config_error(error),
 .host_write(hw),.host_read(hr),.host_row(row),.host_beat(beat),.host_data(hd),
 .host_ready(hready),.host_response(hvalid),.host_result(result),
 .start_valid(start),.start_ready(sready),.update_mask(mask),.observations(obs),
 .busy(busy),.done(done),.row_commit(commit),.committed_row(committed_row),.epoch(epoch),
 .cycles(cycles),.issued_macs(macs),.frontend_reads(fr),.writeback_reads(wr),.grid_writes(ww),
 .residual_saturations(rs),.marker_saturations(ms),.accumulator_saturations(asat),.output_saturations(ysat));
reg [WW-1:0] k[0:1079];reg [AW-1:0] b[0:29];
reg [SW-1:0] words[0:6143],expected[0:6143],obswords[0:7];
reg masks[0:1023];
reg [SW-1:0] l0[0:20479],l1[0:30719],l2[0:6143];
integer i,j,e,r,bt,ni,no,ticks,commits,overlap,checks;
reg [31:0] seen;
task configure;
begin
 for(integer l=0;l<3;l=l+1) begin
  layer=l;ni=l==0?54:l==1?20:30;no=l==0?20:l==1?30:6;
  $readmemh($sformatf("kernel%0d.hex",l),k,0,ni*no-1);
  $readmemh($sformatf("bias%0d.hex",l),b,0,no-1);
  for(i=0;i<ni*no;i=i+1) begin @(negedge clk);cv=1;cb=0;addr=i;data=$signed(k[i]);end
  for(i=0;i<no;i=i+1) begin @(negedge clk);cb=1;addr=i;data=$signed(b[i]);end
  @(negedge clk);cv=0;cc=1;@(negedge clk);cc=0;
 end
 if(!configured || error) $fatal(1,"configuration");
end endtask
task load_grid;
begin
 $readmemh("initial.hex",words);
 for(r=0;r<32;r=r+1) for(bt=0;bt<8;bt=bt+1) begin
  @(negedge clk);hw=1;row=r;beat=bt;
  for(j=0;j<24;j=j+1) hd[j*SW +: SW]=words[r*192+bt*24+j];
 end
 @(negedge clk);hw=0;
end endtask
task check_layer(input integer which,input integer row_number);
integer c,o,nout;reg [SW-1:0] want,actual;
begin
 nout=which==0?20:which==1?30:6;
 for(c=0;c<32;c=c+1) for(o=0;o<nout;o=o+1) begin
  case(which)
   0:begin want=l0[(row_number*32+c)*nout+o];actual=dut.convolution_features[(c*nout+o)*SW +: SW];end
   1:begin want=l1[(row_number*32+c)*nout+o];actual=dut.dense1_features[(c*nout+o)*SW +: SW];end
   2:begin want=l2[(row_number*32+c)*nout+o];actual=dut.delta_features[(c*nout+o)*SW +: SW];end
  endcase
  if({skip} && !mask[row_number*32+c]) want=0;
  if(actual!==want) $fatal(1,"layer=%0d row=%0d cell=%0d out=%0d actual=%h expected=%h",which,row_number,c,o,actual,want);
  checks=checks+1;
 end
end endtask
always @(posedge clk) if(!rst && busy && en) begin
 if(dut.convolution_result_valid && dut.convolution_result_ready) check_layer(0,dut.convolution_row_tag[4:0]);
 if(dut.dense1_result_valid && dut.dense1_result_ready) check_layer(1,dut.dense1_row_tag[4:0]);
 if(dut.dense2_result_valid && dut.writeback_ready) check_layer(2,dut.dense2_row_tag[4:0]);
 if(dut.convolution.calculating_row && dut.dense_one.calculating_row) overlap=overlap+1;
end
initial begin
 checks=0;overlap=0;
 repeat(2) @(negedge clk);rst=0;
 if(sready) $fatal(1,"uninitialized start accepted");
 configure;load_grid;
 for(e=0;e<{epochs};e=e+1) begin
  $readmemh($sformatf("mask%0d.hex",e),masks);
  $readmemh($sformatf("obs%0d.hex",e),obswords);
  $readmemh($sformatf("expected%0d.hex",e),expected);
  $readmemh($sformatf("layer0_%0d.hex",e),l0);
  $readmemh($sformatf("layer1_%0d.hex",e),l1);
  $readmemh($sformatf("layer2_%0d.hex",e),l2);
  for(i=0;i<1024;i=i+1) mask[i]=masks[i];
  for(i=0;i<8;i=i+1) obs[i*SW +: SW]=obswords[i];
  @(negedge clk);if(!sready) $fatal(1,"start not ready");start=1;
  @(negedge clk);start=0;mask='x;obs='x;
  // The command owns mask and observation, external buses may change.
  // Restore only the test-side mask for reference comparisons.
  for(i=0;i<1024;i=i+1) mask[i]=masks[i];
  ticks=0;commits=0;seen=0;
  while(!done) begin
   en=(ticks%19<16);
   @(posedge clk);#1;
   if(commit) begin
    if(seen[committed_row]) $fatal(1,"duplicate commit");
    seen[committed_row]=1;commits=commits+1;
   end
   ticks=ticks+1;if(ticks>100000) $fatal(1,"epoch timeout");
   if(ticks%10000==0) begin $display("progress epoch=%0d ticks=%0d center=%0d commits=%0d",e,ticks,dut.convolution_row,commits);$fflush();end
   @(negedge clk);
  end
  en=1;
  if(commits!=32 || seen!==32'hffffffff || epoch!=e+1 || busy) $fatal(1,"barrier/commit");
  if(fr!=256 || wr!=256 || ww!=256) $fatal(1,"transfer counts %0d %0d %0d",fr,wr,ww);
  case(e)
   {' '.join(f'{q}:begin if(macs!={v}) $fatal(1,"MAC count %0d",macs); if(rs!={counts[q][0]} || ms!={counts[q][1]}) $fatal(1,"post saturation counts %0d %0d",rs,ms);end' for q,v in enumerate(expected_macs))}
  endcase
  for(r=0;r<32;r=r+1) for(bt=0;bt<8;bt=bt+1) begin
   @(negedge clk);hr=1;row=r;beat=bt;
   @(posedge clk);#1;
   if(!hvalid) $fatal(1,"readback missing");
   for(j=0;j<24;j=j+1) if(result[j*SW +: SW]!==expected[r*192+bt*24+j])
    $fatal(1,"grid epoch=%0d row=%0d beat=%0d word=%0d actual=%h expected=%h",e,r,bt,j,result[j*SW +: SW],expected[r*192+bt*24+j]);
  end
  @(negedge clk);hr=0;
  $display("epoch PASS e=%0d SW=%0d skip={skip} cycles=%0d MACs=%0d",e,SW,cycles,macs);
 end
 if(overlap==0) $fatal(1,"no actual pipeline overlap");
 // Reset during active computation invalidates state/configuration and responses.
 @(negedge clk);start=1;@(negedge clk);start=0;
 repeat(40) @(negedge clk);rst=1;
 @(negedge clk);rst=0;
 repeat(10) @(negedge clk);
 if(busy || done || sready || configured || dut.grid_beat_loaded!==0) $fatal(1,"reset validity");
 $display("pipeline PASS SW=%0d skip={skip} layer comparisons=%0d overlap=%0d",SW,checks,overlap);
 $finish;
end
initial begin #10000000;$fatal(1,"watchdog");end
endmodule
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--restricted', action='store_true')
    parser.add_argument('--format', choices=('fidelity32','row16'))
    parser.add_argument('--mask-skip', type=int, choices=(0,1))
    parser.add_argument('--jobs', type=int, choices=(1,2,4), default=1)
    args = parser.parse_args()
    name='restricted' if args.restricted else 'synthetic'
    if args.jobs>1:
        commands=[]
        for fmt_name in (args.format,) if args.format else ('fidelity32','row16'):
            for skip in (args.mask_skip,) if args.mask_skip is not None else (0,1):
                commands.append([sys.executable,str(Path(__file__).resolve()),'--format',fmt_name,
                                 '--mask-skip',str(skip),*(['--restricted'] if args.restricted else [])])
        def execute(command):
            p=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
            if p.returncode: raise RuntimeError(p.stdout+p.stderr)
            return p.stdout
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            for result in as_completed([pool.submit(execute,c) for c in commands]):
                print(result.result(),flush=True)
        reports=[json.loads((ROOT/f'artifacts/row_pipeline/{name}_{f}_skip{s}.json').read_text())
                 for f in ((args.format,) if args.format else ('fidelity32','row16'))
                 for s in ((args.mask_skip,) if args.mask_skip is not None else (0,1))]
        report=reports[0]
        report['cases']=[c for r in reports for c in r['cases']]
        (ROOT/f'artifacts/row_pipeline/{name}.json').write_text(json.dumps(report,indent=2)+'\n')
        return
    compiler, simulator = shutil.which('iverilog'), shutil.which('vvp')
    if not compiler or not simulator:
        raise SystemExit('Icarus/vvp required')
    weights = fixture()
    if args.restricted:
        from model_export.cartpole.freeze import load_frozen
        from model_export.cartpole.accepted_arithmetic import load_accepted_arithmetic
        from reference.original_nca.core import load_tfjs_weights
        frozen = load_frozen()
        load_accepted_arithmetic()
        base = ROOT/'self-organized-control/demo/models/model2'
        if sha256(base/'group1-shard1of1.bin') != frozen['weights']['blob_sha256']:
            raise ValueError('checkpoint identity mismatch')
        weights = load_tfjs_weights(base/'model.json',base/'group1-shard1of1.bin')
    sources = [ROOT / f'rtl/core/{name}.sv' for name in
               ('nca_round_sat','nca_row_stage','nca_banked_state','nca_row_window','nca_epoch_core')]
    report = {'scope':'full epoch pipeline, not action controller or physical signoff',
              'restricted':args.restricted,'sources':{str(p.relative_to(ROOT)):sha256(p) for p in sources},'cases':[]}
    for fmt in (Format('fidelity32',32,24,24,22,62), EXPECTED):
        if args.format and args.format!=fmt.name: continue
        for skip in (0,1):
            if args.mask_skip is not None and args.mask_skip!=skip: continue
            model = FixedNCA(weights,fmt)
            rng = np.random.RandomState(528)
            grid = model.initial_grid(rng.uniform(-.1,.1,(1,32,32,6)))
            # Explicit signed extremes exercise residual and marker saturation.
            grid[0,13,16,4:] = (1<<(fmt.state_bits-1))-1
            grid[0,0,0,:] = -(1<<(fmt.state_bits-1))
            folder = ROOT / f'artifacts/row_pipeline/{"restricted" if args.restricted else "synthetic"}_{fmt.name}_skip{skip}'
            folder.mkdir(parents=True,exist_ok=True)
            hex_file(folder/'initial.hex',grid,fmt.state_bits)
            for layer in range(3):
                k = model.kernels[layer]
                hex_file(folder/f'kernel{layer}.hex',k.reshape(-1,k.shape[-1]).T,fmt.weight_bits)
                hex_file(folder/f'bias{layer}.hex',model.biases[layer],fmt.accumulator_bits)
            macs,counts = [],[]
            for e in range(3):
                mask = (rng.random_sample((1,32,32,1))<.5) if e==0 else np.full((1,32,32,1),e==2)
                obs = rng.uniform(-.2,.2,(1,4)).astype(np.float32)
                before = dict(model.counters)
                grid,trace = model.step(grid,obs,mask,trace=True)
                counts.append([model.counters.get(label,0)-before.get(label,0) for label in ('residual','output_marker')])
                for layer in range(3):
                    hex_file(folder/f'layer{layer}_{e}.hex',trace[f'layer{layer}_output'],fmt.state_bits)
                hex_file(folder/f'expected{e}.hex',grid,fmt.state_bits)
                hex_file(folder/f'mask{e}.hex',mask,1)
                hex_file(folder/f'obs{e}.hex',model.observations(obs),fmt.state_bits)
                macs.append(int(mask.sum() if skip else 1024)*1860)
            (folder/'tb.sv').write_text(bench(fmt,skip,macs,counts,3))
            commands = [[compiler,'-g2012','-Wall','-s','tb','-o','sim.vvp',*map(str,sources),'tb.sv'],[simulator,'sim.vvp']]
            elapsed = time.monotonic()
            for number,command in enumerate(commands):
                with (folder/f'command{number}.log').open('w') as log:
                    p = subprocess.run(command,cwd=folder,stdout=log,stderr=subprocess.STDOUT,text=True,timeout=900)
                output=(folder/f'command{number}.log').read_text()
                if p.returncode: raise RuntimeError(f'{folder.name}: {output[-3500:]}')
            if 'pipeline PASS' not in output: raise AssertionError('no simulator pass')
            print(output,flush=True)
            report['cases'].append({'format':fmt.name,'mask_skip':skip,'epochs':3,'grid_comparisons':18432,
                                    'layer_comparisons':172032,'expected_macs':macs,'commands':commands,
                                    'elapsed_seconds':time.monotonic()-elapsed,'stdout':output,'result':'PASS'})
    if args.format: name+=f'_{args.format}'
    if args.mask_skip is not None: name+=f'_skip{args.mask_skip}'
    (ROOT/f'artifacts/row_pipeline/{name}.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    main()
