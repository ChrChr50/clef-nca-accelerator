"""Run retained component tests after the source-only RTL cleanup."""
import json
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]


def main():
    output=ROOT/'artifacts/rtl_cleanup'
    output.mkdir(parents=True,exist_ok=True)
    temporary=output/'testtmp'
    temporary.mkdir(exist_ok=True)
    environment=dict(os.environ,TMP=str(temporary),TEMP=str(temporary))
    commands=[
        ['tb/rtl_cleanup/check_refactor.py'],
        ['tb/row_pipeline/window.py'],
        ['tb/row_stage/run.py'],
        ['tb/row_stage/memory.py'],
        ['tb/row_stage/audit_transcripts.py'],
        ['tb/p08_primitives/run.py'],
        ['tb/p08_primitives/run.py','--restricted'],
        ['tb/p09_local_rule/run.py'],
        ['tb/p09_local_rule/run.py','--restricted'],
        ['-m','unittest','tb.p09_local_rule.test_support','tb.p08_primitives.test_vectors',
         'model_export.cartpole.test_fixed_point','model_export.cartpole.test_accepted_arithmetic',
         'model_export.cartpole.test_export_local','model_export.cartpole.test_row16_candidate','-q'],
        ['-m','unittest','discover','-s','reference/original_nca/tests','-q'],
        ['-m','unittest','discover','-s','sw/cartpole/tests','-q'],
        ['-m','unittest','discover','-s','reference/hanoi/tests','-q'],
        ['-m','unittest','discover','-s','training/hanoi_nca/tests','-q'],
        ['-m','unittest','model_export.cartpole.test_exact_blas','experiments.row16_validation.test_resume','-q'],
        ['experiments/p07_cartpole/check_vectors.py'],
        ['reference/original_nca/tools/verify_upstream.py','--upstream','self-organized-control'],
        ['scripts/run_smoke.py']]
    results=[]
    for index,arguments in enumerate(commands):
        command=[sys.executable,*arguments]
        log=output/f'regression{index:02d}.log'
        with log.open('w') as stream:
            process=subprocess.run(command,cwd=ROOT,env=environment,stdout=stream,
                                   stderr=subprocess.STDOUT,text=True,timeout=240)
        results.append({'command':command,'returncode':process.returncode,
                        'log':str(log.relative_to(ROOT))})
        (output/'regressions.json').write_text(json.dumps(results,indent=2)+'\n')
        if process.returncode:
            raise RuntimeError(f'{arguments}: {log.read_text()[-3000:]}')
        print(f'PASS {index+1}/{len(commands)}: {" ".join(arguments)}',flush=True)


if __name__=='__main__':main()
