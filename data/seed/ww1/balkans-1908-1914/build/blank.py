import json
exec(open('make_requests.py').read().split('# ── 來源 ──')[0])
from shapely.geometry import box
import shapefile
sf = shapefile.Reader('/workspace/wl/ohm/ne/ne_10m_land.shp')
F = box(-12, 28, 45, 62)
land = unary_union([make_valid(shape(s.__geo_interface__)).intersection(F) for s in sf.shapes() if box(*s.bbox).intersects(F)])
exec(open('make_requests.py').read().split('# ── 主權紀錄 ──')[1].split('def write_sov')[0].replace('REC = []','REC=[]'), globals()) if False else None
