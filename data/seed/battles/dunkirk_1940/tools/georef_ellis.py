"""Ellis 態勢圖配準（純 Python，無 numpy）：把讀圖得到的像素座標換成經緯度並算誤差。

方法沿用展示頁 tools/georef.py（唯讀參考，未修改）：經度、緯度各以像素座標的二次多項式最小平方擬合；
留一法（leave-one-out）估「非控制點處」的誤差，取中位數與 95 百分位；殘差 > max(閾值, 3×中位數) 的控制點列為可疑。
精度 precision_m ＝ 留一 95 百分位 ＋ 標註框誤差（frame_km；部隊符號／標註框不等於部隊實際位置）。
門檻（主管 2026-11-13 12:05）：留一 95 百分位 ≤ 2 km 才算通過；未通過的圖只作參考，不得用於部隊位置或前線頂點（取代舊的 ≤ 5 km）。

用法：python3 -I georef_ellis.py ../digitized/<mapKey>.readings.json [--frame-km 3]
讀  readings.json：source、mapDate、control_points{名稱:{px:[x,y], lonlat:[lon,lat], osm:{type,id}}}、features[{label, px, side, unitKey?}]
     lines[{lineKey, label, lineKind, side, vertices:[{px, nearPlace?}]}]（R4 前線，可省略）
寫  同名 .json（去掉 .readings）：fit 統計、每個 feature 與 line 頂點的經緯度（estimate=推估）
"""
import json, math, sys

THRESHOLD_P95_KM = 2.0  # 主管 2026-11-13 12:05
from pathlib import Path


def solve(A, b):  # 高斯消去（小矩陣）
    n = len(A); M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c])); M[c], M[p] = M[p], M[c]
        if abs(M[c][c]) < 1e-12: raise ValueError("矩陣奇異（控制點不足或共線）")
        for r in range(n):
            if r != c:
                f = M[r][c] / M[c][c]
                M[r] = [M[r][k] - f * M[c][k] for k in range(n + 1)]
    return [M[i][n] / M[i][i] for i in range(n)]


def design(p, c0, s0):
    x, y = (p[0] - c0[0]) / s0, (p[1] - c0[1]) / s0
    return [1.0, x, y, x * x, x * y, y * y]


def fit(P, G, c0, s0):
    X = [design(p, c0, s0) for p in P]
    coef = []
    for d in range(2):
        A = [[sum(r[i] * r[j] for r in X) for j in range(6)] for i in range(6)]
        b = [sum(X[k][i] * G[k][d] for k in range(len(X))) for i in range(6)]
        coef.append(solve(A, b))
    return coef


def apply(coef, p, c0, s0):
    r = design(p, c0, s0)
    return [sum(a * b for a, b in zip(coef[0], r)), sum(a * b for a, b in zip(coef[1], r))]


def km(a, b):
    la = math.radians((a[1] + b[1]) / 2)
    return math.hypot((a[0] - b[0]) * 111.32 * math.cos(la), (a[1] - b[1]) * 110.57)


def pct(v, q):
    v = sorted(v); i = (len(v) - 1) * q; lo = int(math.floor(i)); hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (i - lo)


def main():
    path = Path(sys.argv[1]); frame_km = float(sys.argv[sys.argv.index("--frame-km") + 1]) if "--frame-km" in sys.argv else 3.0
    R = json.loads(path.read_text())
    names = list(R["control_points"]); P = [R["control_points"][n]["px"] for n in names]; G = [R["control_points"][n]["lonlat"] for n in names]
    c0 = [sum(p[0] for p in P) / len(P), sum(p[1] for p in P) / len(P)]
    s0 = math.sqrt(sum((p[0] - c0[0]) ** 2 + (p[1] - c0[1]) ** 2 for p in P) / (2 * len(P)))
    C = fit(P, G, c0, s0)
    res = [km(apply(C, P[i], c0, s0), G[i]) for i in range(len(P))]
    loo = []
    for i in range(len(P)):
        Pm = [p for j, p in enumerate(P) if j != i]; Gm = [g for j, g in enumerate(G) if j != i]
        loo.append(km(apply(fit(Pm, Gm, c0, s0), P[i], c0, s0), G[i]))
    med, p95 = pct(loo, 0.5), pct(loo, 0.95)
    bad = [(names[i], round(loo[i], 2)) for i in range(len(P)) if loo[i] > max(5.0, 3 * med)]
    passes = p95 <= THRESHOLD_P95_KM
    feats = []
    for f in R.get("features", []):
        ll = apply(C, f["px"], c0, s0)
        feats.append({**f, "lonlat": [round(ll[0], 4), round(ll[1], 4)], "estimate": "推估", "basis": "map-digitized", "usable": passes})
    lines = []
    for ln in R.get("lines", []):  # R4 前線：每條線的頂點 px → 經緯度（同一配準）
        vs = [{**v, "lonlat": [round(apply(C, v["px"], c0, s0)[0], 4), round(apply(C, v["px"], c0, s0)[1], 4)]} for v in ln.get("vertices", [])]
        lines.append({**ln, "vertices": vs, "estimate": "推估", "basis": "map-digitized", "usable": passes})
    out = {"source": R["source"], "mapKey": R.get("mapKey"), "mapDate": R.get("mapDate"), "method": R.get("method"),
           "threshold": {"rule": "留一法 95 百分位 ≤ 2 km（主管 2026-11-13 12:05）", "loo_p95_km": round(p95, 2), "passes": passes,
                         "use": "可用於部隊位置與前線頂點" if passes else "僅供參考：不得用於部隊位置或前線頂點"},
           "georef": {"tool": "data/seed/battles/dunkirk_1940/tools/georef_ellis.py", "model": "二次多項式（經、緯度各一）", "control_points": len(P),
                      "residual_median_km": round(pct(res, 0.5), 2), "loo_median_km": round(med, 2), "loo_p95_km": round(p95, 2),
                      "loo_max_km": round(max(loo), 2), "suspect_control_points": bad, "frame_km": frame_km},
           "precision_m": int(round((p95 + frame_km) * 1000, -2)),
           "precisionNote": f"留一法 95 百分位 {p95:.1f} km ＋ 標註框誤差 {frame_km:g} km；位置為部隊符號／標註框中心，非司令部精確位置",
           "control_points": {n: {**R["control_points"][n], "loo_km": round(loo[i], 2)} for i, n in enumerate(names)},
           "features": feats, "lines": lines, "unresolved": R.get("unresolved", [])}
    path.with_name(path.name.replace(".readings.json", ".json")).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"控制點 {len(P)}｜殘差中位數 {pct(res, .5):.2f} km｜留一中位數 {med:.2f} km、95% {p95:.2f} km、最大 {max(loo):.2f} km｜可疑 {bad}｜部隊 {len(feats)}｜precision_m {out['precision_m']}｜門檻 2 km：{'通過' if passes else '未通過（僅參考）'}")


if __name__ == "__main__":
    main()
