"""產出疊圖預覽：描線疊在 Leconte 分界線圖（CC0）上，以及 Natural Earth 底圖總覽。"""
import json, numpy as np
from PIL import Image, ImageDraw, ImageFont
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
fm.fontManager.addfont('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
plt.rcParams['font.family'] = ['Noto Sans CJK JP', 'DejaVu Sans']
from shapely.geometry import shape, box
Image.MAX_IMAGE_PIXELS = None
T = '/workspace/world-line-ww2/trace/'
P = json.load(open(T + 'build/leconte_gcps.json'))['points']
px = np.array([[p[1], p[2]] for p in P], float); ll = np.array([[p[3], p[4]] for p in P], float)
def feats(a):
    x, y = a[:, 0], a[:, 1]; return np.stack([np.ones_like(x), x, y, x * x, x * y, y * y], 1)
A = feats(ll); cx = np.linalg.lstsq(A, px[:, 0], rcond=None)[0]; cy = np.linalg.lstsq(A, px[:, 1], rcond=None)[0]
rmse = float(np.sqrt(((A @ cx - px[:, 0]) ** 2 + (A @ cy - px[:, 1]) ** 2).mean()))
def to_px(coords, s=1.0):
    a = np.asarray(coords, float)[:, :2]; F = feats(a); return list(zip((F @ cx) * s, (F @ cy) * s))

zone = shape(json.load(open(T + 'occupied-zone-1940-07-15.geojson'))['features'][0]['geometry'])
ref = json.load(open(T + 'build/reference-layers.geojson'))['features']
line = shape(ref[0]['geometry'])

# ── 1) 疊在 Leconte 圖上（縮到寬 3000 px） ──
src = Image.open(T + 'leconte-2015.3.1.230-recto.jpg').convert('RGB')
s = 3000 / src.width
base = src.resize((3000, round(src.height * s)), Image.LANCZOS)
over = Image.new('RGBA', base.size, (0, 0, 0, 0)); d = ImageDraw.Draw(over)
for g in zone.geoms:
    d.polygon(to_px(g.exterior.coords, s), fill=(200, 0, 0, 55))
for g in zone.geoms:
    d.line(to_px(g.exterior.coords, s), fill=(170, 0, 0, 255), width=3)
d.line(to_px(line.coords, s), fill=(0, 60, 220, 255), width=3)
for p in P:
    x, y = p[1] * s, p[2] * s; d.ellipse((x - 5, y - 5, x + 5, y + 5), outline=(0, 140, 0, 255), width=2)
out = Image.alpha_composite(base.convert('RGBA'), over).convert('RGB')
d2 = ImageDraw.Draw(out)
try: font = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 30, index=4)
except Exception: font = ImageFont.load_default()
legend = ['DRAFT 待 Tai 檢查：1940-07-15 德國在法國本土的軍事佔領區',
          '紅：描繪的佔領區（Natural Earth 10m 法國外框 ∩ Ain 分界線切割）',
          '藍：Ain 省「Ligne de démarcation」資料集（Licence Ouverte 2.0）',
          f'綠圈：配準控制點 {len(P)} 個，二次多項式，RMSE ≈ {rmse:.0f} px（原圖）≈ {rmse/5.5:.1f} km',
          '底圖：Leconte《Nouvelle carte de France… (ligne de démarcation)》CC0，館藏號 2015.3.1.230']
y = 2290
d2.rectangle((40, y - 10, 1500, y + 40 * len(legend) + 10), fill=(255, 255, 255))
for i, t in enumerate(legend): d2.text((55, y + i * 40), t, fill=(0, 0, 0), font=font)
out.quantize(colors=192, method=Image.Quantize.MEDIANCUT).save(T + 'preview-overlay-leconte.png', optimize=True)

# 分界線局部放大（原圖解析度）：檢查描線與圖上分界線是否吻合
def crop_full(name, lon, lat, half=450):
    (x, y), = to_px([(lon, lat)])
    x0, y0 = int(x - half), int(y - half)
    c = src.crop((x0, y0, x0 + 2 * half, y0 + 2 * half)).convert('RGBA')
    o = Image.new('RGBA', c.size, (0, 0, 0, 0)); dd = ImageDraw.Draw(o)
    sh = lambda pts: [(a - x0, b - y0) for a, b in pts]
    for g in zone.geoms:
        if g.intersects(box(lon - 1.5, lat - 1, lon + 1.5, lat + 1)):
            dd.line(sh(to_px(g.exterior.coords)), fill=(170, 0, 0, 230), width=3)
    dd.line(sh(to_px(line.coords)), fill=(0, 60, 220, 200), width=3)
    Image.alpha_composite(c, o).convert('RGB').save(T + f'preview-detail-{name}.png', optimize=True)
crop_full('tours-vierzon', 1.2, 47.1)
crop_full('moulins-chalon', 4.0, 46.7)
crop_full('mont-de-marsan', -0.6, 43.9)
crop_full('geneve-gex', 5.95, 46.3, 350)

# ── 2) 總覽（Natural Earth 底圖） ──
ne = json.load(open(T + 'ne_10m_admin_0_countries.geojson'))
fig, ax = plt.subplots(figsize=(12, 12))
for f in ne['features']:
    g = shape(f['geometry'])
    if not g.intersects(box(-7, 41, 10, 52)): continue
    for p in (g.geoms if g.geom_type == 'MultiPolygon' else [g]):
        ax.fill(*p.exterior.xy, color='#eeeeee', ec='#999999', lw=.5)
free = shape(ref[1]['geometry'])
for p in free.geoms: ax.fill(*p.exterior.xy, color='#7fbf7f', alpha=.5, ec='none')
for p in zone.geoms: ax.fill(*p.exterior.xy, color='#c0392b', alpha=.55, ec='#7b1d14', lw=.8)
ax.plot(*line.xy, color='#0b3cdc', lw=1.5)
for n, lo, la in [('Paris', 2.35, 48.86), ('Vichy', 3.43, 46.13), ('Bordeaux', -0.58, 44.84), ('Tours', 0.69, 47.39), ('Lyon', 4.84, 45.76), ('Genève', 6.14, 46.2)]:
    ax.plot(lo, la, 'ko', ms=3); ax.annotate(n, (lo, la), (4, 4), textcoords='offset points', fontsize=9)
ax.set_xlim(-6, 9.8); ax.set_ylim(41.2, 51.3); ax.set_aspect(1 / np.cos(np.radians(46.5)))
ax.set_title('DRAFT（待 Tai 檢查）German military occupation zone, 1940-07-15\n'
             'red = traced zone; green = free zone (reference only); blue = Ain demarcation line', fontsize=11)
fig.savefig(T + 'preview-overview.png', dpi=110, bbox_inches='tight')
print('rmse', round(rmse, 1))
