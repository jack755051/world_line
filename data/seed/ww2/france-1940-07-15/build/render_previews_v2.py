"""v2 疊圖預覽：各區不同顏色，疊在 Leconte（CC0）上＋總覽（TRF-GIS 1940 省界底圖）。"""
import json, numpy as np, shapefile, shapely
from PIL import Image, ImageDraw, ImageFont
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from shapely.geometry import shape, box
from shapely.ops import transform
from pyproj import Transformer
fm.fontManager.addfont('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
plt.rcParams['font.family'] = ['Noto Sans CJK JP', 'DejaVu Sans']
Image.MAX_IMAGE_PIXELS = None
T = '/workspace/world-line-ww2/trace/'
P = json.load(open(T + 'build/leconte_gcps.json'))['points']
px = np.array([[p[1], p[2]] for p in P], float); ll = np.array([[p[3], p[4]] for p in P], float)
feats = lambda a: np.stack([np.ones(len(a)), a[:, 0], a[:, 1], a[:, 0] ** 2, a[:, 0] * a[:, 1], a[:, 1] ** 2], 1)
cx = np.linalg.lstsq(feats(ll), px[:, 0], rcond=None)[0]; cy = np.linalg.lstsq(feats(ll), px[:, 1], rcond=None)[0]
def to_px(coords, s=1.0):
    F = feats(np.asarray(coords, float)[:, :2]); return list(zip((F @ cx) * s, (F @ cy) * s))

Z = json.load(open(T + 'build/zones-v2.json'))
STYLE = {  # key: (中文標籤, RGB)
    'main': ('本體軍事佔領區', (200, 30, 30)),
    'nord': ('北部兩省（布魯塞爾軍管）', (240, 140, 0)),
    'am':   ('亞爾薩斯－摩澤爾', (130, 40, 170)),
    'zi':   ('東北禁區（zone réservée）', (0, 130, 150)),
}
ain = shape(json.load(open(T + 'ain-ligne-demarcation.geojson'))['features'][0]['geometry'])
nel = shape(json.load(open(T + 'build/nordest-line.geojson'))['features'][0]['geometry'])
font = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 30, index=4)

src = Image.open(T + 'leconte-2015.3.1.230-recto.jpg').convert('RGB')
def draw_layers(base, s, x0=0, y0=0, width=3, fill_alpha=70):
    over = Image.new('RGBA', base.size, (0, 0, 0, 0)); d = ImageDraw.Draw(over)
    sh = lambda pts: [(a - x0, b - y0) for a, b in pts]
    for k, (_, c) in STYLE.items():
        for g in shape(Z[k]).geoms:
            d.polygon(sh(to_px(g.exterior.coords, s)), fill=c + (fill_alpha,))
            for h in g.interiors: d.polygon(sh(to_px(h.coords, s)), fill=(0, 0, 0, 0))
    for k, (_, c) in STYLE.items():
        for g in shape(Z[k]).geoms:
            d.line(sh(to_px(g.exterior.coords, s)), fill=c + (255,), width=width)
    d.line(sh(to_px(ain.coords, s)), fill=(0, 40, 160, 255), width=width)
    d.line(sh(to_px(nel.coords, s)), fill=(0, 0, 0, 255), width=width)
    return Image.alpha_composite(base.convert('RGBA'), over).convert('RGB')

# ── 1) 全圖疊 Leconte ──
s = 3000 / src.width
out = draw_layers(src.resize((3000, round(src.height * s)), Image.LANCZOS), s)
d2 = ImageDraw.Draw(out)
legend = [('DRAFT v2 待 Tai 檢查：1940 德國在法國本土的控制區（各區獨立紀錄）', (0, 0, 0))]
legend += [(f'■ {lab}', c) for lab, c in STYLE.values()]
legend += [('— 藍：分界線（照原圖描，Ain 資料集座標，對照 Leconte）', (0, 40, 160)),
           ('— 黑：ligne du Nord-Est（Perseus112 圖向量化，CC BY-SA，僅輔助）', (0, 0, 0)),
           ('其他邊界：TRF-GIS 1940 年省界（CC BY 4.0）；底圖 Leconte 館藏號 2015.3.1.230（CC0）', (0, 0, 0))]
y = 2230
d2.rectangle((40, y - 10, 1560, y + 40 * len(legend) + 10), fill=(255, 255, 255))
for i, (t, c) in enumerate(legend): d2.text((55, y + i * 40), t, fill=c, font=font)
out.quantize(colors=192, method=Image.Quantize.MEDIANCUT).save(T + 'preview-v2-overlay-leconte.png', optimize=True)

# ── 2) 原解析度局部 ──
def detail(name, lon, lat, half=450):
    (x, y), = to_px([(lon, lat)]); x0, y0 = int(x - half), int(y - half)
    c = src.crop((x0, y0, x0 + 2 * half, y0 + 2 * half))
    draw_layers(c, 1.0, x0, y0, width=4, fill_alpha=45).save(T + f'preview-v2-detail-{name}.png', optimize=True)
for n, lo, la in [('somme-amiens', 2.2, 49.95), ('chaumont-langres', 5.2, 47.95), ('dole-jura', 5.6, 46.95),
                  ('lille-nord', 3.0, 50.3), ('strasbourg-am', 7.3, 48.6), ('tours-cher', 1.2, 47.1)]:
    detail(n, lo, la)

# ── 3) 總覽：TRF-GIS 1940 省界底圖 ──
tr = Transformer.from_crs(2154, 4326, always_xy=True).transform
r = shapefile.Reader(T + 'trf-gis/DEPARTEMENTS_1940', encoding='utf-8')
fig, ax = plt.subplots(figsize=(13, 13))
ne = json.load(open(T + 'ne_10m_admin_0_countries.geojson'))
for f in ne['features']:
    if f['properties'].get('ADM0_A3') == 'FRA': continue
    g = shape(f['geometry'])
    if not g.intersects(box(-7, 41, 11, 52)): continue
    for p in (g.geoms if g.geom_type == 'MultiPolygon' else [g]): ax.fill(*p.exterior.xy, color='#eeeeee', ec='#aaaaaa', lw=.4)
for p in shape(Z['free_reference']).geoms: ax.fill(*p.exterior.xy, color='#a8d5a2', alpha=.6, ec='none')
for k, (lab, c) in STYLE.items():
    col = tuple(v / 255 for v in c)
    for i, p in enumerate(shape(Z[k]).geoms):
        ax.fill(*p.exterior.xy, color=col, alpha=.45, ec=col, lw=.8, label=lab if i == 0 else None)
for sr in r.shapeRecords():
    g = transform(tr, shape(sr.shape.__geo_interface__))
    for p in (g.geoms if g.geom_type == 'MultiPolygon' else [g]): ax.plot(*p.exterior.xy, color='#555555', lw=.3)
ax.plot(*ain.xy, color='#0028a0', lw=1.6, label='分界線（Ain／對照 Leconte）')
ax.plot(*nel.xy, color='black', lw=1.4, ls='--', label='ligne du Nord-Est（Perseus112，輔助）')
ax.legend(loc='lower left', fontsize=10, framealpha=.95)
ax.set_xlim(-5.5, 9.8); ax.set_ylim(41.2, 51.3); ax.set_aspect(1 / np.cos(np.radians(46.5)))
ax.set_title('DRAFT v2（待 Tai 檢查）1940 德國在法國本土的控制區：各區獨立紀錄\n綠色為自由區（僅參考，不送出）；細灰線為 TRF-GIS 1940 年省界', fontsize=12)
fig.savefig(T + 'preview-v2-overview.png', dpi=110, bbox_inches='tight')
print('ok')
