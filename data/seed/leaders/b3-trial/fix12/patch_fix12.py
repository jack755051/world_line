#!/usr/bin/env python3
"""B3 生卒 12 筆矛盾修正（Tai 2026-11-11 21:24；依 consistency-check.md／findings.json 建議與五項預設做法）。

只產生 patch 與 SQL 計畫，不寫庫：
  python3 -I patch_fix12.py            → fix12.json、paragraphs.patched.json、plan.sql、fix12-diff.md（唯讀 SELECT 核對 5442 現況）
  python3 -I patch_fix12.py --dry-run  → 另把 plan.sql 送進 5442 執行（plan.sql 以 ROLLBACK 結尾，不留任何變更），輸出存 dryrun.txt
plan.sql 沒有 COMMIT；本腳本沒有寫庫選項。連線同 run100/write_b3_paragraphs.py（docker exec worldline-borders-dev-db，5442）。
新列 id 以 uuid5 固定（可重跑、輸出相同）。修正依 I5：段落撤回重寫＋superseded_by；缺漏、引文只撤回不刪。
"""
import json, subprocess, sys, uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN100 = HERE.parent / "run100"
CONTAINER, DBUSER, DBNAME = "worldline-borders-dev-db", "worldline", "worldline_borders_dev"
NS = uuid.UUID("6b3f9a52-1d2e-4c1a-9f0e-0b3f1a2c2026")
DECISION = "Tai 2026-11-11 21:24"
CHECKED_ON = "2026-11-11"

def uid(k): return str(uuid.uuid5(NS, k))

def psql(sql):
    r = subprocess.run(["docker", "exec", "-i", CONTAINER, "psql", "-U", DBUSER, "-d", DBNAME, "-X", "-At", "-F", "\t", "-v", "ON_ERROR_STOP=1"],
                       input="begin transaction read only;\n" + sql.rstrip().rstrip(";") + ";\nrollback;\n", capture_output=True, text=True)
    if r.returncode: sys.exit(r.stderr[:500])
    return [l.split("\t") for l in r.stdout.splitlines() if l and l not in ("BEGIN", "ROLLBACK")]

def lit(v):
    if v is None: return "NULL"
    if isinstance(v, (dict, list)): v = json.dumps(v, ensure_ascii=False)
    return "'" + str(v).replace("'", "''") + "'"

P = {  # bioId
 "wu": ("01a1c437-b43f-7116-bd87-22313035593e", "Wu Tingfang", "伍廷芳"),
 "hansson": ("01a1b4b0-6fe9-72db-be2c-915cf61baa62", "Per Albin Hansson", "佩爾·阿爾賓·漢森"),
 "mironas": ("01a1b545-5f9a-74f7-b257-4aca0ce09d17", "Vladas Mironas", "弗拉達斯·米羅納斯"),
 "noronha": ("c414bfc4-ad7e-4565-b494-541ad432dfa5", "José Isaías de Noronha", "伊薩亞斯·德諾羅尼亞"),
 "lyzohub": ("01a1c35f-186c-7459-94d9-f5c3a548ec1c", "Fedir Lyzohub", "費奧多爾·利佐胡布"),
 "avila": ("01a1aa4a-da74-77db-baee-0f57adbb1f2c", "Manuel Ávila Camacho", "曼努埃爾·阿維拉·卡馬喬"),
 "meierovics": ("01a1b51c-8311-70df-b77c-97d89e470686", "Zigfrīds Anna Meierovics", "齊格弗里茲·安納·梅耶羅維奇"),
 "negrin": ("01a1b52a-620e-7c9f-9408-9cb081f47412", "Juan Negrín López", "胡安·內格林"),
 "leygues": ("cbb09808-0930-40ae-b03a-51d7d1d3c8a6", "Georges Leygues", "喬治·萊格"),
 "saidhalim": ("01a1b512-3353-74ad-a495-5ee6c8e7d198", "Said Halim Pasha", "賽義德·哈利姆帕夏"),
 "hilmi": ("01a1c37d-aa7e-7cda-b68d-029070be86f1", "Hüseyin Hilmi Paşa", "侯賽因·希勒米帕夏"),
}
# 現況（plan 前置檢查；不符即中止）
EXPECT_BIOS = {  # key: (birth_date, birth_prec, death_date, death_prec)
 "wu": ("1842-07-30", "day", "1922-06-23", "day"), "hansson": ("1885-10-28", "day", "1946-10-06", "day"),
 "mironas": ("1880-06-22", "day", "1953-02-17", "day"), "noronha": ("1873-07-06", "day", "1963-01-29", ""),
 "lyzohub": ("1851-11-06", "day", "1928-01-01", "year"), "avila": ("1897-04-24", "day", "1955-10-13", ""),
 "meierovics": ("", "", "1925-08-22", "day"), "negrin": ("", "", "1956-11-12", "day"), "leygues": ("", "", "1933-09-02", ""),
 "saidhalim": ("", "", "", ""), "hilmi": ("1855-01-01", "year", "", ""),
}
OLD_PAR = {"wu": "37d0857a-9d93-462a-931b-05bb2c756887", "hansson": "6456dabd-c1ae-4bf2-a3b7-f79d036c9c9b"}
SEED = {"wu": ("batch12", "cn-wu-tingfang", 1), "hansson": ("batch02", "se-per-albin-hansson", 3)}

def main():
    dry = "--dry-run" in sys.argv[1:]
    ids = ",".join(lit(v[0]) for v in P.values())
    bios = {r[0]: r[1:] for r in psql(f"select id, coalesce(birth_date::text,''), coalesce(birth_date_precision,''), coalesce(death_date::text,''), coalesce(death_date_precision,''), version from leader_bios where id in ({ids}) and retracted_at is null")}
    for k, exp in EXPECT_BIOS.items():
        got = tuple(bios[P[k][0]][:4])
        if got != exp: sys.exit(f"{k} 現況不符：{got} ≠ {exp}")
    gaps = {(r[0], r[1], r[2]): r[3] for r in psql(f"select bio_id, target, gap_kind, id from leader_bio_gaps where bio_id in ({ids}) and retracted_at is null and resolved_at is null and target in ('field:birthDate','field:deathDate','field:birthPlace')")}
    fc = {r[0]: r[1:] for r in psql(f"select id, bio_id, field, source_id, locator, quote, coalesce(grade,''), accessed_on::text from leader_bio_field_citations where bio_id in ({ids}) and retracted_at is null")}
    pars = {r[0]: r for r in psql("select id, bio_id, ord, period::text, coalesce(period_start_precision,''), coalesce(period_end_precision,''), heading::text, body::text from leader_bio_paragraphs where id in (%s) and retracted_at is null and superseded_by is null" % ",".join(lit(v) for v in OLD_PAR.values()))}
    pcs = {}
    for r in psql("select paragraph_id, id, source_id, locator, quote, coalesce(quote_lang,''), coalesce(evidence_note,''), accessed_on::text, coalesce(grade,''), coalesce(date_precision,''), coalesce(policy_version,'') from leader_bio_paragraph_citations where paragraph_id in (%s) and retracted_at is null order by created_at, id" % ",".join(lit(v) for v in OLD_PAR.values())):
        pcs.setdefault(r[0], []).append(r)
    src = {r[0]: r[1:] for r in psql("select id, url, title from sources where id in ('01a1c437-b3d1-7748-8ae2-1225ad16c615','01a1b4b0-6f5f-7efd-ab4b-363b2ece9b1e','3ece627e-0999-4403-91f3-f88fd2ced41e','01a1b545-5f34-7661-bd54-67a0a3334846','33cf8e33-0211-4472-9deb-459c6065023c','3936c259-c113-449f-a300-6f99d419db91')")}
    # 段落：DB 與 seed 必須一致
    seedp = {}
    for k, (b, key, ord_) in SEED.items():
        d = json.loads((RUN100 / b / "research.json").read_text(encoding="utf-8"))
        p = next(p for p in d["people"] if p["key"] == key)
        g = next(g for g in p["paragraphs"] if g["ord"] == ord_)
        db = pars[OLD_PAR[k]]
        if json.loads(db[7]) != g["body"]: sys.exit(f"{k} 段落 body：DB 與 seed 不一致")
        seedp[k] = (b, key, g, d["sources"])
    def need(cond, msg):
        if not cond: sys.exit("前置檢查失敗：" + msg)
    W, H, M = P["wu"][0], P["hansson"][0], P["mironas"][0]
    need(fc["01a1c437-b43f-78cb-b8df-0150971deb93"][4] == "1842-07-30, Malacca (Malaisie)", "Wu BnF birthDate 引文")
    need(fc["01a1c437-b440-77da-ba1d-3f3f9a4ebbc6"][4] == "Malacca (Malaisie)", "Wu BnF birthPlace 引文")
    need(fc["01a1b4b0-6fea-7f53-ae6b-4357e7174ee7"][4] == "Mort : 1946-10-06", "Hansson BnF deathDate 引文")
    need(fc["01a1b545-5f9b-7b3a-9c61-4d35e19af689"][1] == "deathDate", "Mironas VLE deathDate 引文")
    need((H, "field:deathDate", "not_found") in gaps and (M, "field:deathDate", "not_found") in gaps and (P["avila"][0], "field:birthDate", "not_found") in gaps, "三筆 not_found 缺漏")
    for k, t in (("meierovics", "field:birthDate"), ("negrin", "field:birthDate"), ("saidhalim", "field:birthDate"), ("hilmi", "field:deathDate")):
        need((P[k][0], t, "conflict") in gaps, f"{k} 既有 conflict")
    for k, t in (("wu", "field:birthDate"), ("wu", "field:birthPlace"), ("hansson", "field:deathDate"), ("mironas", "field:deathDate"),
                 ("noronha", "field:birthDate"), ("lyzohub", "field:birthDate"), ("avila", "field:birthDate"), ("leygues", "field:birthDate")):
        need((P[k][0], t, "conflict") not in gaps, f"{k} {t} 已有未解 conflict（重跑？）")

    ops = {"bios_update": [], "field_cit_insert": [], "field_cit_retract": [], "gap_retract": [], "gap_insert": [],
           "par_supersede": [], "par_cit_copy": 0, "par_cit_new": [], "noop": []}
    sql = ["-- B3 fix12 計畫（%s）；由 patch_fix12.py 產生，勿手改。以 ROLLBACK 結尾，不寫庫。" % DECISION, "\\set ON_ERROR_STOP on", "BEGIN;"]
    A = sql.append
    # ---- 段落撤回重寫 ----
    NEWTXT = {
     "wu": ({"en": "According to the BnF authority record, Wu Tingfang was born on 30 July 1842 in Malacca. He was called to the English bar in 1876, becoming the first Chinese barrister, and in 1897 he was appointed minister to the United States, Spain and Peru.",
             "zh-Hant": "據法國國家圖書館（BnF）權威記錄，伍廷芳於1842年7月30日生於馬六甲；1876年取得英國律師資格，成為首位華人大律師，1897年被任命為駐美國、西班牙與秘魯公使。"},
            "[1842-07-30,1898-01-01)", "day", "year",
            {"bc302e78-ed21-40cd-916d-665d0a99b108": "生日 9 July 1842 與 BnF 1842-07-30 矛盾（Tai 21:24 以基本資料為準）",
             "124157ae-aa27-4c36-95b8-4b4d4e8916ff": "出生地 Singapore 與 BnF Malacca 矛盾（Tai 21:24 以基本資料為準）"},
            [("01a1c437-b3d1-7748-8ae2-1225ad16c615", "Naissance", "1842-07-30, Malacca (Malaisie)", "fr", "A", "day", "2026-11-10",
              "同 leader_bio_field_citations 01a1c437-b43f-78cb（BnF 權威記錄 Naissance 欄）；%s 以基本資料為準改版" % DECISION)]),
     "hansson": ({"en": "In 1932, in the midst of the economic crisis, Hansson became leader of a Social Democratic minority government, and in 1933 reached the so-called crisis settlement with the Agrarian League. His government was replaced by an Agrarian League government in summer 1936, but in September that year he formed a government again. After the outbreak of the Winter War in December 1939 he formed a national coalition government, and externally Sweden’s formal, later somewhat contested neutrality was secured. He died on 6 October 1946.",
                  "zh-Hant": "1932年經濟危機中，漢森出任社會民主黨少數政府的領導人，1933年與農民聯盟達成「危機協議」。1936年夏天其政府被農民聯盟政府取代，同年9月他再度組閣。1939年12月冬季戰爭爆發後他組成國家聯合政府，對外確保瑞典形式上、後來頗受爭議的中立。他於1946年10月6日逝世。"},
                 "[1932-01-01,1946-10-07)", "year", "day",
                 {"485a2e57-c2b3-4f82-991d-7ac36b1e0133": "卒日 5. oktober 1946 與基本資料 1946-10-06 矛盾（Tai 21:24 以基本資料為準）；逝世地 Stockholm 僅此引文支持，新版刪去地點"},
                 [("01a1b4b0-6f5f-7efd-ab4b-363b2ece9b1e", "Mort", "Mort : 1946-10-06", "fr", "A", "day", "2026-11-07",
                   "同 leader_bio_field_citations 01a1b4b0-6fea-7f53（BnF 權威記錄 Mort 欄）；%s 以基本資料為準改版" % DECISION)]),
    }
    patched = []
    for k, (body, per, sp, ep, drop, add) in NEWTXT.items():
        old = pars[OLD_PAR[k]]; bio = old[1]; ordv = int(old[2]); new = uid("par:" + OLD_PAR[k])
        reason = "%s：生卒矛盾修正（fix12），撤回重寫為 %s" % (DECISION, new)
        A(f"UPDATE leader_bio_paragraphs SET retracted_at=now(), retraction_reason={lit(reason)} WHERE id={lit(OLD_PAR[k])} AND retracted_at IS NULL;")
        A(f"INSERT INTO leader_bio_paragraphs (id,bio_id,ord,period,period_start_precision,period_end_precision,heading,body,version) VALUES ({lit(new)},{lit(bio)},{ordv},{lit(per)}::daterange,{lit(sp)},{lit(ep)},{lit(old[6])}::jsonb,{lit(body)}::jsonb,0);")
        A(f"UPDATE leader_bio_paragraphs SET superseded_by={lit(new)} WHERE id={lit(OLD_PAR[k])};")
        kept = []
        for c in pcs[OLD_PAR[k]]:
            if c[1] in drop: continue
            nid = uid("pc:" + c[1]); kept.append(c)
            A("INSERT INTO leader_bio_paragraph_citations (id,paragraph_id,source_id,locator,quote,quote_lang,evidence_note,accessed_on,grade,date_precision,policy_version) VALUES (%s);" %
              ",".join(lit(x or None) if i not in (0, 1) else lit(x) for i, x in enumerate([nid, new] + c[2:])))
        ops["par_cit_copy"] += len(kept)
        for j, (sid, loc, q, ql, gr, dp, acc, note) in enumerate(add):
            nid = uid(f"pcnew:{k}:{j}")
            A("INSERT INTO leader_bio_paragraph_citations (id,paragraph_id,source_id,locator,quote,quote_lang,evidence_note,accessed_on,grade,date_precision,policy_version) VALUES (%s);" %
              ",".join(lit(x) for x in (nid, new, sid, loc, q, ql, note, acc, gr, dp, "bio-2026-11-v0")))
            ops["par_cit_new"].append({"person": k, "id": nid, "source": src[sid][0], "locator": loc, "quote": q, "grade": gr})
        ops["par_supersede"].append({"person": k, "old": OLD_PAR[k], "new": new, "ord": ordv, "oldPeriod": old[3], "newPeriod": per,
                                     "oldPrecision": [old[4], old[5]], "newPrecision": [sp, ep], "oldBody": json.loads(old[7]), "newBody": body,
                                     "droppedCitations": [{"id": c[1], "quote": c[4], "locator": c[3], "url": src.get(c[2], ["?"])[0], "why": drop[c[1]]} for c in pcs[OLD_PAR[k]] if c[1] in drop],
                                     "keptCitations": len(kept)})
        b, key, g, _ = seedp[k]
        pg = json.loads(json.dumps(g)); pg["body"] = body
        s, e = per[1:-1].split(","); pg["period"] = {"start": s, "end": e}; pg["periodStartPrecision"], pg["periodEndPrecision"] = sp, ep
        pg["citations"] = [c for c in g["citations"] if c["quote"] not in {cc[4] for cc in pcs[OLD_PAR[k]] if cc[1] in drop}]
        for (sid, loc, q, ql, gr, dp, acc, note) in add:
            pg["citations"].append({"sourceKey": "db:" + sid, "locator": loc, "quote": q, "quoteLang": ql, "evidenceNote": note, "accessedOn": acc,
                                    "grade": gr, "datePrecision": dp, "claimSpan": None, "policyVersion": "bio-2026-11-v0"})
        pg["supersedes"] = {"paragraphId": OLD_PAR[k], "decision": DECISION, "newParagraphId": new}
        patched.append({"seedFile": f"run100/{b}/research.json", "personKey": key, "bioId": bio, "paragraph": pg})
    # ---- leader_bios ----
    def bio_upd(k, col, newv, prec_col, newp, why):
        bid = P[k][0]
        A(f"UPDATE leader_bios SET {col}={lit(newv)}::date, {prec_col}={lit(newp)}, version=version+1 WHERE id={lit(bid)} AND retracted_at IS NULL;")
        e = EXPECT_BIOS[k]; oldv, oldp = (e[0], e[1]) if col == "birth_date" else (e[2], e[3])
        ops["bios_update"].append({"person": k, "field": col, "old": f"{oldv or 'NULL'}（{oldp or '—'}）", "new": f"{newv or 'NULL'}（{newp or '—'}）", "why": why})
    bio_upd("mironas", "death_date", "1953-02-18", "death_date_precision", "day", "以段落為準：Seimas（A）「Mirė 1953 m. vasario 18 d.」")
    bio_upd("noronha", "birth_date", "1873-01-01", "birth_date_precision", "year", "保留年份＋conflict（§16.7.3 放寬規則）")
    bio_upd("lyzohub", "birth_date", "1851-01-01", "birth_date_precision", "year", "保留年份＋conflict（§16.7.3 放寬規則）")
    bio_upd("avila", "birth_date", None, "birth_date_precision", None, "留空＋conflict（年份互斥 1896／1897）")
    # ---- field citations（Mironas）----
    nfc = uid("fc:mironas:deathDate:seimas")
    A("INSERT INTO leader_bio_field_citations (id,bio_id,field,source_id,locator,quote,quote_lang,evidence_note,accessed_on,grade,date_precision,policy_version) VALUES (%s);" %
      ",".join(lit(x) for x in (nfc, M, "deathDate", "3ece627e-0999-4403-91f3-f88fd2ced41e", "Seimas 傳記頁", "Mirė 1953 m. vasario 18 d. Vladimiro kalėjime (Rusija)", "lt",
                                 "同段落引文（run100 batch 段落 052aaa93 ord 5）；%s 以段落（Seimas）為準" % DECISION, "2026-11-11", "A", "day", "bio-2026-11-v0")))
    ops["field_cit_insert"].append({"person": "mironas", "id": nfc, "field": "deathDate", "url": src["3ece627e-0999-4403-91f3-f88fd2ced41e"][0], "quote": "Mirė 1953 m. vasario 18 d. Vladimiro kalėjime (Rusija)", "grade": "A"})
    A("UPDATE leader_bio_field_citations SET retracted_at=now(), retraction_reason=%s WHERE id='01a1b545-5f9b-7b3a-9c61-4d35e19af689' AND retracted_at IS NULL;" % lit("%s：卒日以 Seimas 1953-02-18 為準（fix12），VLE 1953 02 17 撤回" % DECISION))
    ops["field_cit_retract"].append({"person": "mironas", "id": "01a1b545-5f9b-7b3a-9c61-4d35e19af689", "quote": fc["01a1b545-5f9b-7b3a-9c61-4d35e19af689"][4], "url": src["01a1b545-5f34-7661-bd54-67a0a3334846"][0]})
    # ---- gaps ----
    for k, t in (("hansson", "field:deathDate"), ("mironas", "field:deathDate"), ("avila", "field:birthDate")):
        gid = gaps[(P[k][0], t, "not_found")]
        A(f"UPDATE leader_bio_gaps SET retracted_at=now(), retraction_reason={lit(DECISION + '：既有缺漏改記為 conflict（fix12）')} WHERE id={lit(gid)} AND retracted_at IS NULL;")
        ops["gap_retract"].append({"person": k, "id": gid, "target": t, "kind": "not_found"})
    G = [  # key, target, note, resolved_by
     ("wu", "field:birthDate", "BnF 權威記錄 1842-07-30 vs X-Boorman 轉載《民國人物傳記辭典》9 July 1842；%s 以基本資料（BnF，A）為準，段落改版" % DECISION, "01a1c437-b43f-78cb-b8df-0150971deb93"),
     ("wu", "field:birthPlace", "BnF 權威記錄 Malacca vs X-Boorman 轉載《民國人物傳記辭典》Singapore；%s 以基本資料（BnF，A）為準，段落改版" % DECISION, "01a1c437-b440-77da-ba1d-3f3f9a4ebbc6"),
     ("hansson", "field:deathDate", "Malmö stad、BnF 1946-10-06 vs Lex、SNL 1946-10-05；%s 以基本資料為準，段落改版" % DECISION, "01a1b4b0-6fea-7f53-ae6b-4357e7174ee7"),
     ("mironas", "field:deathDate", "Seimas（A）1953-02-18 vs Visuotinė lietuvių enciklopedija 1953 02 17；%s 以段落（Seimas）為準，基本資料改為 1953-02-18" % DECISION, nfc),
     ("noronha", "field:birthDate", "保留現有值：\"1873-01-01\"；[birthDate (day)] Arquivo Nacional（field_sources）1873-07-06 vs FGV CPDOC DHBB「no dia 6 de junho de 1873」；年份一致，依 §16.7.3 保留年份（%s）" % DECISION, None),
     ("lyzohub", "field:birthDate", "保留現有值：\"1851-01-01\"；[birthDate (day)] Encyclopedia of Ukraine「b 6 November 1851」vs Український історичний журнал「народився в жовтні 1851 р.」；年份一致，依 §16.7.3 保留年份（%s）" % DECISION, None),
     ("avila", "field:birthDate", "Museo de los Presidentes Coahuilenses（field_sources）1897-04-24 vs gob.mx「Nació el 24 de abril de 1896」；年份互斥，依 §16 該欄留空（%s）" % DECISION, None),
     ("leygues", "field:birthDate", "Assemblée nationale fiche 1857-10-26 vs Sycomore 1856-10-29（field_sources 註記；段落採 Sycomore「Né le 29 octobre 1856」）；年份互斥，依 §16 該欄維持空（%s）" % DECISION, None),
    ]
    for k, t, note, rb in G:
        gid = uid(f"gap:{k}:{t}:conflict")
        A("INSERT INTO leader_bio_gaps (id,bio_id,target,gap_kind,note,candidate_citations,checked_on,resolved_at,resolved_by_citation_id) VALUES (%s,%s,%s,'conflict',%s,'[]'::jsonb,%s,%s,%s);" %
          (lit(gid), lit(P[k][0]), lit(t), lit(note), lit(CHECKED_ON), "now()" if rb else "NULL", lit(rb)))
        ops["gap_insert"].append({"person": k, "id": gid, "target": t, "resolved": bool(rb), "resolvedBy": rb, "note": note})
    for k, t in (("meierovics", "field:birthDate"), ("negrin", "field:birthDate"), ("saidhalim", "field:birthDate"), ("hilmi", "field:deathDate")):
        ops["noop"].append({"person": k, "target": t, "why": "該欄已為 NULL，且已有未解 conflict 缺漏（%s）；不需變更" % gaps[(P[k][0], t, "conflict")]})
    # ---- 交易內檢查 ----
    A("DO $$ BEGIN")
    A(f"  IF (SELECT count(*) FROM leader_bio_paragraphs WHERE id IN ({lit(OLD_PAR['wu'])},{lit(OLD_PAR['hansson'])}) AND retracted_at IS NOT NULL AND superseded_by IS NOT NULL) <> 2 THEN RAISE EXCEPTION 'fix12: 舊段落撤回數不符'; END IF;")
    A(f"  IF (SELECT count(*) FROM leader_bio_paragraphs WHERE bio_id IN ({lit(W)},{lit(H)}) AND retracted_at IS NULL) <> (SELECT count(*) FROM leader_bio_paragraphs WHERE bio_id IN ({lit(W)},{lit(H)}) AND retracted_at IS NULL AND superseded_by IS NULL) THEN RAISE EXCEPTION 'fix12: 現行段落含 superseded'; END IF;")
    A(f"  IF (SELECT count(*) FROM leader_bio_gaps WHERE bio_id IN ({ids}) AND gap_kind='conflict' AND retracted_at IS NULL AND checked_on='{CHECKED_ON}' AND id IN ({','.join(lit(g['id']) for g in ops['gap_insert'])})) <> {len(G)} THEN RAISE EXCEPTION 'fix12: 新 conflict 數不符'; END IF;")
    A(f"  IF EXISTS (SELECT 1 FROM leader_bio_gaps g JOIN leader_bios b ON b.id=g.bio_id WHERE g.bio_id IN ({ids}) AND g.gap_kind='conflict' AND g.retracted_at IS NULL AND g.resolved_at IS NULL AND g.note NOT LIKE '保留現有值%' AND ((g.target='field:birthDate' AND b.birth_date IS NOT NULL) OR (g.target='field:deathDate' AND b.death_date IS NOT NULL))) THEN RAISE EXCEPTION 'fix12: 未解且無限定詞的 conflict 欄位不是 NULL（§16）'; END IF;")
    A("END $$;")
    A("SELECT 'bios', name, birth_date, birth_date_precision, death_date, death_date_precision FROM leader_bios WHERE id IN (%s) ORDER BY name;" % ids)
    A("SELECT 'paragraph', bio_id, ord, period, left(body->>'en', 90), left(body->>'zh-Hant', 40), (SELECT count(*) FROM leader_bio_paragraph_citations c WHERE c.paragraph_id=p.id) FROM leader_bio_paragraphs p WHERE id IN (%s);" % ",".join(lit(x["new"]) for x in ops["par_supersede"]))
    A("SELECT 'gaps', b.name, g.target, g.gap_kind, g.resolved_at IS NOT NULL AS resolved FROM leader_bio_gaps g JOIN leader_bios b ON b.id=g.bio_id WHERE g.bio_id IN (%s) AND g.retracted_at IS NULL AND g.target IN ('field:birthDate','field:deathDate','field:birthPlace') ORDER BY 2,3,4;" % ids)
    A("ROLLBACK;")
    (HERE / "plan.sql").write_text("\n".join(sql) + "\n", encoding="utf-8")
    (HERE / "fix12.json").write_text(json.dumps({"decision": DECISION, "ops": ops}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (HERE / "paragraphs.patched.json").write_text(json.dumps(patched, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    write_diff(ops, src)
    print("bios_update=%d field_cit_insert=%d field_cit_retract=%d gap_retract=%d gap_insert=%d par_supersede=%d par_cit_copy=%d par_cit_new=%d noop=%d" % (
        len(ops["bios_update"]), len(ops["field_cit_insert"]), len(ops["field_cit_retract"]), len(ops["gap_retract"]), len(ops["gap_insert"]),
        len(ops["par_supersede"]), ops["par_cit_copy"], len(ops["par_cit_new"]), len(ops["noop"])))
    if dry:
        r = subprocess.run(["docker", "exec", "-i", CONTAINER, "psql", "-U", DBUSER, "-d", DBNAME, "-X", "-A", "-F", " | ", "-v", "ON_ERROR_STOP=1"],
                           input=(HERE / "plan.sql").read_text(encoding="utf-8"), capture_output=True, text=True)
        out = "exit=%d\n--- stdout ---\n%s\n--- stderr ---\n%s" % (r.returncode, r.stdout, r.stderr)
        (HERE / "dryrun.txt").write_text(out, encoding="utf-8")
        print(out[-3000:])
        if r.returncode: sys.exit(1)
        if not r.stdout.rstrip().endswith("ROLLBACK"): sys.exit("dry-run 未以 ROLLBACK 結束")

def write_diff(ops, src):
    nm = {k: f"{v[2]}（{v[1]}，`{v[0]}`）" for k, v in P.items()}
    L = ["# B3 生卒 12 筆矛盾修正：差異清單（dry-run，未寫庫）", "",
         f"依據：{DECISION}（World Line 主管轉達）；consistency-check.md／consistency-findings.json 建議＋五項預設做法。由 `data/seed/leaders/b3-trial/fix12/patch_fix12.py` 產生。", "",
         "| 處理 | 筆數 | 人物（欄位） |", "|---|---|---|",
         "| 以基本資料為準 | 3 | 伍廷芳（生日、出生地）、Hansson（卒日）→ 段落撤回重寫，基本資料不變，記已解決 conflict |",
         "| 以段落為準 | 1 | Mironas（卒日）→ 基本資料改 1953-02-18，補 Seimas 引文、撤回 VLE 引文，記已解決 conflict |",
         "| 保留年份＋記 conflict | 2 | Noronha、Lyzohub（生日）→ 降為年精度，記帶限定詞 conflict |",
         "| 留空＋記 conflict | 6 | Ávila Camacho（生日改 NULL、not_found 改 conflict）、Leygues（補 conflict）；Meierovics、Negrín、Said Halim、Hilmi 已符合（NULL＋既有 conflict），不變 |", "",
         "## 1. 基本資料（leader_bios）", "", "| 人物 | 欄位 | 舊值 | 新值 | 理由／來源 |", "|---|---|---|---|---|"]
    for b in ops["bios_update"]:
        L.append(f"| {nm[b['person']]} | {b['field']} | {b['old']} | {b['new']} | {b['why']} |")
    L += ["", "## 2. 欄位引文（leader_bio_field_citations）", ""]
    for c in ops["field_cit_insert"]:
        L.append(f"- 新增 {nm[c['person']]} {c['field']}：「{c['quote']}」（{c['grade']}）{c['url']}　id `{c['id']}`")
    for c in ops["field_cit_retract"]:
        L.append(f"- 撤回 {nm[c['person']]} deathDate：「{c['quote']}」{c['url']}　id `{c['id']}`")
    L += ["", "## 3. 缺漏（leader_bio_gaps）", "", "| 人物 | target | 動作 | 內容 |", "|---|---|---|---|"]
    for g in ops["gap_retract"]:
        L.append(f"| {nm[g['person']]} | {g['target']} | 撤回 not_found `{g['id']}` | 改記 conflict |")
    for g in ops["gap_insert"]:
        L.append(f"| {nm[g['person']]} | {g['target']} | 新增 conflict{'（已解決，resolved_by `' + g['resolvedBy'] + '`）' if g['resolved'] else '（未解決）'} | {g['note']} |")
    for g in ops["noop"]:
        L.append(f"| {nm[g['person']]} | {g['target']} | 不變 | {g['why']} |")
    L += ["", "## 4. 段落改版（leader_bio_paragraphs 撤回重寫＋superseded_by）", ""]
    for p in ops["par_supersede"]:
        L += [f"### {nm[p['person']]} 第 {p['ord']} 段", "",
              f"- 舊 `{p['old']}` → 新 `{p['new']}`；period {p['oldPeriod']}（{'/'.join(p['oldPrecision'])}）→ {p['newPeriod']}（{'/'.join(p['newPrecision'])}）",
              f"- 舊英文：{p['oldBody']['en']}", f"- 新英文：{p['newBody']['en']}", f"- 舊中文：{p['oldBody']['zh-Hant']}", f"- 新中文：{p['newBody']['zh-Hant']}",
              f"- 引文：沿用 {p['keptCitations']} 筆（複製到新段落）；不沿用："]
        L += [f"  - 「{c['quote']}」（{c['locator']}）{c['url']}：{c['why']}" for c in p["droppedCitations"]]
        L += [f"- 新增引文：「{c['quote']}」（{c['locator']}，{c['grade']}）{c['source']}" for c in ops["par_cit_new"] if c["person"] == p["person"]]
        L.append("")
    L += ["## 5. 注意", "",
          "- Hansson、Mironas、伍廷芳的 conflict 記為**已解決**（resolved_at＋resolved_by_citation_id 指向採用的欄位引文），因 §16「欄位有 conflict 時該欄須為 NULL」只適用未解決者；若 Tai 認為應記未解決，該欄依規則須改 NULL 或降精度。",
          "- Hansson 新版刪去逝世地「Stockholm」：唯一支持的引文（Lex「5. oktober 1946, Stockholm, Sverige」）日期與採用值矛盾而不沿用；死亡地本次不補（Tai 預設 4）。",
          "- Ávila Camacho 的 field_sources.birthDate 仍為 verified 1897-04-24（jsonb 說明欄不改）；欄位值改 NULL。",
          "- seed：run100 的 research.json 不改；修正版段落見 `fix12/paragraphs.patched.json`（seed 格式，含 supersedes）。日後若在空庫重建，需在 run100 寫入後套用本 patch。",
          "- 寫庫需另經同意；plan.sql 結尾為 ROLLBACK、沒有 COMMIT。"]
    (HERE / "fix12-diff.md").write_text("\n".join(L) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
