"""從名冊、位置、前線、交戰、易手、指揮官與 gaps／匯入報告算出缺口清單，並切成小任務。

缺口類型：
  R3-none  該階段完全沒有位置
  R3-dates 集團軍／軍（或焦點地點已出現的部隊）缺某些關鍵日的位置
  R4       該日沒有文字或地圖前線（含「圖上沒畫線、可用文字補」的 gapsByDate）
  R5       交戰缺起日或迄日
  R6       易手缺日期
  R7       指揮官缺就任日（只缺迄日且人還在任者不列）

不寫戰役資料；只把清單寫到 staging。
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

HIGH_ECHELONS = ("army_group", "army", "corps")

PILOTS = {
    "ellis-ch10-calais": {
        "battle": "dunkirk_1940",
        "label": "Ellis 第 10 章（Channel Ports，5/22–5/26）補加萊",
        "url_substr": "UK-NWE-Flanders-10.html",
        "source_key": "ellis-war-in-france-flanders",
        "places": ["Calais", "加萊"],
        "date_from": "1940-05-22",
        "date_to": "1940-05-26",
        "include_leadin": True,
    }
}


def _d(s):
    return date.fromisoformat(s[:10]) if s else None


def daterange(a, b):
    a, b = _d(a), _d(b)
    if not a or not b or a > b:
        return []
    out = []
    cur = a
    while cur <= b:
        out.append(cur.isoformat())
        cur += timedelta(days=1)
    return out


def overlap(a0, a1, b0, b1):
    a0, a1, b0, b1 = _d(a0), _d(a1), _d(b0), _d(b1)
    if not all([a0, a1, b0, b1]):
        return True
    return not (a1 < b0 or b1 < a0)


def unit_names(u, aliases):
    names = [u.get("nameOrig") or "", u.get("nameZh") or ""]
    for a in aliases:
        if a.get("unitKey") == u.get("unitKey") and a.get("label"):
            names.append(a["label"])
    # 去空、保序
    return [x for x in dict.fromkeys(names) if x]


def _aliases(files):
    raw = files.get("unit-label-aliases.json") or {}
    return raw.get("aliases") or []


def _positions(files, name):
    return (files.get(name) or {}).get("positions") or []


def _period_of(u, fallback):
    p = u.get("period") or {}
    return p.get("start") or fallback.get("start"), p.get("end") or fallback.get("end")


def _place_hit(obj, places):
    if not places:
        return False
    blob = obj if isinstance(obj, str) else _blob(obj)
    return any(p.lower() in blob.lower() for p in places)


def _blob(obj):
    import json
    return json.dumps(obj, ensure_ascii=False)


def expected_front_dates(files, phase_key, window=None):
    """r4.dates（若有）否則既有前線日 ∪ gapsByDate ∪ 該階段已出現的前線日。"""
    cfg = files.get("battle.config.json") or {}
    r4cfg = cfg.get("r4") or {}
    dates = list(r4cfg.get("dates") or [])
    fname = "r4-fronts.json" if phase_key == "main" else "r4-leadin-fronts.json"
    rec = files.get(fname) or {}
    for f in rec.get("fronts") or []:
        if f.get("date") and f["date"] not in dates:
            dates.append(f["date"])
    for g in rec.get("gapsByDate") or []:
        if g.get("date") and g["date"] not in dates:
            dates.append(g["date"])
    if window:
        dates = [d for d in dates if overlap(d, d, window[0], window[1])]
        # 試跑有明確日期窗時，窗內每一日都列（章節是連續幾天）
        if not dates or (window[0] and window[1] and (_d(window[1]) - _d(window[0])).days <= 14):
            dates = daterange(window[0], window[1])
    return sorted(set(dates))


def key_position_dates(files, phase_key, window=None):
    """部隊位置的關鍵日：該階段已有位置的日期 ∪ 前線預期日。有日期窗且不超過 14 天時，用窗內每一日。"""
    if window and window[0] and window[1] and (_d(window[1]) - _d(window[0])).days <= 14:
        return daterange(window[0], window[1])
    pname = "r3-unit-positions.json" if phase_key == "main" else "r3-leadin-positions.json"
    dates = [p["date"] for p in _positions(files, pname) if p.get("date")]
    dates += expected_front_dates(files, phase_key, window=None)
    dates = sorted(set(dates))
    if window:
        dates = [d for d in dates if overlap(d, d, window[0], window[1])]
    return dates


def build_gaps(files, *, include_leadin=True, dated_echelons=HIGH_ECHELONS,
               date_from=None, date_to=None, places=None, import_notes=None):
    """files: 檔名 → 已載入的 json。回傳 {battle, phases, counts, gaps}。"""
    cfg = files.get("battle.config.json") or {}
    battle = cfg.get("battle") or files.get("_battle") or "unknown"
    aliases = _aliases(files)
    units = (files.get("r1-units.json") or {}).get("units") or []
    U = {u["unitKey"]: u for u in units}
    gaps = []
    window = (date_from, date_to) if (date_from or date_to) else None

    phases = []
    if include_leadin and cfg.get("leadIn"):
        phases.append(("leadin", cfg["leadIn"], "r3-leadin-positions.json", "r4-leadin-fronts.json"))
    if cfg.get("mainPhase"):
        phases.append(("main", cfg["mainPhase"], "r3-unit-positions.json", "r4-fronts.json"))
    if not phases:
        # 沒設定就當作只有主期，日期從資料推
        phases.append(("main", {"start": date_from, "end": date_to}, "r3-unit-positions.json", "r4-fronts.json"))

    # 焦點地點已出現的部隊：即使是師級，也為缺的日子列 R3-dates
    focus_units = set()
    if places:
        for fname in ("r3-unit-positions.json", "r3-leadin-positions.json"):
            for p in _positions(files, fname):
                if _place_hit(p, places):
                    focus_units.add(p.get("unitKey"))

    for phase_key, period, pfile, ffile in phases:
        have = {}
        for p in _positions(files, pfile):
            have.setdefault(p["unitKey"], set()).add(p.get("date"))
        key_dates = key_position_dates(files, "main" if phase_key == "main" else "leadin", window)
        # R3-none / R3-dates
        for u in units:
            uk = u["unitKey"]
            ustart, uend = _period_of(u, period)
            # 單位任期與本階段／日期窗完全不重疊就跳過
            phase_start, phase_end = period.get("start"), period.get("end")
            if ustart and uend and phase_start and phase_end and not overlap(ustart, uend, phase_start, phase_end):
                if uk not in focus_units:
                    continue
            if window and ustart and uend and not overlap(ustart, uend, window[0], window[1]):
                # 任期完全在窗外；但焦點地點部隊仍列
                if uk not in focus_units:
                    continue
            days = have.get(uk) or set()
            days = {d for d in days if d}
            names = unit_names(u, aliases)
            if window:
                relevant = [d for d in key_dates if overlap(d, d, window[0], window[1])]
            else:
                relevant = list(key_dates)
            # 再以單位任期裁一次
            if ustart or uend:
                clipped = [d for d in relevant if overlap(d, d, ustart or d, uend or d)]
                # 焦點地點部隊：名冊任期可能過窄（例：第 10 裝甲師只寫了 5/28），仍用日期窗
                if clipped or uk not in focus_units:
                    relevant = clipped
            if not days:
                if not relevant:
                    continue
                gaps.append({
                    "id": f"r3:{phase_key}:{uk}",
                    "type": "R3",
                    "subtype": "none",
                    "phase": phase_key,
                    "unitKey": uk,
                    "names": names,
                    "echelon": u.get("echelon"),
                    "side": u.get("side"),
                    "parentKey": u.get("parentKey"),
                    "period": u.get("period"),
                    "missingDates": relevant,
                    "need": f"部隊在{('前置期' if phase_key=='leadin' else '主期')}內某日的位置（具體城鎮＋日期），文字出處",
                })
                continue
            missing = [d for d in relevant if d not in days]
            if not missing:
                continue
            if u.get("echelon") in dated_echelons or uk in focus_units:
                gaps.append({
                    "id": f"r3:{phase_key}:{uk}:dates",
                    "type": "R3",
                    "subtype": "dates",
                    "phase": phase_key,
                    "unitKey": uk,
                    "names": names,
                    "echelon": u.get("echelon"),
                    "side": u.get("side"),
                    "parentKey": u.get("parentKey"),
                    "period": u.get("period"),
                    "haveDates": sorted(days),
                    "missingDates": missing,
                    "need": f"補 {'、'.join(missing[:8])}{'…' if len(missing)>8 else ''} 的位置（具體城鎮＋日期）",
                })

        # R4
        fronts_rec = files.get(ffile) or {}
        have_fronts = {f["date"] for f in fronts_rec.get("fronts") or [] if f.get("lineKind") in (None, "front", "perimeter") and f.get("date")}
        notes = {g["date"]: g.get("reason") or g.get("note") for g in fronts_rec.get("gapsByDate") or [] if g.get("date")}
        cfg_notes = (cfg.get("r4") or {}).get("dateGapNotes") or {}
        notes.update(cfg_notes)
        default_note = (cfg.get("r4") or {}).get("defaultGapNote")
        for d in expected_front_dates(files, "main" if phase_key == "main" else "leadin", window):
            if period.get("start") and period.get("end") and not overlap(d, d, period["start"], period["end"]):
                continue
            if d in have_fronts:
                continue
            gaps.append({
                "id": f"r4:{phase_key}:{d}",
                "type": "R4",
                "phase": phase_key,
                "date": d,
                "triedNote": notes.get(d, default_note),
                "hasSpecificNote": d in notes,
                "need": "該日（或前後 1–2 日）戰線經過的具名城鎮（至少 2 個），文字出處",
            })

    # R5 / R6 / R7 不分階段，但可用日期窗與地點過濾
    for e in (files.get("r5-engagements.json") or {}).get("engagements") or []:
        p = e.get("period") or {}
        if p.get("start") and p.get("end"):
            # 已有起迄：若不是焦點地點就不列；焦點地點已補完也不列
            continue
        place = (e.get("place") or {}).get("asInSource") or e.get("nameZh") or e.get("nameOrig")
        if places and not _place_hit(e, places):
            # 沒有日期且不是焦點：仍列（除非日期窗與已知部分完全無關——未知日期時保留）
            pass
        if window and p.get("start") and p.get("end") and not overlap(p.get("start"), p.get("end"), window[0], window[1]):
            continue
        gaps.append({
            "id": "r5:" + e.get("key", e.get("nameZh") or "unknown"),
            "type": "R5",
            "key": e.get("key"),
            "names": [x for x in (e.get("nameOrig"), e.get("nameZh")) if x],
            "place": place,
            "period": p,
            "attackers": e.get("attackers"),
            "defenders": e.get("defenders"),
            "need": "交戰起日／止日" + ("（缺起日）" if not p.get("start") else "（缺止日）" if not p.get("end") else ""),
        })

    for s in (files.get("r6-site-control.json") or {}).get("sites") or []:
        if s.get("date"):
            continue
        if places and not _place_hit(s, places):
            pass
        gaps.append({
            "id": "r6:" + (s.get("placeAsInSource") or s.get("event") or "site"),
            "type": "R6",
            "place": s.get("placeAsInSource"),
            "event": s.get("event"),
            "controllerAfter": s.get("controllerAfter"),
            "need": "易手（失守／占領）日期",
        })

    people = {(p.get("unitKey"), p.get("name")): p for p in (files.get("r7-missing-people.json") or {}).get("people") or []}
    for c in (files.get("r7-commanders.json") or {}).get("commanders") or []:
        t = c.get("tenure") or {}
        if t.get("start"):
            continue  # 只缺迄日者多為「戰役結束仍在任」，不列
        u = U.get(c.get("unitKey"), {})
        gaps.append({
            "id": f"r7:{c.get('unitKey')}:{c.get('personKey') or c.get('name')}",
            "type": "R7",
            "unitKey": c.get("unitKey"),
            "unitNames": unit_names(u, aliases) if u else [],
            "person": c.get("name"),
            "nameZh": c.get("nameZh"),
            "role": c.get("role"),
            "tenure": t,
            "need": "任期起日（就任該部隊指揮的日期）",
        })

    # 附加：gaps.json 與匯入報告裡、與文字位置／日期有關的備註（不重複已列 id）
    seed_gaps = (files.get("gaps.json") or {}).get("gaps") or []
    notes = []
    interesting = ("not_found", "partial", "missing", "conflict", "blocked")
    for g in seed_gaps:
        if g.get("kind") in interesting or (places and _place_hit(g, places)):
            if g.get("kind") in ("unit_label_unmatched", "map_label_reading_mismatch"):
                continue  # 讀圖對名冊，不在本 skill 文字流程
            notes.append({
                "target": g.get("target"),
                "kind": g.get("kind"),
                "note": (g.get("note") or "")[:400],
            })
    import_bits = []
    if import_notes:
        import_bits = list(import_notes)

    # 地點過濾：R3 焦點部隊或缺口 need／names 命中；R5/R6 地名命中；R4/R7 在日期窗內全留
    if places:
        kept = []
        for g in gaps:
            if g["type"] == "R3" and (g.get("unitKey") in focus_units or _place_hit(g, places)):
                kept.append(g)
            elif g["type"] in ("R5", "R6") and _place_hit(g, places):
                kept.append(g)
            elif g["type"] in ("R4", "R7"):
                kept.append(g)  # 日期窗已在前面裁過；R7 交給片段預篩
            else:
                # 沒有焦點命中的 R3-none 仍留給預篩（章節可能點名）
                if g["type"] == "R3" and g.get("subtype") == "none":
                    kept.append(g)
        gaps = kept

    out = {
        "battle": battle,
        "window": {"date_from": date_from, "date_to": date_to, "places": places or []},
        "mainPhase": cfg.get("mainPhase"),
        "leadIn": cfg.get("leadIn"),
        "counts": {},
        "gaps": gaps,
        "sourceNotes": notes,
        "importNotes": import_bits,
    }
    for g in gaps:
        out["counts"][g["type"]] = out["counts"].get(g["type"], 0) + 1
        if g.get("subtype"):
            key = g["type"] + ":" + g["subtype"]
            out["counts"][key] = out["counts"].get(key, 0) + 1
    return out


def split_batches(gaps, *, max_per_batch=8, by="unit"):
    """把缺口切成小任務。R3/R7 盡量同一部隊一組；R4 按日期；R5/R6 按筆。"""
    buckets = []
    r3 = {}
    for g in gaps:
        if g["type"] in ("R3", "R7") and g.get("unitKey"):
            r3.setdefault(g["unitKey"], []).append(g)
        else:
            buckets.append([g])
    batches = []
    for uk, items in r3.items():
        batches.append(items)
    batches.extend(buckets)
    # 合併過小批
    merged, cur = [], []
    for b in batches:
        if len(cur) + len(b) <= max_per_batch:
            cur.extend(b)
        else:
            if cur:
                merged.append(cur)
            if len(b) <= max_per_batch:
                cur = list(b)
            else:
                for i in range(0, len(b), max_per_batch):
                    merged.append(b[i:i + max_per_batch])
                cur = []
    if cur:
        merged.append(cur)
    out = []
    for i, items in enumerate(merged, 1):
        out.append({"batch": f"b{i:02d}", "gapIds": [g["id"] for g in items], "gaps": items})
    return out


def parse_import_report(text: str):
    """從 IMPORT-REPORT.md 抽出「還缺什麼」條目（純文字，供計畫附註）。"""
    if not text:
        return []
    lines = text.splitlines()
    items, grab = [], False
    for line in lines:
        if "還缺什麼" in line:
            grab = True
            continue
        if grab and line.startswith("## ") and "還缺" not in line:
            break
        if grab and line.strip().startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "- ", "* ")):
            items.append(line.strip())
    return items


def load_battle_files(repo, battle, paths_mod):
    names = [
        "battle.config.json", "r1-units.json", "unit-label-aliases.json",
        "r3-unit-positions.json", "r3-leadin-positions.json",
        "r4-fronts.json", "r4-leadin-fronts.json",
        "r5-engagements.json", "r6-site-control.json",
        "r7-commanders.json", "r7-missing-people.json", "gaps.json",
    ]
    files = {"_battle": battle}
    for n in names:
        files[n] = paths_mod.load_battle(repo, battle, n, {})
    return files


def apply_pilot(name, kwargs):
    if not name:
        return kwargs
    if name not in PILOTS:
        raise SystemExit(f"未知試跑 {name}，可選：{', '.join(PILOTS)}")
    p = PILOTS[name]
    out = dict(kwargs)
    def take(key, val):
        cur = out.get(key)
        if cur is None or cur == "" or cur == []:
            out[key] = val
    take("battle", p["battle"])
    take("date_from", p.get("date_from"))
    take("date_to", p.get("date_to"))
    take("places", p.get("places"))
    if "include_leadin" not in out:
        out["include_leadin"] = p.get("include_leadin", True)
    out["pilot"] = p
    return out
