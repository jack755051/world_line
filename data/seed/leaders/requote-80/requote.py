#!/usr/bin/env python3
"""引文重摘（ARCHITECTURE §16.7.4；Tai 2026-11-10 21:52：quote 上限 80 字，NFC 後字元計）。

對象：B2（§16.7.3）因超過 25 字而 quote 留 NULL 的 3265 筆（`gap-830/b2_dryrun/report.json` 的 skipped/quote_over_25）。
只產 seed／dry-run 檔，**不寫任何資料庫**；5442 只以 default_transaction_read_only=on 查 citation id。

子命令：
  prepare            讀 report.json＋各批 research.json＋sent.5052.json，唯讀查 5442 取 citation id，
                     產 worklist.json（每筆含 citationId、批次 rNN、欄位值、evidence、NFC 字數）。
  build rNN          依 worklist 與 decisions/rNN.json 產 results/rNN.json；並驗證：
                       - 直接採用：NFC(evidence) ≤ 80 字，quote＝evidence 原句。
                       - 重摘：quote 必須逐字（NFC 後）出現在 evidence 中、≤ 80 字、起訖不切斷字詞，
                         且不得是「evidence 前 80 字」這種機械截斷；需附 basis（為何支持該欄位值）。
                       - 留空：需附原因。
                     決策檔缺任何 > 80 字的 citationId 即失敗。
處理方式：direct（直接採用）／requote（重摘）／blank（留空）。
"""
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
GAP = os.path.join(HERE, "..", "gap-830")
sys.path.insert(0, GAP)
QUOTE_MAX = 80
# 依 gap-830 批次分組（每組 5 批，最後一組 4 批）
GROUPS = {f"r{i + 1:02d}": [f"b{n:02d}" for n in range(i * 5 + 1, min(i * 5 + 6, 50))] for i in range(10)}
METHOD_ZH = {"direct": "直接採用", "requote": "重摘", "blank": "留空"}


def nfc(s):
    return unicodedata.normalize("NFC", s)


def n_chars(s):
    return len(nfc(s))


def group_of(batch):
    for g, bs in GROUPS.items():
        if batch in bs:
            return g
    raise SystemExit(f"批次 {batch} 不在分組內")


def prepare():
    import b2_backfill as b  # 唯讀連線（default_transaction_read_only=on，並先驗證生效）
    rep = json.load(open(os.path.join(GAP, "b2_dryrun", "report.json"), encoding="utf-8"))
    todo = [x for x in rep["skipped"] if x["reason"] == "quote_over_25"]
    bios, cits, srcs, _, _ = b.load_db("worldline_borders_dev")
    url_to_src = {}
    for s in srcs.values():
        if s["url"]:
            url_to_src.setdefault(s["url"], s["id"])
    quotes = {r["id"]: r["quote"] for r in b.q_json("worldline_borders_dev",
              "select id::text, quote from leader_bio_field_citations")}
    idx = defaultdict(list)
    for c in cits:
        idx[(c["bio_id"], c["field"], c["source_id"], c["locator"], c["evidence_note"])].append(c)
    docs, ledgers = {}, {}
    out, problems = [], []
    for x in todo:
        bt = x["batch"]
        if bt not in docs:
            docs[bt] = json.load(open(os.path.join(GAP, bt, "research.json"), encoding="utf-8"))
            ledgers[bt] = json.load(open(os.path.join(GAP, bt, "sent.5052.json"), encoding="utf-8"))
        person = next(p for p in docs[bt]["people"] if p.get("key") == x["key"])
        value = (person.get(x["field"]) or {}).get("value")
        src_id = ledgers[bt]["sources"].get(x["url"]) or url_to_src.get(x["url"])
        live = [c for c in idx.get((x["bioId"], x["field"], src_id, x["locator"], x["evidence"]), []) if not c["retracted"]]
        if len(live) != 1:
            problems.append({**x, "matches": len(live)})
            continue
        cid = live[0]["id"]
        if quotes.get(cid) is not None:
            problems.append({**x, "citationId": cid, "problem": "DB quote 已非 NULL"})
            continue
        out.append({"citationId": cid, "group": group_of(bt), "batch": bt, "key": x["key"], "bioId": x["bioId"],
                    "field": x["field"], "value": value, "sourceId": src_id, "url": x["url"], "locator": x["locator"],
                    "evidence": x["evidence"], "nfcChars": n_chars(x["evidence"])})
    out.sort(key=lambda r: (r["batch"], r["key"], r["field"], r["url"] or "", r["locator"] or "", r["citationId"]))
    if problems or len(out) != len(todo) or len({r["citationId"] for r in out}) != len(out):
        json.dump(problems, open(os.path.join(HERE, "prepare_problems.json"), "w"), ensure_ascii=False, indent=1)
        raise SystemExit(f"對應失敗：{len(problems)} 筆（見 prepare_problems.json）；out={len(out)} todo={len(todo)}")
    json.dump({"source": "gap-830/b2_dryrun/report.json skipped[reason=quote_over_25]", "quoteMax": QUOTE_MAX,
               "count": len(out), "groups": GROUPS, "items": out},
              open(os.path.join(HERE, "worklist.json"), "w"), ensure_ascii=False, indent=1)
    print(f"worklist {len(out)}；≤80 {sum(r['nfcChars'] <= QUOTE_MAX for r in out)}；>80 {sum(r['nfcChars'] > QUOTE_MAX for r in out)}")


WORD = re.compile(r"\w", re.UNICODE)
CJK = re.compile(r"[぀-ヿ㐀-鿿豈-﫿\U00020000-\U0003ffff]")


def boundary_ok(ev, start, end):
    """片段起訖不切斷字詞（拉丁等以空白分詞的文字）；CJK 字元間視為可切。"""
    def cuts(i):  # 在 ev[i-1] 與 ev[i] 之間切
        if i <= 0 or i >= len(ev):
            return False
        a, b_ = ev[i - 1], ev[i]
        return bool(WORD.match(a) and WORD.match(b_) and not (CJK.match(a) or CJK.match(b_)))
    return not cuts(start) and not cuts(end)


def check_requote(item, d):
    ev, q = nfc(item["evidence"]), nfc(d.get("quote") or "")
    errs = []
    if not q.strip():
        errs.append("quote 空白")
    if q != q.strip():
        errs.append("quote 前後有空白")
    if n_chars(q) > QUOTE_MAX:
        errs.append(f"quote {n_chars(q)} 字 > {QUOTE_MAX}")
    pos = ev.find(q)
    if pos < 0:
        errs.append("quote 未逐字出現在 evidence")
    else:
        if not boundary_ok(ev, pos, pos + len(q)):
            errs.append("quote 起訖切斷字詞")
        if pos == 0 and len(q) >= QUOTE_MAX - 3:
            errs.append("疑似取前 80 字的機械截斷")
    if not (d.get("basis") or "").strip():
        errs.append("缺 basis（支持欄位值的理由）")
    return errs


def build(group):
    wl = json.load(open(os.path.join(HERE, "worklist.json"), encoding="utf-8"))
    items = [r for r in wl["items"] if r["group"] == group]
    dpath = os.path.join(HERE, "decisions", f"{group}.json")
    dec = json.load(open(dpath, encoding="utf-8")) if os.path.exists(dpath) else {}
    rows, errors = [], []
    for it in items:
        base = {"id": it["citationId"], "batch": it["batch"], "key": it["key"], "bioId": it["bioId"],
                "field": it["field"], "url": it["url"], "locator": it["locator"], "evidenceChars": it["nfcChars"]}
        if it["nfcChars"] <= QUOTE_MAX:
            if it["citationId"] in dec:
                errors.append((it["citationId"], "≤80 字者不應有重摘決策"))
            rows.append({**base, "method": "direct", "methodZh": METHOD_ZH["direct"], "quote": it["evidence"],
                         "quoteChars": it["nfcChars"]})
            continue
        d = dec.get(it["citationId"])
        if d is None:
            errors.append((it["citationId"], "缺決策"))
            continue
        if d.get("method") == "requote":
            e = check_requote(it, d)
            if e:
                errors.append((it["citationId"], "；".join(e)))
                continue
            q = nfc(d["quote"])
            rows.append({**base, "method": "requote", "methodZh": METHOD_ZH["requote"], "quote": q,
                         "quoteChars": n_chars(q), "quoteFrom": "evidence", "basis": d["basis"],
                         "evidence": it["evidence"]})
        elif d.get("method") == "blank":
            if not (d.get("reason") or "").strip():
                errors.append((it["citationId"], "留空缺原因"))
                continue
            rows.append({**base, "method": "blank", "methodZh": METHOD_ZH["blank"], "quote": None,
                         "blankReason": d["reason"], "evidence": it["evidence"]})
        else:
            errors.append((it["citationId"], f"未知 method {d.get('method')}"))
    extra = set(dec) - {it["citationId"] for it in items}
    for cid in extra:
        errors.append((cid, "決策 id 不屬本批"))
    if errors:
        for e in errors[:50]:
            print("ERR", *e)
        raise SystemExit(f"{group}：{len(errors)} 個錯誤，未輸出")
    cnt = {m: sum(r["method"] == m for r in rows) for m in METHOD_ZH}
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    json.dump({"group": group, "batches": GROUPS[group], "quoteMax": QUOTE_MAX, "count": len(rows), "counts": cnt,
               "rows": rows}, open(os.path.join(HERE, "results", f"{group}.json"), "w"), ensure_ascii=False, indent=1)
    print(group, len(rows), cnt)


if __name__ == "__main__":
    if sys.argv[1:2] == ["prepare"]:
        prepare()
    elif sys.argv[1:2] == ["build"] and len(sys.argv) == 3:
        build(sys.argv[2])
    else:
        raise SystemExit(__doc__)
