#!/usr/bin/env python3
"""主段落的「沒有出處的子句」檢查（審查之後跑；Tai 2026-11-18）。

每段 zh-Hant 正文依「。！？；」切句，句號從 1 起算。citation 的 claimSpan 寫它支撐哪幾句（整數清單，例 [1, 2]），
也可寫正文裡的一段字串。找不到任何 citation 支撐的句子就是「沒有出處」。
舊資料沒有 claimSpan 時：只有一句的段落算有出處；句中的年份（或「M月D日」）都出現在該段 quote 裡的句子算有出處；
其餘列為沒有出處（待對應，交給 Sonnet 補 claimSpan 或刪句）。

    python3 -I tools/b3v3/uncited.py check --file people/<bioId>.json            # 印 UNCITED 行，exit 0
    python3 -I tools/b3v3/uncited.py map --file F --json '{"1":{"0":[1,2]},"drop":{"2":[3]}}'
        # 段 ord → citation 索引 → 句號；drop：段 ord → 要刪的句號（zh 與 en 同句數時一起刪）
    python3 -I tools/b3v3/uncited.py finalize --file F    # 仍沒有出處的句子：中英句數相同就刪，否則保留並標 待補；都寫 gap
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

ZH_SPLIT = re.compile(r"(?<=[。！？；])")
EN_SPLIT = re.compile(r"(?<=[.!?;])\s+(?=[A-Z0-9\"“‘(])")
YEAR = re.compile(r"(?<!\d)(1[5-9]\d\d|20[0-4]\d)(?!\d)")
MONTH_DAY = re.compile(r"(?<!\d)(\d{1,2})月(\d{1,2})日")
PENDING = "待補"


def nfc(text):
    return unicodedata.normalize("NFC", text or "")


def zh_sentences(text):
    return [part for part in (s.strip() for s in ZH_SPLIT.split(nfc(text))) if part]


def en_sentences(text):
    return [part for part in (s.strip() for s in EN_SPLIT.split(nfc(text).strip())) if part]


def _span_hits(span, sentences):
    if isinstance(span, int):
        span = [span]
    hits = set()
    if isinstance(span, list):
        for item in span:
            if isinstance(item, int) and 1 <= item <= len(sentences):
                hits.add(item)
            elif isinstance(item, str):
                hits |= _span_hits(item, sentences)
    elif isinstance(span, str) and span.strip():
        frag = nfc(span).strip()
        for index, sent in enumerate(sentences, 1):
            if frag in sent or sent.rstrip("。！？；") in frag:
                hits.add(index)
    return hits


def paragraph_status(para):
    """回傳 (句子清單, {句號: 'span'|'single'|'year'|None})。None＝沒有出處。"""
    body = para.get("body") or {}
    sentences = zh_sentences(body.get("zh-Hant"))
    cites = [c for c in para.get("citations") or [] if (c.get("quote") or "").strip()]
    status = {index: None for index in range(1, len(sentences) + 1)}
    for cite in cites:
        for index in _span_hits(cite.get("claimSpan"), sentences):
            status[index] = "span"
    # 舊資料的推定（逐句後備）：有沒有 claimSpan 都適用，免得補掛一句之後，其他原本算有出處的句子反而被刪
    if True:
        if len(sentences) == 1 and cites:
            status[1] = status[1] or "single"
        else:
            quote_years, quote_days = set(), set()
            for cite in cites:
                quote_years |= set(YEAR.findall(nfc(cite.get("quote"))))
                quote_days |= set(MONTH_DAY.findall(nfc(cite.get("quote"))))
            for index, sent in enumerate(sentences, 1):
                years = set(YEAR.findall(sent))
                days = set(MONTH_DAY.findall(sent))
                if status[index] is None and ((years and years <= quote_years) or (days and days <= quote_days)):
                    status[index] = "year"
    return sentences, status


def find_uncited(person):
    """每段沒有出處的句子：[{ord, s, zh, mapped}]。mapped=False 表示整段都沒有 claimSpan（舊資料）。"""
    out = []
    for para in person.get("paragraphs") or []:
        sentences, status = paragraph_status(para)
        mapped = any(c.get("claimSpan") not in (None, "", []) for c in para.get("citations") or [])
        for index, sent in enumerate(sentences, 1):
            if status[index] is None:
                out.append({"ord": para.get("ord"), "s": index, "zh": sent, "mapped": mapped})
    return out


def load(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data, (data.get("person") if isinstance(data.get("person"), dict) else data)


def save(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def _para(person, ord_value):
    for para in person.get("paragraphs") or []:
        if str(para.get("ord")) == str(ord_value):
            return para
    raise SystemExit(f"沒有段 {ord_value}")


def drop_sentences(para, numbers):
    """刪 zh 第 n 句；en 句數相同時刪同一句，不同時 en 不動並回傳 False（呼叫端要標 待補）。"""
    body = dict(para.get("body") or {})
    zh = zh_sentences(body.get("zh-Hant"))
    en = en_sentences(body.get("en"))
    numbers = sorted({n for n in numbers if 1 <= n <= len(zh)}, reverse=True)
    if not numbers:
        return True, []
    same = len(zh) == len(en)
    if not same:
        return False, []
    removed = []
    for n in numbers:
        removed.append(zh.pop(n - 1))
        en.pop(n - 1)
    body["zh-Hant"] = "".join(zh)
    body["en"] = " ".join(en)
    para["body"] = body
    # 句號往前移：重算 claimSpan 整數
    for cite in para.get("citations") or []:
        span = cite.get("claimSpan")
        if isinstance(span, list):
            new = []
            for item in span:
                if isinstance(item, int):
                    if item in numbers:
                        continue
                    item -= sum(1 for n in numbers if n < item)
                new.append(item)
            cite["claimSpan"] = new
    return True, removed


def add_gap(person, ord_value, sentence, removed):
    gaps = person.setdefault("gaps", [])
    note = f"{PENDING}引文：{'已刪除' if removed else '保留待補'}「{sentence[:60]}」"
    target = f"paragraph:{ord_value}"
    if not any(g.get("target") == target and g.get("note") == note for g in gaps):
        gaps.append({"target": target, "gapKind": "not_found", "note": note, "candidateCitations": []})


def cmd_check(path):
    _data, person = load(path)
    items = find_uncited(person)
    print(f"UNCITED {len(items)}")
    for item in items[:30]:
        print(f"- 段{item['ord']} 句{item['s']}{'' if item['mapped'] else '（整段沒有 claimSpan）'}：{item['zh'][:80]}")
    return 0


def cmd_map(path, spec):
    data, person = load(path)
    try:
        plan = json.loads(spec)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"--json 不是合法 JSON：{exc}")
    drops = plan.pop("drop", {}) or {}
    for ord_value, cites in plan.items():
        para = _para(person, ord_value)
        for index, span in (cites or {}).items():
            cite_list = para.get("citations") or []
            i = int(index)
            if not 0 <= i < len(cite_list):
                raise SystemExit(f"段{ord_value} 沒有 citation {i}")
            cite_list[i]["claimSpan"] = sorted({int(n) for n in (span if isinstance(span, list) else [span])})
    for ord_value, numbers in drops.items():
        para = _para(person, ord_value)
        sentences = zh_sentences((para.get("body") or {}).get("zh-Hant"))
        ok, removed = drop_sentences(para, [int(n) for n in numbers])
        if not ok:
            for n in numbers:
                if 1 <= int(n) <= len(sentences):
                    para.setdefault("pendingCitation", []).append({"s": int(n), "zh": sentences[int(n) - 1], "status": PENDING})
                    add_gap(person, ord_value, sentences[int(n) - 1], False)
        for sent in removed:
            add_gap(person, ord_value, sent, True)
    save(path, data)
    return cmd_check(path)


def finalize(person):
    """仍沒有出處的句子：能安全刪（中英句數相同）就刪，否則留著標 待補。回傳 (刪, 標)。"""
    removed_n = marked_n = 0
    by_ord = {}
    for item in find_uncited(person):
        by_ord.setdefault(item["ord"], []).append(item)
    for ord_value, items in by_ord.items():
        para = _para(person, ord_value)
        sentences = {item["s"]: item["zh"] for item in items}
        ok, removed = drop_sentences(para, list(sentences))
        if ok and removed:
            removed_n += len(removed)
            for sent in removed:
                add_gap(person, ord_value, sent, True)
        else:
            pend = para.setdefault("pendingCitation", [])
            for n, sent in sentences.items():
                if not any(p.get("zh") == sent for p in pend):
                    pend.append({"s": n, "zh": sent, "status": PENDING})
                add_gap(person, ord_value, sent, False)
                marked_n += 1
    # 刪光的段落不留空殼
    person["paragraphs"] = [p for p in person.get("paragraphs") or [] if zh_sentences((p.get("body") or {}).get("zh-Hant"))]
    return removed_n, marked_n


def cmd_finalize(path):
    data, person = load(path)
    removed, marked = finalize(person)
    save(path, data)
    print(f"FINALIZE 刪除 {removed} 句，標待補 {marked} 句")
    return cmd_check(path)


def main(argv=None):
    parser = argparse.ArgumentParser(description="主段落沒有出處的子句")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("check", "map", "finalize"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--file", required=True)
        if name == "map":
            cmd.add_argument("--json", required=True)
    args = parser.parse_args(argv)
    if args.cmd == "check":
        return cmd_check(args.file)
    if args.cmd == "map":
        return cmd_map(args.file, args.json)
    return cmd_finalize(args.file)


if __name__ == "__main__":
    raise SystemExit(main())
