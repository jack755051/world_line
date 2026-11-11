#!/usr/bin/env python3
"""
B3 分段生平寫入工具（ARCHITECTURE §16.2–16.4；Tai 2026-11-11 拍板）。

範圍：batch01–20 的 research.json；零段落者（pe-schreiber、es-allendesalazar）整人跳過，其餘 98 人寫
leader_bio_paragraphs／person_positions／person_roles（無衝突者）＋各自 citation、需新建的 sources、可入庫的 leader_bio_gaps。

預設 dry-run（唯讀對 5442 開發庫做 SELECT 對帳，印摘要並寫 .dev/b3-write-dryrun.txt、.dev/b3-role-conflicts.md）。
--send 才會寫庫；WRITE_ENABLED=False 時 --send 一律拒絕（Tai 看過網域清單、備份＋套 migration 後才打開）。
連線：docker exec worldline-borders-dev-db（埠 5442）；拒絕 5051／5432／app_postgres 等；不讀、不印任何密鑰。

規則摘要
- 別名正規化只動 gap 的 field: 目標（birth_date→birthDate…）；不在 LeaderBioFields 的（recordIds、positions、biography…）留 seed、不入庫。
- 字串型 claimSpan 併入該筆 evidence_note（已有內容就接在後面，以「；」連接）；claim_span 欄一律空。
- T14 過程註記（t14Overlap、roleEligible…）不入庫；roleCandidates 的 t14Rule 入 person_roles.t14_rule；reason 併入 note。
- person_positions 拒絕 head_of_state／head_of_government／de_facto_leader（應走角色層）。
- 沒有 period.start 的經歷／角色（Tai 2026-11-11 19:14）：不寫 person_positions／person_roles，改記 leader_bio_gaps
    （gap_kind=not_found、note 註明「缺 period.start」；target＝position:<seed_key>／role:<seed_key>）。
    role: target 需 migration GapTargetAllowsRole（尚未套用；套用前 --send 會拒絕）。
- 角色寫入前對 leader_records 比對（同 person_id、有效列）；regime_id 為 null 時不以「政權對不上」當無衝突：
    期間重疊且角色相同 → 擋下（疑似重複，不寫）；期間重疊但角色不同 → 放行（寫入，例：黨職 de_facto_leader 對上元首／首腦）；
    期間不重疊、但 seed reason 自述「待比對」→ 待確認（不寫）；其餘（無重疊）→ 可寫。
- sources 重用／新建：以 URL 對帳（庫內已有相同 URL 就重用）。source_kind 對號（依網域，見 DOMAIN_KIND）：
    具名百科／人物辭典 → encyclopedia；官方機構、政府、議會、檔案館、國家圖書館 → official_website；學術期刊 → peer_reviewed。
    對不上的網域不猜：dry-run 列出，--send 時必須提供 source-kind-overrides.json，否則拒絕。
    overrides 的鍵可為網域或完整 URL（URL 優先）；值為 null 或 "drop" ＝放棄：該來源的引文不寫入，也不算未歸類。
"""
import argparse, json, os, re, subprocess, sys, glob, uuid
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
DEV = os.path.join(REPO, ".dev")
CONTAINER, DBUSER, DBNAME = "worldline-borders-dev-db", "worldline", "worldline_borders_dev"
WRITE_ENABLED = False  # 禁止寫庫；Tai 看過網域清單、備份＋套 migration 後才改。
MISSING_START_CHECKED_ON = "2026-11-11"
DROP = "drop"  # overrides 放棄標記（值 null 或 "drop"）
OVERRIDES = os.path.join(HERE, "source-kind-overrides.json")

PRECISIONS = {"day", "month", "year"}
FIELDS = {"name", "nameZh", "birthDate", "deathDate", "birthPlace", "deathPlace", "party", "summary", "portrait"}
FIELD_ALIAS = {"birth_date": "birthDate", "death_date": "deathDate", "birth_place": "birthPlace", "birthplace": "birthPlace",
               "death_place": "deathPlace", "deathplace": "deathPlace", "name_zh": "nameZh"}
GAP_KINDS = {"conflict", "not_found", "identity_uncertain"}
GAP_TARGET = re.compile(r"^(field|position|paragraph|role):[^\s].*$|^identity$", re.S)
POSITION_KINDS = {"minister", "legislator", "diplomat", "military_command", "military_education", "judicial", "police", "other"}
ROLE_LAYER = {"head_of_state", "head_of_government", "de_facto_leader"}
ROLE_KINDS = ROLE_LAYER | {"cabinet_minister"}
SOURCE_KINDS = {"map", "atlas_map", "treaty", "official_record", "trial_record", "peer_reviewed", "official_history", "dataset",
                "encyclopedia", "official_website"}
SKIP_PEOPLE = {"pe-schreiber", "es-allendesalazar"}

_ENC = """encyclopedia.com www.encyclopedia.com esu.com.ua biografiskleksikon.lex.dk lex.dk snl.no tekst.devb.be
 www.encyclopediaofukraine.com www.treccani.it www.universalis.fr www.enciclopedia.cat islamansiklopedisi.org.tr
 www.deutsche-biographie.de hls-dhs-dss.ch biography.hiu.cas.cz www.blf.fi www.uppslagsverket.fi www.vle.lt
 enciclopediaromaniei.ro enciclopedia.banrepcultural.org www.ecured.cu www18.fgv.br austria-forum.org xboorman.enpchina.eu
 www.konyapedia.com kureansiklopedi.com kotobank.jp""".split()
_OFF = """archives.government.bg aam.ly.gov.tw gov.ro historico.presidencia.gov.co history.state.gov www.assemblee-nationale.fr
 www2.assemblee-nationale.fr www.senat.fr www.elysee.fr www.forseti.is www.stjornarradid.is www.gob.mx www.mfa.gov.lv
 www.mhk.gov.al www.presidencia.pt www.despan.am www.lrs.lt www3.congreso.gob.pe tile.loc.gov download.data.public.lu
 www.ndl.go.jp catalogue.bnf.fr data.bnf.fr www.katalog.bip.ipn.gov.pl culturacores.azores.gov.pt
 repositoriodigital.bnp.gob.pe""".split()
_PEER = """archivo.revistas.ucr.ac.cr asclepio.revistas.csic.es dergipark.org.tr journal.ipm.edu.mo nasu-periodicals.org.ua
 revistas.uasb.edu.ec revistas.ucm.es revistas.ucsp.edu.pe www.redalyc.org www.ceeol.com""".split()
DOMAIN_KIND = {**{d: "encyclopedia" for d in _ENC}, **{d: "official_website" for d in _OFF}, **{d: "peer_reviewed" for d in _PEER}}


# ---------- 純函式（單測） ----------
def norm_field_target(target):
    """gap target 的 field: 別名正規化；回傳 (target 或 None, 是否改寫)。None＝不合格，留 seed。"""
    if not isinstance(target, str) or not GAP_TARGET.match(target) or len(target) > 64:
        return None, False
    if target.startswith("field:"):
        f = target[6:]
        g = FIELD_ALIAS.get(f, f)
        if g not in FIELDS:
            return None, False
        return "field:" + g, g != f
    return target, False


def merge_claim_span(note, span):
    """字串 claimSpan 併入 evidence_note（已有內容就接在後面）；回傳 (新 note, 是否併入)。"""
    if span is None or span == "":
        return note, False
    if not isinstance(span, str):
        raise ValueError("claimSpan 非字串（預期本批全為字串或空）：%r" % (span,))
    span = span.strip()
    if not span:
        return note, False
    return (note + "；" + span if note and note.strip() else span), True


def guess_kind(url, overrides=None):
    """回傳 source_kind、DROP（overrides 放棄）或 None（未歸類）。URL 鍵優先於網域鍵。"""
    host = urlparse(url or "").netloc.lower()
    if overrides:
        for k in (url, host):
            if k in overrides:
                v = overrides[k]
                return DROP if v is None or v == DROP else v
    return DOMAIN_KIND.get(host)


def missing_start(item):
    """seed 的 period 缺 start（無 period、或 start 為空）。"""
    p = item.get("period")
    return not p or not p.get("start")


def missing_start_gap(bio, kind, item):
    """缺起日的經歷／角色 → leader_bio_gaps 列（target 不合格則回 None，留 seed）。"""
    t, _ = norm_field_target("%s:%s" % (kind, item.get("key", "")))
    if t is None:
        return None
    ttl = item.get("title")
    ttl = (ttl.get("orig") or next(iter(ttl.values()), "")) if isinstance(ttl, dict) else (ttl or "")
    p = item.get("period") or {}
    end = "；period.end=%s" % p["end"] if p.get("end") else ""
    layer = "person_positions" if kind == "position" else "person_roles"
    return {"bio": bio, "target": t, "kind": "not_found", "cand": [], "checked": MISSING_START_CHECKED_ON,
            "note": "缺 period.start，未寫入 %s（表要求起日有界）；原標題：%s%s" % (layer, str(ttl)[:80], end)}


def period_literal(p):
    """seed period {start,end} → daterange 字面值（半開；end 缺＝無界）。"""
    if not p or not p.get("start"):
        return None
    s, e = p["start"], p.get("end")
    if e and e <= s:
        raise ValueError("期間為空或反向：%s–%s" % (s, e))
    return "[%s,%s)" % (s, e or "")


def periods_overlap(a, b):
    """半開區間 (start, end|None) 是否重疊（ISO 日期字串可直接比大小）。"""
    (s1, e1), (s2, e2) = a, b
    return (e2 is None or s1 < e2) and (e1 is None or s2 < e1)


def classify_role(cand, records):
    """
    cand: {key, role_kind, period{start,end}, reason}；records: 同 person 有效 leader_records
    [{role, start, end|None, regime}]。回傳 ('ok'|'conflict'|'pending', 原因, 對上的 records)。
    regime_id 為 null 時不以政權不同當作無衝突（見檔頭規則）。
    ok 且 why 非空＝期間重疊但角色不同，放行（hits 為對上的紀錄，供清單列出）。
    """
    cp = (cand["period"]["start"], cand["period"].get("end"))
    hits = [r for r in records if periods_overlap(cp, (r["start"], r["end"]))]
    same = [r for r in hits if r["role"] == cand["role_kind"]]
    if same:
        return "conflict", "期間重疊且角色相同（疑似重複；候選未指定政權）", same
    if hits:
        return "ok", "期間重疊但角色不同，放行（庫內 %s／候選 %s）" % ("、".join(sorted({r["role"] for r in hits})), cand["role_kind"]), hits
    if records and "待比對" in (cand.get("reason") or ""):
        return "pending", "期間未與現有紀錄重疊，但 seed 自述尚待比對名單，無法確認是否同一政權", []
    return "ok", "", []


def sql_lit(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, (dict, list)):
        v = json.dumps(v, ensure_ascii=False)
    s = str(v)
    if "\x00" in s:
        raise ValueError("字串含 NUL")
    return "'" + s.replace("'", "''") + "'"


def sql_jsonb(v):
    return "NULL" if v is None else sql_lit(v) + "::jsonb"


# ---------- 載入 ----------
def load_batches():
    batches = []
    for f in sorted(glob.glob(os.path.join(HERE, "batch*", "research.json"))):
        d = json.load(open(f, encoding="utf-8"))
        batches.append((os.path.basename(os.path.dirname(f)), d))
    return batches


def psql(sql, check=True):
    r = subprocess.run(["docker", "exec", "-i", CONTAINER, "psql", "-U", DBUSER, "-d", DBNAME, "-At", "-F", "\t", "-v", "ON_ERROR_STOP=1"],
                       input=sql, capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(r.stderr[:500])
    return [l.split("\t") for l in r.stdout.splitlines() if l]


def db_state(bio_ids):
    st = {"tables": psql("select to_regclass('leader_bio_paragraphs') is not null")[0][0] == "t"}
    st["bios"] = {r[0] for r in psql("select id from leader_bios where retracted_at is null")}
    st["regimes"] = {r[0] for r in psql("select id from regimes")}
    st["sources"] = {}
    for r in psql("select url,id,source_kind from sources where url is not null order by created_at"):
        st["sources"].setdefault(r[0], (r[1], r[2]))
    recs = {}
    for r in psql("select l.person_id,l.role,lower(l.valid_period),upper(l.valid_period),coalesce(g.slug,'?'),l.id "
                  "from leader_records l left join regimes g on g.id=l.regime_id where l.retracted_at is null and l.person_id is not null"):
        recs.setdefault(r[0], []).append({"role": r[1], "start": r[2], "end": r[3] or None, "regime": r[4], "id": r[5]})
    st["records"] = recs
    ex = {"paragraphs": set(), "positions": set(), "roles": set()}
    if st["tables"]:
        ex["paragraphs"] = {(r[0], int(r[1])) for r in psql("select bio_id,ord from leader_bio_paragraphs where retracted_at is null")}
        ex["positions"] = {(r[0], r[1]) for r in psql("select bio_id,seed_key from person_positions where retracted_at is null")}
        ex["roles"] = {(r[0], r[1]) for r in psql("select bio_id,seed_key from person_roles where retracted_at is null")}
    st["existing"] = ex
    return st


# ---------- 主流程 ----------
def plan(batches, st, overrides):
    P = {"people": 0, "skipped": [], "bad": [], "claimspan_merged": 0, "bio_missing": [], "precision_fixed": 0}
    P.update(sources_new={}, sources_reused={}, sources_dropped={}, unclassified={}, gaps_missing={"position": 0, "role": 0}, role_released=[],
             nostart=[], gaps_missing_seed=[], par=[], pos=[], role_ok=[], role_conflict=[], role_pending=[],
             gaps=[], gaps_seed=[], gaps_alias=0, gaps_dup=0, cit_dropped=[], parents_nocit=[], already={"par": 0, "pos": 0, "role": 0})

    def resolve_source(batch, d, key):
        s = d["sources"].get(key)
        if not s or not s.get("url"):
            return None
        url = s["url"]
        if url in st["sources"]:
            P["sources_reused"][url] = st["sources"][url][0]
            return st["sources"][url][0]
        if url in P["sources_new"]:
            return P["sources_new"][url]["id"]
        kind = guess_kind(url, overrides)
        if kind == DROP:
            P["sources_dropped"][url] = urlparse(url).netloc
            return None
        if kind is None:
            P["unclassified"].setdefault(urlparse(url).netloc, set()).add((s["title"][:50], s["publisher"][:40], url))
            return None
        if kind not in SOURCE_KINDS:
            raise ValueError("source_kind 非法：" + kind)
        P["sources_new"][url] = {"id": str(uuid.uuid4()), "kind": kind, "title": s["title"], "publisher": s["publisher"],
                                 "authors": "; ".join(s.get("authors") or []) or None, "published_text": s.get("published_text"),
                                 "url": url, "archive_url": s.get("archive_url"), "catalog_id": s.get("catalog_id"),
                                 "license_code": s.get("license_code")}
        return P["sources_new"][url]["id"]

    def cites(batch, d, owner, lst):
        out = []
        for i, c in enumerate(lst or []):
            sid = resolve_source(batch, d, c.get("sourceKey"))
            if sid is None:
                P["cit_dropped"].append((owner, c.get("sourceKey"), "來源無 URL／未分類／已放棄"))
                continue
            if not (c.get("locator") or "").strip() or not (c.get("quote") or "").strip() or c.get("grade") not in (None, "A", "B"):
                P["cit_dropped"].append((owner, c.get("sourceKey"), "locator／quote 空白或 grade 非 A/B"))
                continue
            note, merged = merge_claim_span(c.get("evidenceNote"), c.get("claimSpan"))
            P["claimspan_merged"] += merged
            out.append({"source_id": sid, "locator": c["locator"], "quote": c["quote"], "quote_lang": c.get("quoteLang"),
                        "evidence_note": note, "accessed_on": c["accessedOn"], "grade": c.get("grade"),
                        "date_precision": c.get("datePrecision") if c.get("datePrecision") in PRECISIONS else None,
                        "policy_version": c.get("policyVersion")})
        return out

    def prec(v, bounded):
        if v is None or not bounded:
            if v is not None:
                P["precision_fixed"] += 1
            return None
        return v if v in PRECISIONS else None

    for batch, d in batches:
        for p in d["people"]:
            pk, bio = p["key"], p["bioId"]
            if not p["paragraphs"] or pk in SKIP_PEOPLE:
                P["skipped"].append(pk)
                continue
            if bio not in st["bios"]:
                P["bio_missing"].append(pk)
                continue
            P["people"] += 1
            for g in p["paragraphs"]:
                if (bio, g["ord"]) in st["existing"]["paragraphs"]:
                    P["already"]["par"] += 1
                    continue
                try:
                    per = period_literal(g.get("period"))
                    if not isinstance(g.get("body"), dict) or g["ord"] < 1:
                        raise ValueError("body 非物件或 ord<1")
                except Exception as e:
                    P["bad"].append((pk, "paragraph %s" % g.get("ord"), str(e)))
                    continue
                cs = cites(batch, d, (pk, "paragraph", g["ord"]), g.get("citations"))
                if not cs: P["parents_nocit"].append((pk, "paragraph", g["ord"]))
                P["par"].append({"bio": bio, "ord": g["ord"], "period": per, "sp": g.get("periodStartPrecision") if per else None,
                                 "ep": g.get("periodEndPrecision") if per and not per.endswith(",)") else None,
                                 "heading": g.get("heading"), "body": g["body"], "cit": cs})
            for x in p["positions"]:
                if (bio, x["key"]) in st["existing"]["positions"]:
                    P["already"]["pos"] += 1
                    continue
                if missing_start(x):
                    g = missing_start_gap(bio, "position", x)
                    if g and (g["target"], g["kind"]) not in {(y["target"], y["kind"]) for y in P["gaps"] if y["bio"] == bio}:
                        P["gaps"].append(g); P["gaps_missing"]["position"] += 1
                    elif not g:
                        P["gaps_missing_seed"].append((pk, x.get("key")))
                    P["nostart"].append((pk, "position", x.get("key", "?")))
                    continue
                try:
                    if x["positionKind"] in ROLE_LAYER: raise ValueError("position_kind %s 應走角色層" % x["positionKind"])
                    if x["positionKind"] not in POSITION_KINDS: raise ValueError("position_kind 未知：" + str(x["positionKind"]))
                    per = period_literal(x.get("period"))
                    if not per: raise ValueError("缺起日")
                    if not isinstance(x.get("title"), dict): raise ValueError("title 非物件")
                except Exception as e:
                    P["bad"].append((pk, "position " + x.get("key", "?"), str(e)))
                    continue
                rid = x.get("regimeId")
                if rid and rid not in st["regimes"]:
                    P["bad"].append((pk, "position " + x["key"], "regimeId 不存在：" + rid)); continue
                bounded = not per.endswith(",)")
                cs = cites(batch, d, (pk, "position", x["key"]), x.get("citations"))
                if not cs: P["parents_nocit"].append((pk, "position", x["key"]))
                P["pos"].append({"bio": bio, "key": x["key"], "regime": rid, "org": x.get("organization"), "title": x["title"],
                                 "kind": x["positionKind"], "period": per, "sp": prec(x.get("startPrecision"), True),
                                 "ep": prec(x.get("endPrecision"), bounded), "note": x.get("note"), "cit": cs})
            for r in p["roleCandidates"]:
                if (bio, r["key"]) in st["existing"]["roles"]:
                    P["already"]["role"] += 1
                    continue
                if missing_start(r):
                    g = missing_start_gap(bio, "role", r)
                    if g and (g["target"], g["kind"]) not in {(y["target"], y["kind"]) for y in P["gaps"] if y["bio"] == bio}:
                        P["gaps"].append(g); P["gaps_missing"]["role"] += 1
                    elif not g:
                        P["gaps_missing_seed"].append((pk, r.get("key")))
                    P["nostart"].append((pk, "role", r.get("key", "?")))
                    continue
                try:
                    if r["role_kind"] not in ROLE_KINDS: raise ValueError("role_kind 未知：" + str(r["role_kind"]))
                    per = period_literal(r.get("period"))
                    if not per: raise ValueError("缺起日")
                except Exception as e:
                    P["bad"].append((pk, "role " + r.get("key", "?"), str(e)))
                    continue
                rid = r.get("regimeId")
                if rid and rid not in st["regimes"]:
                    P["bad"].append((pk, "role " + r["key"], "regimeId 不存在：" + rid)); continue
                verdict, why, hits = classify_role(r, st["records"].get(bio, []))
                bounded = not per.endswith(",)")
                note = "；".join(t for t in (r.get("note"), r.get("reason")) if t) or None
                row = {"bio": bio, "person": pk, "key": r["key"], "regime": rid, "org": r.get("organization"), "title": r["title"],
                       "kind": r["role_kind"], "period": per, "sp": prec(r.get("startPrecision"), True), "ep": prec(r.get("endPrecision"), bounded),
                       "acting": bool(r.get("acting")), "t14": r.get("t14Rule"), "note": note, "why": why, "hits": hits, "cand": r}
                if verdict == "ok":
                    row["cit"] = cites(batch, d, (pk, "role", r["key"]), r.get("citations"))
                    P["role_ok"].append(row)
                    if why:
                        P["role_released"].append(row)
                else:
                    (P["role_conflict"] if verdict == "conflict" else P["role_pending"]).append(row)
            seen = set()
            for g in p["gaps"]:
                t, aliased = norm_field_target(g.get("target"))
                if t is None or g.get("gapKind") not in GAP_KINDS or not isinstance(g.get("candidateCitations") or [], list):
                    P["gaps_seed"].append((pk, g.get("target"), g.get("gapKind")))
                    continue
                if (t, g["gapKind"]) in seen:
                    P["gaps_dup"] += 1
                    continue
                seen.add((t, g["gapKind"]))
                P["gaps_alias"] += aliased
                P["gaps"].append({"bio": bio, "target": t, "kind": g["gapKind"], "note": g.get("note"),
                                  "cand": g.get("candidateCitations") or [], "checked": g["checkedOn"]})
    return P


def summary(P):
    nc = lambda rows: sum(len(r.get("cit", [])) for r in rows)
    L = ["B3 分段生平寫入 dry-run（只讀 5442；未寫庫）",
         "處理人數：%d　跳過零段落：%d（%s）　庫內無此 bioId：%d" % (P["people"], len(P["skipped"]), "、".join(P["skipped"]), len(P["bio_missing"])),
         "sources：新建 %d／重用 %d／放棄 %d（URL；網域 %d）／無法歸類網域 %d（涉及 URL %d）" % (
             len(P["sources_new"]), len(P["sources_reused"]), len(P["sources_dropped"]), len(set(P["sources_dropped"].values())),
             len(P["unclassified"]), sum(len(v) for v in P["unclassified"].values())),
         "  新建依 source_kind：" + json.dumps({k: sum(1 for s in P["sources_new"].values() if s["kind"] == k) for k in sorted({s["kind"] for s in P["sources_new"].values()})}),
         "段落：%d　段落引文：%d" % (len(P["par"]), nc(P["par"])),
         "經歷：%d　經歷引文：%d" % (len(P["pos"]), nc(P["pos"])),
         "角色：可寫入 %d（含角色不同、期間重疊而放行 %d）　角色引文 %d／擋下疑似重複 %d／待確認 %d" % (
             len(P["role_ok"]), len(P["role_released"]), nc(P["role_ok"]), len(P["role_conflict"]), len(P["role_pending"])),
         "缺 period.start 改記缺漏：%d（經歷 %d＋角色 %d；已入 gaps %d，target 不合格留 seed %d）" % (
             len(P["nostart"]), sum(1 for n in P["nostart"] if n[1] == "position"), sum(1 for n in P["nostart"] if n[1] == "role"),
             P["gaps_missing"]["position"] + P["gaps_missing"]["role"], len(P["gaps_missing_seed"])),
         "gaps：將入庫 %d＝seed 原有 %d（別名正規化 %d、同人重複略過 %d）＋缺起日 %d（position: %d／role: %d）／留在 seed %d" % (
             len(P["gaps"]), len(P["gaps"]) - P["gaps_missing"]["position"] - P["gaps_missing"]["role"], P["gaps_alias"], P["gaps_dup"],
             P["gaps_missing"]["position"] + P["gaps_missing"]["role"], P["gaps_missing"]["position"], P["gaps_missing"]["role"], len(P["gaps_seed"])),
         "  其中 role: target 需先套 migration GapTargetAllowsRole（尚未套用）",
         "字串 claimSpan 併入 evidence_note：%d 筆（只計入將寫入的引文）" % P["claimspan_merged"],
         "已存在（重跑會略過）：段落 %(par)d／經歷 %(pos)d／角色 %(role)d" % P["already"],
         "驗證不過被略過：%d；因來源缺失而捨棄的引文：%d；寫入後無引文的父列：%d；欄位精度校正：%d" % (len(P["bad"]), len(P["cit_dropped"]), len(P["parents_nocit"]), P["precision_fixed"])]
    from collections import Counter
    for (kind, why), n in sorted(Counter((b[1].split()[0], re.sub(r"[：:].*", "", b[2])) for b in P["bad"]).items()):
        L.append("  略過原因 %s／%s：%d" % (kind, why, n))
    L.append("  擋下原因：" + json.dumps(dict(Counter(r["why"].split("（")[0] for r in P["role_conflict"])), ensure_ascii=False))
    L.append("  放行原因：" + json.dumps(dict(Counter(r["why"].split("（")[0] for r in P["role_released"])), ensure_ascii=False))
    for u, h in sorted(P["sources_dropped"].items()):
        L.append("  放棄來源 %s" % u)
    for dom, v in sorted(P["unclassified"].items()):
        L.append("  未歸類網域 %s：%s" % (dom, "｜".join(sorted(t[1] for t in v))[:90]))
    return "\n".join(L)


def conflicts_md(P):
    out = ["# B3 角色候選比對清單（本機，不 commit）", "",
           "放行 %d 筆（期間重疊但角色不同）、擋下 %d 筆（期間重疊且角色相同，疑似重複）、待確認 %d 筆、缺起日改記缺漏 %d 筆。"
           "比對對象：同 person_id 的有效 leader_records。僅「放行」會寫入 person_roles（連同其無衝突者）。" % (
               len(P["role_released"]), len(P["role_conflict"]), len(P["role_pending"]), sum(1 for n in P["nostart"] if n[1] == "role")), ""]
    for title, rows in (("放行（角色不同，寫入）", P["role_released"]), ("擋下（疑似重複，不寫）", P["role_conflict"]),
                        ("待確認（不寫）", P["role_pending"])):
        out += ["## %s：%d 筆" % (title, len(rows)), "", "| 人 | seed_key | 角色 | 期間 | 對上的 leader_records | 原因 |", "|---|---|---|---|---|---|"]
        for r in rows:
            c = r["cand"]["period"]
            hit = "；".join("%s %s~%s（%s）" % (h["role"], h["start"], h["end"] or "", h["regime"]) for h in r["hits"]) or "—"
            out.append("| %s | %s | %s%s | %s~%s | %s | %s |" % (r["person"], r["key"], r["kind"], "（代理）" if r["acting"] else "", c["start"], c.get("end") or "", hit, r["why"]))
        out.append("")
    out += ["## 缺 period.start 改記 leader_bio_gaps（target＝role:<seed_key>）", ""]
    out += ["- %s／%s" % (n[0], n[2]) for n in P["nostart"] if n[1] == "role"]
    return "\n".join(out)


def build_sql(P):
    q = []
    A = q.append
    A("BEGIN;")
    for s in P["sources_new"].values():
        A("INSERT INTO sources (id,source_kind,title,publisher,authors,published_text,url,archive_url,catalog_id,license_code) VALUES (%s);" %
          ",".join(sql_lit(s[k]) for k in ("id", "kind", "title", "publisher", "authors", "published_text", "url", "archive_url", "catalog_id", "license_code")))

    def cit(table, fk, pid, c):
        A("INSERT INTO %s (%s,source_id,locator,quote,quote_lang,evidence_note,accessed_on,grade,date_precision,policy_version) VALUES (%s);" %
          (table, fk, ",".join(sql_lit(x) for x in (pid, c["source_id"], c["locator"], c["quote"], c["quote_lang"], c["evidence_note"],
                                                    c["accessed_on"], c["grade"], c["date_precision"], c["policy_version"]))))
    for g in P["par"]:
        pid = str(uuid.uuid4())
        A("INSERT INTO leader_bio_paragraphs (id,bio_id,ord,period,period_start_precision,period_end_precision,heading,body) VALUES (%s,%s,%s,%s,%s,%s,%s,%s);" %
          (sql_lit(pid), sql_lit(g["bio"]), g["ord"], sql_lit(g["period"]) + ("::daterange" if g["period"] else ""), sql_lit(g["sp"]), sql_lit(g["ep"]),
           sql_jsonb(g["heading"]), sql_jsonb(g["body"])))
        for c in g["cit"]: cit("leader_bio_paragraph_citations", "paragraph_id", pid, c)
    for tbl, ctbl, fk, rows, extra in (("person_positions", "person_position_citations", "position_id", P["pos"], "position_kind"),
                                       ("person_roles", "person_role_citations", "role_id", P["role_ok"], "role_kind")):
        for r in rows:
            pid = str(uuid.uuid4())
            cols = "id,bio_id,seed_key,regime_id,organization,title,%s,period,start_precision,end_precision,note" % extra
            vals = [sql_lit(pid), sql_lit(r["bio"]), sql_lit(r["key"]), sql_lit(r["regime"]), sql_jsonb(r["org"]), sql_jsonb(r["title"]),
                    sql_lit(r["kind"]), sql_lit(r["period"]) + "::daterange", sql_lit(r["sp"]), sql_lit(r["ep"]), sql_lit(r["note"])]
            if tbl == "person_roles":
                cols += ",acting,t14_rule"; vals += [sql_lit(r["acting"]), sql_lit(r["t14"])]
            A("INSERT INTO %s (%s) VALUES (%s);" % (tbl, cols, ",".join(vals)))
            for c in r["cit"]: cit(ctbl, fk, pid, c)
    for g in P["gaps"]:
        A("INSERT INTO leader_bio_gaps (bio_id,target,gap_kind,note,candidate_citations,checked_on) VALUES (%s,%s,%s,%s,%s::jsonb,%s) ON CONFLICT DO NOTHING;" %
          (sql_lit(g["bio"]), sql_lit(g["target"]), sql_lit(g["kind"]), sql_lit(g["note"]), sql_lit(g["cand"]), sql_lit(g["checked"])))
    A("COMMIT;")
    return "\n".join(q)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", action="store_true", help="寫庫（WRITE_ENABLED=False 時一律拒絕）")
    ap.add_argument("--port", default="5442")
    a = ap.parse_args()
    if a.port != "5442":
        sys.exit("只允許 5442 開發庫（拒絕 %s）" % a.port)
    overrides = json.load(open(OVERRIDES)) if os.path.exists(OVERRIDES) else {}
    batches = load_batches()
    st = db_state(None)
    P = plan(batches, st, overrides)
    text = summary(P)
    os.makedirs(DEV, exist_ok=True)
    open(os.path.join(DEV, "b3-write-dryrun.txt"), "w", encoding="utf-8").write(text + "\n")
    open(os.path.join(DEV, "b3-role-conflicts.md"), "w", encoding="utf-8").write(conflicts_md(P) + "\n")
    print(text)
    if not a.send:
        print("\n（dry-run；未寫庫）")
        return
    if not WRITE_ENABLED:
        sys.exit("不允許寫庫（WRITE_ENABLED=False）。")
    if not st["tables"] or "encyclopedia" not in psql("select pg_get_constraintdef(oid) from pg_constraint where conname='ck_sources_source_kind'")[0][0]:
        sys.exit("migration 尚未套用，拒絕寫入。")
    if P["unclassified"]:
        sys.exit("有未歸類的來源網域，請先提供 source-kind-overrides.json。")
    if P["gaps_missing"]["role"] and "role" not in psql("select pg_get_constraintdef(oid) from pg_constraint where conname='ck_leader_bio_gaps_target'")[0][0]:
        sys.exit("migration GapTargetAllowsRole 尚未套用（role: target 會被 CHECK 擋下），拒絕寫入。")
    r = subprocess.run(["docker", "exec", "-i", CONTAINER, "psql", "-U", DBUSER, "-d", DBNAME, "-v", "ON_ERROR_STOP=1", "-1"],
                       input=build_sql(P), capture_output=True, text=True)
    sys.exit(r.stderr[:500] if r.returncode else print("已寫入。") or 0)


if __name__ == "__main__":
    main()
