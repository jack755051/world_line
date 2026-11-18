#!/usr/bin/env python3
"""舊格式人物生平：依來源規則更正欄位（docs/source-rules.md §5 補充 4、5 與 §7；Tai 2026-11-14 同意＋常態授權）。

三類更正（皆不刪資料，撤回附理由）：
1. 合格出處優先（§5 補充 4）：欄位值只有不合格出處撐、合格出處寫的不同 → 改成合格出處的值；原不合格出處移到欄位 supersededSources，庫內引文撤回。
2. 日期精度（§7）與說法衝突（§5）：合格出處只撐到年／月，或兩個合格出處日期不同 → 降到共同精度；
   年份就不同（無法再降）→ 值保留、標說法衝突。field_sources 記狀態與兩說。
3. 不合格欄位撤回（§5 補充 5）：補查後仍只有 C／X 的欄位 → seed 移到 unverified、庫內引文撤回、欄位值清空、field_sources 標待查證；
   姓名不可空白，保留並標待查證。
庫內主檔就地更新並 version+1（前例 b3-trial/fix12/plan.sql）。預設 dry-run；--apply 改 seed；--send --allow-write 寫開發庫（單一交易）。
用法（repo 根目錄）：python3 -I data/seed/leaders/gap-830/apply_rule_corrections.py <cfields 資料夾> [--apply] [--send --allow-write]
"""
import json, sys, subprocess, collections
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
P1 = HERE.parent / "batch-p1-20261107"
CONTAINER, DBUSER, DBNAME = "worldline-borders-dev-db", "worldline", "worldline_borders_dev"
RUN = "rule-corrections-2026-11-14"
DEV = REPO / ".dev" / "dbwrite"
FIELDS = ("name", "nameZh", "birthDate", "deathDate", "birthPlace", "deathPlace", "party", "summary")
COL = {"name": "name", "nameZh": "name_zh", "birthDate": "birth_date", "deathDate": "death_date", "birthPlace": "birth_place",
       "deathPlace": "death_place", "party": "party", "summary": "summary"}
PREC = {"birthDate": "birth_date_precision", "deathDate": "death_date_precision"}
JSONB = {"birthPlace", "deathPlace", "party", "summary"}

# 2. 日期：(人物, 欄位) → (新精度, 衝突說明或 None)
DATES = {
    ("se-de-geer-dy", "deathDate"): ("year", None),
    ("ad-benlloch-i-vivo", "birthDate"): ("year", None),
    ("ad-benlloch-i-vivo", "deathDate"): ("year", "LC（引 Enciclopedia universal ilustrada）記 1926-02-15，原值 02-14 只有不合格出處"),
    ("py-gonzalez-navero", "birthDate"): ("year", None),
    ("py-gonzalez-navero", "deathDate"): ("year", None),
    ("lt-vytautas-petrulis", "birthDate"): ("year", None),
    ("lt-vytautas-petrulis", "deathDate"): ("year", "LC 記 1941，GND 141512172 記 1942"),
    ("iq-faisal-ii", "birthDate"): ("year", None),
    ("ua-fedir-lyzohub", "birthDate"): ("year", "ESU 與 GND 記 1851-10-06，ESU 另記異說 1851-11-06（可能為新舊曆）"),
    ("lt-vladas-mironas", "deathDate"): ("month", "BnF 記 1953-02-17，GND 138508933 記 1953-02-18"),
    ("lt-augustinas-voldemaras", "deathDate"): ("year", "GND 記 1942-12-16，BnF cb12982005v 記 1942-05-16"),
    ("lt-mykolas-slezevicius", "deathDate"): ("year", "GND 記 1939-11-11，BnF 17013162w 記 1939-02-11"),
    ("b04-carol-ii", "birthDate"): ("month", "原值 1893-10-15，BnF cb14403314n 記 1893-10-16"),
    ("gr-ioannis-metaxas", "birthDate"): ("month", "GND 記 1871-04-12（舊曆），BnF 記 1871-04-24（新曆），LC 結構欄記 1871-04-02"),
    ("gr-plastiras", "birthDate"): (None, "BnF、GND 記 1883，LC n82037656 標目記 1882"),
    ("ro-alexandru-vaida-voevod", "birthDate"): (None, "Buda（B）與原值記 1872，GND 118803662 記 1873"),
}

# 1. 合格出處優先：新值（seed 用的 value 結構）與依據來源取自補查結果（value_differs 或指定）
VALUES = {
    ("ru-boris-sturmer", "birthPlace"): {"zh-Hant": "聖彼得堡", "en": "Saint Petersburg"},
    ("es-samper", "party"): {"zh-Hant": "共和自治聯盟黨（PURA）", "en": "Republican Autonomist Union Party (PURA)"},
    ("es-samper", "summary"): {"zh-Hant": "西班牙政治人物，1931 與 1933 年當選眾議員（共和自治聯盟黨），1934 年 4 月 28 日接替勒魯斯任政府首長，同年 10 月 4 日辭職。",
                               "en": "Spanish politician elected deputy in 1931 and 1933 (Republican Autonomist Union Party); appointed head of government on 28 April 1934 after Lerroux resigned, he stepped down on 4 October 1934."},
    ("es-moret", "summary"): {"zh-Hant": "西班牙政治家，兩度出任部長會議主席（1905–1906 年、1906 年）。",
                              "en": "Spanish statesman who twice served as President of the Council of Ministers (1905–06 and 1906)."},
    ("su-stalin", "summary"): {"zh-Hant": "史達林自 1922 年起任俄共（布）—聯共（布）中央總書記，1941 年至 1953 年任蘇聯人民委員會（後為部長會議）主席。",
                               "en": "Stalin was General Secretary of the RCP(b)–VKP(b) Central Committee from 1922 and chairman of the USSR Council of People's Commissars (later Council of Ministers) from 1941 to 1953."},
}
VALUE_WHY = {
    ("ru-boris-sturmer", "birthPlace"): "BnF（A）記生於聖彼得堡；原值「別熱茨克附近」只有 VLE 無署名條目（C）",
    ("es-samper", "party"): "西班牙眾議院歷史議員檔（A）登記黨團為 Unión Republicana Autonomista；原值「激進共和黨」只有 UNED 無署名頁（C）",
    ("es-samper", "summary"): "黨派依眾議院議員檔（A）改正，其餘照原值（Gaceta de Madrid，A）",
    ("es-moret", "summary"): "眾議院歷任議長頁（A）記兩任部長會議主席為 1905-12-01～1906-07-06、1906-11-30～12-04；原值的 1909 年任期與「薩加斯塔死後任自由黨領袖」只有 Encyclopedia.com 無署名條目（C），刪除",
    ("su-stalin", "summary"): "BnF（A）記總書記任期至 1953、主席 1941–1953；原值的確切日期與「至 1934 年」只有 knowbysight.info（C），刪除到合格出處撐得住的範圍",
}


def lit(v):
    return "NULL" if v is None else "'" + str(v).replace("'", "''") + "'"


def qjson(sql):
    r = subprocess.run(["docker", "exec", "-i", CONTAINER, "psql", "-U", DBUSER, "-d", DBNAME, "-At", "-v", "ON_ERROR_STOP=1"],
                       input="select coalesce(json_agg(t),'[]'::json)::text from (%s) t" % sql, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr[:500])
    return json.loads(r.stdout)


def seeds():
    out = [(d / "research.json", d / "sent.5052.json") for d in sorted(HERE.glob("b[0-9][0-9]"))]
    out += [(P1 / n, P1 / "sent-p1.5052.json") for n in ("roc.json", "su-tr.json", "us-es.json")]
    return [(s, l) for s, l in out if s.exists() and l.exists()]


def ab(srcs):
    return bool({s.get("grade") for s in srcs if isinstance(s, dict)} & {"A", "B"})


def lower(value, prec):
    v = str(value)
    return v[:4] + "-01-01" if prec == "year" else v[:7] + "-01"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    apply, send, allow = "--apply" in sys.argv, "--send" in sys.argv, "--allow-write" in sys.argv
    cf = Path(args[0])
    newsrc = {}  # value_differs 的合格出處
    for g in ("q1", "q2", "q3", "q4"):
        for r in json.loads((cf / g / "result.json").read_text()):
            if r["status"] == "value_differs" and r.get("newSource"):
                s = {k: r["newSource"].get(k) for k in ("title", "publisher", "url", "sourceKind", "licenseCode", "locator", "evidence", "accessedOn", "grade", "gradeBasis")}
                s["gradeBasis"] = (s.get("gradeBasis") or "") + "（%s）" % RUN
                newsrc[(r["personKey"], r["field"])] = s
    newsrc[("es-samper", "summary")] = None  # 摘要已有 Gaceta（A）撐；黨派依據見 party 欄
    newsrc[("su-stalin", "summary")] = None  # 已有 BnF（A）
    plan = []  # (bio, kind, field, payload)
    log = collections.Counter()
    for seed, led in seeds():
        raw = seed.read_text(); d = json.loads(raw); bios = json.loads(led.read_text()).get("bios") or {}; changed = False
        for p in d.get("people") or []:
            bio = bios.get(p["key"])
            for f in FIELDS:
                v = p.get(f)
                if not isinstance(v, dict) or "value" not in v:
                    continue
                k = (p["key"], f)
                if RUN in (v.get("note") or ""):
                    continue  # 已更正過（可重跑）
                srcs = [s for s in v.get("sources") or [] if isinstance(s, dict) and "sourceKind" in s]
                if k in VALUES:
                    keep = [s for s in srcs if s.get("grade") in ("A", "B")]
                    gone = [s for s in srcs if s.get("grade") not in ("A", "B")]
                    if newsrc.get(k):
                        keep.append(newsrc[k])
                    v["value"] = VALUES[k]; v["sources"] = keep
                    if gone:
                        v["supersededSources"] = gone
                    v["note"] = "合格出處優先（source-rules §5 補充 4）：" + VALUE_WHY[k] + "（%s）" % RUN
                    plan.append((bio, "value", f, {"value": VALUES[k], "add": newsrc.get(k), "retract_urls": [s["url"] for s in gone], "why": VALUE_WHY[k]}))
                    changed = True; log["value"] += 1
                elif k in DATES:
                    prec, conflict = DATES[k]
                    old = (v["value"], v.get("precision"))
                    if prec and (v.get("precision") in ("day",) or (prec == "year" and v.get("precision") == "month")):
                        v["value"], v["precision"] = lower(v["value"], prec), prec
                    if conflict:
                        v["note"] = "說法衝突（source-rules §5）：" + conflict + "（%s）" % RUN
                    elif prec:
                        v["note"] = "合格出處只撐到%s，依 source-rules §7 降低精度（%s）" % ({"year": "年", "month": "月"}[prec], RUN)
                    plan.append((bio, "date", f, {"value": v["value"], "precision": v.get("precision"), "old": old, "conflict": conflict}))
                    changed = True; log["date"] += 1
                elif srcs and not ab(srcs):
                    why = "補查後仍只有 C／X 出處（%s），依 source-rules §5 補充 5 撤回" % "、".join(sorted({(s.get('publisher') or '')[:40] for s in srcs}))
                    if f == "name":
                        v["note"] = "姓名不可空白，保留並標待查證：" + why + "（%s）" % RUN
                        plan.append((bio, "name_flag", f, {"why": why})); log["name_flag"] += 1
                    else:
                        p.setdefault("unverified", []).append({"field": f, "note": why + "（%s）" % RUN, "retractedValue": v.get("value"),
                                                                "retractedPrecision": v.get("precision"), "retractedSources": srcs})
                        p.pop(f)
                        plan.append((bio, "retract", f, {"why": why, "urls": [s["url"] for s in srcs]})); log["retract"] += 1
                    changed = True
        if apply and changed:
            ind = 2 if raw.startswith("{\n  ") else 1
            seed.write_text(json.dumps(d, ensure_ascii=False, indent=ind) + ("\n" if raw.endswith("\n") else ""))
    if any(b is None for b, *_ in plan):
        raise SystemExit("有人物沒有 bio 對照")
    # SQL
    q = ["BEGIN;"]
    fs = lambda bio, f, obj: q.append("UPDATE leader_bios SET field_sources = jsonb_set(coalesce(field_sources,'{}'::jsonb), %s, %s::jsonb) WHERE id=%s AND retracted_at IS NULL;"
                                      % (lit("{%s}" % f), lit(json.dumps(obj, ensure_ascii=False)), lit(bio)))
    def retract_cites(bio, f, urls, why):
        for u in urls:
            q.append("UPDATE leader_bio_field_citations c SET retracted_at=now(), retraction_reason=%s FROM sources s WHERE s.id=c.source_id AND c.bio_id=%s AND c.field=%s AND s.url=%s AND c.retracted_at IS NULL;"
                     % (lit(RUN + "：" + why), lit(bio), lit(f), lit(u)))
    have = {x["url"]: x["id"] for x in qjson("select url,id from sources where url in (%s)" % ",".join(lit(p["add"]["url"]) for _, k, _, p in plan if k == "value" and p.get("add")) or "select 1 where false")} \
        if any(k == "value" and p.get("add") for _, k, _, p in plan) else {}
    for bio, kind, f, p in plan:
        if kind == "value":
            val = lit(json.dumps(p["value"], ensure_ascii=False)) + "::jsonb" if f in JSONB else lit(p["value"])
            q.append("UPDATE leader_bios SET %s=%s, version=version+1 WHERE id=%s AND retracted_at IS NULL;" % (COL[f], val, lit(bio)))
            retract_cites(bio, f, p["retract_urls"], "合格出處優先，原不合格出處不再支撐此欄（source-rules §5 補充 4）")
            if p.get("add"):
                s = p["add"]; sid = have.get(s["url"])
                if not sid:
                    q.append("INSERT INTO sources (id,source_kind,title,publisher,url,license_code) VALUES (gen_random_uuid(),%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING;"
                             % (lit(s["sourceKind"]), lit(s["title"]), lit(s["publisher"]), lit(s["url"]), lit(s.get("licenseCode"))))
                q.append("INSERT INTO leader_bio_field_citations (bio_id,field,source_id,locator,evidence_note,accessed_on,grade,quote,policy_version) "
                         "SELECT %s,%s,(SELECT id FROM sources WHERE url=%s ORDER BY created_at LIMIT 1),%s,%s,%s,%s,%s,'source-2026-11-13';"
                         % (lit(bio), lit(f), lit(s["url"]), lit(s["locator"]), lit(s["evidence"]), lit(s["accessedOn"]), lit(s["grade"]), lit(s["evidence"])))
            fs(bio, f, {"status": "verified", "note": "合格出處優先：" + p["why"] + "（%s）" % RUN})
        elif kind == "date":
            q.append("UPDATE leader_bios SET %s=%s::date, %s=%s, version=version+1 WHERE id=%s AND retracted_at IS NULL;"
                     % (COL[f], lit(p["value"]), PREC[f], lit(p["precision"]), lit(bio)))
            if p["conflict"]:
                fs(bio, f, {"status": "說法衝突", "note": p["conflict"] + "（%s）" % RUN})
        elif kind == "retract":
            q.append("UPDATE leader_bios SET %s=NULL, version=version+1 WHERE id=%s AND retracted_at IS NULL;" % (COL[f], lit(bio)))
            if f in PREC:
                q.append("UPDATE leader_bios SET %s=NULL WHERE id=%s AND retracted_at IS NULL;" % (PREC[f], lit(bio)))
            retract_cites(bio, f, p["urls"], p["why"])
            fs(bio, f, {"status": "待查證", "note": p["why"] + "（%s）" % RUN})
        elif kind == "name_flag":
            fs(bio, f, {"status": "待查證", "note": "姓名不可空白，保留：" + p["why"] + "（%s）" % RUN})
    q.append("COMMIT;")
    DEV.mkdir(parents=True, exist_ok=True)
    (DEV / "rule-corrections.sql").write_text("\n".join(q) + "\n")
    detail = collections.defaultdict(list)
    for bio, kind, f, p in plan:
        detail[kind].append(f)
    print(json.dumps({"apply_seed": apply, "counts": dict(log), "by_field": {k: dict(collections.Counter(v)) for k, v in detail.items()},
                      "sql_lines": len(q)}, ensure_ascii=False, indent=1))
    if not send:
        print("（未寫庫；SQL 見 .dev/dbwrite/rule-corrections.sql）"); return
    if not allow:
        raise SystemExit("需 --send --allow-write")
    r = subprocess.run(["docker", "exec", "-i", CONTAINER, "psql", "-U", DBUSER, "-d", DBNAME, "-v", "ON_ERROR_STOP=1", "-1", "-q"],
                       input="\n".join(q) + "\n", capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("寫入失敗（整筆交易回滾）：" + r.stderr[:800])
    print("已寫入。")


if __name__ == "__main__":
    main()
