"""戰役態勢圖配準（共用工具，純 Python，無 numpy）：把讀圖得到的像素座標換成經緯度並算誤差。
由 data/seed/battles/dunkirk_1940/tools/georef_ellis.py 一般化而來（Tai 2026-11-13 13:39 流程修正第 2 項）；戰役代碼當參數，
各戰役只留設定檔 data/seed/battles/<battle>/georef.config.json：{"thresholdP95Km", "thresholdRule", "defaultFrameKm", "maps": {mapKey: {"frameKm"}}}。

方法沿用展示頁 tools/georef.py（唯讀參考，未修改）：經度、緯度各以像素座標的二次多項式最小平方擬合；
留一法（leave-one-out）估「非控制點處」的誤差，取中位數與 95 百分位；殘差 > max(閾值, 3×中位數) 的控制點列為可疑。
精度 precision_m ＝ 留一 95 百分位 ＋ 標註框誤差（frame_km；部隊符號／標註框不等於部隊實際位置）。
門檻（主管 2026-11-13 12:05）：留一 95 百分位 ≤ 2 km 才算通過；未通過的圖只作參考，不得用於部隊位置或前線頂點（取代舊的 ≤ 5 km）。

全戰區圖（Tai 2026-11-17 拍板，docs/source-rules.md「讀圖配準門檻」）：readings.json 頂層有
     "scaleClass": {"class": "theatre", "basis": "…", "decidedBeforeFit": true} 的圖走另一級門檻：
     模型改用仿射（經、緯度各 3 個係數；這類圖的控制點少，二次式的留一法不成立）；留一 95 百分位 ≤ 15 km 才通過；
     通過後只有集團軍群、集團軍、裝甲師的標註可用（usable），前線頂點一律不可用；輸出 coarse=true，展示頁不拿它算領地。
     分級必須在配準前依圖本身決定（圖幅橫跨超過 200 公里、畫的是集團軍層級的配置），不得因為過不了 2 km 才改級：
     decidedBeforeFit 不是 true 一律僅供參考。

用法：python3 -I tools/battles/georef.py <battle> [mapKey ...]          # 不給 mapKey 則處理 digitized/ 下全部 *.readings.json
      python3 -I tools/battles/georef.py --file <path/to/x.readings.json> [--frame-km 3]   # 舊用法（單檔）
讀  readings.json：source、mapDate、control_points{名稱:{px:[x,y], lonlat:[lon,lat], osm:{type,id}}}、features[{label, px, side, unitKey?}]
     lines[{lineKey, label, lineKind, side, vertices:[{px, nearPlace?}]}]（R4 前線，可省略）
控制點排除規則（主管 2026-11-13 15:33）：排除控制點的理由必須在看殘差之前就定好。readings.json 以
     "controlPointExclusions": [{"name", "reason", "decidedBeforeResiduals": true|false}] 記錄每個被排除的點；
     任何一點 decidedBeforeResiduals 不是 true（看過殘差後才排除，或未記錄），或頂層 "referenceOnly": {"reason"} 存在，
     本工具一律把 threshold.passes 設為 false、referenceOnly 設為 true（即使 P95 ≤ 門檻），features／lines 的 usable 皆為 false。
寫  同名 .json（去掉 .readings）：fit 統計、每個 feature 與 line 頂點的經緯度（estimate=推估）
"""
import json, math, sys

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
THRESHOLD_P95_KM = 2.0  # 預設；以戰役 georef.config.json 為準（Dunkirk：主管 2026-11-13 12:05）
THRESHOLD_RULE = "留一法 95 百分位 ≤ 2 km（主管 2026-11-13 12:05）"


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


THEATRE_P95_KM = 15.0
THEATRE_RULE = "全戰區圖：留一法 95 百分位 ≤ 15 km，只用於集團軍群、集團軍、裝甲師（Tai 2026-11-17）"
ORDER = 6  # 模型係數個數：6＝二次多項式；3＝仿射（全戰區圖）


def design(p, c0, s0):
    x, y = (p[0] - c0[0]) / s0, (p[1] - c0[1]) / s0
    return [1.0, x, y, x * x, x * y, y * y][:ORDER]


def theatre_ok(f):
    return f.get("echelon") in ("army_group", "army") or (f.get("echelon") == "division" and f.get("armoured") is True)


def fit(P, G, c0, s0):
    X = [design(p, c0, s0) for p in P]
    coef = []
    for d in range(2):
        n = ORDER
        A = [[sum(r[i] * r[j] for r in X) for j in range(n)] for i in range(n)]
        b = [sum(X[k][i] * G[k][d] for k in range(len(X))) for i in range(n)]
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


def run(path, frame_km, threshold_km=None, rule=None):
    threshold_km = THRESHOLD_P95_KM if threshold_km is None else threshold_km; rule = rule or THRESHOLD_RULE
    R = json.loads(path.read_text())
    global ORDER
    sc = R.get("scaleClass") or {}
    theatre = sc.get("class") == "theatre"
    ORDER = 3 if theatre else 6
    if theatre: threshold_km, rule = THEATRE_P95_KM, THEATRE_RULE
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
    p95_ok = p95 <= threshold_km
    excl = R.get("controlPointExclusions", [])
    posthoc = [x.get("name") for x in excl if x.get("decidedBeforeResiduals") is not True]
    ref_only = []
    if posthoc:
        ref_only.append(f"有控制點在看過殘差後才排除（{'、'.join(map(str, posthoc))}），依主管 2026-11-13 15:33 規則整張圖僅供參考")
    if theatre and sc.get("decidedBeforeFit") is not True:
        ref_only.append("全戰區圖的分級不是在配準前決定的（scaleClass.decidedBeforeFit 不是 true）")
    if R.get("referenceOnly"):
        ref_only.append(R["referenceOnly"].get("reason", "readings 標記 referenceOnly"))
    passes = p95_ok and not ref_only
    feats = []
    for f in R.get("features", []):
        ll = apply(C, f["px"], c0, s0)
        feats.append({**f, "lonlat": [round(ll[0], 4), round(ll[1], 4)], "estimate": "推估", "basis": "map-digitized", "usable": passes and (not theatre or theatre_ok(f))})
    lines = []
    for ln in R.get("lines", []):  # R4 前線：每條線的頂點 px → 經緯度（同一配準）
        vs = [{**v, "lonlat": [round(apply(C, v["px"], c0, s0)[0], 4), round(apply(C, v["px"], c0, s0)[1], 4)]} for v in ln.get("vertices", [])]
        lines.append({**ln, "vertices": vs, "estimate": "推估", "basis": "map-digitized", "usable": passes and not theatre})
    out = {"source": R["source"], "mapKey": R.get("mapKey"), "mapDate": R.get("mapDate"), "method": R.get("method"),
           "threshold": {"rule": rule, "loo_p95_km": round(p95, 2), "p95Passes": p95_ok, "passes": passes,
                         "referenceOnly": bool(ref_only), "referenceOnlyReasons": ref_only,
                         "controlPointExclusions": excl,
                         "use": ("只可用於集團軍群、集團軍、裝甲師的位置；不得用於前線頂點，不得用來推算領地" if theatre else "可用於部隊位置與前線頂點") if passes else "僅供參考：不得用於部隊位置或前線頂點"},
           "georef": {"tool": "tools/battles/georef.py", "model": "仿射（經、緯度各 3 個係數）" if theatre else "二次多項式（經、緯度各一）", "control_points": len(P),
                      "residual_median_km": round(pct(res, 0.5), 2), "loo_median_km": round(med, 2), "loo_p95_km": round(p95, 2),
                      "loo_max_km": round(max(loo), 2), "suspect_control_points": bad, "frame_km": frame_km},
           **({"scaleClass": sc, "coarse": True} if theatre else {}),
           "precision_m": int(round((p95 + frame_km) * 1000, -2)),
           "precisionNote": f"留一法 95 百分位 {p95:.1f} km ＋ 標註框誤差 {frame_km:g} km；位置為部隊符號／標註框中心，非司令部精確位置",
           "control_points": {n: {**R["control_points"][n], "loo_km": round(loo[i], 2)} for i, n in enumerate(names)},
           "features": feats, "lines": lines, "unresolved": R.get("unresolved", [])}
    path.with_name(path.name.replace(".readings.json", ".json")).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"控制點 {len(P)}｜殘差中位數 {pct(res, .5):.2f} km｜留一中位數 {med:.2f} km、95% {p95:.2f} km、最大 {max(loo):.2f} km｜可疑 {bad}｜部隊 {len(feats)}｜precision_m {out['precision_m']}｜門檻 {threshold_km:g} km：{'通過' if passes else ('P95 達標但強制僅參考：' + '；'.join(ref_only) if p95_ok else '未通過（僅參考）')}")
    return out


def main(argv):
    if "--file" in argv:
        fk = float(argv[argv.index("--frame-km") + 1]) if "--frame-km" in argv else 3.0
        return run(Path(argv[argv.index("--file") + 1]), fk)
    battle = argv[0]; D = REPO / "data" / "seed" / "battles" / battle
    cfg_p = D / "georef.config.json"
    cfg = json.loads(cfg_p.read_text()) if cfg_p.exists() else {}
    keys = argv[1:] or sorted(p.name[:-len(".readings.json")] for p in (D / "digitized").glob("*.readings.json"))
    for k in keys:
        m = cfg.get("maps", {}).get(k, {})
        print(k, end="：")
        run(D / "digitized" / (k + ".readings.json"), float(m.get("frameKm", cfg.get("defaultFrameKm", 3.0))),
            cfg.get("thresholdP95Km"), cfg.get("thresholdRule"))


if __name__ == "__main__":
    main(sys.argv[1:])
