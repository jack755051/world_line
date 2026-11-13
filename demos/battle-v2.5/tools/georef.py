"""把「從公有領域地圖讀出來的像素座標」配準成經緯度。
用法（在 demo 根目錄）：python tools/georef.py battles/<id>/digitized/<name>.readings.json
讀  *.readings.json：control_points（城鎮：像素＋經緯度）、features（部隊標註：像素、對應的 unit_id）
寫  同名 .json：每個 feature 的經緯度、配準誤差、和展示頁原本位置的差距
做法：經度、緯度各用像素座標的二次多項式擬合（地圖投影未標示，二次項足以吸收圓錐投影的彎曲）。
誤差：對每個控制點做「拿掉自己再擬合」的留一檢驗，取誤差的中位數與 95 百分位——這才是沒當控制點的地方大概會差多少。
      殘差特別大的控制點（> 3 倍中位數且 > 15 公里）會列出來：通常是讀錯圓點或座標查錯，要人工看。
"""
import json, sys, math, os
import numpy as np

path = sys.argv[1]; R = json.load(open(path)); bid = path.split('/')[1]
names = list(R['control_points']); P = np.array([R['control_points'][n]['px'] for n in names], float); G = np.array([R['control_points'][n]['lonlat'] for n in names], float)
c0 = P.mean(0); s0 = P.std()
def design(p): x, y = (p[:, 0] - c0[0]) / s0, (p[:, 1] - c0[1]) / s0; return np.stack([np.ones_like(x), x, y, x * x, x * y, y * y], 1)
def fit(p, g): return np.linalg.lstsq(design(p), g, rcond=None)[0]
def km(a, b): la = math.radians((a[1] + b[1]) / 2); return math.hypot((a[0] - b[0]) * 111.32 * math.cos(la), (a[1] - b[1]) * 110.57)
C = fit(P, G); pred = design(P) @ C
res = [km(pred[i], G[i]) for i in range(len(names))]
loo = []
for i in range(len(names)):
    m = np.arange(len(names)) != i; Ci = fit(P[m], G[m]); loo.append(km((design(P[i:i + 1]) @ Ci)[0], G[i]))
med, p95 = float(np.median(loo)), float(np.percentile(loo, 95))
bad = [(names[i], round(loo[i], 1)) for i in range(len(names)) if loo[i] > max(15, 3 * med)]
B = json.load(open(f'battles/{bid}/battle.json')); kd = R.get('applies_to_keyframe')
cur = {p['unit_id']: p for p in B['positions'] if p['date'] == kd}
feats = []
for f in R['features']:
    ll = (design(np.array([f['px']], float)) @ C)[0]; o = {'label': f['label'], 'unit_id': f['unit_id'], 'px': f['px'], 'lonlat': [round(float(ll[0]), 3), round(float(ll[1]), 3)]}
    if f['unit_id'] in cur: c = cur[f['unit_id']]; o['was'] = c.get('was') or [c['lng'], c['lat']]; o['moved_km'] = round(km(ll, o['was']), 1)   # was＝手擺的原值（battle.json 已套用過數位化時，原值存在 was 欄位）
    else: o['was'] = None
    feats.append(o)
out = {'source': R['source'], 'date': R['date'], 'applies_to_keyframe': kd, 'method': R['method'],
       'fit': {'model': '二次多項式', 'control_points': len(names), 'residual_median_km': round(float(np.median(res)), 1), 'loo_median_km': round(med, 1), 'loo_p95_km': round(p95, 1), 'suspect_control_points': bad},
       # 位置精度＝配準誤差（留一 95 百分位）＋讀圖誤差＋「標註框不等於部隊實際範圍」；最後一項最大，保守估 20 公里
       'precision_m': int(round((p95 + 20) * 1000, -3)), 'features': feats, 'unresolved': R.get('unresolved', [])}
json.dump(out, open(path.replace('.readings.json', '.json'), 'w'), ensure_ascii=False, indent=1)
mv = [f['moved_km'] for f in feats if f.get('moved_km') is not None]
print(f"控制點 {len(names)}｜殘差中位數 {out['fit']['residual_median_km']} km｜留一中位數 {med:.1f} km、95% {p95:.1f} km｜可疑控制點 {bad}")
print(f"部隊 {len(feats)}（展示頁有對應 {len(mv)}）｜和原本手擺位置的差距：中位數 {np.median(mv):.0f} km、最大 {max(mv):.0f} km")
for f in sorted(feats, key=lambda f: -(f.get('moved_km') or 0)): print(f"  {f['unit_id']:9s} {f['label'][:34]:34s} → {f['lonlat']}  原本 {f['was']}  差 {f.get('moved_km')} km")
