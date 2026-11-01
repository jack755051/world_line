"""1942 後期（1942-07-01～1942-12-31）南歐、東南歐與法國主權圖層的衍生幾何（沿用「事實國界」，同一天不重疊）。
- 義大利＝relation/2747829（1942-11-11 前的國界；OHM 2747832 多出的部分＝義軍佔領的法國領土，另畫非主權）。
- 義佔法國區＝2747832 − 2747829（科西嘉與法國東南部），1942-11-11 起，非主權。
- 法蘭西國（維琪）1942-11-11 起＝2747869，非主權（德國全面佔領法國本土）。
- FIXS_FR_EU＝FIXS_FR 只留北緯 40 度以北（法國本土）。OHM 2747869 仍含阿爾及利亞北部，但 1942-11-08 起盟軍登陸北非，那裡不屬德國佔領；FIXS_FR 第一次送出後撤回，改用 FIXS_FR_EU，阿爾及利亞 1942-11-11 起留白（待查證）。
- 羅馬尼亞＝2693255 − 外涅斯特里亞；外涅斯特里亞＝2693255 − 2693259（1940-06-28 前的羅馬尼亞），只取德涅斯特河以東的部分（質心經度 > 28.5），非主權。
- 希臘（軸心佔領）＝2920398 − 保加利亞 2695478（保加利亞佔領併入的色雷斯、馬其頓東部），非主權。
- 匈牙利 2692359、保加利亞 2695478、克羅埃西亞 2692713、阿爾巴尼亞 2695459 照 OHM；塞爾維亞軍事指揮官轄區 2692357、蒙特內哥羅總督轄區 2695479 為非主權。
"""
import json, os
from shapely.geometry import shape, mapping, MultiPolygon, Polygon, box
from shapely.ops import unary_union
from shapely.validation import make_valid
from shapely import set_precision
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
g = {f['id']: make_valid(shape(f['geometry'])) for f in json.load(open(os.path.join(ROOT, 'borders-ohm-1942-south.geojson')))['features']}
def polys(x):
    if isinstance(x, Polygon): return [x]
    if isinstance(x, MultiPolygon): return list(x.geoms)
    return [p for y in getattr(x, 'geoms', []) for p in polys(y)]
def clean(x, keep=lambda p: True):
    x = make_valid(set_precision(make_valid(x), 1e-4))
    return MultiPolygon([p for p in polys(x) if p.area > 1e-5 and keep(p)])
tr = clean(g[2693255].difference(g[2693259]), keep=lambda p: p.centroid.x > 28.5 and p.area > 0.01)
out = {
    'FIXS_IT': clean(g[2747829]),
    'FIXS_IT_OCC_FR': clean(g[2747832].difference(g[2747829])),
    'FIXS_FR': clean(g[2747869]),
    'FIXS_HU': clean(g[2692359]),
    'FIXS_RO': clean(g[2693255].difference(tr)),
    'FIXS_TRANSNISTRIA': tr,
    'FIXS_BG': clean(g[2695478]),
    'FIXS_GR': clean(g[2920398].difference(g[2695478])),
    'FIXS_HR': clean(g[2692713]),
    'FIXS_RS': clean(g[2692357]),
    'FIXS_ME': clean(g[2695479]),
    'FIXS_AL': clean(g[2695459]),
}
out['FIXS_FR_EU'] = clean(out['FIXS_FR'].intersection(box(-12, 40, 42, 72)))
ids = list(out)
for i in ids:
    for j in ids:
        if i < j and not ({i, j} == {'FIXS_IT_OCC_FR', 'FIXS_IT'}) and not ({i, j} == {'FIXS_FR', 'FIXS_FR_EU'}):
            a = out[i].intersection(out[j]).area
            assert a < 1e-3, (i, j, a)
assert out['FIXS_IT'].intersection(out['FIXS_IT_OCC_FR']).area < 1e-3
qa = {k: {'area_deg2': round(v.area, 3), 'polygons': len(v.geoms), 'bounds': [round(b, 2) for b in v.bounds]} for k, v in out.items()}
json.dump({'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'id': k, 'properties': {}, 'geometry': mapping(v)} for k, v in out.items()]},
          open(os.path.join(ROOT, 'borders-1942-south-derived.geojson'), 'w'), separators=(',', ':'))
json.dump(qa, open(os.path.join(ROOT, 'qa.json'), 'w'), ensure_ascii=False, indent=1)
print(json.dumps(qa, ensure_ascii=False))
