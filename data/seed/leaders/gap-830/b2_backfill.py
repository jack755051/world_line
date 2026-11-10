#!/usr/bin/env python3
"""B2 回填（ARCHITECTURE §16.7 B2；Tai 2026-11-10 16:20 核准「只寫腳本＋dry-run，不寫入」）。

把 gap-830 `bNN/research.json` 既有資料回填到 B1 新欄位／新表（只讀 seed 檔，不重新查證）：
  1. S.evidence → leader_bio_field_citations.quote（以 bio_id＋field＋source_id＋locator＋evidence_note 對到既有列）
  2. P.conflicts → leader_bio_gaps(gap_kind='conflict')；P.unverified → leader_bio_gaps(gap_kind='not_found')

本腳本**只有 dry-run**：沒有任何寫入程式路徑。讀 5442 時以 `default_transaction_read_only=on` 連線，
即使誤加寫入語句也會被 DB 拒絕。實際寫入需先套用 migration BioCitationFieldsAndGaps，且需 Tai 另行核准後再補寫入模式。

規則（對齊 Domain/BioSourcePolicy.cs，版本 bio-2026-11-v0）：
  - quote ≤ 25 字，以 Unicode text element 計（NFC 後）。Python 標準庫沒有 UAX #29 分段，
    這裡用近似：NFC 後的 code point 數，扣掉組合符號（Mn/Mc/Me）、ZWJ 及其後一字、變體選擇符、膚色修飾符。
    近似與純 code point 數落在 25 兩側者列入 `quoteNeedsCsharpCheck`，寫入前以 C# 規則複核。
  - 硬性排除網域／出版者 → 不回填 quote，列入 skip。
  - conflict 缺口：DB 該欄須為 NULL，否則列入 conflicts（不回填）。
  - unverified：DB 該欄已有值者不建 not_found 缺口，列入 skip。

用法：python3 b2_backfill.py [--db worldline_borders_dev] [--out b2_dryrun]
輸出：<out>/report.json（明細）、<out>/summary.md（數字）。
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import unicodedata
from collections import Counter, defaultdict
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
CONTAINER = "worldline-borders-dev-db"
ALLOWED_DBS = {"worldline_borders_dev"}  # 只允許 5442 的開發庫；絕不連 appdb_ww2／5432
POLICY_VERSION = "bio-2026-11-v0"
QUOTE_MAX = 25
EXCLUDED_HOSTS = ("wikipedia.org", "wikidata.org", "baidu.com", "enciclopediadelecuador.com")
EXCLUDED_PUBLISHER_FRAGMENTS = ("wikipedia", "wikidata", "百度", "baidu")
SELF_MADE = {"自製", "自制", "self-made", "self made", "selfmade", "own work"}
# Domain/Vocabulary.cs LeaderBioFields.All（含 B1 新增 deathPlace）
BIO_FIELDS = ["name", "nameZh", "birthDate", "deathDate", "birthPlace", "deathPlace", "party", "summary", "portrait"]
# send_batch.py 寫 citation 的欄位
CITED_FIELDS = ["name", "nameZh", "birthDate", "deathDate", "birthPlace", "party", "summary"]
# DB 欄位對照（判斷「該欄是否為 NULL」）；deathPlace 欄 B1 才新增，DB 尚無 → 視為 NULL
DB_COL = {"name": "name", "nameZh": "name_zh", "birthDate": "birth_date", "deathDate": "death_date",
          "birthPlace": "birth_place", "party": "party", "summary": "summary", "portrait": "portrait_url"}


def parse_field(raw):
    """seed 的 field 寫法不一：'birthDate'、'birthDate (day)'、'birthDate/deathDate day'、'identity'…
    回傳 (欄位清單, 限定詞)。斜線拆成多欄；結尾括號或 day|month|year 視為精度／細節限定詞。不做其他推測。"""
    s, q = (raw or "").strip(), None
    m = re.match(r"^(.*?)\s*\(([^)]*)\)$", s)
    if m:
        s, q = m.group(1), m.group(2).strip()
    else:
        m = re.match(r"^(.*\S)\s+(day|month|year)$", s)
        if m:
            s, q = m.group(1), m.group(2)
    return [x.strip() for x in s.split("/") if x.strip()], q


# ── 字數（近似 text element）──
def cp_len(s):
    return len(unicodedata.normalize("NFC", s))


def te_len(s):
    s = unicodedata.normalize("NFC", s)
    n, skip_next = 0, False
    for ch in s:
        o = ord(ch)
        if skip_next:
            skip_next = False
            continue
        if o == 0x200D:  # ZWJ：與下一字併入前一個叢集
            skip_next = True
            continue
        if unicodedata.category(ch) in ("Mn", "Mc", "Me") or 0xFE00 <= o <= 0xFE0F or 0x1F3FB <= o <= 0x1F3FF:
            continue
        n += 1
    return n


def host_excluded(url):
    try:
        h = (urlparse((url or "").strip()).hostname or "").lower().rstrip(".")
    except ValueError:
        return False
    return any(h == x or h.endswith("." + x) for x in EXCLUDED_HOSTS)


def publisher_excluded(p):
    p = (p or "").strip()
    return bool(p) and (p.lower() in SELF_MADE or any(f in p.lower() for f in EXCLUDED_PUBLISHER_FRAGMENTS))


# ── 唯讀 DB ──
def q_json(db, sql):
    """回傳 json_agg 結果。連線設 default_transaction_read_only=on。"""
    if db not in ALLOWED_DBS:
        sys.exit(f"拒絕連線 {db}（只允許 {ALLOWED_DBS}）")
    cmd = ["docker", "exec", "-i", "-e", "PGOPTIONS=-c default_transaction_read_only=on", CONTAINER,
           "psql", "-U", "worldline", "-d", db, "-At", "-v", "ON_ERROR_STOP=1",
           "-c", f"select coalesce(json_agg(t), '[]'::json) from ({sql}) t"]
    out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    return json.loads(out)


def load_db(db):
    ro = q_json(db, "select current_setting('default_transaction_read_only') as ro")[0]["ro"]
    if ro != "on":
        sys.exit("唯讀連線設定未生效，停止")
    bios = {r["id"]: r for r in q_json(db, """
        select id::text, retracted_at is not null as retracted, superseded_by::text,
               name, name_zh, birth_date, death_date, birth_place, party, summary, portrait_url
        from leader_bios""")}
    cits = q_json(db, """
        select c.id::text, c.bio_id::text, c.field, c.source_id::text, c.locator, c.evidence_note,
               c.retracted_at is not null as retracted
        from leader_bio_field_citations c""")
    srcs = {r["id"]: r for r in q_json(db, "select id::text, url, archive_url, publisher, title from sources")}
    has_quote_col = q_json(db, """select count(*) as n from information_schema.columns
        where table_name='leader_bio_field_citations' and column_name='quote'""")[0]["n"] > 0
    has_gaps = q_json(db, "select to_regclass('leader_bio_gaps') is not null as x")[0]["x"]
    return bios, cits, srcs, has_quote_col, has_gaps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="worldline_borders_dev")
    ap.add_argument("--out", default=os.path.join(HERE, "b2_dryrun"))
    a = ap.parse_args()

    bios, cits, srcs, has_quote_col, has_gaps = load_db(a.db)
    url_to_src = {}
    for s in srcs.values():
        if s["url"]:
            url_to_src.setdefault(s["url"], s["id"])
    cit_index = defaultdict(list)  # (bio, field, source, locator, evidence) → [cit]
    for c in cits:
        cit_index[(c["bio_id"], c["field"], c["source_id"], c["locator"], c["evidence_note"])].append(c)

    R = {"policyVersion": POLICY_VERSION, "db": a.db, "schema": {"quoteColumn": has_quote_col, "gapsTable": has_gaps},
         "quoteUpdates": [], "gapInserts": [], "skipped": [], "conflicts": [], "quoteNeedsCsharpCheck": []}
    C = Counter()
    matched_cit_ids = set()  # 計畫回填 quote 的列
    found_cit_ids = set()    # 被 seed 對到的列（不論是否通過政策）
    gap_keys = {}
    touched_bios = set()

    def skip(kind, **kw):
        C[f"skip:{kind}"] += 1
        R["skipped"].append({"reason": kind, **kw})

    def conflict(kind, **kw):
        C[f"conflict:{kind}"] += 1
        R["conflicts"].append({"reason": kind, **kw})

    for bdir in sorted(glob.glob(os.path.join(HERE, "b[0-9][0-9]"))):
        batch = os.path.basename(bdir)
        rp, sp = os.path.join(bdir, "research.json"), os.path.join(bdir, "sent.5052.json")
        if not os.path.exists(rp):
            continue
        doc = json.load(open(rp, encoding="utf-8"))
        ledger = json.load(open(sp, encoding="utf-8")) if os.path.exists(sp) else {"bios": {}, "sources": {}}
        checked_on = doc.get("researchedOn")
        C["seed:staging"] += len(doc.get("staging") or [])
        for p in doc.get("people") or []:
            C["seed:people"] += 1
            key = p.get("key")
            where = {"batch": batch, "key": key}
            bio_id = ledger["bios"].get(key)
            if not bio_id:
                skip("person_not_sent", **where)
                continue
            bio = bios.get(bio_id)
            if not bio:
                conflict("bio_missing_in_db", bioId=bio_id, **where)
                continue
            if bio["retracted"]:
                conflict("bio_retracted", bioId=bio_id, supersededBy=bio["superseded_by"], **where)
                continue
            touched_bios.add(bio_id)

            # 1. evidence → quote
            for f in CITED_FIELDS:
                v = p.get(f) or {}
                if not v.get("value"):
                    continue
                for s in v.get("sources") or []:
                    C["seed:citations"] += 1
                    w = {**where, "bioId": bio_id, "field": f, "url": s.get("url"), "locator": s.get("locator")}
                    ev = s.get("evidence")
                    if not (ev or "").strip():
                        skip("evidence_blank", **w)
                        continue
                    src_id = ledger["sources"].get(s.get("url")) or url_to_src.get(s.get("url"))
                    if not src_id:
                        conflict("source_not_in_db", **w)
                        continue
                    rows = cit_index.get((bio_id, f, src_id, s.get("locator"), ev), [])
                    live = [r for r in rows if not r["retracted"]]
                    if not live:
                        conflict("citation_not_in_db" if not rows else "citation_retracted", sourceId=src_id, **w)
                        continue
                    found_cit_ids.update(r["id"] for r in live)
                    src = srcs[src_id]
                    if host_excluded(src.get("url")) or host_excluded(src.get("archive_url")) or publisher_excluded(src.get("publisher")):
                        skip("source_hard_excluded", sourceId=src_id, publisher=src.get("publisher"), **w)
                        continue
                    n_te, n_cp = te_len(ev), cp_len(ev)
                    if (n_te <= QUOTE_MAX) != (n_cp <= QUOTE_MAX):
                        R["quoteNeedsCsharpCheck"].append({**w, "evidence": ev, "approxTextElements": n_te, "codePoints": n_cp})
                    if n_te > QUOTE_MAX:
                        skip("quote_over_25", length=n_te, evidence=ev, **w)
                        continue
                    for r in live:
                        if r["id"] in matched_cit_ids:
                            C["dup:same_db_row_matched_twice"] += 1
                            continue
                        matched_cit_ids.add(r["id"])
                        R["quoteUpdates"].append({"citationId": r["id"], "quote": ev, "quoteLength": n_te, **w})
                    if len(live) > 1:
                        C["info:seed_citation_matched_multiple_db_rows"] += 1

            # 2. conflicts / unverified → gaps
            for kind, items in (("conflict", p.get("conflicts") or []), ("not_found", p.get("unverified") or [])):
                for it in items:
                    C[f"seed:{kind}"] += 1
                    raw = it.get("field")
                    fields, qual = parse_field(raw)
                    if fields == ["identity"] and kind == "not_found":
                        targets = [("identity", None, "identity_uncertain")]
                    else:
                        targets = [(f"field:{f}", f, kind) for f in fields]
                    for target, f, gkind in targets:
                        w = {**where, "bioId": bio_id, "rawField": raw, "target": target, "gapKind": gkind}
                        if f is not None and f not in BIO_FIELDS:
                            skip("gap_field_not_in_vocabulary", **w)
                            continue
                        col = DB_COL.get(f) if f else None
                        has_value = col is not None and bio.get(col) not in (None, "", {})
                        if has_value and gkind == "conflict":
                            # 有限定詞（例：日精度衝突、年份一致）＝欄位以較粗精度有值；違反「conflict 時該欄須為 NULL」，需裁定
                            conflict("conflict_qualified_field_has_value" if qual else "conflict_but_field_has_value",
                                     dbValue=bio.get(col), qualifier=qual, **w)
                            continue
                        if has_value and gkind == "not_found":
                            skip("unverified_qualified_field_has_value" if qual else "unverified_but_field_has_value",
                                 qualifier=qual, **w)
                            continue
                        gk = (bio_id, target, gkind)
                        if gk in gap_keys:
                            skip("gap_duplicate", firstSeenIn=gap_keys[gk], **w)
                            continue
                        gap_keys[gk] = batch
                        cands = None
                        if gkind == "conflict":
                            cands = []
                            for x in it.get("values") or []:
                                if isinstance(x, dict):
                                    src = x.get("source") or {}
                                    cands.append({"value": x.get("value"), "url": src.get("url"), "title": src.get("title"),
                                                  "publisher": src.get("publisher"), "locator": src.get("locator"),
                                                  "quote": src.get("evidence")})
                                else:
                                    cands.append({"value": x})  # 舊寫法只有文字，沒有結構化來源
                            note = it.get("note") or it.get("why")
                        else:
                            note = "；".join(x for x in (it.get("why"), it.get("clue") and f"線索：{it['clue']}") if x) or None
                        if raw != f:
                            note = f"[{raw}] {note or ''}".strip()
                        R["gapInserts"].append({"bioId": bio_id, "target": target, "gapKind": gkind, "note": note,
                                                "candidateCitations": cands, "checkedOn": checked_on, **where})

    # DB 中屬這些人、但沒有被任何 seed 對到的 citation（例：batch p1 或手動寫入）
    unmatched_db = [c for c in cits if c["bio_id"] in touched_bios and not c["retracted"] and c["id"] not in found_cit_ids]
    C["db:citations_found_by_seed"] = len(found_cit_ids)
    C["db:citations_total_live"] = sum(1 for c in cits if not c["retracted"])
    C["db:citations_of_touched_bios_unmatched"] = len(unmatched_db)
    C["plan:quote_updates"] = len(R["quoteUpdates"])
    C["plan:gap_inserts"] = len(R["gapInserts"])
    C["plan:gap_inserts_conflict"] = sum(1 for g in R["gapInserts"] if g["gapKind"] == "conflict")
    C["plan:gap_inserts_not_found"] = sum(1 for g in R["gapInserts"] if g["gapKind"] == "not_found")
    C["plan:gap_inserts_identity_uncertain"] = sum(1 for g in R["gapInserts"] if g["gapKind"] == "identity_uncertain")
    C["check:quoteNeedsCsharpCheck"] = len(R["quoteNeedsCsharpCheck"])
    R["counts"] = dict(sorted(C.items()))
    R["unmatchedDbCitationsSample"] = unmatched_db[:50]

    os.makedirs(a.out, exist_ok=True)
    json.dump(R, open(os.path.join(a.out, "report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    lines = ["# B2 回填 dry-run（不寫入）", "", f"- 資料庫：{a.db}（唯讀連線）；政策版本 {POLICY_VERSION}",
             f"- 目前 schema：quote 欄 {'有' if has_quote_col else '無（migration 未套用）'}；leader_bio_gaps 表 {'有' if has_gaps else '無（migration 未套用）'}",
             "", "| 項目 | 數量 |", "|---|---|"] + [f"| {k} | {v} |" for k, v in sorted(C.items())]
    open(os.path.join(a.out, "summary.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
