import json, datetime
from shapely.geometry import shape
from shapely.validation import make_valid
from shapely.ops import unary_union
F=json.load(open('/workspace/wl/fix40/exp_all.json'))['features']
R=[]
for f in F:
    if not f['geometry']: continue
    p=f['properties']; R.append(dict(id=f['id'],slug=p['slug'],rid=p['regime_id'],lo=p['lo'],hi=p['hi'] or '9999-12-31',st=p['status'],sev=p['start_ev'],eev=p['end_ev'],g=make_valid(shape(f['geometry']))))
BYID={r['id']:r for r in R}
def active(d, excl=()): return [r for r in R if r['lo']<=d<r['hi'] and r['id'] not in excl]
def prev(d): return (datetime.date.fromisoformat(d)-datetime.timedelta(days=1)).isoformat()
def pieces(g, m=1e-4):
    return sorted([p for p in getattr(g,'geoms',[g]) if p.area>m], key=lambda p:-p.area)
