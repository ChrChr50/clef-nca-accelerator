"""Validate completed replay reports and bind their local generated inputs."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from model_export.cartpole.freeze import sha256,load_frozen
from model_export.cartpole.accepted_arithmetic import load_accepted_arithmetic


def main():
    load_frozen();load_accepted_arithmetic()
    base=ROOT/'artifacts/row_pipeline'
    summaries=[]
    for name,expected_cases in (('synthetic',4),('restricted',2)):
        path=base/f'{name}.json'
        report=json.loads(path.read_text())
        if len(report['cases'])!=expected_cases: raise ValueError('incomplete matrix')
        for relative,digest in report['sources'].items():
            if sha256(ROOT/relative)!=digest: raise ValueError(f'stale source: {relative}')
        for case in report['cases']:
            if case['result']!='PASS' or case['stdout'].count('epoch PASS')!=3:
                raise ValueError('incomplete epoch evidence')
            if [int(x) for x in re.findall(r'MACs=(\d+)',case['stdout'])]!=case['expected_macs']:
                raise ValueError('work counter evidence mismatch')
            folder=base/f"{name}_{case['format']}_skip{case['mask_skip']}"
            summaries.append({
                'suite':name,'format':case['format'],'mask_skip':case['mask_skip'],
                'epochs':case['epochs'],'grid_comparisons':case['grid_comparisons'],
                'layer_comparisons':case['layer_comparisons'],
                'simulation_cycles':list(map(int,re.findall(r'cycles=(\d+)',case['stdout']))),
                'report_sha256':sha256(path),
                'generated_inputs':{p.name:sha256(p) for p in sorted(folder.glob('*.hex'))},
                'bench_sha256':sha256(folder/'tb.sv'),
                'command_logs':{p.name:sha256(p) for p in sorted(folder.glob('command*.log'))}})
    versions={}
    for name in ('iverilog','vvp'):
        tool=shutil.which(name)
        if not tool: raise ValueError(f'{name} missing')
        p=subprocess.run([tool,'-V'],capture_output=True,text=True,timeout=15)
        raw=p.stdout+p.stderr
        (base/f'{name}_version.log').write_text(raw)
        versions[name]={'path':tool,'sha256':sha256(Path(tool)),'version':raw.splitlines()[0]}
    output={'scope':'epoch equivalence only; no controller/physical signoff',
            'seed':528,'cases':summaries,'tools':versions,
            'test_sources':{str(p.relative_to(ROOT)):sha256(p) for p in
                            (Path(__file__).resolve(),Path(__file__).with_name('run.py'),
                             ROOT/'model_export/cartpole/fixed_point.py',
                             ROOT/'model_export/cartpole/test_fixed_point.py')},
            'epochs':sum(c['epochs'] for c in summaries),
            'grid_comparisons':sum(c['grid_comparisons'] for c in summaries),
            'layer_comparisons':sum(c['layer_comparisons'] for c in summaries)}
    (base/'evidence.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({k:output[k] for k in ('epochs','grid_comparisons','layer_comparisons')}))


if __name__=='__main__':main()
