"""P09 local image/layout and scalar compute authority, outside immutable P07."""
from pathlib import Path
import json
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from model_export.cartpole.accepted_arithmetic import accepted_format,load_accepted_arithmetic
from model_export.cartpole.freeze import load_frozen,sha256
from model_export.cartpole.fixed_point import FixedNCA,scalar_cell_delta
from model_export.cartpole.test_fixed_point import fixture
from tb.p08_primitives.run import clipped,rounded


def encode(words,width):
    mask=(1<<width)-1
    result=[]
    for v in words:
        v=int(v)
        if not -(1<<(width-1))<=v<(1<<(width-1)): raise ValueError('word outside signed width')
        result.append(f'{v & mask:0{(width+3)//4}x}')
    return '\n'.join(result)+'\n'


def decode(text,width):
    mask=(1<<width)-1
    values=[]
    for line in text.splitlines():
        v=int(line,16)
        if v>mask: raise ValueError('nonzero padding bits')
        values.append(v-(1<<width) if v&(1<<(width-1)) else v)
    return np.asarray(values,np.int64)


def words(model):
    return (np.concatenate([k.reshape(-1) for k in model.kernels]),
            np.concatenate([b.reshape(-1) for b in model.biases]))


def write_images(model,directory):
    directory.mkdir(parents=True,exist_ok=True)
    kernels,biases=words(model)
    paths=[]
    for name,data,width in (('kernels.mem',kernels,24),('biases.mem',biases,62)):
        text=encode(data,width)
        np.testing.assert_array_equal(decode(text,width),data)
        path=directory/name;path.write_text(text,encoding='ascii');paths.append(path)
    meta={'kernel_words':1860,'bias_words':56,'packed_bits':48112,
          'order':'layer; kernel row, column, input, output; biases layer/output',
          'encoding':'ASCII fixed-width two\u2019s-complement hex; kernel24/bias62; high padding bits zero',
          'kernel_offsets':[0,1080,1680],'bias_offsets':[0,20,50],
          'sha256':{p.name:sha256(p) for p in paths},'round_trip':'PASS'}
    (directory/'images.json').write_text(json.dumps(meta,indent=2,sort_keys=True)+'\n')
    return meta


def patch(grid,row,col):
    result=[]
    for kr in range(3):
        for kc in range(3):
            r,c=row+kr-1,col+kc-1
            result.extend([int(grid[0,r,c,ch]) if 0<=r<32 and 0<=c<32 else 0 for ch in range(6)])
    return result


def compute(model,values):
    if len(values)!=54: raise ValueError('54 patch words required')
    trace=[]
    for layer,(k,b) in enumerate(zip(model.kernels,model.biases)):
        matrix=k.reshape(len(values),-1);outputs=[]
        for out in range(matrix.shape[1]):
            acc,sat=clipped(sum(int(x)*int(matrix[i,out]) for i,x in enumerate(values))+int(b[out]),62)
            value,ysat=clipped(rounded(acc,relu=layer<2),32)
            trace.append((layer,out,acc,value,sat,ysat));outputs.append(value)
        values=outputs
    return values,trace


def active_cycles(lanes):
    if not 1<=lanes<=30: raise ValueError('invalid lane count')
    return sum(((outputs+lanes-1)//lanes)*fan for fan,outputs in ((54,20),(20,30),(30,6)))+2


def fixtures(restricted=False):
    load_frozen();manifest=load_accepted_arithmetic();fmt=accepted_format()
    if restricted:
        from reference.original_nca.core import load_tfjs_weights
        base=ROOT/'self-organized-control/demo/models/model2'
        frozen=load_frozen()
        if sha256(base/'group1-shard1of1.bin')!=frozen['weights']['blob_sha256']: raise ValueError('checkpoint changed')
        model=FixedNCA(load_tfjs_weights(base/'model.json',base/'group1-shard1of1.bin'),fmt)
        if [b['required_signed_bits'] for b in model.bounds]!=[58,57,57]: raise ValueError('unexpected frozen bounds')
        grids=[];bindings=[]
        for item in manifest['verification_vectors']:
            path=ROOT/item['restricted_vector_path']
            if sha256(path)!=item['sha256']: raise ValueError('vector hash mismatch')
            with np.load(path,allow_pickle=False) as saved:
                grids.append((saved['old_grid'].copy(),[tuple(map(int,c)) for c in saved['cells']],
                              {f'layer{i}_{suffix}':saved[f'layer{i}_{suffix}'].copy() for i in range(3) for suffix in ('accumulator','output')}))
            bindings.append({'path':item['restricted_vector_path'],'sha256':item['sha256']})
    else:
        model=FixedNCA(fixture(),fmt);rng=np.random.RandomState(909)
        grids=[(rng.randint(-(1<<31),1<<31,(1,32,32,6),dtype=np.int64),
                [(0,0),(0,31),(31,0),(31,31),(0,16),(16,16)],None)]
        bindings=[]
    result=[]
    for grid,coords,saved_trace in grids:
        _,golden=model.delta(grid,True)
        for row,col in coords:
            p=patch(grid,row,col);delta,trace=compute(model,p)
            np.testing.assert_array_equal(delta,scalar_cell_delta(model,grid,row,col))
            for layer,out,acc,value,_,_ in trace:
                assert acc==int(golden[f'layer{layer}_accumulator'][0,row,col,out])
                assert value==int(golden[f'layer{layer}_output'][0,row,col,out])
                if saved_trace:
                    assert acc==int(saved_trace[f'layer{layer}_accumulator'][0,row,col,out])
                    assert value==int(saved_trace[f'layer{layer}_output'][0,row,col,out])
            result.append((p,delta,trace))
    return model,result,bindings
