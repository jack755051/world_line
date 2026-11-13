"""地圖標註兩次獨立判讀比對（共用工具；Tai 2026-11-13 13:39 流程修正第 3 項）。

第一次判讀＝digitized/<mapKey>.readings.json 的 features；第二次判讀＝checks/label-reading2/<mapKey>.json
（另一個判讀者在隔離資料夾只看原圖重讀，沒看過第一次結果）。
配對：以像素距離最近者配對（容差＝圖寬 × 1.5%，Ellis 1200 px 圖約 18 px），一對一貪婪配對。
比對：標註文字去大小寫、空白、句點、撇號後須完全相同；含「?」視為不一致。
結果：第一次判讀每筆加 labelCheck = {"status": "agree"|"待查證", "reading2Label", "reason"}；
      第二次判讀有、第一次沒有的標註列為 reading2Only（可能漏讀），寫入報告並記 gaps.json（kind=map_label_reading_mismatch）。
用法：python3 -I tools/battles/compare_readings.py <battle> [--apply]
報告：checks/label-readings.json
"""
import json, math, re, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TODAY = __import__("datetime").date.today().isoformat()
BELOW_DIV = ("other", "brigade", "regiment", "battalion", "group")  # 低於師級或非正規編組（第二次判讀 division-and-above 範圍外）


def nl(s):
    return re.sub(r"[\s.'’`\"]", "", (s or "").upper())


def width(img):
    try:
        out = subprocess.run(["sips", "-g", "pixelWidth", str(img)], capture_output=True, text=True).stdout
        return int(re.search(r"pixelWidth:\s*(\d+)", out).group(1))
    except Exception:
        return 1200


def main():
    battle = sys.argv[1]; apply = "--apply" in sys.argv
    D = REPO / "data" / "seed" / "battles" / battle
    rep, tot = {}, {"reading1": 0, "agree": 0, "labelDiffers": 0, "notFoundInReading2": 0, "reading2Only": 0, "mapsWithoutReading2": []}
    gaps = []
    for p in sorted((D / "digitized").glob("*.readings.json")):
        mk = p.name[:-len(".readings.json")]; R = json.loads(p.read_text()); F1 = R.get("features", [])
        q = D / "checks" / "label-reading2" / (mk + ".json")
        if not q.exists():  # 尚無第二次判讀：全部標待查證（未檢查，不算不一致）
            tot["mapsWithoutReading2"].append(mk); tot["unchecked"] = tot.get("unchecked", 0) + len(F1)
            if apply:
                for f in F1: f["labelCheck"] = {"status": "待查證", "reading2Label": None, "reason": "尚無第二次判讀"}
                p.write_text(json.dumps(R, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            continue
        R2 = json.loads(q.read_text()); F2 = R2.get("features", [])
        div_only = R2.get("scope") == "division-and-above"
        img = D / "maps" / Path(R2.get("image", "")).name
        tol = width(img) * 0.015 if img.exists() else 18
        pairs = sorted(((math.dist(a["px"], b["px"]), i, j) for i, a in enumerate(F1) for j, b in enumerate(F2)), key=lambda t: t[0])
        used1, used2, m = set(), set(), {}
        for dd, i, j in pairs:
            if dd > tol: break
            if i in used1 or j in used2: continue
            used1.add(i); used2.add(j); m[i] = (j, dd)
        # 第二輪：文字相同、但距離在容差 1–3 倍之間者也配對（文字一致，位置差另標 pxCheck 待查證）
        for dd, i, j in pairs:
            if dd <= tol: continue
            if dd > 3 * tol: break
            if i in used1 or j in used2 or nl(F1[i]["label"]) != nl(F2[j]["label"]): continue
            used1.add(i); used2.add(j); m[i] = (j, dd)
        # 第三輪：一方把標註拆成兩段或只抄一部分（如「XIV CORPS」＋「(KLEIST GROUP)」、「1ST ARMY」⊂「PART OF FRENCH 1ST ARMY」）
        joined = {}
        for i, a in enumerate(F1):
            if i in used1: continue
            near = sorted((math.dist(a["px"], b["px"]), j) for j, b in enumerate(F2) if j not in used2 and math.dist(a["px"], b["px"]) <= 3 * tol)
            la = nl(a["label"])
            hit = next((j for dd, j in near if min(len(la), len(nl(F2[j]["label"]))) >= 3 and (la in nl(F2[j]["label"]) or nl(F2[j]["label"]) in la)), None)
            if hit is not None:
                used1.add(i); used2.add(hit); m[i] = (hit, math.dist(a["px"], F2[hit]["px"])); joined[i] = "一方只抄部分文字"; continue
            for x in range(len(near)):
                for y in range(len(near)):
                    j1, j2 = near[x][1], near[y][1]
                    if j1 != j2 and nl(F2[j1]["label"]) + nl(F2[j2]["label"]) == la and "?" not in la:
                        used1.add(i); used2.update((j1, j2)); m[i] = (j1, near[x][0]); joined[i] = f"第二次判讀拆成兩段：「{F2[j1]['label']}」＋「{F2[j2]['label']}」"; break
                if i in used1: break
        unres = R.get("unresolved", [])
        rows = []
        for i, f in enumerate(F1):
            if f.get("origin") == "second-reading-only":  # 只有第二次判讀讀到、已併入的標註：無第一次判讀可比，一律待查證
                lc = {"status": "待查證", "reading2Label": f["label"], "reason": "僅第二次判讀讀到（第一次未列），併入待查證"}
                tot["importedFromReading2"] = tot.get("importedFromReading2", 0) + 1
                if apply: f["labelCheck"] = lc
                rows.append({"label": f["label"], "px": f["px"], **lc})
                gaps.append({"target": f"map-label:{mk}:{f['label']}@{f['px'][0]},{f['px'][1]}", "kind": "map_label_reading_mismatch",
                             "note": f"{mk} 標註「{f['label']}」僅第二次判讀讀到，第一次未列；依主管 2026-11-13 14:03 併入，待查證",
                             "checkedOn": TODAY, "tool": "tools/battles/compare_readings.py"})
                continue
            tot["reading1"] += 1
            if i in m:
                b = F2[m[i][0]]; same = (nl(f["label"]) == nl(b["label"]) or i in joined) and "?" not in f["label"] + b["label"]
                lc = {"status": "agree" if same else "待查證", "reading2Label": b["label"], "reason": None if same else "兩次判讀文字不同", "distPx": round(m[i][1], 1)}
                if i in joined and same: lc["note"] = joined[i]
                if m[i][1] > tol: lc["pxCheck"] = "待查證"; lc["pxNote"] = f"兩次判讀位置差 {m[i][1]:.0f} px（> 容差 {tol:.0f} px）"
                tot["agree" if same else "labelDiffers"] += 1
            elif div_only and f.get("echelon") in BELOW_DIV:
                lc = {"status": "待查證", "reading2Label": None, "reason": "第二次判讀範圍未含旅／團／營級（未檢查）"}
                tot["unchecked"] = tot.get("unchecked", 0) + 1
            else:
                lc = {"status": "待查證", "reading2Label": None, "reason": "第二次判讀在附近沒有讀到標註"}
                tot["notFoundInReading2"] += 1
            if apply: f["labelCheck"] = lc
            rows.append({"label": f["label"], "px": f["px"], **lc})
            if lc["status"] != "agree" and "未檢查" not in (lc["reason"] or ""):
                gaps.append({"target": f"map-label:{mk}:{f['label']}@{f['px'][0]},{f['px'][1]}", "kind": "map_label_reading_mismatch",
                             "note": f"{mk} 標註兩次判讀不一致：第一次「{f['label']}」、第二次「{lc['reading2Label']}」（{lc['reason']}），待查證",
                             "checkedOn": TODAY, "tool": "tools/battles/compare_readings.py"})
        only2 = [F2[j] for j in range(len(F2)) if j not in used2]
        tot["reading2Only"] += len(only2)
        tot["pxDiffers"] = tot.get("pxDiffers", 0) + sum(1 for i in m if m[i][1] > tol)
        for b in only2:
            u = next((x for x in unres if x.get("px") and math.dist(x["px"], b["px"]) <= 3 * tol), None)
            b["_why"] = f"第一次判讀列為未解（unresolved：{u.get('label')}）" if u else "第一次判讀附近沒有（可能漏讀）"
            gaps.append({"target": f"map-label:{mk}:{b['label']}@{b['px'][0]},{b['px'][1]}", "kind": "map_label_reading_mismatch",
                         "note": f"{mk} 第二次判讀讀到「{b['label']}」，{b['_why']}，待查證", "checkedOn": TODAY, "tool": "tools/battles/compare_readings.py"})
        rep[mk] = {"tolerancePx": round(tol, 1), "reading1": len(F1), "reading2": len(F2), "rows": rows,
                   "reading2Only": [{"label": b["label"], "px": b["px"], "confidence": b.get("confidence"), "why": b["_why"]} for b in only2]}
        if apply:
            R["labelCheckMethod"] = "兩次獨立判讀比對：tools/battles/compare_readings.py；第二次判讀檔 checks/label-reading2/" + mk + ".json"
            p.write_text(json.dumps(R, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tot["disagreements"] = tot["labelDiffers"] + tot["notFoundInReading2"] + tot["reading2Only"] + tot.get("importedFromReading2", 0)
    (D / "checks" / "label-readings.json").write_text(json.dumps({"summary": tot, "maps": rep}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if apply:
        G = D / "gaps.json"; g = json.loads(G.read_text())
        g["gaps"] = [x for x in g["gaps"] if x.get("kind") != "map_label_reading_mismatch"] + gaps
        G.write_text(json.dumps(g, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(tot, ensure_ascii=False))


if __name__ == "__main__":
    main()
