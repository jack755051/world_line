#!/usr/bin/env python3
"""
人物生平補齊 batch p1（2026-11-07）：驗證 staged 檔 → 試跑 → 寫入（經 API，不直接寫 DB）。

- 讀本資料夾的 us-es.json、su-tr.json、roc.json（格式見 SCHEMA.md）。
- 驗證（不過就整個人跳過，列在報告）：
  * 每個有值的欄位至少一個非 Wikidata／Wikipedia 來源，且有 url、locator、evidence、accessedOn、合法 sourceKind；
  * 列在 conflicts 的欄位不可有值；日期格式、精度、卒日不早於生日；
  * 照片授權在允許清單（us_federal_pd、pd_expired、cc0、cc_by、cc_by_sa）、出處頁在 commons.wikimedia.org、署名與查證日期齊全；
  * recordIds 在庫中有效、目前沒有連生平、任期姓名在 recordNameVariants 內（唯讀查 DB）。
- 寫入順序：POST /sources（同一網址只建一次；庫中已有同網址就沿用）→ POST /leader-bios（含 citations、portrait、
  fieldSources 只記待查證欄的狀態）→ PATCH /leader-records/{id}/person。不 DELETE、不覆蓋已連生平的任期。
- 預設只驗證並印出計畫；--send 才寫入。--base 指定 API（預設 5052；拒絕 5051）；--db 指定唯讀查詢用的資料庫名。
- 記帳：sent-p1.<port>.json（person key → bio id、source url → source id），重跑冪等。
- API key 讀 .dev/api.env 的 WORLDLINE_API_KEY，不印出。
"""
import argparse, glob, json, os, re, subprocess, sys, urllib.error, urllib.request
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CONTAINER = "worldline-borders-dev-db"
LICENSES = {"us_federal_pd", "pd_expired", "cc0", "cc_by", "cc_by_sa"}
KINDS = {"official_record", "official_history", "peer_reviewed", "dataset", "trial_record", "treaty"}
PRECS = {"day", "month", "year"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
QID_RE = re.compile(r"^Q[1-9]\d*$")
FIELDS = ["name", "nameZh", "birthDate", "deathDate", "birthPlace", "party", "summary"]
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(next(p for p in _Path(__file__).resolve().parents if (p / "data" / "source-policy.json").exists()) / "tools"))
import source_policy as _sp  # 全專案唯一的來源政策：data/source-policy.json
BANNED_HOSTS = _sp.BANNED_HOSTS


def api_key():
    for line in open(os.path.join(REPO, ".dev", "api.env"), encoding="utf-8"):
        if line.startswith("WORLDLINE_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit("找不到 WORLDLINE_API_KEY")


def call(base, method, path, body, key):
    req = urllib.request.Request(base + path, method=method, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "X-API-Key": key})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:400]


def sql(db, q):
    out = subprocess.run(["docker", "exec", "-i", CONTAINER, "psql", "-U", "worldline", "-d", db, "-At", "-F", "\t", "-c", q],
                         check=True, capture_output=True, text=True).stdout
    return [l.split("\t") for l in out.splitlines() if l]


def check_source(s, where, errs):
    for k in ("title", "publisher", "url", "locator", "evidence", "accessedOn", "sourceKind"):
        if not (s.get(k) or "").strip():
            errs.append(f"{where}: 來源缺 {k}")
    url = s.get("url") or ""
    if any(h in url for h in BANNED_HOSTS):
        errs.append(f"{where}: {url} 只能當線索，不能當來源")
    if s.get("sourceKind") and s["sourceKind"] not in KINDS:
        errs.append(f"{where}: sourceKind {s['sourceKind']} 不合法")
    if s.get("accessedOn") and not DATE_RE.match(s["accessedOn"]):
        errs.append(f"{where}: accessedOn 格式")


def validate(p, records):
    errs, key = [], p.get("key", "?")
    conflict_fields = {c.get("field") for c in p.get("conflicts") or []}
    for f in FIELDS:
        v = p.get(f)
        if not v or v.get("value") in (None, "", {}):
            continue
        if f in conflict_fields:
            errs.append(f"{key}.{f}: 列在 conflicts 卻有值")
        srcs = v.get("sources") or []
        if f != "nameZh" and not srcs:
            errs.append(f"{key}.{f}: 有值但沒有來源")
        for i, s in enumerate(srcs):
            check_source(s, f"{key}.{f}.sources[{i}]", errs)
        if f in ("birthDate", "deathDate"):
            if not DATE_RE.match(v["value"]):
                errs.append(f"{key}.{f}: 日期格式 {v['value']}")
            if v.get("precision") not in PRECS:
                errs.append(f"{key}.{f}: precision 必須是 day/month/year")
        if f in ("birthPlace", "party", "summary") and not isinstance(v["value"], dict):
            errs.append(f"{key}.{f}: 必須是 {{zh-Hant, en}}")
    b, d = (p.get("birthDate") or {}).get("value"), (p.get("deathDate") or {}).get("value")
    if b and d and d < b:
        errs.append(f"{key}: 卒日早於生日")
    if p.get("wikidataQid") and not QID_RE.match(p["wikidataQid"]):
        errs.append(f"{key}: wikidataQid 格式")
    pt = p.get("portrait")
    if pt:
        if pt.get("licenseCode") not in LICENSES:
            errs.append(f"{key}.portrait: 授權 {pt.get('licenseCode')} 不在允許清單")
        for k in ("fileUrl", "sourceUrl", "attribution", "retrievedOn"):
            if not (pt.get(k) or "").strip():
                errs.append(f"{key}.portrait: 缺 {k}")
        if not (pt.get("sourceUrl") or "").startswith("https://commons.wikimedia.org/wiki/File:"):
            errs.append(f"{key}.portrait: sourceUrl 不是 Commons 檔案頁")
        if not (pt.get("fileUrl") or "").startswith("https://"):
            errs.append(f"{key}.portrait: fileUrl 不是 https")
    ids = p.get("recordIds") or []
    if not ids:
        errs.append(f"{key}: 沒有 recordIds")
    variants = set(p.get("recordNameVariants") or [])
    for rid in ids:
        r = records.get(rid)
        if not r:
            errs.append(f"{key}: 任期 {rid} 不存在或已撤回")
        elif r["person_id"]:
            errs.append(f"{key}: 任期 {rid} 已連到生平 {r['person_id']}，不覆蓋")
        elif variants and r["name"] not in variants:
            errs.append(f"{key}: 任期 {rid} 姓名「{r['name']}」不在 recordNameVariants")
    return errs


def build_bio(p, src_ids):
    body = {"name": p["name"]["value"], "isTest": False}
    if (p.get("nameZh") or {}).get("value"):
        body["nameZh"] = p["nameZh"]["value"]
    for f in ("birthDate", "deathDate"):
        v = p.get(f) or {}
        if v.get("value"):
            body[f] = v["value"]
            body[f + "Precision"] = v["precision"]
    for f in ("birthPlace", "party", "summary"):
        v = p.get(f) or {}
        if v.get("value"):
            body[f] = {k: x for k, x in v["value"].items() if x}
    if p.get("wikidataQid"):
        body["wikidataQid"] = p["wikidataQid"]
    pt = p.get("portrait")
    if pt:
        body["portrait"] = {"url": pt["fileUrl"], "sourceUrl": pt["sourceUrl"], "author": pt.get("author"),
                            "licenseCode": pt["licenseCode"], "licenseUrl": pt.get("licenseUrl") or None,
                            "attribution": pt["attribution"], "retrievedOn": pt["retrievedOn"]}
    # 舊格式 fieldSources 只記狀態：沒有值的欄位標「待查證」（附線索），有值的欄位改由 citations 溯源
    fs = {}
    unv = {u.get("field"): u for u in p.get("unverified") or []}
    con = {c.get("field"): c for c in p.get("conflicts") or []}
    for f in ("birthDate", "deathDate", "birthPlace", "party", "summary"):
        if not (p.get(f) or {}).get("value"):
            note = (con.get(f) or {}).get("note") or (unv.get(f) or {}).get("why") or ""
            fs[f] = {"status": "待查證", **({"note": ("說法衝突：" if f in con else "") + note} if note else {})}
    if fs:
        body["fieldSources"] = fs
    cits = []
    for f in FIELDS:
        v = p.get(f) or {}
        if not v.get("value"):
            continue
        for s in v.get("sources") or []:
            cits.append({"field": f, "sourceId": src_ids.get(s["url"], "<new>"), "locator": s["locator"],
                         "evidenceNote": s["evidence"], "accessedOn": s["accessedOn"]})
    body["citations"] = cits
    return body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:5052/api/v1")
    ap.add_argument("--db", default="worldline_borders_dev")
    ap.add_argument("--send", action="store_true")
    a = ap.parse_args()
    if ":5051" in a.base:
        sys.exit("拒絕 5051")
    port = re.search(r":(\d+)", a.base).group(1)
    ledger_path = os.path.join(HERE, f"sent-p1.{port}.json")
    ledger = json.load(open(ledger_path)) if os.path.exists(ledger_path) else {"bios": {}, "sources": {}}

    people = []
    for fn in sorted(glob.glob(os.path.join(HERE, "*.json"))):
        if os.path.basename(fn).startswith("sent-"):
            continue
        doc = json.load(open(fn, encoding="utf-8"))
        if "people" in doc:
            people += [(os.path.basename(fn), p) for p in doc["people"]]

    rows = sql(a.db, "select id, name, coalesce(person_id::text,'') from leader_records where retracted_at is null")
    records = {r[0]: {"name": r[1], "person_id": r[2]} for r in rows}
    existing_src = {r[1]: r[0] for r in sql(a.db, "select id, url from sources where url is not null")}

    ok, skipped = [], []
    for fn, p in people:
        if p["key"] in ledger["bios"]:
            print(f"已寫過，略過：{p['key']} → {ledger['bios'][p['key']]}")
            continue
        errs = validate(p, records)
        (skipped if errs else ok).append((fn, p, errs))
    for fn, p, errs in skipped:
        print(f"✗ {fn}:{p['key']}")
        for e in errs:
            print(f"    {e}")

    src_ids = {**existing_src, **ledger["sources"]}
    plan_sources = {}
    for _, p, _ in ok:
        for f in FIELDS:
            for s in (p.get(f) or {}).get("sources") or []:
                if s["url"] not in src_ids:
                    plan_sources[s["url"]] = s
    print(f"\n計畫：新來源 {len(plan_sources)}（沿用既有 {sum(1 for _, p, _ in ok for f in FIELDS for s in (p.get(f) or {}).get('sources') or [] if s['url'] in src_ids)} 次）、新生平 {len(ok)}、"
          f"連結任期 {sum(len(p['recordIds']) for _, p, _ in ok)}、略過 {len(skipped)}")
    for _, p, _ in ok:
        vals = [f for f in FIELDS if (p.get(f) or {}).get("value")]
        print(f"  ✓ {p['key']}: 欄位 {','.join(vals)}；照片 {'有' if p.get('portrait') else '無'}；任期 {len(p['recordIds'])}")
    if not a.send:
        print("\n（試跑：未寫入。加 --send 才寫入）")
        return

    key = api_key()
    for url, s in plan_sources.items():
        st, res = call(a.base, "POST", "/sources", {
            "sourceKind": s["sourceKind"], "title": s["title"], "publisher": s["publisher"], "url": url,
            "licenseCode": s.get("licenseCode"), "note": f"人物生平補齊 batch p1（{date.today().isoformat()} 查證）"}, key)
        if st != 201:
            sys.exit(f"POST /sources 失敗 {st}: {res}")
        src_ids[url] = ledger["sources"][url] = res["data"]["id"]
        json.dump(ledger, open(ledger_path, "w"), ensure_ascii=False, indent=1)
    for _, p, _ in ok:
        body = build_bio(p, src_ids)
        st, res = call(a.base, "POST", "/leader-bios", body, key)
        if st != 201:
            print(f"✗ POST /leader-bios {p['key']} 失敗 {st}: {res}")
            continue
        bid = res["data"]["id"]
        ledger["bios"][p["key"]] = bid
        json.dump(ledger, open(ledger_path, "w"), ensure_ascii=False, indent=1)
        for rid in p["recordIds"]:
            st, res = call(a.base, "PATCH", f"/leader-records/{rid}/person", {"personId": bid}, key)
            if st != 200:
                print(f"  ✗ PATCH {rid} 失敗 {st}: {res}")
        print(f"✓ {p['key']} → {bid}（任期 {len(p['recordIds'])}）")
    print("完成")


if __name__ == "__main__":
    main()
