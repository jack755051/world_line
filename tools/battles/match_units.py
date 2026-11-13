"""地圖部隊標註 ↔ R1 部隊名冊對應，填 unitKey（共用工具；Tai 2026-11-13 13:39 流程修正第 3 項）。

用法：python3 -I tools/battles/match_units.py <battle> [--apply]
讀  data/seed/battles/<battle>/r1-units.json、digitized/*.readings.json、data/seed/battles/<battle>/unit-label-aliases.json（名稱別名設定）
寫  checks/unitkey-match.json（逐筆與總表）；--apply：把 unitKey／unitKeyStatus／unitKeyBasis 寫回 readings（再跑 georef.py 帶到輸出），
    未對上的標註依（標註, 陣營）彙整成 gaps.json 的 unit_label_unmatched 條目。

規則（保守，寧可不對也不亂對）：
- matched    名冊中唯一候選，且有明確佐證：標註本身帶兵種／國別（DLM、DI、Mot、ARMD、名稱別名），或讀圖註記的兵種／國別與候選一致。
- candidate  名冊中唯一候選，但只靠編號（灰階圖分不出英法比、或讀圖未判兵種），或讀圖註記與候選矛盾 → unitKey 照填但標「待查證」。
- unmatched  名冊沒有、或候選不只一個、或一圈多師；旅／團／支隊（other）不在 R1 名冊層級。
陣營：readings 的 sideGuess german ↔ R1 side axis；allied ↔ allied。
"""
import collections, json, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TODAY = __import__("datetime").date.today().isoformat()
SIDE = {"german": "axis", "allied": "allied"}


def norm(s):
    return re.sub(r"\s+", " ", s.replace("’", "'").strip().upper())


def num_candidates(units, side, n):
    return [u for u in units if u["side"] == side and u["echelon"] == "division" and re.search(rf"(^|-){n}-", u["unitKey"])]


def classify(f, units, aliases):
    L, side = norm(f["label"]), SIDE.get(f.get("sideGuess"))
    note = f.get("note") or ""  # 只看逐筆讀圖註記；sideNote 是圖例通則（含「無法分辨英法比」字樣），不能當國別佐證
    ech = f.get("echelon")
    if side is None:
        return None, "unmatched", "陣營未判"
    ROM = {"I": "i", "II": "ii", "III": "iii", "IV": "iv", "V": "v"}
    if side == "allied" and L in ROM:  # 盟軍羅馬數字軍：讀圖註記明寫英軍／法軍（First Army 區）時才依註記
        nat = "uk" if "英軍" in note else "fr" if ("First Army" in note or "法軍" in note) else None
        if nat:
            k = f"uk-{ROM[L]}-corps" if nat == "uk" else f"fr-{ROM[L]}-ca"
            if any(u["unitKey"] == k for u in units):
                return k, "matched", f"羅馬數字 {L} 軍，國別依讀圖註記（{nat}）"
            return None, "unmatched", f"羅馬數字 {L} 軍（{nat}）不在 R1 名冊"
    a = aliases.get(f"{f.get('sideGuess')}|{L}")
    if a is not None:
        if a.get("unitKey") is None:
            return None, "unmatched", a.get("why", "名冊無此單位")
        return a["unitKey"], a.get("status", "matched"), "名稱別名：" + a.get("why", L)
    if ech == "other":
        return None, "unmatched", "旅／團／支隊等，低於 R1 名冊層級"
    if "," in L:
        return None, "unmatched", "一圈多師，需拆分後再對"
    m = re.fullmatch(r"(\d+)\s*(DIV|DI|DLM|MOT|MOT DIV|ARMD DIV|C\.I\.DIV)?", L)
    if not m:
        return None, "unmatched", "名冊無對應名稱"
    n, suf = m.group(1), (m.group(2) or "")
    cands = num_candidates(units, side, n)
    hint = None
    if side == "axis":
        if "MOT" in suf or "摩托化" in note: hint = "mot"
        elif "ARMD" in suf or "裝甲" in note: hint = "pz"
        elif "步兵" in note: hint = "id"
        typed = [u for u in cands if hint and (hint + "-" in u["unitKey"] + "-" or u["unitKey"].endswith("-" + hint) or (hint == "pz" and "pzdiv" in u["unitKey"]) or (hint == "mot" and "mot-div" in u["unitKey"]))]
        if hint and len(typed) == 1:
            return typed[0]["unitKey"], "matched", f"德軍 {n} 號師，兵種依{'標註' if suf else '讀圖註記'}（{hint}）"
        if hint and not typed:
            return None, "unmatched", f"德軍 {n} 號師（{hint}）不在 R1 名冊" + (f"；名冊只有 {[u['unitKey'] for u in cands]}" if cands else "")
        if len(cands) == 1:
            return cands[0]["unitKey"], "candidate", f"德軍 {n} 號師只靠編號對上（讀圖未判兵種）"
        return None, "unmatched", f"德軍 {n} 號師：名冊候選 {len(cands)} 個"
    # 盟軍
    if suf == "DLM":
        cands = [u for u in cands if "dlm" in u["unitKey"]]
        return (cands[0]["unitKey"], "matched", "標註帶 DLM") if len(cands) == 1 else (None, "unmatched", f"{n} DLM 不在名冊")
    if suf == "DI":
        cands = [u for u in cands if u["unitKey"].startswith("fr-") and u["unitKey"].endswith("-di")]
        return (cands[0]["unitKey"], "matched", "標註帶 DI（法軍步兵師）") if len(cands) == 1 else (None, "unmatched", f"法軍 {n} DI 不在名冊")
    if suf == "C.I.DIV":
        return None, "unmatched", "C.I.DIV 單位不在名冊"
    cands = [u for u in cands if "dlm" not in u["unitKey"]]
    nat = "uk" if "英軍" in note else "fr" if "法軍" in note else "be" if "比利時軍" in note else None
    if len(cands) == 1:
        c = cands[0]["unitKey"]
        if nat and c.startswith(nat + "-"):
            return c, "matched", f"盟軍 {n} 號師，國別依讀圖註記（{nat}）"
        if nat:
            return c, "candidate", f"讀圖註記國別 {nat} 與名冊唯一候選 {c} 不符，待查證"
        return c, "candidate", f"盟軍 {n} 號師只靠編號對上（灰階圖無法辨英法比）"
    if not cands:
        return None, "unmatched", f"盟軍 {n} 號師不在 R1 名冊"
    if nat:
        c2 = [u for u in cands if u["unitKey"].startswith(nat + "-")]
        if len(c2) == 1:
            return c2[0]["unitKey"], "matched", f"盟軍 {n} 號師，國別依讀圖註記（{nat}）"
    return None, "unmatched", f"盟軍 {n} 號師：名冊候選 {[u['unitKey'] for u in cands]}，無法判定"


def classify_low(f, units, aliases):
    k, st, why = classify(f, units, aliases)
    note = f.get("note") or ""
    if st == "matched" and ("低信心" in note or f.get("confidence") == "low"):
        return k, "candidate", why + "；讀圖低信心，降為待查證"
    if st == "matched" and (f.get("labelCheck") or {}).get("status") == "待查證":
        return k, "candidate", why + "；兩次判讀標註文字不一致，降為待查證"
    return k, st, why


def main():
    battle = sys.argv[1]; apply = "--apply" in sys.argv
    D = REPO / "data" / "seed" / "battles" / battle
    units = json.loads((D / "r1-units.json").read_text())["units"]
    ap = D / "unit-label-aliases.json"
    aliases = {f"{a['sideGuess']}|{norm(a['label'])}": a for a in json.loads(ap.read_text())["aliases"]} if ap.exists() else {}
    rows, cnt, unmatched = [], collections.Counter(), collections.defaultdict(list)
    for p in sorted((D / "digitized").glob("*.readings.json")):
        R = json.loads(p.read_text()); mk = p.name[:-len(".readings.json")]
        for i, f in enumerate(R.get("features", [])):
            k, st, why = classify_low(f, units, aliases)
            rows.append({"map": mk, "i": i, "label": f["label"], "side": f.get("sideGuess"), "echelon": f.get("echelon"), "unitKey": k, "status": st, "basis": why})
            cnt[st] += 1; cnt["div+" + st] += f.get("echelon") != "other"
            if st == "unmatched": unmatched[(f["label"], f.get("sideGuess"))].append(mk)
            if apply:
                f["unitKey"] = k; f["unitKeyStatus"] = {"matched": "matched", "candidate": "待查證", "unmatched": "unmatched"}[st]; f["unitKeyBasis"] = why
        if apply:
            p.write_text(json.dumps(R, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    n = len(rows); nd = sum(1 for r in rows if r["echelon"] != "other")
    summ = {"labels": n, "matched": cnt["matched"], "candidate": cnt["candidate"], "unmatched": cnt["unmatched"],
            "matchRate": round(cnt["matched"] / n, 3), "matchRateInclCandidate": round((cnt["matched"] + cnt["candidate"]) / n, 3),
            "divisionAndAbove": {"labels": nd, "matched": cnt["div+matched"], "candidate": cnt["div+candidate"], "unmatched": cnt["div+unmatched"],
                                 "matchRate": round(cnt["div+matched"] / nd, 3), "matchRateInclCandidate": round((cnt["div+matched"] + cnt["div+candidate"]) / nd, 3)},
            "distinctUnmatchedLabels": len(unmatched)}
    (D / "checks").mkdir(exist_ok=True)
    (D / "checks" / "unitkey-match.json").write_text(json.dumps({"summary": summ, "rows": rows}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if apply:
        G = D / "gaps.json"; g = json.loads(G.read_text())
        g["gaps"] = [x for x in g["gaps"] if x.get("kind") != "unit_label_unmatched"]  # 本工具產生的條目每次重建
        for (lab, side), maps in sorted(unmatched.items(), key=lambda kv: (kv[0][1] or "", kv[0][0])):
            why = next(r["basis"] for r in rows if r["label"] == lab and r["side"] == side and r["status"] == "unmatched")
            g["gaps"].append({"target": f"map-label:{side}:{lab}", "kind": "unit_label_unmatched",
                              "note": f"地圖標註「{lab}」（{side}）未對上 R1 名冊：{why}；出現於 {', '.join(sorted(set(maps)))}",
                              "checkedOn": TODAY, "tool": "tools/battles/match_units.py"})
        G.write_text(json.dumps(g, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summ, ensure_ascii=False))


if __name__ == "__main__":
    main()
