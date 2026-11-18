import json,gzip
from shapely.geometry import shape
def load(fn='/workspace/ru/all_before.jsonl.gz', geom=True):
    out=[]
    for l in gzip.open(fn,'rt'):
        r=json.loads(l)
        lo,hi=r['valid_period'][1:11], r['valid_period'][12:22] or '9999-12-31'
        r['lo'],r['hi']=lo,hi
        if geom: r['g']=shape(r['geom'])
        out.append(r)
    return out
