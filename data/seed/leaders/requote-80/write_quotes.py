#!/usr/bin/env python3
"""80 字引文寫入 5442（ARCHITECTURE §16.7.4；Tai 2026-11-10 22:28 核准）。

來源：results/r01.json–r10.json 的 rows；method ∈ {direct, requote} 的列寫入
leader_bio_field_citations.quote（id＝列 id，quote＝NFC 正規化後的列 quote）；method＝blank 不寫。
不寫 leader_record_citations。

三種模式（皆只連 5442 容器 worldline-borders-dev-db 的 worldline_borders_dev）：
  預設 dry-run：唯讀連線（default_transaction_read_only=on）。檢查將更新筆數＝3212、每個 id 存在且 quote IS NULL、
                留空 53 筆亦存在且為 NULL；另存寫入前狀態（全表列數、非空 quote 數、全表除 quote 外各欄雜湊、
                非目標列 quote 雜湊、相關表列數）到 write/pre-state.json。任一條件不符即停止（exit 非 0）。
  --write：先重跑 dry-run 檢查，再以單一交易寫入：暫存表載入 3212 筆 → 只 UPDATE quote（id 相符且 quote IS NULL）
           → 交易內核對受影響筆數＝3212、非空 quote 數＝寫前＋3212，不符即 RAISE（整筆 ROLLBACK）。
           不 INSERT（暫存表除外）、不 DELETE、不改其他欄位或表、不跑 migration。
  --verify：唯讀對帳（e 條），結果寫 write/verify.json、write/verify.md。

用法：python3 write_quotes.py [--write --expect 3212] [--verify]
"""
import argparse
import glob
import hashlib
import json
import os
import subprocess
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "write")
CONTAINER = "worldline-borders-dev-db"
DB = "worldline_borders_dev"
ALLOWED = {(CONTAINER, DB)}  # 白名單：只允許 5442 開發庫；絕不連 5432／app_postgres
QUOTE_MAX = 80
EXPECT_TOTAL, EXPECT_WRITE, EXPECT_BLANK = 3265, 3212, 53
OTHER_TABLES = ["leader_bios", "leader_bio_gaps", "leader_records", "leader_record_citations", "sources"]


def nfc(s):
    return unicodedata.normalize("NFC", s)


def psql(sql, readonly=True, stdin=None):
    if (CONTAINER, DB) not in ALLOWED:
        sys.exit("連線目標不在白名單，停止")
    cmd = ["docker", "exec", "-i"]
    if readonly:
        cmd += ["-e", "PGOPTIONS=-c default_transaction_read_only=on"]
    cmd += [CONTAINER, "psql", "-U", "worldline", "-d", DB, "-At", "-v", "ON_ERROR_STOP=1", "-q"]
    if sql is not None:
        cmd += ["-c", sql]
    return subprocess.run(cmd, input=stdin, capture_output=True, text=True)


def q_json(sql):
    r = psql(f"select coalesce(json_agg(t), '[]'::json) from ({sql}) t")
    if r.returncode != 0:
        sys.exit(f"查詢失敗：{r.stderr}")
    return json.loads(r.stdout)


def load_rows():
    rows = []
    for f in sorted(glob.glob(os.path.join(HERE, "results", "r[0-9][0-9].json"))):
        rows += json.load(open(f, encoding="utf-8"))["rows"]
    return rows


def plan(rows):
    """回傳 (寫入清單, 留空 id 清單, 錯誤清單)。"""
    errs = []
    ids = [r["id"] for r in rows]
    if len(rows) != EXPECT_TOTAL:
        errs.append(f"結果檔總列數 {len(rows)} ≠ {EXPECT_TOTAL}")
    if len(set(ids)) != len(ids):
        errs.append("結果檔 id 重複")
    writes, blanks = [], []
    for r in rows:
        m = r["method"]
        if m in ("direct", "requote"):
            q = nfc(r["quote"] or "")
            if not q.strip():
                errs.append(f"{r['id']} quote 空白")
            if len(q) > QUOTE_MAX:
                errs.append(f"{r['id']} quote {len(q)} 字 > {QUOTE_MAX}")
            writes.append({"id": r["id"], "quote": q})
        elif m == "blank":
            if r.get("quote") not in (None, ""):
                errs.append(f"{r['id']} 留空列帶 quote")
            blanks.append(r["id"])
        else:
            errs.append(f"{r['id']} 未知 method {m}")
    if len(writes) != EXPECT_WRITE:
        errs.append(f"將更新筆數 {len(writes)} ≠ {EXPECT_WRITE}")
    if len(blanks) != EXPECT_BLANK:
        errs.append(f"留空筆數 {len(blanks)} ≠ {EXPECT_BLANK}")
    return writes, blanks, errs


def db_state(target_ids):
    """全表狀態：列數、非空 quote 數、除 quote 外各欄雜湊、非目標列 quote 雜湊、其他表列數。"""
    ro = q_json("select current_setting('default_transaction_read_only') as ro, current_database() as db")[0]
    if ro["ro"] != "on" or ro["db"] != DB:
        sys.exit(f"唯讀連線未生效或連錯庫：{ro}")
    s = q_json("""select count(*) as total, count(quote) as quote_nonnull,
        md5(string_agg((to_jsonb(c) - 'quote')::text, E'\\n' order by id)) as other_cols_md5
        from leader_bio_field_citations c""")[0]
    rows = q_json("select id::text, quote from leader_bio_field_citations order by id")
    h = hashlib.md5()
    for r in rows:
        if r["id"] not in target_ids:
            h.update(f"{r['id']}\t{r['quote']!r}\n".encode())
    s["non_target_quote_md5"] = h.hexdigest()
    s["other_tables"] = {t: q_json(f"select count(*) as n from {t}")[0]["n"] for t in OTHER_TABLES}
    return s, {r["id"]: r["quote"] for r in rows}


def dry_run(rows):
    writes, blanks, errs = plan(rows)
    target = {w["id"] for w in writes}
    state, cur = db_state(target)
    missing = [i for i in target if i not in cur]
    nonnull = [i for i in target if i in cur and cur[i] is not None]
    blank_missing = [i for i in blanks if i not in cur]
    blank_nonnull = [i for i in blanks if i in cur and cur[i] is not None]
    if missing:
        errs.append(f"{len(missing)} 個 id 不在 leader_bio_field_citations：{missing[:5]}")
    if nonnull:
        errs.append(f"{len(nonnull)} 個 id 目前 quote 非 NULL：{nonnull[:5]}")
    if blank_missing or blank_nonnull:
        errs.append(f"留空列：不存在 {len(blank_missing)}、非 NULL {len(blank_nonnull)}")
    res = {"mode": "dry-run", "db": DB, "container": CONTAINER, "toUpdate": len(writes), "blanks": len(blanks),
           "idsExist": len(target) - len(missing), "idsQuoteNull": len(target) - len(missing) - len(nonnull),
           "pre": state, "errors": errs,
           "payloadMd5": hashlib.md5(json.dumps(writes, ensure_ascii=False, sort_keys=True).encode()).hexdigest()}
    return res, writes, blanks


def write_sql(writes, pre_nonnull):
    payload = json.dumps(writes, ensure_ascii=False)
    tag = "$qw80$"
    if tag in payload:
        sys.exit("資料含界定符，停止")
    n = len(writes)
    return f"""BEGIN;
CREATE TEMP TABLE qw80_payload ON COMMIT DROP AS
  SELECT x.id, x.quote FROM jsonb_to_recordset({tag}{payload}{tag}::jsonb) AS x(id uuid, quote text);
DO $qw$
DECLARE k bigint;
BEGIN
  SELECT count(*) INTO k FROM qw80_payload;
  IF k <> {n} THEN RAISE EXCEPTION 'QW80 暫存表筆數 % ≠ {n}', k; END IF;
  SELECT count(quote) INTO k FROM leader_bio_field_citations;
  IF k <> {pre_nonnull} THEN RAISE EXCEPTION 'QW80 前置：非空 quote % ≠ 寫前 {pre_nonnull}', k; END IF;
  UPDATE leader_bio_field_citations c SET quote = p.quote
    FROM qw80_payload p WHERE c.id = p.id AND c.quote IS NULL;
  GET DIAGNOSTICS k = ROW_COUNT;
  IF k <> {n} THEN RAISE EXCEPTION 'QW80 受影響筆數 % ≠ {n}', k; END IF;
  SELECT count(quote) INTO k FROM leader_bio_field_citations;
  IF k <> {pre_nonnull + n} THEN RAISE EXCEPTION 'QW80 寫後非空 quote % ≠ {pre_nonnull + n}', k; END IF;
  RAISE NOTICE 'QW80 OK: updated %', {n};
END
$qw$;
COMMIT;
"""


def verify(rows):
    pre = json.load(open(os.path.join(OUT, "pre-state.json"), encoding="utf-8"))["pre"]
    writes, blanks, errs = plan(rows)
    target = {w["id"]: w["quote"] for w in writes}
    state, cur = db_state(set(target))
    C = {}
    # 1. 3212 筆逐筆一致（DB 值 NFC 後與結果檔 NFC 後完全相等；另記 DB 原值是否已為 NFC）
    mism = [i for i, q in target.items() if cur.get(i) is None or nfc(cur[i]) != q]
    C["quotes_match"] = {"expected": len(target), "matched": len(target) - len(mism), "mismatch": mism[:20]}
    C["db_quote_already_nfc"] = all(cur[i] == nfc(cur[i]) for i in target if cur.get(i) is not None)
    sql_match = q_json("""select count(*) as n from leader_bio_field_citations
        where quote is not null and normalize(quote, NFC) = quote""")[0]["n"]
    C["sql_quotes_nfc_rows"] = sql_match
    # 2. 非空總數＝寫前＋3212；全表列數不變
    C["quote_nonnull"] = {"pre": pre["quote_nonnull"], "post": state["quote_nonnull"],
                          "ok": state["quote_nonnull"] == pre["quote_nonnull"] + len(target)}
    C["total_rows"] = {"pre": pre["total"], "post": state["total"], "ok": state["total"] == pre["total"]}
    # 3. 其他欄與其他列未變
    C["other_cols_md5"] = {"pre": pre["other_cols_md5"], "post": state["other_cols_md5"],
                           "ok": pre["other_cols_md5"] == state["other_cols_md5"]}
    C["non_target_quote_md5"] = {"pre": pre["non_target_quote_md5"], "post": state["non_target_quote_md5"],
                                 "ok": pre["non_target_quote_md5"] == state["non_target_quote_md5"]}
    C["other_tables"] = {"pre": pre["other_tables"], "post": state["other_tables"],
                         "ok": pre["other_tables"] == state["other_tables"]}
    # 4. 留空 53 筆仍為 NULL
    bn = [i for i in blanks if cur.get(i, "MISSING") is not None]
    C["blanks_still_null"] = {"expected": len(blanks), "null": len(blanks) - len(bn), "bad": bn}
    # 5. 全表 quote ≤ 80（char_length）
    mx = q_json("""select max(char_length(quote)) as mx, count(*) filter (where char_length(quote) > 80) as over
        from leader_bio_field_citations""")[0]
    C["max_char_length"] = {**mx, "ok": mx["over"] == 0 and (mx["mx"] or 0) <= QUOTE_MAX}
    ok = (not mism and C["quote_nonnull"]["ok"] and C["total_rows"]["ok"] and C["other_cols_md5"]["ok"]
          and C["non_target_quote_md5"]["ok"] and C["other_tables"]["ok"] and not bn and C["max_char_length"]["ok"]
          and not errs)
    return {"mode": "verify", "ok": ok, "checks": C, "post": state, "planErrors": errs}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--expect", type=int, help="--write 時必填，須為 3212")
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    rows = load_rows()

    if a.verify:
        v = verify(rows)
        json.dump(v, open(os.path.join(OUT, "verify.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(json.dumps(v["checks"], ensure_ascii=False, indent=1))
        print("對帳", "通過" if v["ok"] else "未通過")
        sys.exit(0 if v["ok"] else 1)

    res, writes, blanks = dry_run(rows)
    print(json.dumps({k: v for k, v in res.items()}, ensure_ascii=False, indent=1))
    if res["errors"]:
        sys.exit("dry-run 檢查未通過，不寫入")
    if not a.write:
        json.dump(res, open(os.path.join(OUT, "pre-state.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("dry-run 通過（未寫入）；寫入前狀態已存 write/pre-state.json")
        return

    if a.expect != EXPECT_WRITE or len(writes) != a.expect:
        sys.exit(f"--expect {a.expect} 與計畫 {len(writes)}／{EXPECT_WRITE} 不符，停止")
    saved = json.load(open(os.path.join(OUT, "pre-state.json"), encoding="utf-8"))
    if saved["pre"] != res["pre"] or saved["payloadMd5"] != res["payloadMd5"]:
        sys.exit("DB 狀態或資料與 dry-run 時不同，停止（請重跑 dry-run 確認）")
    r = psql(None, readonly=False, stdin=write_sql(writes, res["pre"]["quote_nonnull"]))
    print(r.stdout, r.stderr, sep="\n")
    if r.returncode != 0 or "QW80 OK" not in r.stderr:
        sys.exit(f"寫入失敗（rc={r.returncode}），交易已回復")
    log = {"mode": "write", "updated": len(writes), "notice": r.stderr.strip(), "payloadMd5": res["payloadMd5"]}
    json.dump(log, open(os.path.join(OUT, "write-log.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"寫入完成：{len(writes)} 筆")


if __name__ == "__main__":
    main()
