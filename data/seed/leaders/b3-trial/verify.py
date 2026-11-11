"""B3 試跑離線檢查（不連任何資料庫、不連網）。以 ../b3-sample/verify.py 為底，加上 Tai 2026-11-11 09:35 定案（ARCHITECTURE §16.3.2）。

用法：python3 -I verify.py batchNN/research.json [--raw RAW_DIR RAWMAP.json] [--report out.json]
- 有 --raw：引文須空白正規化後逐字出現在研究當天抓下的原文（RAW_DIR 內純文字檔；RAWMAP：sourceKey → 檔名）。
  原文不進版控（著作權），報告只記 sha256。沒有 --raw 時只做格式檢查，報告標 rawChecked=false。
- 若 research.json 頂層有 "rawDir"、"rawMap" 且未給 --raw，會自動採用（rawMap 為相對 research.json 的路徑）。
檢查：
 1. 引文 NFC ≤ 80 字元（§16.4.1）；非空；（有原文時）逐字出現。
 2. 每段落、每職位至少 1 筆 citation（§16.1-3）；段落／職位 citation 的 grade 必須是 A 或 B，且與來源一致（Q9：未評等來源只可出現在 gaps 候選）。
 3. 來源網域不在硬性排除清單（含任何 wikipedia／wikidata／百度）；citation 的 sourceKey 必須存在於頂層 sources（建議 5）。
 4. Q2：段落中文 ≤ 400 字、英文 ≤ 800 字元（NFC code point）。ord 唯一；period 起 < 迄。
 5. Q3：month／year 精度的端點必須是該單位的起日（YYYY-MM-01／YYYY-01-01）。
 6. 職位 roleKind 不得為元首／首腦（Q4：範圍外元首任期只寫正文；元首／首腦任期只在 leader_records）；值域照 §16.3 提案。
 7. Q5：regimeId 非空時，職位期間必須與 1908-01-01～1945-10-01 有交集；regimeId 為空時須有 organization。
 8. Q7：evidenceNote 提到「下一任」者，必須同時含「推論」。
 9. gaps：target 格式、gap_kind 三值（§16.4.2）。
10. 每人必須有 bioId 鍵（建議 6；值可為 null）。
"""
import hashlib, json, re, sys, unicodedata
from pathlib import Path
from urllib.parse import urlparse

EXCLUDED_HOSTS = ("wikipedia.org", "wikidata.org", "wikimedia.org", "baidu.com", "enciclopediadelecuador.com")
ROLE_KINDS = {"minister", "legislator", "military_command", "party", "diplomat", "judicial", "other"}
FORBIDDEN_ROLES = {"head_of_state", "head_of_government"}
GAP_KINDS = {"conflict", "not_found", "identity_uncertain"}
PREC = {None, "day", "month", "year"}
SCOPE_START, SCOPE_END = "1908-01-01", "1945-10-01"


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
    for k, s in srcs.items():
        for u in (s.get("url"), s.get("archive_url")):
            host = (urlparse(u).hostname or "") if u else ""
            if any(host == h or host.endswith("." + h) for h in EXCLUDED_HOSTS):
                errs.append(f"來源 {k} 網域被排除：{host}")
        if s.get("grade") not in (None, "A", "B"):
            errs.append(f"來源 {k} grade 非法：{s.get('grade')}")
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

    people = data.get("people") or []
    if not people:
        errs.append("people 為空")
    for p in people:
        key = p.get("key", "?")
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
                if c.get("grade") not in ("A", "B"):
                    errs.append(f"{where} c{i}：段落／職位出處須 A 或 B，實為 {c.get('grade')}（Q9）")
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
        for x in poss:
            rk = x.get("roleKind")
            if rk in FORBIDDEN_ROLES:
                errs.append(f"{key} 職位 {x.get('key')}：不得建元首／首腦職位（§16.3、Q4）")
            elif rk not in ROLE_KINDS:
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
