"""B3 試跑離線檢查（不連任何資料庫、不連網）。以 ../b3-sample/verify.py 為底，加上 Tai 2026-11-11 09:35 定案（ARCHITECTURE §16.3.2）。

用法：python3 -I verify.py batchNN/research.json [--raw RAW_DIR RAWMAP.json] [--report out.json]
- 有 --raw：引文須空白正規化後逐字出現在研究當天抓下的原文（RAW_DIR 內純文字檔；RAWMAP：sourceKey → 檔名）。
  原文不進版控（著作權），報告只記 sha256。沒有 --raw 時只做格式檢查，報告標 rawChecked=false。
- 若 research.json 頂層有 "rawDir"、"rawMap" 且未給 --raw，會自動採用（rawMap 為相對 research.json 的路徑）。
檢查：
 1. 引文 NFC ≤ 80 字元（§16.4.1）；非空；（有原文時）逐字出現。
 2. 每段落、每職位至少 1 筆 citation（§16.1-3）；段落／職位 citation 的 grade 必須是 A 或 B，且與來源一致（Q9：未評等來源只可出現在 gaps 候選）。
    將領生平檔（gradePolicy=ABC-2026-11-12 或 rawDir 含 /generals-）另收具名 C 級（Tai 2026-11-12 06:34）；C 須具名作者／出版機構，論壇／部落格／維基類不收。
 3. 來源網域不在硬性排除清單（含任何 wikipedia／wikidata／百度）；citation 的 sourceKey 必須存在於頂層 sources（建議 5）。
 4. Q2：段落中文 ≤ 400 字、英文 ≤ 800 字元（NFC code point）。ord 唯一；period 起 < 迄。
 5. Q3：month／year 精度的端點必須是該單位的起日（YYYY-MM-01／YYYY-01-01）。
 6. 職位 roleKind 不得為元首／首腦（Q4：範圍外元首任期只寫正文；元首／首腦任期只在 leader_records）；值域照 §16.3 提案。
 7. Q5：regimeId 非空時，職位期間必須與 1908-01-01～1945-10-01 有交集；regimeId 為空時須有 organization。
 8. Q7：evidenceNote 提到「下一任」者，必須同時含「推論」。
 9. gaps：target 格式、gap_kind 三值（§16.4.2）。
10. 每人必須有 bioId 鍵（建議 6；值可為 null）。
對齊後檔案（頂層 alignedTo == "b0b0e0f"，research.aligned.json；ARCHITECTURE b0b0e0f／T11／T12／T14）另加：
11. positions 用 positionKind，出現 roleKind 即違規；positionKind 值域沿用原 7 種（僅供參考，實作時再定）；不得為元首／首腦／實際掌權者。
12. roleCandidates 每筆必須有 citations（逐筆照第 1、2 項檢查）、role_kind ∈ {head_of_state, head_of_government, de_facto_leader}、reason 非空；
    不得有 roleKind／candidateRoleKind（Tai 2026-11-11 12:12 第 4 項：統一為 role_kind）。
13. t14Overlap 若有，值須為 cabinet／general／occupation_colonial。
14. positions 不得含 positionKind=party（Tai 2026-11-11 12:12 第 2 項：黨職一律移至 roleCandidates 為 de_facto_leader），
    除非該項標 partyPostAmbiguous=true 且附 partyPostAmbiguousReason；positionKind 不得為三種角色值（同第 11 項）。
T14 R0–R6（T14_RECOMMENDATION.md；Tai 2026-11-11 12:47 第 5 項）、黨籍席位（同日第 2 項）另加：
15. roleCandidates.role_kind 值域擴為 ROLE_LAYER_KINDS（元首／首腦／實際掌權者＋cabinet_minister、military_commander、
    occupation_administrator、colonial_governor）；positions.positionKind 不得為任何角色層值；positionKind 值域加 police、military_education。
16. 每筆帶 t14Overlap 的 positions 項須有 t14Rule ∈ R0–R6（或 t14Ambiguous=true 附理由）；positions 內 t14Rule 只可為 R5／R6，
    R0–R4 只能出現在 roleCandidates（兩層互斥），除非 t14Ambiguous=true。
17. t14Rule=R6 須 roleEligible=true、roleEligibleKind ∈ 角色層值、roleGap 非空、t14Reason 非空；非 R6 不得有 roleEligible。
18. positions 若有 originalPositionKind（邊界個案改類別），須與 positionKind 不同且屬原值域；roleCandidates 的 t14Rule 若有，須 ∈ R0–R4。
"""
import hashlib, json, re, sys, unicodedata
from pathlib import Path
from urllib.parse import urlparse

EXCLUDED_HOSTS = ("wikipedia.org", "wikidata.org", "wikimedia.org", "baidu.com", "enciclopediadelecuador.com")
# 具名 C 級（Tai 本人 2026-11-12 06:34「將領生平來源放寬到具名 C 級」）：只對將領生平檔開放
# （頂層 gradePolicy == "ABC-2026-11-12"，或 rawDir 含 "/generals-"）；B3 其他檔仍只收 A／B。
# C 級來源須有具名作者或具名出版機構，且網域不得是論壇／部落格／維基類／AI 內容農場。
GRADE_C_POLICY = "ABC-2026-11-12"
C_BANNED_HOSTS = ("wikipedia.org", "wikidata.org", "wikimedia.org", "wikiwand.com", "wikia.com", "fandom.com",
                  "everybodywiki.com", "baidu.com", "blogspot.com", "wordpress.com", "medium.com", "substack.com",
                  "tumblr.com", "livejournal.com", "reddit.com", "quora.com", "stackexchange.com", "zhihu.com",
                  "tieba.baidu.com", "ptt.cc", "mobile01.com", "pixnet.net", "weebly.com", "wixsite.com",
                  "sites.google.com", "hubpages.com", "ancestry.com", "findagrave.com", "geni.com",
                  "fold3.com", "historynet.com/forum", "axishistory.com", "ww2talk.com", "feldgrau.net")
C_BANNED_HOST_HINTS = ("forum", "bbs.", "blog.", ".blog", "wiki.")
ROLE_KINDS = {"minister", "legislator", "military_command", "party", "diplomat", "judicial", "other"}
ALIGNED_POSITION_KINDS = ROLE_KINDS | {"police", "military_education"}   # T14 文件 §4 邊界個案
ROLE_LAYER_KINDS = {"head_of_state", "head_of_government", "de_facto_leader", "cabinet_minister", "military_commander",
                    "occupation_administrator", "colonial_governor"}   # T14 文件 §1 R0–R4
T14_RULES = {"R0", "R1", "R2", "R3", "R4", "R5", "R6"}
ROLE_RULES = {"R0", "R1", "R2", "R3", "R4"}
FORBIDDEN_ROLES = {"head_of_state", "head_of_government"}
FORBIDDEN_ALIGNED = FORBIDDEN_ROLES | {"de_facto_leader"}
CANDIDATE_KINDS = ROLE_LAYER_KINDS
T14_VALUES = {"cabinet", "general", "occupation_colonial"}
GAP_KINDS = {"conflict", "not_found", "identity_uncertain"}
PREC = {None, "day", "month", "year"}
SCOPE_START, SCOPE_END = "1908-01-01", "1945-10-01"


# 將領 nameZh 正體檢查用（../generals-roster/zh_trad.py；OpenCC 在使用者層 venv，zh_trad 自行加路徑，因主迴圈用 python3 -I）
try:
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("zh_trad", str(Path(__file__).resolve().parent.parent / "generals-roster" / "zh_trad.py"))
    _zt = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_zt)
    _zt.to_trad("测试")
    _TO_TRAD, _TRAD_ERR = _zt.to_trad, None

    def _legacy_ok(nz):  # 10:07 版規則（s2t＋PROTECT，不含 t2tw／PRE）下是否已是正體
        t = _zt._load().convert(nz)
        return (t if len(t) != len(nz) else "".join(a if a in _zt.PROTECT else b for a, b in zip(nz, t))) == nz
except Exception as _e:  # noqa
    _TO_TRAD, _TRAD_ERR = None, repr(_e)


def norm(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s)).strip()


def nfc_len(s):
    return len(unicodedata.normalize("NFC", s or ""))


def arg(name, n=1):
    if name not in sys.argv:
        return None
    i = sys.argv.index(name)
    return sys.argv[i + 1:i + 1 + n]


def main():
    rp = Path(sys.argv[1])
    data = json.load(open(rp))
    report_path = (arg("--report") or [None])[0]
    raw = arg("--raw", 2)
    if not raw and data.get("rawDir") and data.get("rawMap"):
        raw = [data["rawDir"], str(rp.parent / data["rawMap"])]
    texts, hashes, errs, warns, stats = {}, {}, [], [], {}
    if raw:
        raw_dir, rawmap = raw[0], json.load(open(raw[1]))
        for k, f in rawmap.items():
            p = Path(raw_dir) / f
            if not p.exists():
                errs.append(f"原文檔不存在：{k} → {p}"); continue
            b = p.read_bytes()
            texts[k] = norm(b.decode("utf-8", errors="replace"))
            hashes[k] = {"file": f, "sha256": hashlib.sha256(b).hexdigest()}
    srcs = data.get("sources") or {}
    allow_c = data.get("gradePolicy") == GRADE_C_POLICY or "/generals-" in str(data.get("rawDir") or "")
    OKG = ("A", "B", "C") if allow_c else ("A", "B")
    for k, s in srcs.items():
        for u in (s.get("url"), s.get("archive_url")):
            host = (urlparse(u).hostname or "") if u else ""
            if any(host == h or host.endswith("." + h) for h in EXCLUDED_HOSTS):
                errs.append(f"來源 {k} 網域被排除：{host}")
        if s.get("grade") not in (None,) + OKG:
            errs.append(f"來源 {k} grade 非法：{s.get('grade')}")
        if s.get("grade") == "C":
            if not ([a for a in (s.get("authors") or []) if str(a).strip()] or str(s.get("publisher") or "").strip()):
                errs.append(f"來源 {k}：C 級須有具名作者或具名出版機構")
            for u in (s.get("url"), s.get("archive_url")):
                if not u:
                    continue
                host = (urlparse(u).hostname or "").lower()
                full = u.lower()
                if any(host == h or host.endswith("." + h) or (("/" in h) and h in full) for h in C_BANNED_HOSTS) \
                        or any(x in host for x in C_BANNED_HOST_HINTS):
                    errs.append(f"來源 {k}：C 級網域不收（論壇／部落格／維基類／內容農場）：{host}")
    blob = json.dumps(data, ensure_ascii=False).lower()
    if "wikipedia" in blob or "wikidata.org" in blob:
        for m in re.finditer(r"https?://[^\s\"']*(wikipedia|wikidata)[^\s\"']*", blob):
            errs.append(f"檔內出現 Wikipedia／Wikidata 網址：{m.group(0)}")

    qlens = []

    def chk_quote(where, sk, q):
        if sk not in srcs:
            errs.append(f"{where}：未知來源 {sk}"); return 0
        if not q or not q.strip():
            errs.append(f"{where}：引文空白"); return 0
        n = nfc_len(q)
        if n > 80:
            errs.append(f"{where}：引文 {n} 字 > 80：{q}")
        if raw:
            if sk not in texts:
                errs.append(f"{where}：來源 {sk} 沒有原文檔，無法核對引文")
            elif norm(q) not in texts[sk]:
                errs.append(f"{where}：引文未逐字出現於 {sk}：{q}")
        return n

    def chk_bound(where, d, prec, end):
        if not d or prec in (None, "day"):
            return
        if prec == "year" and not d.endswith("-01-01"):
            errs.append(f"{where}：year 精度{'終點' if end else '起點'}須為 YYYY-01-01（Q3），實為 {d}")
        if prec == "month" and not d.endswith("-01"):
            errs.append(f"{where}：month 精度{'終點' if end else '起點'}須為 YYYY-MM-01（Q3），實為 {d}")

    aligned = data.get("alignedTo") == "b0b0e0f"
    if aligned and not data.get("alignNote"):
        errs.append("對齊檔缺 alignNote")
    people = data.get("people") or []
    if not people:
        errs.append("people 為空")
    for p in people:
        key = p.get("key", "?")
        if allow_c:  # 將領生平檔：nameZh 須等於 zh_trad.to_trad(nameZh)（s2t→t2tw 台灣字形＋PRE＋PROTECT；World Line 主管 2026-11-12 10:07／10:20）
            nz = p.get("nameZh")
            if _TO_TRAD is None:
                errs.append(f"{key}：無法載入 zh_trad／OpenCC，nameZh 正體檢查無法執行（{_TRAD_ERR}）")
            elif isinstance(nz, str) and nz and _TO_TRAD(nz) != nz:
                # 過渡：A/batch022 在 10:20 字形規則加入前已開跑；若只差台灣字形（10:07 版 s2t 規則已過）只記 note，commit 後由 patch_name_trad.py 補轉；A/batch023 起一律擋
                if "/A/batch022/" in str(data.get("rawDir") or "") and _legacy_ok(nz):
                    warns.append(f"{key}：nameZh 非台灣標準字形（過渡批，待 patch_name_trad.py）：{nz} → {_TO_TRAD(nz)}")
                else:
                    errs.append(f"{key}：nameZh 非正體／非台灣標準字形：{nz} → {_TO_TRAD(nz)}")
        if "bioId" not in p:
            errs.append(f"{key}：缺 bioId 鍵（建議 6）")
        paras, poss, gaps = p.get("paragraphs", []), p.get("positions", []), p.get("gaps", [])
        st = stats[key] = {"paragraphs": len(paras), "positions": len(poss), "gaps": len(gaps), "citations": 0, "sources": set()}
        if not paras:
            warns.append(f"{key}：沒有段落（薄資料可接受 1 段＋待查證，0 段需在 gaps 說明）")
        ords = [x.get("ord") for x in paras]
        if len(set(ords)) != len(ords):
            errs.append(f"{key}：ord 重複")
        items = [(f"{key} 段{x.get('ord')}", x, x.get("period") or {}, x.get("periodStartPrecision"), x.get("periodEndPrecision")) for x in paras]
        items += [(f"{key} 職位 {x.get('key')}", x, x.get("period") or {}, x.get("startPrecision"), x.get("endPrecision")) for x in poss]
        for where, x, per, sp, ep in items:
            cits = x.get("citations") or []
            if not cits:
                errs.append(f"{where}：沒有 citation")
            if sp not in PREC or ep not in PREC:
                errs.append(f"{where}：精度值非法")
            if (per.get("start") is None) != (sp is None) or (per.get("end") is None) != (ep is None):
                errs.append(f"{where}：期間端點與精度不一致")
            if per.get("start") and per.get("end") and per["start"] >= per["end"]:
                errs.append(f"{where}：起 >= 迄")
            chk_bound(where, per.get("start"), sp, False)
            chk_bound(where, per.get("end"), ep, True)
            for i, c in enumerate(cits):
                qlens.append(chk_quote(f"{where} c{i}", c.get("sourceKey"), c.get("quote")))
                st["citations"] += 1; st["sources"].add(c.get("sourceKey"))
                if c.get("grade") not in OKG:
                    errs.append(f"{where} c{i}：段落／職位出處須 {'／'.join(OKG)}，實為 {c.get('grade')}（Q9）")
                if c.get("sourceKey") in srcs and c.get("grade") != srcs[c["sourceKey"]].get("grade"):
                    errs.append(f"{where} c{i}：grade 與來源不符")
                if c.get("datePrecision") not in PREC:
                    errs.append(f"{where} c{i}：datePrecision 非法")
                if not c.get("locator"):
                    errs.append(f"{where} c{i}：缺 locator")
                if not c.get("accessedOn"):
                    errs.append(f"{where} c{i}：缺 accessedOn")
                note = c.get("evidenceNote") or ""
                if "下一任" in note and "推論" not in note:
                    errs.append(f"{where} c{i}：以下一任起日推得的迄日須在 evidenceNote 標「推論」（Q7）")
        for x in paras:
            body = x.get("body") or {}
            zh, en = nfc_len(body.get("zh-Hant")), nfc_len(body.get("en"))
            if not zh:
                errs.append(f"{key} 段{x.get('ord')}：缺 zh-Hant 正文")
            if zh > 400:
                errs.append(f"{key} 段{x.get('ord')} zh-Hant 正文 {zh} 字 > 400（Q2）")
            if en > 800:
                errs.append(f"{key} 段{x.get('ord')} en 正文 {en} 字元 > 800（Q2）")
        if aligned:
            for x in poss:
                w = f"{key} 職位 {x.get('key')}"
                if "roleKind" in x:
                    errs.append(f"{w}：對齊檔不得再用 roleKind，須為 positionKind")
                if x.get("positionKind") in ROLE_LAYER_KINDS:
                    errs.append(f"{w}：經歷層不得含角色層值 {x.get('positionKind')}（兩層互斥）")
                if "originalPositionKind" in x and (x["originalPositionKind"] == x.get("positionKind")
                                                    or x["originalPositionKind"] not in ROLE_KINDS):
                    errs.append(f"{w}：originalPositionKind 須屬原值域且與 positionKind 不同")
                amb = x.get("t14Ambiguous")
                if "t14Ambiguous" in x and (amb is not True or not (x.get("t14AmbiguousReason") or "").strip()):
                    errs.append(f"{w}：t14Ambiguous 須為 true 且附 t14AmbiguousReason")
                r = x.get("t14Rule")
                if "t14Overlap" in x and r not in T14_RULES and amb is not True:
                    errs.append(f"{w}：t14Overlap 項須有 t14Rule（R0–R6）或標 t14Ambiguous")
                if r is not None and r not in T14_RULES:
                    errs.append(f"{w}：t14Rule 非法 {r}")
                if r in ROLE_RULES and amb is not True:
                    errs.append(f"{w}：t14Rule={r} 屬角色層，須移至 roleCandidates（兩層互斥）")
                if r and not (x.get("t14Reason") or "").strip():
                    errs.append(f"{w}：有 t14Rule 須附 t14Reason")
                if r == "R6":
                    if x.get("roleEligible") is not True or x.get("roleEligibleKind") not in ROLE_LAYER_KINDS - FORBIDDEN_ALIGNED \
                            or not x.get("roleGap"):
                        errs.append(f"{w}：R6 須 roleEligible=true、roleEligibleKind（閣員／將領／佔領殖民長官）、roleGap 非空")
                elif any(k in x for k in ("roleEligible", "roleEligibleKind", "roleGap")):
                    errs.append(f"{w}：非 R6 不得有 roleEligible／roleEligibleKind／roleGap")
                if x.get("positionKind") == "party" and x.get("partyPostAmbiguous") is not True:
                    errs.append(f"{w}：黨職須移至 roleCandidates（de_facto_leader），或標 partyPostAmbiguous")
                if "partyPostAmbiguous" in x and (x["partyPostAmbiguous"] is not True
                                                  or not (x.get("partyPostAmbiguousReason") or "").strip()):
                    errs.append(f"{w}：partyPostAmbiguous 須為 true 且附 partyPostAmbiguousReason")
                if "t14Overlap" in x and x["t14Overlap"] not in T14_VALUES:
                    errs.append(f"{w}：t14Overlap 非法 {x['t14Overlap']}")
            for x in p.get("roleCandidates") or []:
                w = f"{key} 候選角色 {x.get('key')}"
                if x.get("role_kind") not in CANDIDATE_KINDS:
                    errs.append(f"{w}：role_kind 非法或缺 {x.get('role_kind')}")
                for bad in ("roleKind", "candidateRoleKind"):
                    if bad in x:
                        errs.append(f"{w}：不得有 {bad}（統一為 role_kind）")
                if not (x.get("reason") or "").strip():
                    errs.append(f"{w}：缺 reason")
                if "t14Rule" in x and x["t14Rule"] not in ROLE_RULES:
                    errs.append(f"{w}：roleCandidates 的 t14Rule 須為 R0–R4，實為 {x['t14Rule']}")
                if "positionKind" in x or "roleEligible" in x:
                    errs.append(f"{w}：roleCandidates 不得有 positionKind／roleEligible（原值存 originalPositionKind）")
                cc = x.get("citations") or []
                if not cc:
                    errs.append(f"{w}：沒有 citation（出處）")
                for i, c in enumerate(cc):
                    chk_quote(f"{w} c{i}", c.get("sourceKey"), c.get("quote"))
                    if c.get("grade") not in OKG:
                        errs.append(f"{w} c{i}：grade 須 {'／'.join(OKG)}")
                    if c.get("sourceKey") in srcs and c.get("grade") != srcs[c["sourceKey"]].get("grade"):
                        errs.append(f"{w} c{i}：grade 與來源不符")
            st["roleCandidates"] = len(p.get("roleCandidates") or [])
        for x in poss:
            rk = x.get("positionKind") if aligned else x.get("roleKind")
            if rk in (FORBIDDEN_ALIGNED if aligned else FORBIDDEN_ROLES):
                errs.append(f"{key} 職位 {x.get('key')}：不得建元首／首腦職位（§16.3、Q4）")
            elif rk not in (ALIGNED_POSITION_KINDS if aligned else ROLE_KINDS):
                errs.append(f"{key} 職位 {x.get('key')}：role_kind 非法 {rk}")
            per = x.get("period") or {}
            if x.get("regimeId"):
                s, e = per.get("start"), per.get("end")
                if (s and s >= SCOPE_END) or (e and e <= SCOPE_START) or (not s and not e):
                    errs.append(f"{key} 職位 {x.get('key')}：regimeId 只可填於清楚落在 1908–1945 的職位（Q5）")
            elif not x.get("organization"):
                errs.append(f"{key} 職位 {x.get('key')}：regimeId 空時須填 organization（Q5）")
        for g in gaps:
            if not re.fullmatch(r"(field:\w+|position:[\w-]+|paragraph:[\w-]+|identity)", g.get("target", "")):
                errs.append(f"{key} gap target 格式：{g.get('target')}")
            if g.get("gapKind") not in GAP_KINDS:
                errs.append(f"{key} gap_kind 非法：{g.get('gapKind')}")
            for i, c in enumerate(g.get("candidateCitations") or []):
                chk_quote(f"{key} gap {g.get('target')} cand{i}", c.get("sourceKey"), c.get("quote"))
        st["sources"] = sorted(s for s in st["sources"] if s)
    qn = [n for n in qlens if n]
    rep = {"ok": not errs, "rawChecked": bool(raw), "errors": errs, "notes": warns, "people": stats,
           "quoteLen": {"n": len(qn), "max": max(qn) if qn else 0, "min": min(qn) if qn else 0}, "rawFiles": hashes}
    if report_path:
        Path(report_path).write_text(json.dumps(rep, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({k: rep[k] for k in ("ok", "rawChecked", "errors", "quoteLen")}, ensure_ascii=False, indent=1))
    for k, v in stats.items():
        print(k, v["paragraphs"], "段", v["positions"], "職位", v["gaps"], "缺漏", v["citations"], "引用")
    sys.exit(0 if not errs else 1)


main()
