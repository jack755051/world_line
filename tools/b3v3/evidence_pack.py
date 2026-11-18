#!/usr/bin/env python3
"""為審查產生短證據包。

每個主張單位（段落、職位、候選角色、gap；iter_citations 的 where）只寫一次 text，
其下 citations 逐筆含 index、quote、sourceKey、grade、verify。
claimCount 是單位數，citationCount 是引文數。failedClaimIndexes 是有任一引文
verify.ok 不為真的單位，在 claims 裡的索引。
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


def iter_units(person):
    """有引文的主張單位。沒有引文的段落／職位／候選／gap 不出現（與舊的逐筆展開相同）。"""
    for para in person.get("paragraphs") or []:
        cites = para.get("citations") or []
        if cites:
            yield f"段{para.get('ord')}", claim_text("paragraph", para), cites
    for kind, items in (("職位", person.get("positions") or []), ("候選角色", person.get("roleCandidates") or [])):
        for item in items:
            cites = item.get("citations") or []
            if cites:
                yield f"{kind} {item.get('key')}", claim_text(kind, item), cites
    for gap in person.get("gaps") or []:
        cites = gap.get("candidateCitations") or []
        if cites:
            yield f"gap {gap.get('target')}", claim_text("gap", gap), cites


def unit_paths(person, prefix="person"):
    """每個段落／職位／候選角色／gap 在單人檔裡的路徑，給審查用 person_patch.py 局部修改。"""
    out = []
    for index, para in enumerate(person.get("paragraphs") or []):
        out.append({"where": f"段{para.get('ord')}", "path": f"{prefix}.paragraphs[{index}]"})
    for kind, field in (("職位", "positions"), ("候選角色", "roleCandidates")):
        for index, item in enumerate(person.get(field) or []):
            out.append({"where": f"{kind} {item.get('key')}", "path": f"{prefix}.{field}[{index}]"})
    for index, gap in enumerate(person.get("gaps") or []):
        out.append({"where": f"gap {gap.get('target')}", "path": f"{prefix}.gaps[{index}]"})
    return out


def iter_citations(person):
    for where, text, cites in iter_units(person):
        for index, cite in enumerate(cites):
            yield where, index, text, cite


def clip(text, limit=500):
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


def verify_one(verify, texts, missing, cite, index):
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
    return {
        "index": index,
        "quote": quote,
        "sourceKey": source_key,
        "grade": cite.get("grade"),
        "verify": result,
    }


def unit_failed(claim):
    return any(not (cite.get("verify") or {}).get("ok") for cite in claim.get("citations") or [])


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
    citation_count = 0
    for person in data.get("people") or []:
        for where, text, cites in iter_units(person):
            citations = []
            for index, cite in enumerate(cites):
                citations.append(verify_one(verify, texts, missing, cite, index))
                citation_count += 1
            claim = {
                "personKey": person.get("key"),
                "personName": person.get("name"),
                "where": where,
                "text": clip(text, text_limit),
                "citations": citations,
            }
            if unit_failed(claim):
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
        "citationCount": citation_count,
        "failedClaimIndexes": failed,
        "claims": claims,
    }


def slice_person(pack, person_key):
    """只留一個人的主張單位，供審查 agent 讀，不要把整批證據包送進上下文。"""
    claims = [claim for claim in pack.get("claims") or [] if claim.get("personKey") == person_key]
    citation_count = sum(len(claim.get("citations") or []) for claim in claims)
    sliced = dict(pack)
    sliced["personKey"] = person_key
    sliced["claims"] = claims
    sliced["claimCount"] = len(claims)
    sliced["citationCount"] = citation_count
    sliced["failedClaimIndexes"] = [index for index, claim in enumerate(claims) if unit_failed(claim)]
    return sliced


def main(argv=None):
    parser = argparse.ArgumentParser(description="產生審查用的短證據包")
    parser.add_argument("research")
    parser.add_argument("--out")
    parser.add_argument("--text-limit", type=int, default=500)
    parser.add_argument("--person", help="只寫這個人的切片（person.key；找不到時改對 bioId）")
    args = parser.parse_args(argv)
    pack = build(args.research, args.text_limit)
    if args.person:
        sliced = slice_person(pack, args.person)
        if not sliced["claims"]:
            data = json.loads(Path(args.research).read_text(encoding="utf-8"))
            key = next(
                (person.get("key") for person in data.get("people") or [] if person.get("bioId") == args.person),
                None,
            )
            if key:
                sliced = slice_person(pack, key)
        pack = sliced
    out = Path(args.out) if args.out else Path(args.research).parent / "evidence-pack.json"
    out.write_text(json.dumps(pack, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(
        f"evidence {out} claims={pack['claimCount']} citations={pack['citationCount']} "
        f"failed={len(pack['failedClaimIndexes'])} "
        f"verifyOk={None if not pack['verifyReport'] else pack['verifyReport'].get('ok')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
