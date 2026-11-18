"""把一場戰役的考證檔轉成「只新增」的開發庫寫入 SQL（§19.1 C1 表；I5：不 UPDATE、不 DELETE）。
用法：python3 -I tools/battles/write_battle_sql.py <battle>
輸出：data/seed/battles/<battle>/db/<battle>.write.sql、<battle>.write-plan.json。本程式不連任何資料庫。
- id 一律 uuid5（可重跑、逐位元相同）；SQL 開頭檢查 slug 不存在，否則中止（不覆寫）。
- 只寫 A/B 引文（citation 等級＝來源等級，不因來源數目更動；C 不寫；docs/source-rules.md）；沒有任何 A/B 引文的圖形／部隊不寫，列入 plan 的 skipped。
- 圖形只收前線（r4）與據點（r5 交戰地、r6 易手地）；部隊位置（r3）依 §19.1.3 G3 不建幾何。
- 文字推定前線 geom_basis='derived'（城鎮中心直線相連），status 一律 pending；props 帶「待查證／文字推定」。
- 階段取 frontend/public/campaigns/<battle>.json 的 phases；階段引文須在本機原文逐字找到且 ≤ 80 字，找不到就不寫。
- 政權 id 以 slug 子查詢取得；交戰方只寫 r1 有 A/B 引文部隊的政權。
"""
import json, sys, uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from citelib import Cites, REPO

NS = uuid.uuid5(uuid.NAMESPACE_URL, "https://worldline.local/battle-seed")
POLICY = "battle-db-2026-11-13"
KIND = {"official_history": "official_history"}
SOURCE_KIND = {"us-army-dapam": "official_history", "usma-atlas": "atlas_map", "de-okh-records": "archive",
               "de-academic": "official_website", "pl-ipn": "official_website", "jp-jacar": "archive", "jp-monographs": "official_history", "tw-roc": "peer_reviewed", "us-frus": "official_record"}
CAMP = {"de": "axis", "su": "soviet", "axis": "axis", "allied": "allied", "soviet": "soviet"}
SIDE_REGIME = {"de": "deutsches-reich", "su": "soviet-union", "axis": "deutsches-reich"}
RANK = {"A": 0, "B": 1, "C": 2}


def uid(*p): return str(uuid.uuid5(NS, "|".join(str(x) for x in p)))
def q(s): return "NULL" if s is None else "'" + str(s).replace("'", "''") + "'"
def j(o): return "NULL" if o is None else q(json.dumps(o, ensure_ascii=False, sort_keys=True)) + "::jsonb"
def reg(slug): return f"(SELECT id FROM regimes WHERE slug = {q(slug)})"


def main():
    battle = sys.argv[1]
    D = REPO / "data/seed/battles" / battle
    L = lambda f: json.loads((D / f).read_text())
    cfg, src, name = L("battle.config.json"), L("sources.json"), L("name.json")
    fam = cfg["sourceFamilies"]["map"]
    SIDE = {**SIDE_REGIME, **(cfg.get("db") or {}).get("sideRegimes", {})}  # 戰役可在 battle.config.json db.sideRegimes 指定陣營→政權（由 builder 寫入）
    web = json.loads((REPO / "frontend/public/campaigns" / f"{battle}.json").read_text())
    op = L("osm-places.json") if (D / "osm-places.json").exists() else {}; co = op.get("coords", {})
    seedp = REPO / "data/seed/battles" / f"{battle}.seed.json"; seed = json.loads(seedp.read_text()) if seedp.exists() else None
    P = {"relation": "R", "way": "W", "node": "N"}
    def xy(osm):
        c = co.get(P[osm["type"]] + str(osm["id"])) if osm else None
        return (c["lon"], c["lat"]) if c else None
    sql, plan, used = [], {"battle": battle, "rows": {}, "skipped": [], "notes": []}, set()
    def add(table, cols, vals):
        sql.append(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(vals)});"); plan["rows"][table] = plan["rows"].get(table, 0) + 1
    def grade(c, rec):
        g = c.get("grade")
        return g if g in ("A", "B") else None
    def cites(table, owner_col, owner_id, rec, cs, extra_cols=(), extra_vals=(), note=None):
        n = 0
        for c in cs:
            g = grade(c, rec)
            if not g or len(c["quote"]) > 80: continue
            used.add(c["sourceKey"])
            add(table, ["id", owner_col, *extra_cols, "source_id", "locator", "quote", "quote_lang", "evidence_note", "accessed_on", "grade", "policy_version"],
                [q(uid(table, owner_id, c["sourceKey"], c["quote"])), q(owner_id), *extra_vals, q(uid("source", c["sourceKey"])), q(c["locator"]), q(c["quote"]),
                 q(c.get("quoteLang")), q(note), q(c.get("accessedOn") or "2026-11-13"), q(g), q(POLICY)])
            n += 1
        return n
    mp = cfg["mainPhase"]; ev = uid("event", battle)
    end_excl = (seed["event"]["occurred"]["end"] if seed else None) or web.get("end") or mp["end"]
    prof = (seed or {}).get("profile") or {}
    body = []
    # 事件、profile
    add("historical_events", ["id", "event_kind", "summary", "occurred", "date_precision"],
        [q(ev), q("battle"), j({"zh-Hant": name["nameZh"], "en": name["nameEn"]}), q(f"[{mp['start']},{end_excl})") + "::daterange", q("day")])
    add("battle_profiles", ["event_id", "slug", "name", "objective", "objective_kind", "control_change", "status"],
        [q(ev), q(battle), j({k: v for k, v in {"zh-Hant": name["nameZh"], "en": name["nameEn"], "de": name.get("nameDe"), "pl": name.get("namePl")}.items() if v}),
         j(dict(prof["objective"], note="目標文字取自考證 seed；objective_kind 暫填候選值，待查證") if prof.get("objective") else {"zh-Hant": "待查證", "note": "目標未考證；objective_kind 暫填 regime，待查證"}),
         q(prof.get("objective_kind") or prof.get("objective_kind_candidate") or "regime"),
         j(dict(prof["control_change"], note="取自考證 seed，待查證") if prof.get("control_change") else {"zh-Hant": "待查證", "note": "控制變化未考證"}), q("pending")])
    cites("battle_profile_citations", "event_id", ev, name, name["citations"], ["field"], [q("name")])
    # 交戰方
    units = L("r1-units.json")["units"]
    ok_units = [u for u in units if any(grade(c, u) for c in u["citations"])]
    part_slugs = {u["regimeSlug"] for u in ok_units if u.get("regimeSlug")}  # 交戰方：有 A/B 部隊者，另加已寫入交戰紀錄所列部隊之政權（見下）
    part_at = len(sql)
    # 階段
    phase_ids = []
    if seed and seed.get("phases"):
        surl = {x["key"]: x.get("url") or "" for x in seed["sources"]}
        def rkey(sk):
            u = surl.get(sk, "")
            return next((k for k, v in src.items() if v.get("url") and u.rsplit("/", 1)[0] == v["url"].rsplit("/", 1)[0]), None)
        for p in seed["phases"]:
            pid = uid("phase", battle, p["seq"]); a, b = p["period"]["start"], p["period"]["end"]; phase_ids.append((pid, a, b))
            add("battle_phases", ["id", "event_id", "seq", "name", "period", "start_precision", "end_precision", "summary", "status"],
                [q(pid), q(ev), str(p["seq"]), j({k: v for k, v in p["name"].items() if v}), q(f"[{a},{b})") + "::daterange", q(p.get("start_precision") or "day"),
                 q(p.get("end_precision") or "day"), j(p.get("summary")), q("pending")])
            good = []
            for c in p.get("citations", []):
                k = rkey(c["source_key"])
                if not k or c.get("verification") != "verbatim" or c.get("grade") not in ("A", "B"):
                    plan["skipped"].append({"phase": p["seq"], "quote": c["quote"][:90], "why": "未逐字驗證／非 A/B／對不到來源"}); continue
                good.append({"sourceKey": k, "locator": c["locator"], "quote": c["quote"], "quoteLang": c.get("quote_lang"), "accessedOn": c.get("accessed_on"), "grade": c["grade"]})
            cites("battle_phase_citations", "phase_id", pid, None, good, note="階段引文取自考證 seed（逐字驗證）")
    C = Cites(battle) if not phase_ids else None
    for p in ([] if phase_ids else web["phases"]):
        pid = uid("phase", battle, p["seq"]); phase_ids.append((pid, p["start"], p["end"]))
        add("battle_phases", ["id", "event_id", "seq", "name", "period", "start_precision", "end_precision", "summary", "status"],
            [q(pid), q(ev), str(p["seq"]), j({k: v for k, v in {"zh-Hant": p["name_zh"], "en": p.get("name_en")}.items() if v}),
             q(f"[{p['start']},{p['end']})") + "::daterange", q("day"), q("day"), j({"zh-Hant": p["summary_zh"]} if p.get("summary_zh") else None), q("pending")])
        good = []
        for s in p["sources"]:
            key = next((k for k, v in src.items() if v.get("url") and s["url"].startswith(v["url"].rstrip("/"))), None)
            try:
                c = C(key, s["quote"]) if key else None
            except SystemExit as e:
                c = None; plan["skipped"].append({"phase": p["seq"], "quote": s["quote"][:90], "why": str(e)[:60]})
            if c:
                good.append(c)
        cites("battle_phase_citations", "phase_id", pid, None, good, note="階段引文")
    def phase_of(d):
        for pid, a, b in phase_ids:
            if a <= d < b: return pid
        return None
    # 前線
    for f in L("r4-fronts.json")["fronts"]:
        pts = [v["lonlat"] for v in f["vertices"] if v.get("lonlat")]
        pid = phase_of(f["date"]); mapped = f.get("basis") == "map-digitized" and f.get("mapRef")
        fcs = f.get("citations") or []
        if mapped:
            import re as _re
            mr = f["mapRef"]; mk = next((k for k, v in src.items() if v.get("url") and mr["url"].startswith(v["url"].rsplit("/", 1)[0])), None)
            t = _re.search(r"'([^']+)'", mr["citation"])
            fcs = [{"sourceKey": mk, "locator": mr["citation"], "quote": t.group(1), "quoteLang": "en", "accessedOn": "2026-11-13", "grade": mr.get("grade")}] if mk and t else []
            f = dict(f, confidence=None)
        if len(pts) < 2 or not pid or not any(grade(c, f) for c in fcs):
            plan["skipped"].append({"front": f["lineKey"], "why": "頂點不足／無階段／無 A/B 引文"}); continue
        fid = uid("feature", battle, f["lineKey"]); side = f.get("side")
        props = {"date": f["date"], "lineKind": f.get("lineKind"), "status": "待查證", "precisionNote": f.get("precisionNote"), "confidence": (f.get("confidence") or {}).get("level")}
        if mapped: props.update(mapKey=f["mapRef"]["mapKey"], georef=f.get("georef"), method=f.get("method"), precision_m=f.get("precision_m"))
        else: props.update(inference=f.get("inference", "文字推定"), method=f.get("method"))
        wkt = "LINESTRING(" + ", ".join(f"{x:.5f} {y:.5f}" for x, y in pts) + ")"
        add("battle_map_features", ["id", "phase_id", "feature_key", "feature_kind", "side_regime_id", "side_camp", "geom", "label", "props", "geom_basis", "status"],
            [q(fid), q(pid), q(f"{battle}:front:{f['lineKey']}"[:96]), q("front"), reg(SIDE[side]) if side in SIDE else "NULL",
             q(CAMP.get(side)), f"ST_GeomFromText({q(wkt)}, 4326)", j({"zh-Hant": f["label"]}), j(props), q("source_map" if mapped else "derived"), q("pending")])
        cites("battle_map_feature_citations", "feature_id", fid, f, fcs, note="地圖數位化（georef 通過門檻），引文為圖題" if mapped else "文字推定前線，待查證")
    # 據點：r6 易手、r5 交戰地
    for fn, arr, kind in (("r6-site-control.json", "sites", "control"), ("r5-engagements.json", "engagements", "engagement")):
        for s in L(fn)[arr]:
            pl = s.get("place") or {}; pt = xy(pl.get("osm")); d = s.get("date") or (s.get("period") or {}).get("start") or (s.get("period") or {}).get("end")  # 只有止日者以止日歸階段
            key = s.get("key") or f"{pl.get('nameOsm')}-{d}"
            pid = phase_of(d) if d else None
            if not pt or not pid or not any(grade(c, s) for c in s["citations"]):
                plan["skipped"].append({kind: key, "why": "無座標／無階段／無 A/B 引文"}); continue
            fid = uid("feature", battle, kind, key)
            lab = {"zh-Hant": s.get("nameZh") or pl.get("nameOsm"), "orig": s.get("nameOrig") or s.get("placeAsInSource")}
            props = {"date": d, "kind": kind, "status": "待查證", "event": s.get("event"), "period": s.get("period"), "place": pl.get("nameOsm"),
                     "confidence": (s.get("confidence") or {}).get("level"), "coordNote": "OSM 物件中心點"}
            camp = s.get("controllerAfter") if kind == "control" else None
            add("battle_map_features", ["id", "phase_id", "feature_key", "feature_kind", "side_regime_id", "side_camp", "geom", "label", "props", "geom_basis", "status"],
                [q(fid), q(pid), q(f"{battle}:site:{kind}:{key}"[:96]), q("site"), reg(s["controllerRegimeSlug"]) if kind == "control" and s.get("controllerRegimeSlug") else "NULL",
                 q(CAMP.get(camp)), f"ST_SetSRID(ST_MakePoint({pt[0]:.5f}, {pt[1]:.5f}), 4326)", j(lab), j(props), q("source_text"), q("pending")])
            cites("battle_map_feature_citations", "feature_id", fid, s, s["citations"])
            if kind == "engagement":
                rs = {u["unitKey"]: u.get("regimeSlug") for u in units}
                part_slugs.update(rs[k] for k in (s.get("attackers") or []) + (s.get("defenders") or []) if rs.get(k))
    for slug in sorted(part_slugs, reverse=True):
        sql.insert(part_at, f"INSERT INTO event_participants (event_id, regime_id, role) VALUES ({q(ev)}, {reg(slug)}, {q('belligerent')});")
        plan["rows"]["event_participants"] = plan["rows"].get("event_participants", 0) + 1
    # 部隊（父先子後）
    byk = {u["unitKey"]: u for u in ok_units}; done = set()
    for u in units:
        if u not in ok_units: plan["skipped"].append({"unit": u["unitKey"], "why": "無 A/B 引文（單一來源降 C）"})
    def put(u):
        if u["unitKey"] in done: return
        par = u.get("parentKey") if u.get("parentKey") in byk else None
        if par: put(byk[par])
        done.add(u["unitKey"]); i = uid("unit", battle, u["unitKey"])
        add("battle_units", ["id", "event_id", "side_regime_id", "parent_unit_id", "unit_name", "unit_echelon", "status"],
            [q(i), q(ev), reg(u["regimeSlug"]), q(uid("unit", battle, par)) if par else "NULL",
             j({k: v for k, v in {"orig": u["nameOrig"], "zh-Hant": u.get("nameZh"), "unitKey": u["unitKey"]}.items() if v}), q(u.get("echelon")), q("pending")])
        cites("battle_unit_citations", "unit_id", i, u, u["citations"])
    for u in ok_units: put(u)
    # 來源（先寫）
    head = []
    for k in sorted(used):
        s = src[k]; sid = uid("source", k)
        head.append(f"INSERT INTO sources (id, source_kind, title, publisher, authors, published_text, url, note) VALUES ({q(sid)}, {q(SOURCE_KIND.get(fam.get(k), 'official_website'))}, "
                    f"{q(s['title'])}, {q(s.get('publisher') or s['title'])}, {q(', '.join(s.get('authors') or []) or None)}, {q(s.get('year'))}, {q(s.get('url'))}, "
                    f"{q('battle ' + battle + ' 考證來源（' + (s.get('gradeBasis') or '') + '）')}) ON CONFLICT (id) DO NOTHING;")
        plan["rows"]["sources"] = plan["rows"].get("sources", 0) + 1
    import re as _re2
    slugs = set(_re2.findall(r"FROM regimes WHERE slug = '([^']+)'", "\n".join(sql)))
    guard = (f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM battle_profiles WHERE slug = {q(battle)}) THEN RAISE EXCEPTION 'battle % already exists; not overwriting', {q(battle)}; END IF;\n"
             f"  IF (SELECT count(*) FROM regimes WHERE slug IN ({', '.join(q(x) for x in sorted(slugs))})) <> {len(slugs)} THEN RAISE EXCEPTION 'regime slug missing'; END IF; END $$;")
    out = D / "db"; out.mkdir(exist_ok=True)
    (out / f"{battle}.write.sql").write_text(f"-- {battle} 開發庫寫入（tools/battles/write_battle_sql.py 產生；只 INSERT，單一交易由呼叫端包住）\n" + guard + "\n" + "\n".join(head + sql) + "\n")
    plan["eventId"] = ev; plan["sourcesUsed"] = sorted(used)
    (out / f"{battle}.write-plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(plan["rows"], ensure_ascii=False), "skipped", len(plan["skipped"]))


if __name__ == "__main__":
    main()
