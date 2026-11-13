"""把 Natural Earth 1:10m（公有領域）裁到戰區範圍，簡化後存成小檔 GeoJSON。
用法：python tools/clip_geo.py /path/to/ne_dir
"""
import json, sys
from shapely.geometry import shape, box, mapping
from shapely.ops import unary_union
src = sys.argv[1]
BB = box(-6.5, 46.0, 13.0, 56.5)
OUT = 'geo/'
def load(n): return json.load(open(f'{src}/{n}.geojson'))
def rnd(g, nd=4):
    return json.loads(json.dumps(mapping(g)), parse_float=lambda x: round(float(x), nd))
def dump(name, feats):
    json.dump({'type':'FeatureCollection','features':feats}, open(OUT+name,'w'), separators=(',',':'), ensure_ascii=False)
# land
land = unary_union([shape(f['geometry']).intersection(BB) for f in load('ne_10m_land')['features'] if shape(f['geometry']).intersects(BB)])
land = land.simplify(0.004, preserve_topology=True)
dump('land.geojson', [{'type':'Feature','properties':{},'geometry':rnd(land)}])
# countries (modern borders, approximate for 1940)
keep = {'France','Belgium','Netherlands','Luxembourg','Germany','United Kingdom','Switzerland','Denmark','Austria','Czechia','Italy','Liechtenstein'}
feats=[]
for f in load('ne_10m_admin_0_countries')['features']:
    n=f['properties']['ADMIN']
    g=shape(f['geometry'])
    if n in keep and g.intersects(BB):
        g=g.intersection(BB).simplify(0.004, preserve_topology=True)
        feats.append({'type':'Feature','properties':{'name':n,'iso':f['properties']['ISO_A3']},'geometry':rnd(g)})
dump('countries.geojson', feats)
# land borders
feats=[]
for f in load('ne_10m_admin_0_boundary_lines_land')['features']:
    g=shape(f['geometry'])
    if g.intersects(BB):
        feats.append({'type':'Feature','properties':{},'geometry':rnd(g.intersection(BB).simplify(0.003))})
dump('borders.geojson', feats)
# rivers (scalerank <= 8)
feats=[]
for f in load('ne_10m_rivers_lake_centerlines')['features']:
    g=shape(f['geometry']); p=f['properties']
    if g.intersects(BB) and (p.get('scalerank') or 10) <= 9 and p.get('featurecla','').startswith('River'):
        feats.append({'type':'Feature','properties':{'name':p.get('name'),'sr':p.get('scalerank')},'geometry':rnd(g.intersection(BB).simplify(0.003))})
dump('rivers.geojson', feats)
print('rivers', sorted({f['properties']['name'] for f in feats if f['properties']['name']}))
