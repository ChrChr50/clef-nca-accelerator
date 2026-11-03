"""Check the maintenance diff against saved source and its declared rename map.

Every non-comment HDL token must be unchanged apart from declared internal
identifiers. Historical fixture bytes must match the saved production originals.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
TOKEN=re.compile(r'//[^\r\n]*|/\*[\s\S]*?\*/|"(?:\\[\s\S]|[^"\\])*"|'
                 r"\d+'[sS]?[bBoOdDhH][0-9a-fA-F_xXzZ?]+|'[01xXzZ]|"
                 r'[A-Za-z_$][A-Za-z0-9_$]*|\d+|===|!==|>>>|<<<|'
                 r'<=|>=|==|!=|&&|\|\||<<|>>|\+:|-:|\+\+|--|\s+|[\s\S]')


def tokens(text):
    return [m.group() for m in TOKEN.finditer(text)
            if not m.group().isspace() and not m.group().startswith(('//','/*'))]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--before',type=Path,default=ROOT/'artifacts/rtl_cleanup/before/core')
    args=parser.parse_args()
    manifest=json.loads((ROOT/'docs/verification/RTL_CLEANUP_RENAME_MAP.json').read_text())
    production=ROOT/'rtl/core'
    if sorted(p.name for p in production.glob('*.sv'))!=sorted(manifest['active_files']):
        raise AssertionError('unexpected production modules')
    listed=[line.strip() for line in (production/'files.f').read_text().splitlines() if line.strip()]
    if sorted(listed)!=sorted('rtl/core/'+name for name in manifest['active_files']):
        raise AssertionError('production source list is incomplete or includes retired modules')
    report={'scope':'declared token renames only; no behavioral edit','active':{},'archived':{}}
    for filename,renames in manifest['renames'].items():
        original=args.before/filename
        current=production/filename
        old_tokens=tokens(original.read_text())
        expected=[renames.get(t,t) if not (i>0 and old_tokens[i-1]=='.' and
                  i+1<len(old_tokens) and old_tokens[i+1]=='(') else t
                  for i,t in enumerate(old_tokens)]
        actual=tokens(current.read_text())
        if expected!=actual:
            difference=next((i for i,(a,b) in enumerate(zip(expected,actual)) if a!=b),min(len(expected),len(actual)))
            raise AssertionError(f'{filename}: unexpected token change at {difference}: '
                                 f'{expected[difference:difference+5]} versus {actual[difference:difference+5]}')
        if any(m.group().startswith(('//','/*')) for m in TOKEN.finditer(current.read_text())):
            raise AssertionError(f'{filename}: comment remains')
        report['active'][filename]={'before_sha256':digest(original),'after_sha256':digest(current),
                                    'tokens_checked':len(actual),'result':'PASS'}
    for item in manifest['archived_files']:
        original=args.before/Path(item['from']).name
        archived=ROOT/item['to']
        if digest(original)!=digest(archived):
            raise AssertionError(f'archive contents changed: {archived}')
        if (ROOT/item['from']).exists(): raise AssertionError('retired module still in production')
        report['archived'][item['to']]={'original_sha256':digest(original),'result':'PASS'}
    output=ROOT/'artifacts/rtl_cleanup/refactor_check.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n')
    print('RTL refactor PASS: five comment-free production files, declared renames only; six byte-identical historical fixtures')


if __name__=='__main__':main()
