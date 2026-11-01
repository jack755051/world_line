import json, glob
from shapely.geometry import shape, box
from shapely.ops import unary_union
from shapely.validation import make_valid
import shapefile
G={f['id']: make_valid(shape(f['geometry'])) for f in json.load(open('../ww1-1908-1914-derived.geojson'))['features']}
recs=[]
for p in sorted(glob.glob('../requests/05-*.json')):
    r=json.load(open(p)); b=r['body']; recs.append((G[r['_geometryFrom']], b['validPeriod']['start'], b['validPeriod']['end'] or '9999'))
for r in json.load(open('../db-export/ww1_rows.json')):
    if r['slug']!='portuguese-republic': recs.append((make_valid(shape(r['geometry'])), r['start'], r['end'] or '9999'))
sf = shapefile.Reader('/workspace/wl/ohm/ne/ne_10m_land.shp')
F = box(-12, 28, 45, 62)
land = unary_union([make_valid(shape(s.__geo_interface__)).intersection(F) for s in sf.shapes() if box(*s.bbox).intersects(F)])
for d in ['1908-10-07','1913-01-01','1913-07-01','1913-09-01','1914-07-28']:
    cov=unary_union([g for g,s,e in recs if s<=d<e]); bl=land.difference(cov)
    big=sorted([p for p in getattr(bl,'geoms',[bl]) if p.area>0.05], key=lambda p:-p.area)[:8]
    print(d, round(bl.area,2), [(round(p.centroid.x,1),round(p.centroid.y,1),round(p.area,2)) for p in big])
