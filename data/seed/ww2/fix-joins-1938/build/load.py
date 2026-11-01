import json
from shapely.geometry import shape
from shapely.validation import make_valid
from shapely import STRtree
F=json.load(open('/workspace/wl/fix39/exp_all.json'))['features']
R=[]
for f in F:
    if not f['geometry']: continue
    p=f['properties']; R.append(dict(id=f['id'],slug=p['slug'],rid=p['regime_id'],lo=p['lo'],hi=p['hi'] or '9999-12-31',st=p['status'],g=make_valid(shape(f['geometry']))))
BYID={r['id']:r for r in R}
def active(d, excl=()):
    return [r for r in R if r['lo']<=d<r['hi'] and r['id'] not in excl]
