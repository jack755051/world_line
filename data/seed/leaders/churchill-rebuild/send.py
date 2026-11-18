#!/usr/bin/env python3
"""邱吉爾補建送出腳本（Tai 2026-11-11 10:13 核准；比照 gap-830/send_batch.py 與 b2_backfill.py）。

讀 pending-write.json（由 build.py 產生，不手改），照 WRITE_PLAN.md 步驟：
  步驟1 POST /sources ≤3（先唯讀查 sources.url，已存在就沿用其 id，不重建）
  步驟2 POST /leader-bios 1（含 11 筆 field citations）
  步驟3 POST /leader-records 1（[1940-05-10,1945-07-26)，personId＝步驟2 的 bio id）
  步驟4 單一交易 SQL（docker exec psql，BEGIN…COMMIT）：
        UPDATE 只限步驟2 那 11 列 leader_bio_field_citations（逐列以 citation id＋bio id 指定），
        補 quote、quote_lang、grade、date_precision、policy_version；
        INSERT leader_record_citations 2（record_id＝步驟3 的 record id）。
        交易內逐項核對筆數（每列 UPDATE 1、合計 11；INSERT 2），不符即 RAISE → 整筆回復，腳本停止。

安全：
  - --base、--db 必填，無預設。base 只接受 http(s)://127.0.0.1 或 localhost；拒絕 5051；
    port 與 db 必須配對：5052↔worldline_borders_dev、5062↔worldline_person_dryrun。
  - 容器固定 worldline-borders-dev-db（5442）；絕不連 5432／app_postgres。
  - 預設乾跑：只印計畫與唯讀核對（PGOPTIONS default_transaction_read_only=on），不呼叫任何寫入 API；--send 才寫。
  - 冪等：帳本 sent.<port>.json 記每步的 id；重跑時已完成的步驟不重送。
  - 任何步驟失敗（HTTP 非 2xx、筆數不符、核對不過）立即停止，印出已寫入的 id 供軟撤回（WRITE_PLAN §5），exit 非 0。
  - 不寫 death_place、leader_bio_gaps、照片、wikidata_qid；本檔不含任何刪除或 DDL 語句。
  - API key 讀 .dev/api.env 的 WORLDLINE_API_KEY，只放 header，不印出、不寫帳本。

用法：
  python3 send.py --base http://127.0.0.1:5052/api/v1 --db worldline_borders_dev            # 乾跑
  python3 send.py --base http://127.0.0.1:5062/api/v1 --db worldline_person_dryrun --send   # 試跑庫寫入
"""
import argparse, json, os, subprocess, sys, unicodedata, urllib.error, urllib.request, uuid
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CONTAINER = "worldline-borders-dev-db"   # 5442；絕不連 5432／app_postgres
PORT_DB = {5052: "worldline_borders_dev", 5062: "worldline_person_dryrun"}
ALLOWED_HOSTS = {"127.0.0.1", "localhost"}
BIO_NAME = "Winston Churchill"
PERIOD = ("1940-05-10", "1945-07-26")
N_SOURCES, N_BIO_CITS, N_REC_CITS = 3, 11, 2
BIO_KEYS = {"name", "nameZh", "isTest", "birthDate", "birthDatePrecision", "deathDate", "deathDatePrecision",
            "birthPlace", "party", "summary", "citations"}  # 不含 deathPlace／wikidataQid／portrait／fieldSources
REC_KEYS = {"regimeId", "name", "nameZh", "role", "title", "validFrom", "validTo", "source", "sourceUrl",
            "verified", "personId"}


class Stop(Exception):
    pass


# ── 參數檢查 ──
def check_target(base, db):
    u = urlparse(base)
    if u.scheme not in ("http", "https"):
        sys.exit(f"拒絕：--base 必須是 http(s)（{u.scheme!r}）")
    if (u.hostname or "") not in ALLOWED_HOSTS:
        sys.exit(f"拒絕：--base host 只允許 {sorted(ALLOWED_HOSTS)}（{u.hostname!r}）")
    try:
        port = u.port
    except ValueError:
        sys.exit("拒絕：--base port 格式錯誤")
    if port is None:
        sys.exit("拒絕：--base 必須明確寫 port")
    if port == 5051:
        sys.exit("拒絕 5051")
    if port not in PORT_DB:
        sys.exit(f"拒絕：port 只允許 {sorted(PORT_DB)}（{port}）")
    if db not in PORT_DB.values():
        sys.exit(f"拒絕：--db 只允許 {sorted(PORT_DB.values())}（{db!r}）")
    if PORT_DB[port] != db:
        sys.exit(f"拒絕：port {port} 只能配 {PORT_DB[port]}，不能配 {db}")
    return port


# ── DB（唯讀查詢／單一交易寫入）──
def ro(db, q):
    """唯讀查詢，回傳 json_agg 結果。連線設 default_transaction_read_only=on。"""
    if db not in PORT_DB.values():
        raise Stop(f"拒絕連線 {db}")
    cmd = ["docker", "exec", "-i", "-e", "PGOPTIONS=-c default_transaction_read_only=on", CONTAINER,
           "psql", "-U", "worldline", "-d", db, "-At", "-v", "ON_ERROR_STOP=1",
           "-c", f"select coalesce(json_agg(t), '[]'::json) from ({q}) t"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise Stop(f"唯讀查詢失敗：{r.stderr.strip()[:300]}")
    return json.loads(r.stdout)


def lit(s):
    """SQL 字串字面值（standard_conforming_strings=on）；None → NULL。"""
    if s is None:
        return "NULL"
    s = str(s)
    if "\x00" in s:
        raise Stop("字串含 NUL")
    return "'" + s.replace("'", "''") + "'"


def uid(s):
    return str(uuid.UUID(str(s)))  # 不是合法 uuid 就丟例外


# ── API ──
def api_key():
    for line in open(os.path.join(REPO, ".dev", "api.env"), encoding="utf-8"):
        if line.startswith("WORLDLINE_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise Stop("找不到 WORLDLINE_API_KEY")


def post(base, path, body, key):
    req = urllib.request.Request(base + path, method="POST", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "X-API-Key": key})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            st, res = r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        raise Stop(f"POST {path} 失敗 HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:400]}")
    except urllib.error.URLError as e:
        raise Stop(f"POST {path} 連線失敗：{e.reason}")
    if not (200 <= st < 300):
        raise Stop(f"POST {path} 失敗 HTTP {st}: {str(res)[:400]}")
    try:
        return uid(res["data"]["id"])
    except (KeyError, TypeError, ValueError):
        raise Stop(f"POST {path} 回應沒有 data.id：{str(res)[:300]}")


# ── 帳本 ──
class Ledger:
    def __init__(self, path):
        self.path = path
        self.d = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
        self.d.setdefault("sources", {})

    def save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.d, fh, ensure_ascii=False, indent=1); fh.write("\n")
        os.replace(tmp, self.path)


# ── 讀計畫 ──
def load_plan():
    rep = json.load(open(os.path.join(HERE, "verify-report.json"), encoding="utf-8"))
    if not rep.get("ok"):
        raise Stop("verify-report.json 不是 ok，先重跑 build.py")
    pw = json.load(open(os.path.join(HERE, "pending-write.json"), encoding="utf-8"))
    src = pw["step1_sources"]
    bio = pw["step2_leaderBio"]["request"]
    rec = pw["step3_leaderRecord"]["request"]
    upd = pw["step4_sql"]["leader_bio_field_citations_update"]
    ins = pw["step4_sql"]["leader_record_citations_insert"]
    errs = []
    if len(src) != N_SOURCES: errs.append(f"sources {len(src)} ≠ {N_SOURCES}")
    if len(bio["citations"]) != N_BIO_CITS: errs.append(f"bio citations {len(bio['citations'])} ≠ {N_BIO_CITS}")
    if len(upd) != N_BIO_CITS: errs.append(f"step4 update {len(upd)} ≠ {N_BIO_CITS}")
    if len(ins) != N_REC_CITS: errs.append(f"step4 insert {len(ins)} ≠ {N_REC_CITS}")
    if set(bio) - BIO_KEYS: errs.append(f"bio 請求含計畫外欄位 {sorted(set(bio) - BIO_KEYS)}")
    if set(rec) - REC_KEYS: errs.append(f"record 請求含計畫外欄位 {sorted(set(rec) - REC_KEYS)}")
    if bio["name"] != BIO_NAME or bio.get("isTest") is not False: errs.append("bio name／isTest 不符")
    if (rec["validFrom"], rec["validTo"]) != PERIOD or rec["role"] != "head_of_government":
        errs.append("record 期間／role 不符")
    for x in upd + ins:
        if len(unicodedata.normalize("NFC", x["set"]["quote"] if "set" in x else x["quote"])) > 80:
            errs.append("quote 超過 80 字")
    if errs:
        raise Stop("pending-write.json 不合計畫：" + "；".join(errs))
    return pw, src, bio, rec, upd, ins


def subst_source(ph, src_ids):
    if not (ph.startswith("<step1:") and ph.endswith(">")):
        raise Stop(f"非預期 sourceId 佔位 {ph}")
    k = ph[len("<step1:"):-1]
    if k not in src_ids:
        raise Stop(f"source {k} 沒有 id")
    return src_ids[k]


# ── 唯讀核對 ──
def checks(db, pw, src, rec, led):
    """回傳 (state, problems)。state 描述每一步目前是否已完成。"""
    probs, st = [], {}
    if ro(db, "select current_setting('default_transaction_read_only') as v")[0]["v"] != "on":
        raise Stop("唯讀連線設定未生效，停止")
    # regime
    g = ro(db, "select id::text from regimes where slug='united-kingdom' and retracted_at is null")
    if len(g) != 1 or g[0]["id"] != rec["regimeId"]:
        probs.append(f"regime united-kingdom 不存在或 id 不符（{g}）")
    print(f"  regime united-kingdom：{'✓ ' + g[0]['id'] if len(g) == 1 else '✗'}")
    # sources
    urls = [s["request"]["url"] for s in src]
    rows = ro(db, "select id::text, url from sources where url in (" + ",".join(lit(u) for u in urls) + ") order by id")
    by_url = {}
    for r in rows:
        by_url.setdefault(r["url"], r["id"])
    st["sources"] = {}
    for s in src:
        k, u = s["sourceKey"], s["request"]["url"]
        lid = led.d["sources"].get(k)
        if lid and lid != by_url.get(u):
            probs.append(f"帳本 source {k}={lid} 與庫中網址對應 {by_url.get(u)} 不符（試跑庫重建後請移除舊帳本）")
        st["sources"][k] = by_url.get(u)
        print(f"  source {k}：{'已存在 ' + by_url[u] + '（沿用）' if u in by_url else '不存在（將新建）'}")
    # bio
    bios = ro(db, f"select id::text, is_test from leader_bios where name={lit(BIO_NAME)} and retracted_at is null")
    lb = led.d.get("bioId")
    if len(bios) > 1:
        probs.append(f"有效 {BIO_NAME} bio 超過 1 筆：{[b['id'] for b in bios]}")
    elif bios:
        if bios[0]["is_test"]:
            probs.append(f"有效 bio {bios[0]['id']} 是測試資料")
        if lb and lb != bios[0]["id"]:
            probs.append(f"帳本 bioId {lb} 與庫中有效 bio {bios[0]['id']} 不符")
        st["bio"] = bios[0]["id"]
    elif lb:
        probs.append(f"帳本 bioId {lb} 在庫中不存在或已撤回（試跑庫重建後請移除舊帳本）")
    st.setdefault("bio", None)
    print(f"  邱吉爾有效 bio：{st['bio'] + '（已存在，不重建）' if st['bio'] else '無（將新建）'}")
    # 期間內 head_of_government
    ov = ro(db, f"""select r.id::text, r.name, r.person_id::text as person_id, lower(r.valid_period)::text as lo,
                           upper(r.valid_period)::text as hi
                    from leader_records r join regimes g on g.id=r.regime_id
                    where g.slug='united-kingdom' and r.role='head_of_government' and r.retracted_at is null
                      and r.valid_period && daterange({lit(PERIOD[0])},{lit(PERIOD[1])})""")
    lr = led.d.get("recordId")
    mine = [r for r in ov if r["name"] == BIO_NAME and (r["lo"], r["hi"]) == PERIOD
            and st["bio"] and r["person_id"] == st["bio"]]
    others = [r for r in ov if r not in mine]
    if others:
        probs.append(f"{PERIOD[0]}~{PERIOD[1]} 已有其他有效 head_of_government：{others}")
    if len(mine) > 1:
        probs.append(f"邱吉爾任期重複 {len(mine)} 筆")
    st["record"] = mine[0]["id"] if len(mine) == 1 else None
    if lr and lr != st["record"]:
        probs.append(f"帳本 recordId {lr} 與庫中狀態 {st['record']} 不符")
    print(f"  {PERIOD[0]}~{PERIOD[1]} 有效 head_of_government：{len(ov)} 筆"
          + (f"（邱吉爾 {st['record']}，已存在不重建）" if st["record"] else "") + ("" if not others else " ✗"))
    # 相鄰任期
    ch = ro(db, f"""select r.id::text from leader_records r join regimes g on g.id=r.regime_id
                    where g.slug='united-kingdom' and r.role='head_of_government' and r.retracted_at is null
                      and r.name ilike '%Chamberlain%' and upper(r.valid_period)={lit(PERIOD[0])}::date""")
    at = ro(db, f"""select r.id::text from leader_records r join regimes g on g.id=r.regime_id
                    where g.slug='united-kingdom' and r.role='head_of_government' and r.retracted_at is null
                      and r.name ilike '%Attlee%' and lower(r.valid_period)={lit(PERIOD[1])}::date""")
    print(f"  張伯倫止於 {PERIOD[0]}：{'✓ ' + ch[0]['id'] if len(ch) == 1 else '✗'}；"
          f"艾德禮始於 {PERIOD[1]}：{'✓ ' + at[0]['id'] if len(at) == 1 else '✗'}")
    if len(ch) != 1: probs.append(f"張伯倫止於 {PERIOD[0]} 的有效任期應為 1 筆（{len(ch)}）")
    if len(at) != 1: probs.append(f"艾德禮始於 {PERIOD[1]} 的有效任期應為 1 筆（{len(at)}）")
    # 不得動的撤回列
    dn = pw["doNotTouch"]
    nb = ro(db, "select count(*) as n from leader_bios where retracted_at is not null and id in ("
            + ",".join(lit(uid(x)) for x in dn["retractedTestBios"]) + ")")[0]["n"]
    nr = ro(db, f"select count(*) as n from leader_records where retracted_at is not null and id={lit(uid(dn['retractedRecord']))}")[0]["n"]
    print(f"  撤回測試 bio 仍撤回：{nb}/3；撤回任期仍撤回：{nr}/1")
    if (nb, nr) != (3, 1): probs.append(f"撤回列狀態改變（bio {nb}/3、record {nr}/1）")
    return st, probs


def match_bio_cits(db, bio_id, upd, src_ids):
    """把計畫 11 列對到庫中該 bio 的 citation id（以 field＋source_id＋locator＋evidence_note 唯一對應）。"""
    rows = ro(db, f"""select id::text, field, source_id::text, locator, evidence_note, quote, quote_lang, grade,
                             date_precision, policy_version
                      from leader_bio_field_citations where bio_id={lit(uid(bio_id))} and retracted_at is null""")
    if len(rows) != N_BIO_CITS:
        raise Stop(f"bio {bio_id} 的有效 citation {len(rows)} 筆 ≠ {N_BIO_CITS}")
    out, used = [], set()
    for x in upd:
        m = x["match"]
        sid = subst_source(m["source_id"], src_ids)
        hit = [r for r in rows if r["field"] == m["field"] and r["source_id"] == sid
               and r["locator"] == m["locator"] and r["evidence_note"] == m["evidence_note"] and r["id"] not in used]
        if len(hit) != 1:
            raise Stop(f"citation 對不到唯一列：{m['field']} / {m['locator']}（{len(hit)}）")
        used.add(hit[0]["id"])
        out.append((hit[0], x["set"]))
    return out


def step4_state(db, matched, rec_id, ins, src_ids):
    """回傳 'todo'、'done'；部分完成或與計畫不符 → Stop。"""
    filled = [r for r, s in matched if r["quote"] is not None]
    for r, s in matched:
        if r["quote"] is not None and (r["quote"], r["quote_lang"], r["grade"], r["date_precision"],
                                       r["policy_version"]) != (s["quote"], s["quote_lang"], s["grade"],
                                                                s["date_precision"], s["policy_version"]):
            raise Stop(f"citation {r['id']} 已有 quote 但與計畫不符")
    rc = ro(db, f"""select source_id::text, locator, quote from leader_record_citations
                    where record_id={lit(uid(rec_id))} and retracted_at is null""") if rec_id else []
    plan_rc = {(subst_source(x["source_id"], src_ids), x["locator"], x["quote"]) for x in ins}
    have_rc = {(r["source_id"], r["locator"], r["quote"]) for r in rc}
    if len(filled) == N_BIO_CITS and len(rc) == N_REC_CITS and have_rc == plan_rc:
        return "done"
    if not filled and not rc:
        return "todo"
    raise Stop(f"步驟4 部分完成或不符計畫（quote 已填 {len(filled)}/{N_BIO_CITS}、record citations {len(rc)}），"
               "停止，請人工檢查")


def step4_sql(bio_id, rec_id, matched, ins, src_ids):
    bio_id, rec_id = uid(bio_id), uid(rec_id)
    L = ["\\set ON_ERROR_STOP on", "BEGIN;", "DO $cw$", "DECLARE n bigint; total bigint := 0;", "BEGIN",
         f"  SELECT count(*) INTO n FROM leader_bios WHERE id={lit(bio_id)} AND retracted_at IS NULL;",
         "  IF n <> 1 THEN RAISE EXCEPTION 'churchill 前置失敗：bio 不存在或已撤回'; END IF;",
         f"  SELECT count(*) INTO n FROM leader_records WHERE id={lit(rec_id)} AND retracted_at IS NULL"
         f" AND person_id={lit(bio_id)};",
         "  IF n <> 1 THEN RAISE EXCEPTION 'churchill 前置失敗：record 不存在／已撤回／未連 bio'; END IF;",
         f"  SELECT count(*) INTO n FROM leader_record_citations WHERE record_id={lit(rec_id)};",
         "  IF n <> 0 THEN RAISE EXCEPTION 'churchill 前置失敗：record 已有 % 筆 citation', n; END IF;"]
    for r, s in matched:
        cid = uid(r["id"])
        L += [f"  UPDATE leader_bio_field_citations SET quote={lit(s['quote'])}, quote_lang={lit(s['quote_lang'])},"
              f" grade={lit(s['grade'])}, date_precision={lit(s['date_precision'])},"
              f" policy_version={lit(s['policy_version'])}",
              f"   WHERE id={lit(cid)} AND bio_id={lit(bio_id)} AND retracted_at IS NULL AND quote IS NULL;",
              "  GET DIAGNOSTICS n = ROW_COUNT;",
              f"  IF n <> 1 THEN RAISE EXCEPTION 'churchill UPDATE {cid} 筆數 % ≠ 1', n; END IF;",
              "  total := total + n;"]
    L.append(f"  IF total <> {N_BIO_CITS} THEN RAISE EXCEPTION 'churchill UPDATE 合計 % ≠ {N_BIO_CITS}', total; END IF;")
    vals = []
    for x in ins:
        vals.append("    (" + ", ".join([lit(rec_id), lit(uid(subst_source(x["source_id"], src_ids))), lit(x["locator"]),
                                         lit(x["quote"]), lit(x["quote_lang"]), lit(x["evidence_note"]),
                                         lit(x["accessed_on"]) + "::date", lit(x["grade"]), lit(x["date_precision"]),
                                         lit(x["policy_version"])]) + ")")
    L += ["  INSERT INTO leader_record_citations (record_id, source_id, locator, quote, quote_lang, evidence_note,"
          " accessed_on, grade, date_precision, policy_version) VALUES",
          ",\n".join(vals) + ";",
          "  GET DIAGNOSTICS n = ROW_COUNT;",
          f"  IF n <> {N_REC_CITS} THEN RAISE EXCEPTION 'churchill INSERT 筆數 % ≠ {N_REC_CITS}', n; END IF;",
          f"  RAISE NOTICE 'CHURCHILL STEP4 OK: update %, insert %', total, n;",
          "END", "$cw$;", "COMMIT;", ""]
    sql = "\n".join(L)
    if "$cw$" in "".join(str(v) for _, s in matched for v in s.values()) + json.dumps(ins, ensure_ascii=False):
        raise Stop("資料含界定符，停止")
    return sql


def run_step4(db, sql):
    if db not in PORT_DB.values():
        raise Stop(f"拒絕寫入 {db}")
    cmd = ["docker", "exec", "-i", CONTAINER, "psql", "-U", "worldline", "-d", db, "-v", "ON_ERROR_STOP=1", "-q"]
    r = subprocess.run(cmd, input=sql, capture_output=True, text=True)
    print(r.stdout.strip(), r.stderr.strip(), sep="\n")
    if r.returncode != 0 or "CHURCHILL STEP4 OK" not in r.stderr:
        raise Stop(f"步驟4 交易失敗（rc={r.returncode}），已回復（未 COMMIT）")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", required=True, help="API base，例 http://127.0.0.1:5052/api/v1（無預設）")
    ap.add_argument("--db", required=True, help="worldline_borders_dev 或 worldline_person_dryrun（無預設）")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true", help="乾跑（預設）")
    g.add_argument("--send", action="store_true", help="實際寫入")
    a = ap.parse_args()
    port = check_target(a.base, a.db)
    base = a.base.rstrip("/")
    led = Ledger(os.path.join(HERE, f"sent.{port}.json"))
    mode = "寫入" if a.send else "乾跑（不寫入）"
    print(f"邱吉爾補建 send.py：{mode}；API {base}；DB {a.db}（容器 {CONTAINER}）；帳本 {os.path.basename(led.path)}")
    try:
        pw, src, bio, rec, upd, ins = load_plan()
        print(f"計畫：sources ≤{N_SOURCES}、bio 1（citations {N_BIO_CITS}）、record 1 {PERIOD}、"
              f"UPDATE {N_BIO_CITS}、INSERT leader_record_citations {N_REC_CITS}")
        print("唯讀核對：")
        st, probs = checks(a.db, pw, src, rec, led)
        if probs:
            raise Stop("核對不過：\n    " + "\n    ".join(probs))
        src_ids = {k: v for k, v in st["sources"].items() if v}
        todo = [s for s in src if not st["sources"][s["sourceKey"]]]
        step4 = "todo"
        if st["bio"]:
            matched = match_bio_cits(a.db, st["bio"], upd, src_ids)
            step4 = step4_state(a.db, matched, st["record"], ins, src_ids)
        print("步驟狀態：")
        print(f"  1 sources：新建 {len(todo)}、沿用 {len(src) - len(todo)}")
        print(f"  2 bio：{'已完成 ' + st['bio'] if st['bio'] else '待建'}")
        print(f"  3 record：{'已完成 ' + st['record'] if st['record'] else '待建'}")
        print(f"  4 SQL：{'已完成' if step4 == 'done' else '待執行'}")
        if not a.send:
            print("\n（乾跑：未呼叫任何寫入 API、未執行寫入 SQL。加 --send 才寫入）")
            return 0

        key = api_key()
        # 步驟1
        for s in todo:
            k = s["sourceKey"]
            body = dict(s["request"], note="邱吉爾補建 churchill-rebuild（2026-11-11 查證；Tai 2026-11-11 10:13 核准）")
            src_ids[k] = led.d["sources"][k] = post(base, "/sources", body, key)
            led.save()
            print(f"✓ 步驟1 source {k} → {src_ids[k]}")
        for k, v in src_ids.items():
            led.d["sources"].setdefault(k, v)
        # 步驟2
        bio_id = st["bio"]
        if not bio_id:
            body = dict(bio, citations=[dict(c, sourceId=subst_source(c["sourceId"], src_ids)) for c in bio["citations"]])
            bio_id = led.d["bioId"] = post(base, "/leader-bios", body, key)
            led.save()
            print(f"✓ 步驟2 bio → {bio_id}")
        led.d["bioId"] = bio_id
        matched = match_bio_cits(a.db, bio_id, upd, src_ids)
        led.d["bioCitationIds"] = [r["id"] for r, _ in matched]
        led.save()
        # 步驟3
        rec_id = st["record"]
        if not rec_id:
            rec_id = led.d["recordId"] = post(base, "/leader-records", dict(rec, personId=bio_id), key)
            led.save()
            print(f"✓ 步驟3 record → {rec_id}")
        led.d["recordId"] = rec_id
        led.save()
        # 步驟4
        if step4_state(a.db, matched, rec_id, ins, src_ids) == "todo":
            run_step4(a.db, step4_sql(bio_id, rec_id, matched, ins, src_ids))
            if step4_state(a.db, match_bio_cits(a.db, bio_id, upd, src_ids), rec_id, ins, src_ids) != "done":
                raise Stop("步驟4 寫入後核對不過")
            print("✓ 步驟4 UPDATE 11、INSERT 2")
        else:
            print("步驟4 已完成，略過")
        rc = ro(a.db, f"select id::text from leader_record_citations where record_id={lit(uid(rec_id))} and retracted_at is null")
        led.d["recordCitationIds"] = [r["id"] for r in rc]
        led.d["step4"] = "done"
        led.save()
        print(f"完成：bio {bio_id}、record {rec_id}；帳本 {os.path.basename(led.path)}")
        return 0
    except Stop as e:
        print(f"\n✗ 停止：{e}", file=sys.stderr)
        if a.send:
            print("已寫入的 id（軟撤回見 WRITE_PLAN §5）：", json.dumps(led.d, ensure_ascii=False, indent=1), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
