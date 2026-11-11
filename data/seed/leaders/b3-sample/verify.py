"""B3 樣本離線檢查（不連任何資料庫、不連網）。

用法：python3 -I verify.py research.json RAW_DIR RAWMAP.json [--report out.json]
- RAW_DIR：研究當天以 curl（未用 -k）抓下的頁面轉純文字檔；RAWMAP：sourceKey → 檔名。
  原始頁面不進版控（著作權），報告只記各檔 sha256。
檢查：
 1. 引文 NFC 後 ≤ 80 字元（§16.4.1）；空白正規化後逐字出現在該來源原文（含 gaps 候選引文）。
 2. 每段落、每職位至少 1 筆 citation（§16.1-3）；段落／職位 citation 的 grade 必須是 A 或 B（未評等來源只能出現在 gaps 候選）。
 3. 來源網域不在硬性排除清單（同 BioSourcePolicy bio-2026-11-v0）。
 4. 段落中文正文 ≤ 400 字（§16.2；英文計法未定義，只記錄字元數與詞數）；ord 唯一；period 起 < 迄。
 5. role_kind 不得為元首／首腦，且屬 §16.3 提案值域。
 6. gaps：target 格式、gap_kind 三值（§16.4.2）。
"""
import hashlib, json, re, sys, unicodedata
from urllib.parse import urlparse

EXCLUDED_HOSTS = ("wikipedia.org", "wikidata.org", "baidu.com", "enciclopediadelecuador.com")
ROLE_KINDS = {"minister", "legislator", "military_command", "party", "diplomat", "judicial", "other"}
GAP_KINDS = {"conflict", "not_found", "identity_uncertain"}
PREC = {None, "day", "month", "year"}


def norm(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s)).strip()


def nfc_len(s):
    return len(unicodedata.normalize("NFC", s))


def main():
    data = json.load(open(sys.argv[1]))
    raw_dir, rawmap = sys.argv[2], json.load(open(sys.argv[3]))
    report_path = sys.argv[sys.argv.index("--report") + 1] if "--report" in sys.argv else None
    texts, hashes = {}, {}
    for k, f in rawmap.items():
        b = open(f"{raw_dir}/{f}", "rb").read()
        texts[k] = norm(b.decode("utf-8"))
        hashes[k] = {"file": f, "sha256": hashlib.sha256(b).hexdigest()}
    errs, warns, stats = [], [], {}
    srcs = data["sources"]
    for k, s in srcs.items():
        host = (urlparse(s["url"]).hostname or "") if s.get("url") else ""
        if any(host == h or host.endswith("." + h) for h in EXCLUDED_HOSTS):
            errs.append(f"來源 {k} 網域被排除：{host}")
        if s["grade"] not in (None, "A", "B"):
            errs.append(f"來源 {k} grade 非法：{s['grade']}")

    def chk_quote(where, sk, q):
        if sk not in srcs:
            errs.append(f"{where}：未知來源 {sk}"); return
        n = nfc_len(q)
        if n > 80:
            errs.append(f"{where}：引文 {n} 字 > 80：{q}")
        if norm(q) not in texts[sk]:
            errs.append(f"{where}：引文未逐字出現於 {sk}：{q}")
        return n

    qlens = []
    for p in data["people"]:
        key = p["key"]
        st = stats[key] = {"paragraphs": len(p["paragraphs"]), "positions": len(p["positions"]), "gaps": len(p["gaps"]), "citations": 0, "sources": set()}
        ords = [x["ord"] for x in p["paragraphs"]]
        if len(set(ords)) != len(ords):
            errs.append(f"{key}：ord 重複")
        items = [(f"{key} 段{x['ord']}", x, x["period"], x["periodStartPrecision"], x["periodEndPrecision"]) for x in p["paragraphs"]]
        items += [(f"{key} 職位 {x['key']}", x, x["period"], x["startPrecision"], x["endPrecision"]) for x in p["positions"]]
        for where, x, per, sp, ep in items:
            if not x["citations"]:
                errs.append(f"{where}：沒有 citation")
            if sp not in PREC or ep not in PREC:
                errs.append(f"{where}：精度值非法")
            if (per["start"] is None) != (sp is None) or (per["end"] is None) != (ep is None):
                errs.append(f"{where}：期間端點與精度不一致")
            if per["start"] and per["end"] and per["start"] > per["end"]:
                errs.append(f"{where}：起 > 迄")
            for i, c in enumerate(x["citations"]):
                n = chk_quote(f"{where} c{i}", c["sourceKey"], c["quote"])
                qlens.append(n or 0)
                st["citations"] += 1; st["sources"].add(c["sourceKey"])
                if c["grade"] not in ("A", "B"):
                    errs.append(f"{where} c{i}：段落／職位出處須 A 或 B，實為 {c['grade']}")
                if c["grade"] != srcs[c["sourceKey"]]["grade"]:
                    errs.append(f"{where} c{i}：grade 與來源不符")
                if c["datePrecision"] not in PREC:
                    errs.append(f"{where} c{i}：datePrecision 非法")
        for x in p["paragraphs"]:
            n = nfc_len(x["body"]["zh-Hant"])
            if n > 400:
                errs.append(f"{key} 段{x['ord']} zh-Hant 正文 {n} 字 > 400")
            # §16.2 的「400 字」未定義英文怎麼計（字元或詞）：英文只記錄、不判錯（待決問題 Q）
            warns.append(f"{key} 段{x['ord']} en 正文 {nfc_len(x['body']['en'])} 字元／{len(x['body']['en'].split())} 詞")
        for x in p["positions"]:
            if x["roleKind"] not in ROLE_KINDS:
                errs.append(f"{key} 職位 {x['key']}：role_kind 非法 {x['roleKind']}")
        for g in p["gaps"]:
            if not re.fullmatch(r"(field:\w+|position:[\w-]+|paragraph:[\w-]+|identity)", g["target"]):
                errs.append(f"{key} gap target 格式：{g['target']}")
            if g["gapKind"] not in GAP_KINDS:
                errs.append(f"{key} gap_kind 非法：{g['gapKind']}")
            for i, c in enumerate(g["candidateCitations"]):
                chk_quote(f"{key} gap {g['target']} cand{i}", c["sourceKey"], c["quote"])
        st["sources"] = sorted(st["sources"])
    rep = {"ok": not errs, "errors": errs, "notes": warns, "people": stats, "quoteLen": {"n": len(qlens), "max": max(qlens), "min": min(qlens)}, "rawFiles": hashes}
    if report_path:
        json.dump(rep, open(report_path, "w"), ensure_ascii=False, indent=1)
    print(json.dumps({k: rep[k] for k in ("ok", "errors", "quoteLen")}, ensure_ascii=False, indent=1))
    for k, v in stats.items():
        print(k, v["paragraphs"], "段", v["positions"], "職位", v["gaps"], "缺漏", v["citations"], "引用")
    sys.exit(0 if not errs else 1)


main()
