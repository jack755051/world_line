#!/usr/bin/env python3
"""
卒日精度補寫（batch p1，2026-11-07）：14 筆生平原文只到年／月，先前因沒有精度欄位而沒寫卒日。
依 death-precision.json（當天重新打開原出處確認）走「撤回重寫」：POST /leader-bios/{id}/revisions。
- 新版內容＝舊版全部欄位＋deathDate／deathDatePrecision＋一筆 deathDate 引用（接 sources，同網址只建一次）。
- 舊版保留並標撤回原因、superseded_by；任期自動改連新版；不 DELETE。
- 只處理 confirmed=true 且舊版仍有效、卒日仍為空者。預設試跑；--send 才寫入；拒絕 5051。
- 記帳：sent-death.<port>.json。
"""
import argparse, json, os, re, sys, urllib.request
from send_p1 import api_key, call, sql

HERE = os.path.dirname(os.path.abspath(__file__))


def get(base, path):
    with urllib.request.urlopen(base + path, timeout=60) as r:
        return json.loads(r.read())["data"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:5052/api/v1")
    ap.add_argument("--db", default="worldline_borders_dev")
    ap.add_argument("--send", action="store_true")
    a = ap.parse_args()
    if ":5051" in a.base:
        sys.exit("拒絕 5051")
    port = re.search(r":(\d+)", a.base).group(1)
    ledger_path = os.path.join(HERE, f"sent-death.{port}.json")
    ledger = json.load(open(ledger_path)) if os.path.exists(ledger_path) else {"bios": {}, "sources": {}}
    items = json.load(open(os.path.join(HERE, "death-precision.json"), encoding="utf-8"))["items"]
    existing_src = {r[1]: r[0] for r in sql(a.db, "select id, url from sources where url is not null")}
    src_ids = {**existing_src, **ledger["sources"]}
    plan = []
    for it in items:
        if it["bioId"] in ledger["bios"]:
            print(f"已寫過：{it['name']}")
            continue
        if not it.get("confirmed"):
            print(f"✗ 未確認，略過：{it['name']}：{it.get('why')}")
            continue
        old = get(a.base, f"/leader-bios/{it['bioId']}")
        if old.get("retractedAt") or old.get("deathDate"):
            print(f"✗ 已撤回或已有卒日，略過：{it['name']}")
            continue
        s = it["source"]
        if not all((s.get(k) or "").strip() for k in ("title", "publisher", "url", "locator", "evidence", "accessedOn")):
            print(f"✗ 來源欄位不全，略過：{it['name']}")
            continue
        plan.append((it, old))
        print(f"  ✓ {it['name']}: {it['deathDate']}（{it['precision']}）← {s['url']}")
    print(f"\n計畫：撤回重寫 {len(plan)} 筆")
    if not a.send:
        print("（試跑：未寫入。加 --send 才寫入）")
        return
    key = api_key()
    for it, old in plan:
        s = it["source"]
        if s["url"] not in src_ids:
            st, res = call(a.base, "POST", "/sources", {"sourceKind": s["sourceKind"], "title": s["title"], "publisher": s["publisher"],
                                                        "url": s["url"], "licenseCode": s.get("licenseCode"),
                                                        "note": "人物生平補齊 batch p1：卒日精度（2026-11-07 重新查證）"}, key)
            if st != 201:
                sys.exit(f"POST /sources 失敗 {st}: {res}")
            src_ids[s["url"]] = ledger["sources"][s["url"]] = res["data"]["id"]
        fs = dict(old.get("fieldSources") or {})
        ds = dict(fs.get("deathDate") or {})
        ds["note"] = f"{ds.get('note', '')}；2026-11-07 起以 deathDatePrecision={it['precision']} 記錄卒日".lstrip("；")
        fs["deathDate"] = ds
        bio = {k: old.get(k) for k in ("name", "nameZh", "birthDate", "birthDatePrecision", "birthPlace", "party", "summary", "wikidataQid", "isTest")}
        bio = {k: v for k, v in bio.items() if v is not None}
        if old.get("portrait"):
            bio["portrait"] = {k: old["portrait"][k] for k in ("url", "sourceUrl", "author", "licenseCode", "licenseUrl", "attribution", "retrievedOn")}
        bio.update({"deathDate": it["deathDate"], "deathDatePrecision": it["precision"], "fieldSources": fs,
                    "citations": [{"field": "deathDate", "sourceId": src_ids[s["url"]], "locator": s["locator"],
                                   "evidenceNote": s["evidence"], "accessedOn": s["accessedOn"]}]})
        st, res = call(a.base, "POST", f"/leader-bios/{it['bioId']}/revisions",
                       {"reason": f"補卒日（原文只到{'年' if it['precision'] == 'year' else '月' if it['precision'] == 'month' else '日'}，新增精度欄位後補寫；2026-11-07 重新查證出處）", "bio": bio}, key)
        if st != 201:
            print(f"✗ {it['name']} 失敗 {st}: {res}")
            continue
        ledger["bios"][it["bioId"]] = res["data"]["id"]
        json.dump(ledger, open(ledger_path, "w"), ensure_ascii=False, indent=1)
        print(f"✓ {it['name']}: {it['bioId']} → {res['data']['id']}")
    print("完成")


if __name__ == "__main__":
    main()
