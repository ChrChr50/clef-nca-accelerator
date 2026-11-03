"""Bind the cleanup checks, fresh replay and unchanged golden inputs together."""
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tb.rtl_cleanup.check_refactor import main as check_refactor


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    check_refactor()
    folder=ROOT/'artifacts/rtl_cleanup'
    regressions=json.loads((folder/'regressions.json').read_text())
    if len(regressions)!=18 or any(r['returncode'] for r in regressions):
        raise ValueError('component/regression matrix incomplete')
    replay=json.loads((ROOT/'artifacts/row_pipeline/evidence.json').read_text())
    if replay['epochs']!=18 or len(replay['cases'])!=6:
        raise ValueError('full-grid replay matrix incomplete')
    bindings=[]
    for case in replay['cases']:
        name=f"{case['suite']}_{case['format']}_skip{case['mask_skip']}"
        old=folder/'before/row_pipeline'/name
        new=ROOT/'artifacts/row_pipeline'/name
        for filename,current_hash in case['generated_inputs'].items():
            if digest(new/filename)!=current_hash or digest(old/filename)!=current_hash:
                raise ValueError(f'golden or input changed: {name}/{filename}')
            bindings.append({'case':name,'file':filename,'sha256':current_hash})
    governance=[]
    for line in (ROOT/'governance/implementation-package.sha256').read_text().splitlines():
        if not line.strip():continue
        expected,path=line.split('  ',1)
        if digest(ROOT/path)!=expected:raise ValueError(f'protected file changed: {path}')
        governance.append(path)
    result={'result':'PASS','unchanged_golden_input_files':len(bindings),
            'epochs':replay['epochs'],'grid_comparisons':replay['grid_comparisons'],
            'layer_comparisons':replay['layer_comparisons'],
            'protected_identities':len(governance),'golden_input_bindings':bindings,
            'regression_report_sha256':digest(folder/'regressions.json'),
            'source_refactor_report_sha256':digest(folder/'refactor_check.json'),
            'replay_evidence_sha256':digest(ROOT/'artifacts/row_pipeline/evidence.json')}
    (folder/'evidence.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='golden_input_bindings'}))


if __name__=='__main__':main()
