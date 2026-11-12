"""由 geo/land.geojson、geo/countries.geojson 產生 MapLibre 用的底圖小檔：
- geo/landc.geojson：陸地依顏色分三類（allied＝法比荷盧、uk＝英國、other），一個填色圖層畫完（省一層全畫面填色）
- geo/sea.geojson：海面遮罩，只做在戰區附近（經度 0.9 以東；疆域只會在這裡伸進海裡）
- geo/graticule.geojson：只畫在海上的經緯網"""
import json
from shapely.geometry import shape, box, mapping, LineString, MultiLineString
from shapely.ops import unary_union
BB = box(-6.5, 46.0, 13.0, 56.5)
land = shape(json.load(open('geo/land.geojson'))['features'][0]['geometry']).buffer(0)
cs = json.load(open('geo/countries.geojson'))['features']
def rnd(g, nd=4): return json.loads(json.dumps(mapping(g)), parse_float=lambda x: round(float(x), nd))
def dump(n, feats): json.dump({'type':'FeatureCollection','features':feats}, open('geo/'+n,'w'), separators=(',',':'))
al = unary_union([shape(f['geometry']) for f in cs if f['properties']['name'] in ('France','Belgium','Netherlands','Luxembourg')]).buffer(0).intersection(land)
uk = unary_union([shape(f['geometry']) for f in cs if f['properties']['name']=='United Kingdom']).buffer(0).intersection(land)
ot = land.difference(al.buffer(0.0005)).difference(uk.buffer(0.0005))
dump('landc.geojson', [{'type':'Feature','properties':{'k':k},'geometry':rnd(g.simplify(0.002))} for k,g in (('other',ot),('allied',al),('uk',uk))])
sea = box(0.9, 46.0, 13.0, 56.5).difference(land)
dump('sea.geojson', [{'type':'Feature','properties':{},'geometry':rnd(sea)}])
seaAll = BB.difference(land)
lines = [LineString([(lon, 46.0 + i*0.1) for i in range(106)]) for lon in range(-6, 14)] + [LineString([(-6.5 + i*0.1, lat) for i in range(196)]) for lat in range(46, 57)]
dump('graticule.geojson', [{'type':'Feature','properties':{},'geometry':rnd(MultiLineString(lines).intersection(seaAll))}])
print('ok')
