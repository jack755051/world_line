#!/usr/bin/env python3
"""為 Opus 審查產生短證據包：每筆 claim 的段落文字、quote、sourceKey、verify 結果。

逐字是否出現用 verify.py 的 quote_hit（同一套空白正規化），不把原文印出來。

    python3 -I tools/b3v3/evidence_pack.py OUT/research.json --out OUT/evidence-pack.json
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
VERIFY_PATH = REPO / "data" / "seed" / "leaders" / "b3-trial" / "verify.py"


def load_verify():
    spec = importlib.util.spec_from_file_location("b3_verify", VERIFY_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def claim_text(kind, obj):
    if kind == "paragraph":
        return ((obj.get("body") or {}).get("zh-Hant")) or ""
    if kind == "gap":
        return obj.get("note") or ""
    title = obj.get("title") or {}
    if isinstance(title, dict):
        title_text = title.get("zh-Hant") or title.get("orig") or ""
    else:
        title_text = str(title)
    org = obj.get("organization") or {}
    org_text = org.get("zh-Hant") if isinstance(org, dict) else ""
    period = obj.get("period") or {}
    span = f"{period.get('start') or ''}–{period.get('end') or ''}"
    return " ".join(part for part in (title_text, org_text, span) if part)


def iter_citations(person):
    for para in person.get("paragraphs") or []:
        text = claim_text("paragraph", para)
        where = f"段{para.get('ord')}"
        for index, cite in enumerate(para.get("citations") or []):
            yield where, index, text, cite
    for kind, items in (("職位", person.get("positions") or []), ("候選角色", person.get("roleCandidates") or [])):
        for item in items:
            text = claim_text(kind, item)
            where = f"{kind} {item.get('key')}"
            for index, cite in enumerate(item.get("citations") or []):
                yield where, index, text, cite
    for gap in person.get("gaps") or []:
        text = claim_text("gap", gap)
        where = f"gap {gap.get('target')}"
        for index, cite in enumerate(gap.get("candidateCitations") or []):
            yield where, index, text, cite


def clip(text, limit=500):
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


def build(research_path, text_limit=500):
    verify = load_verify()
    research_path = Path(research_path)
    data = json.loads(research_path.read_text(encoding="utf-8"))
    texts = {}
    missing = set()
    raw_dir = data.get("rawDir")
    raw_map_name = data.get("rawMap")
    if raw_dir and raw_map_name:
        raw_map_path = research_path.parent / raw_map_name
        if raw_map_path.exists():
            raw_map = json.loads(raw_map_path.read_text(encoding="utf-8"))
            loaded, _hashes, absent = verify.load_raw_texts(raw_dir, raw_map)
            texts = loaded
            missing = {key for key, _path in absent}
    claims = []
    failed = []
    for person in data.get("people") or []:
        for where, index, text, cite in iter_citations(person):
            source_key = cite.get("sourceKey")
            quote = cite.get("quote")
            if source_key not in texts:
                reason = "原文檔不存在" if source_key in missing else "沒有載入此 sourceKey 的原文"
                result = {"ok": False, "reason": reason}
            else:
                offset = verify.quote_hit(texts[source_key], quote)
                result = {"ok": offset is not None, "normOffset": offset}
                if offset is None:
                    result["reason"] = "引文未逐字出現"
            claim = {
                "personKey": person.get("key"),
                "personName": person.get("name"),
                "where": f"{where} c{index}",
                "text": clip(text, text_limit),
                "quote": quote,
                "sourceKey": source_key,
                "grade": cite.get("grade"),
                "verify": result,
            }
            if not result["ok"]:
                failed.append(len(claims))
            claims.append(claim)
    verify_report = None
    report_path = research_path.parent / "verify-report.json"
    if report_path.exists():
        try:
            loaded = json.loads(report_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            loaded = None
        if isinstance(loaded, dict):
            quote_len = loaded.get("quoteLen") or {}
            verify_report = {
                "ok": loaded.get("ok"),
                "rawChecked": loaded.get("rawChecked"),
                "errorCount": len(loaded.get("errors") or []),
                "quoteMax": quote_len.get("max"),
            }
    return {
        "batch": data.get("batch"),
        "generatedBy": "tools/b3v3/evidence_pack.py",
        "quoteCheck": "verify.py quote_hit（NFC、連續空白壓成一個空白後的子字串；normOffset 在正規化後的原文）",
        "verifyReport": verify_report,
        "claimCount": len(claims),
        "failedClaimIndexes": failed,
        "claims": claims,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="產生審查用的短證據包")
    parser.add_argument("research")
    parser.add_argument("--out")
    parser.add_argument("--text-limit", type=int, default=500)
    args = parser.parse_args(argv)
    pack = build(args.research, args.text_limit)
    out = Path(args.out) if args.out else Path(args.research).parent / "evidence-pack.json"
    out.write_text(json.dumps(pack, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(
        f"evidence {out} claims={pack['claimCount']} failed={len(pack['failedClaimIndexes'])} "
        f"verifyOk={None if not pack['verifyReport'] else pack['verifyReport'].get('ok')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
