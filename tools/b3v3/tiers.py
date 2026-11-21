#!/usr/bin/env python3
"""B3 v3 分層補查（Tai 2026-11-18）。

第一階段：既有便宜流程（run_loop.py），只收 A／B。
第二階段：第一階段後仍「篇幅不足」或有缺迄日（含已標「待查證：缺迄日」）的人，做一次較大的 A／B 補查：
  Python 用索引上的原文姓名重新預查（日本人另試 コトバンク、首相官邸），Sonnet 再 WebSearch 3–5 次
  （日本人試 JACAR、NDL、コトバンク、首相官邸），寫 <bioId>.stage2.json，由 Python 套到單人檔。
第三階段：第二階段仍不足才用 C（Wikipedia 等）。Python 抓 Wikipedia 條目、挑段落；Sonnet 只寫
  <bioId>.supplementC.json，Python 組成 person.supplementC（grade C、每條附網址）。主段落永遠不引 C；
  verify 與 check_min 的達標只算 A／B；C 日期一律「待查證」。之後 A／B 找到同一欄位就刪掉對應的 C（prune）。
審查：Sonnet（6 輪）。審查後 Python 檢查主段落沒有出處的句子（uncited.py）；有才給 Sonnet 1–2 輪補 claimSpan 或刪句，
  剩下的中英句數相同就刪，否則標 待補。

試跑都在工作目錄（預設 .dev/b3v3/run/tiers/batchNNN），不改正式批次的 research.json。

    python3 -I tools/b3v3/tiers.py candidates [--json]                # 列出要進第二階段的人（含 source-reeval-chunk4.json）
    python3 -I tools/b3v3/tiers.py run --people 123:<bioId>,109:<bioId> [--work-root …] [--log-dir …] [--no-c]
    python3 -I tools/b3v3/tiers.py check --spec SPEC --id ID [--done]  # agent 用：套用草稿、跑 verify／check_min
    python3 -I tools/b3v3/tiers.py prune --file people/<bioId>.json     # A／B 已補上的欄位刪掉對應的 C
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import re
import unicodedata
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote, urlparse

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT_ROOT = REPO / "data" / "seed" / "leaders" / "b3-trial" / "full" / "v3"
RAW_ROOT = Path.home() / "wl-source-cache" / "b3full-v3"
PROMPT_DIR = REPO / ".dev" / "b3v3" / "prompts"
REEVAL = REPO / ".dev" / "b3v3" / "source-reeval-chunk4.json"
WORK_ROOT = REPO / ".dev" / "b3v3" / "run" / "tiers"
C_STATUS = "A/B不足，已用C補"
C_DISPLAY_FLAG = "未查證・維基百科補充"
C_WIKI_LANGS = ("en", "ja", "zh", "de", "fr", "it", "ru", "pl", "pt", "es", "ka", "fi", "sv", "da", "is")
MIN_CHARS = 300


def _load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


draft = _load("person_draft")
merge = _load("merge_people")
plan = _load("plan_work")
pre = _load("prefilter")
specs = _load("agent_specs")
uncited = _load("uncited")
evidence = _load("evidence_pack")
_cr_spec = importlib.util.spec_from_file_location("c_rules", REPO / "tools" / "c_rules.py")
cr = importlib.util.module_from_spec(_cr_spec)
_cr_spec.loader.exec_module(cr)   # A／B 為準、引文支撐（verify.py 共用）
fetch_source = pre.fetch_source


def dump(data):
    return json.dumps(data, ensure_ascii=False, indent=1) + "\n"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ---------------------------------------------------------------- 候選名單

def needs_of(row):
    """第二階段要補什麼：篇幅、缺迄日（含已標待查證）、缺起日。空清單＝不需要。"""
    needs = []
    if row.get("paragraphs", 0) < 3 or row.get("zhChars", 0) < MIN_CHARS:
        needs.append(f"篇幅（現 {row.get('paragraphs')} 段／{row.get('zhChars')} 字，目標 3 段／300 字）")
    for term in row.get("openTerms") or []:
        needs.append(f"{term['kind']}:{term['key']}.{term['missing']}" + ("（已標待查證）" if term.get("flagged") else ""))
    return needs


def stage2_needs(needs):
    """第二階段的條件只有兩個：篇幅不足、缺迄日（2026-11-18 收窄；不再看搜尋紀錄有沒有 403，缺起日也不算）。"""
    return [n for n in needs if n.startswith("篇幅") or ".end" in n.split("（")[0]]


def need_category(needs):
    """候選分類：篇幅不足（只有篇幅）／只缺迄日／兩者。依實際段數字數與缺的迄日算，不看 check_min 的 verdict 字樣。"""
    short = any(n.startswith("篇幅") for n in needs)
    end = any(".end" in n.split("（")[0] for n in needs)
    return "兩者" if short and end else "篇幅不足" if short else "只缺迄日" if end else None


def skips_stage2(args, needs):
    """--skip-stage2-end-only：篇幅已夠、只缺迄日的人不跑第二階段（pilot5 6／6 這類人第二階段沒找到 A／B 迄日）。"""
    return bool(getattr(args, "skip_stage2_end_only", False)) and need_category(stage2_needs(needs)) == "只缺迄日"


def fetch_failures(person, sources):
    """這個人的來源有抓不到的頁（403／挑戰頁／錯誤）。"""
    bad = [e for e in person.get("searchLog") or [] if e.get("result") in ("blocked_403", "challenge_page")]
    return len(bad)


def candidates(out_root=OUT_ROOT, reeval=REEVAL):
    check_min = plan.load_check_min()
    rows = []
    for research in sorted(Path(out_root).glob("batch*/research.json")):
        nn = research.parent.name.replace("batch", "")
        try:
            data = load(research)
        except json.JSONDecodeError:
            continue
        report = check_min.report_for(data)
        by_key = {r["key"]: r for r in report["people"]}
        for person in data.get("people") or []:
            row = by_key.get(person.get("key")) or {}
            needs = stage2_needs(needs_of(row))
            if not needs:
                continue
            rows.append({
                "batch": nn, "bioId": person.get("bioId"), "key": person.get("key"), "name": person.get("name"),
                "verdict": row.get("verdict"), "category": need_category(needs), "needs": needs,
                "fetchFailures": fetch_failures(person, data.get("sources") or {}),
                "reeval": False,
            })
    if Path(reeval).exists():
        listed = {p["bioId"]: p for p in load(reeval).get("people") or []}
        for row in rows:
            if row["bioId"] in listed:
                row["reeval"] = True
        known = {row["bioId"] for row in rows}
        for bio, item in listed.items():
            if bio not in known:
                ends = [m["field"] for m in item.get("missingEnds") or [] if ".end" in str(m.get("field"))]
                if ends:
                    rows.append({"batch": item["batch"], "bioId": bio, "key": item["key"], "name": item["name"],
                                 "verdict": "（reeval 名單）", "category": need_category(ends), "needs": ends,
                                 "fetchFailures": 0, "reeval": True})
    return rows


def done_bios(paths):
    """已跑過分層補查的人（tiers results.json 裡的 bioId）。"""
    out = set()
    for path in paths or []:
        try:
            out |= {r.get("bioId") for r in load(path) if r.get("bioId")}
        except (OSError, json.JSONDecodeError):
            continue
    return out


def cmd_candidates(args):
    rows = candidates(Path(args.out_root), Path(args.reeval))
    done = done_bios([x for x in (args.exclude_results or "").split(",") if x])
    excluded = [r for r in rows if r["bioId"] in done]
    rows = [r for r in rows if r["bioId"] not in done]
    if args.json:
        print(dump(rows))
        return 0
    cats = {c: sum(1 for r in rows if r["category"] == c) for c in ("篇幅不足", "只缺迄日", "兩者")}
    fails = sum(1 for r in rows if r["fetchFailures"])
    print(f"CANDIDATES {len(rows)} 人（排除已跑 {len(excluded)}；篇幅不足 {cats['篇幅不足']}、只缺迄日 {cats['只缺迄日']}、"
          f"兩者 {cats['兩者']}；reeval 名單 {sum(r['reeval'] for r in rows)}；參考：搜尋紀錄有 403 的 {fails}，不再當條件）")
    for r in rows:
        print(f"- {r['batch']} {r['name']} [{r['category']}] {r['verdict']} 抓不到{r['fetchFailures']} "
              f"{'reeval ' if r['reeval'] else ''}{'；'.join(r['needs'])[:160]}")
    return 0


# ---------------------------------------------------------------- 工作目錄

def person_line(nn, bio):
    prompt = PROMPT_DIR / f"research-{nn}.md"
    if prompt.exists():
        for person in plan.people_from_prompt(prompt.read_text(encoding="utf-8")):
            if person["bioId"] == bio:
                return person["line"]
    return None


def prepare(nn, bio, work_root, out_root=OUT_ROOT, raw_root=RAW_ROOT):
    """把正式批次的這個人抽到工作目錄（已有就沿用）。回傳 agent 基本欄位。"""
    src_dir = Path(out_root) / f"batch{nn}"
    work = Path(work_root) / f"batch{nn}"
    people = work / "people"
    people.mkdir(parents=True, exist_ok=True)
    rawmap_src = src_dir / "rawmap.json"
    if not (work / "rawmap.json").exists() and rawmap_src.exists():
        (work / "rawmap.json").write_text(rawmap_src.read_text(encoding="utf-8"), encoding="utf-8")
    person_file = people / f"{bio}.json"
    if not person_file.exists():
        own = src_dir / "people" / f"{bio}.json"
        if own.exists():
            person_file.write_text(own.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            merge.extract(src_dir / "research.json", bio, person_file)
    doc = load(person_file)
    person = doc["person"]
    return {
        "batch": nn, "bioId": bio, "name": person.get("name"), "key": person.get("key"),
        "line": person_line(nn, bio) or f"{person.get('nameZh') or ''}｜{person.get('name') or ''}｜{bio}",
        "outDir": str(work), "rawDir": str(Path(raw_root) / f"batch{nn}" / "raw"),
        "batchId": f"b3-full-v3-batch{nn}", "reuseRoot": str(out_root),
        "knownUrls": sorted({(s or {}).get("url") for s in (doc.get("sources") or {}).values() if (s or {}).get("url")}),
    }


def tool_counts(log_path):
    """agent 對話紀錄裡實際的工具呼叫次數（WebSearch 次數用這個量，不信 searchLog）。"""
    counts = {}
    try:
        lines = Path(log_path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return counts
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        message = event.get("message") if isinstance(event, dict) else None
        content = message.get("content") if isinstance(message, dict) else None   # system 事件的 message 可能是字串
        for item in content if isinstance(content, list) else []:
            if isinstance(item, dict) and item.get("type") == "tool_use":
                counts[item.get("name")] = counts.get(item.get("name"), 0) + 1
    return counts


def files(agent):
    people = Path(agent["outDir"]) / "people"
    bio = agent["bioId"]
    return {
        "person": people / f"{bio}.json", "base": people / f"{bio}.base.json",
        "stage2": people / f"{bio}.stage2.json", "deep": people / f"{bio}.deep.json",
        "supp": people / f"{bio}.supplementC.json", "cjson": people / f"{bio}.c.json", "cmd": people / f"{bio}.c.md",
        "done": people / f"{bio}.agent-done.json", "rawmap": Path(agent["outDir"]) / "rawmap.json",
    }


# ---------------------------------------------------------------- 套用第二階段草稿

def _texts_for(agent, keys, rawmap):
    out = {}
    for key in keys:
        _name, text = draft.raw_text(agent["rawDir"], rawmap, key)
        if text is not None:
            out[key] = text
    return out


def _reuse(cite, base_cites):
    """agent 重寫段落時，同 sourceKey＋quote 的舊引文沿用 locator、accessedOn、evidenceNote 等欄位。"""
    for old in base_cites:
        if old.get("sourceKey") == cite.get("sourceKey") and draft.norm(old.get("quote")) == draft.norm(cite.get("quote")):
            merged = dict(old)
            merged.update({k: v for k, v in cite.items() if v is not None})
            return merged
    return cite


def quote_years(text):
    """引文裡出現的西元年（含民國、明治／大正／昭和／平成紀年換算；tools/c_rules.py）。"""
    return cr.years(text)


def date_problems(label, period, cites, precision=None):
    """新寫的起迄日，年份要出現在該筆引文裡（防止「民國6年」寫成 1918）。
    day 精度另要求月、日都出現在引文裡（防止 4 月 24 日的電報被寫成 1916-04-01 日精度）。"""
    years, nums = set(), set()
    for cite in cites or []:
        ys, ns = cr.numbers(cite.get("quote"))
        years |= ys
        nums |= ns
    out = []
    for side in ("start", "end"):
        value = str((period or {}).get(side) or "")
        if not re.match(r"\d{4}", value):
            continue
        if int(value[:4]) not in years:
            out.append(f"{label}.{side}={value}：年份不在引文裡（引文年份 {sorted(years) or '無'}）")
        elif (precision or {}).get(side) == "day" and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            month, day = int(value[5:7]), int(value[8:10])
            if month not in nums or day not in nums:
                out.append(f"{label}.{side}={value}：日精度，但引文沒有 {month} 月 {day} 日（改用 month／year 精度或換引文）")
    return out


SUPPORT_LOG = []


def stage2_support(person, ords, sources=None):
    """第二階段新寫的段落：每句的年份／數字要出現在 claimSpan 指到的引文裡。
    缺年份的句子直接刪（中英句數一致時；否則只回報）；只缺其他數字的回報給 agent 改。"""
    log = []
    for para in person.get("paragraphs") or []:
        if str(para.get("ord")) not in ords:
            continue
        sentences = uncited.zh_sentences((para.get("body") or {}).get("zh-Hant"))
        drop = []
        for index, sent in enumerate(sentences, 1):
            quotes = [c.get("quote") or "" for c in para.get("citations") or []
                      if index in uncited._span_hits(c.get("claimSpan"), sentences)]
            if not quotes:
                continue   # 沒有 claimSpan 的句子交給 uncited 檢查
            gaps = cr.support_gaps(sent, " ".join(quotes), names=False)
            if not gaps:
                continue
            has_year = any(re.fullmatch(r"\d{4}", g) for g in gaps)
            log.append({"ord": para.get("ord"), "s": index, "zh": sent, "gaps": gaps, "dropped": has_year})
            if has_year:
                drop.append(index)
        if drop:
            ok, _removed = uncited.drop_sentences(para, drop)
            if not ok:
                for item in log:
                    if item["ord"] == para.get("ord") and item["s"] in drop:
                        item["dropped"] = False
    return log


GAP_LOG = []


def _gap_kind(gap):
    """gap 類別：note 冒號前；「待查證」再加後面三字（缺迄日／缺起日 分開算）。"""
    note = str(gap.get("note") or "")
    if "：" not in note:
        return note[:12]
    head, rest = note.split("：", 1)
    return f"{head}：{rest[:3]}" if head == "待查證" else head


def sync_gaps(person):
    """gaps 整理：同 target＋同類（note 冒號前，如「篇幅不足」「待查證」）只留最後一筆（較新的那筆）；
    篇幅已達標（≥3 段、≥300 字）就拿掉 paragraph:length。回傳做了什麼（寫進 GAP_LOG）。"""
    gaps = list(person.get("gaps") or [])
    actions = []
    keep, seen = [], set()
    for gap in reversed(gaps):
        key = (gap.get("target"), _gap_kind(gap))
        if key in seen:
            actions.append(f"重複 gap 移除：{key[0]}（{key[1]}）")
            continue
        seen.add(key)
        keep.append(gap)
    keep.reverse()
    paras = person.get("paragraphs") or []
    chars = sum(len("".join(str((x.get("body") or {}).get("zh-Hant") or "").split())) for x in paras)
    if len(paras) >= 3 and chars >= MIN_CHARS and any(g.get("target") == "paragraph:length" for g in keep):
        keep = [g for g in keep if g.get("target") != "paragraph:length"]
        actions.append(f"篇幅已達標（{len(paras)} 段／{chars} 字），移除 paragraph:length gap")
    person["gaps"] = keep
    GAP_LOG.extend(actions)
    return actions


def apply_stage2(agent, base_doc, patch, today=None):
    """base 單人檔＋stage2 草稿 → 新單人檔。回傳 (doc, problems)。"""
    today = today or date.today().isoformat()
    doc = copy.deepcopy(base_doc)
    person = doc["person"]
    sources = doc.setdefault("sources", {})
    raw_map = doc.get("rawMap") if isinstance(doc.get("rawMap"), dict) else {}
    doc["rawMap"] = raw_map
    rawmap_all = fetch_source.load_rawmap(files(agent)["rawmap"])
    deep = load(files(agent)["deep"]) if files(agent)["deep"].exists() else {}
    suggested = deep.get("sources") or {}
    problems = []
    for key, over in (patch.get("sources") or {}).items():
        sug = suggested.get(key) or {}
        entry = dict(sources.get(key) or {})
        entry.update({
            "title": over.get("title") or entry.get("title") or sug.get("title") or sug.get("label") or key,
            "authors": over.get("authors") if over.get("authors") is not None else entry.get("authors", []),
            "publisher": over.get("publisher") or entry.get("publisher") or sug.get("label"),
            "published_text": over.get("published_text") or entry.get("published_text") or sug.get("label"),
            "url": over.get("url") or entry.get("url") or sug.get("url"),
            "grade": over.get("grade") or entry.get("grade") or sug.get("suggestedGrade"),
            "gradeBasis": over.get("gradeBasis") or entry.get("gradeBasis"),
        })
        for k, v in over.items():
            entry.setdefault(k, v)
        if entry["grade"] not in ("A", "B"):
            problems.append(f"來源 {key}：主內容只收 A／B（C 只能放第三階段的補充區）")
        if not entry.get("gradeBasis"):
            problems.append(f"來源 {key}：缺 gradeBasis")
        if entry.get("url") and pre.blocked_host(entry["url"]):
            problems.append(f"來源 {key}：禁用網域 {entry['url']}")
        sources[key] = entry
    for key in list(sources):
        if key not in raw_map:
            name, _text = draft.raw_text(agent["rawDir"], rawmap_all, key)
            raw_map[key] = name or f"{key}.txt"
    texts = _texts_for(agent, sources, rawmap_all)
    base_cites = [c for unit in (person.get("paragraphs") or []) + (person.get("positions") or [])
                  + (person.get("roleCandidates") or []) for c in unit.get("citations") or []]

    def fill(cites):
        return [draft.fill_citation(_reuse(c, base_cites), sources, texts, today) for c in cites or []]

    def fill_unit(unit, kind):
        unit = dict(unit)
        unit["citations"] = fill(unit.get("citations"))
        if kind == "paragraph":
            unit.setdefault("relatedRecordIds", [])
        return unit

    paras = person.get("paragraphs") or []
    for ord_key, new in (patch.get("paragraphsReplace") or {}).items():
        for i, old in enumerate(paras):
            if str(old.get("ord")) == str(ord_key):
                paras[i] = fill_unit(dict(new, ord=old.get("ord")), "paragraph")
    for new in patch.get("paragraphsAppend") or []:
        paras.append(fill_unit(new, "paragraph"))
    person["paragraphs"] = paras
    new_ords = [str(k) for k in (patch.get("paragraphsReplace") or {})]
    new_ords += [str(n.get("ord")) for n in patch.get("paragraphsAppend") or []]
    SUPPORT_LOG[:] = stage2_support(person, new_ords, sources)
    for item in SUPPORT_LOG:
        problems.append(f"SUPPORT 段{item['ord']}句{item['s']}：{'已刪（年份不在引文）' if item['dropped'] else '數字不在引文，請改'}"
                        f" {item['gaps']}：{item['zh'][:50]}")
    keep_gaps = set()
    for field, upd_key, add_key in (("positions", "positionsUpdate", "positionsAdd"),
                                    ("roleCandidates", "roleCandidatesUpdate", "roleCandidatesAdd")):
        items = person.get(field) or []
        for key, upd in (patch.get(upd_key) or {}).items():
            match = next((x for x in items if x.get("key") == key), None)
            if match is None:
                problems.append(f"{upd_key}：沒有 {key}")
                continue
            upd = dict(upd)
            add = upd.pop("addCitations", None)
            if "period" in upd:
                label = f"{upd_key}:{key}"
                target = f"{'position' if field == 'positions' else 'role'}:{key}"
                orig = dict(match.get("period") or {})
                changed = {k: v for k, v in (upd.pop("period") or {}).items() if v and v != orig.get(k)}
                for side in ("start", "end"):   # 值沒變、只改精度也算改
                    if upd.get(f"{side}Precision") and upd[f"{side}Precision"] != match.get(f"{side}Precision") \
                            and (orig.get(side) or side in changed):
                        changed.setdefault(side, orig.get(side))
                prec = {side: upd.get(f"{side}Precision") or match.get(f"{side}Precision") for side in ("start", "end")}
                cites = list(add or []) + list(match.get("citations") or [])
                bad = date_problems(label, changed, add or match.get("citations"), prec)
                refuse = {side for side in ("start", "end") if any(b.startswith(f"{label}.{side}=") for b in bad)}
                problems += [f"REFUSED {b}" for b in bad]
                note = " ".join([str(upd.get("evidenceNote") or "")] + [str(c.get("evidenceNote") or "") for c in add or []])
                end = changed.get("end")
                if end and "end" not in refuse and "推論" in note and prec.get("end") == "day" \
                        and not cr.successor_day_quote(end, cites):
                    changed["end"] = next_month_first(end)   # 寫作規則：month 終點寫下一個月第一天
                    upd["endPrecision"] = "month"
                    upd["evidenceNote"] = (str(upd.get("evidenceNote") or "") + f"；推論上限：不晚於 {end}（引文沒寫後任任命那一天）").lstrip("；")
                    problems.append(f"CAPPED {label}.end={end} → {changed['end']} month（推論迄日，引文沒有後任任命日）")
                trial = dict(orig, **{k: v for k, v in changed.items() if k not in refuse})
                breaks = cr.term_breaks(person, match, trial) if trial != orig else []
                if breaks:
                    refuse |= set(changed)
                    problems.append(f"REFUSED {label}：任期 {trial.get('start')}～{trial.get('end')} 中間有免職／辭職／復任記載 "
                                    + "；".join(f"{b['date']}「{b['text'][:30]}」" for b in breaks[:3]) + "，可能是兩段任期，維持原狀與 gap")
                for side in refuse:
                    changed.pop(side, None)
                    upd.pop(f"{side}Precision", None)
                period = dict(orig)
                period.update(changed)
                match["period"] = period
                if refuse:
                    keep_gaps.add(target)
                    if not changed:   # 整筆被退：引文與 evidenceNote 也不加
                        upd.pop("evidenceNote", None)
                        add = None
            match.update(upd)
            if add:
                match["citations"] = (match.get("citations") or []) + fill(add)
        for new in patch.get(add_key) or []:
            problems += date_problems(f"{add_key}:{new.get('key')}", new.get("period"), new.get("citations"),
                                      {side: new.get(f"{side}Precision") for side in ("start", "end")})
            items.append(fill_unit(new, "position"))
        person[field] = items
    remove = set(patch.get("gapsRemove") or []) - keep_gaps
    person["gaps"] = [g for g in person.get("gaps") or [] if g.get("target") not in remove]
    for gap in patch.get("gapsAdd") or []:
        gap = dict(gap)
        gap.setdefault("checkedOn", today)
        gap["candidateCitations"] = fill(gap.get("candidateCitations"))
        person["gaps"].append(gap)
    logs = list(person.get("searchLog") or [])
    for entry in list(deep.get("searchLog") or []) + list(patch.get("searchLog") or []):
        entry = {k: v for k, v in entry.items() if k != "step"}
        entry.setdefault("round", "stage2")
        logs.append(dict({"step": len(logs) + 1}, **entry))
    person["searchLog"] = logs
    sync_gaps(person)
    prune_supplement(person, _row(doc, agent))
    return doc, problems


# ---------------------------------------------------------------- C 級補充區

def _row(doc, agent):
    _e, _c, row = draft.check_person_full(doc, agent["rawDir"], agent.get("batchId") or "b3-full-v3-selfcheck")
    return row


def prune_supplement(person, row):
    """A／B 已補上的欄位刪掉對應的 C：主內容的起迄日有值就刪那筆 C 日期；主內容篇幅達標就刪篇幅條文。"""
    block = person.get("supplementC")
    if not isinstance(block, dict):
        return 0
    removed = 0
    terms = {f"position:{x.get('key')}": x for x in person.get("positions") or []}
    terms.update({f"role:{x.get('key')}": x for x in person.get("roleCandidates") or []})
    kept = []
    for item in block.get("dates") or []:
        target, _, end = str(item.get("target") or "").rpartition(".")
        main = terms.get(target)
        if main and (main.get("period") or {}).get(end):
            removed += 1
            continue
        kept.append(item)
    block["dates"] = kept
    if row and row.get("paragraphs", 0) >= 3 and row.get("zhChars", 0) >= MIN_CHARS:
        removed += len(block.get("clauses") or [])
        block["clauses"] = []
    if not block.get("dates") and not block.get("clauses"):
        person.pop("supplementC", None)
    else:
        used = {i.get("cKey") for i in (block.get("clauses") or []) + (block.get("dates") or [])}
        block["sources"] = {k: v for k, v in (block.get("sources") or {}).items() if k in used}
    return removed


def apply_csupp(agent, base_doc, patch, today=None):
    """base 單人檔＋C 草稿 → person.supplementC。主內容不動。"""
    today = today or date.today().isoformat()
    doc = copy.deepcopy(base_doc)
    person = doc["person"]
    cinfo = load(files(agent)["cjson"]) if files(agent)["cjson"].exists() else {}
    csources = cinfo.get("sources") or {}
    problems = []
    rawmap_all = fetch_source.load_rawmap(files(agent)["rawmap"])
    used = {}

    def build(item, kind):
        key = item.get("cKey")
        src = csources.get(key)
        if not src:
            problems.append(f"{kind}：cKey {key} 不在 C 段落的來源裡")
            return None
        used[key] = src
        out = {
            "target": item.get("target"),
            "cKey": key,
            "url": src["url"],
            "quote": item.get("quote"),
            "quoteLang": item.get("quoteLang") or src.get("lang"),
            "accessedOn": src.get("accessedOn") or today,
            "grade": "C",
        }
        _name, text = draft.raw_text(agent["rawDir"], rawmap_all, key)
        offset = draft.norm(text).find(draft.norm(item.get("quote"))) if text and item.get("quote") else -1
        out["locator"] = f"條目正文（正規化後字元位置 {offset}）" if offset >= 0 else "條目正文"
        if kind == "clause":
            out["text"] = item.get("text") or {}
        else:
            out.update({"value": item.get("value"), "precision": item.get("precision"),
                        "status": "待查證（只有 C 級來源）", "confirmed": False})
        return out

    clauses = [c for c in (build(i, "clause") for i in patch.get("clauses") or []) if c]
    dates = [d for d in (build(i, "date") for i in patch.get("dates") or []) if d]
    if clauses or dates:
        person["supplementC"] = {
            "grade": "C",
            "status": C_STATUS,
            "displayFlag": C_DISPLAY_FLAG,
            "note": "主內容 A／B 不足時的 C 級補充；主段落不引用，達標判定不計入，日期一律待查證。之後 A／B 找到就取代。",
            "addedOn": today,
            "sources": {k: {"url": v["url"], "title": v.get("title"), "publisher": v.get("publisher") or "Wikipedia",
                            "lang": v.get("lang"), "grade": "C", "accessedOn": v.get("accessedOn") or today}
                        for k, v in used.items()},
            "clauses": clauses,
            "dates": dates,
        }
    else:
        person.pop("supplementC", None)
    screen_supplement(person)
    return doc, problems


def screen_supplement(person):
    """A／B 為準＋引文支撐：衝突的 C 移到 conflictNotes（附 conflictsWithAB），沒有支撐的句子刪掉或改成只照引文。
    回傳這次的處理紀錄（也附加到 supplementC.auditLog）。"""
    block = person.get("supplementC")
    if not isinstance(block, dict):
        return []
    log, notes = [], list(block.get("conflictNotes") or [])

    def to_note(item, clash):
        note = dict(item, conflictsWithAB=clash, confirmed=False)
        notes.append(note)

    dates = []
    for d in block.get("dates") or []:
        clash = cr.date_conflict(person, d)
        if clash:
            to_note(d, clash)
            log.append({"action": "conflict→note", "target": d.get("target"), "value": d.get("value"), "reason": clash["reason"]})
            continue
        if str(d.get("target") or "").endswith(".end") and not cr.end_quote_ok(d.get("quote")):
            log.append({"action": "dropped-unsupported", "target": d.get("target"), "value": d.get("value"),
                        "reason": "引文寫的是就任／當選（起點事件），不是這個職位的結束"})
            continue
        if d.get("value") and int(str(d["value"])[:4]) not in cr.years(d.get("quote")):
            log.append({"action": "dropped-unsupported", "target": d.get("target"), "value": d.get("value"),
                        "reason": "年份不在引文裡"})
            continue
        dates.append(d)
    clauses = []
    for c in block.get("clauses") or []:
        clash = cr.clause_conflict(person, c)
        if clash:
            to_note(c, clash)
            log.append({"action": "conflict→note", "target": c.get("target"), "reason": clash["reason"],
                        "text": ((c.get("text") or {}).get("zh-Hant") or "")[:60]})
            continue
        fixed, entry = support_fix(c)
        if entry:
            log.append(entry)
        if fixed:
            clauses.append(fixed)
    block["dates"], block["clauses"] = dates, clauses
    if notes:
        block["conflictNotes"] = notes
    if log:
        block["auditLog"] = list(block.get("auditLog") or []) + log
    if not dates and not clauses and not notes:
        person.pop("supplementC", None)
    else:
        used = {i.get("cKey") for i in clauses + dates + notes}
        block["sources"] = {k: v for k, v in (block.get("sources") or {}).items() if k in used}
    return log


def support_fix(clause):
    """C 句子逐句比對引文：沒支撐的句子刪掉；全句都沒支撐 → 改成只照引文的寫法。回傳 (clause, 紀錄)。"""
    text = dict(clause.get("text") or {})
    quote = clause.get("quote") or ""
    zh = uncited.zh_sentences(text.get("zh-Hant"))
    en = uncited.en_sentences(text.get("en"))
    bad = [i for i, sent in enumerate(zh) if cr.support_gaps(sent, quote)]
    if len(zh) == len(en):
        bad = sorted(set(bad) | {i for i, sent in enumerate(en) if cr.support_gaps(sent, quote, names=False)})
    long = cr.overreach(text.get("zh-Hant") or "", quote)
    if long:   # 整條講得比引文多太多：直接改成只照引文
        bad = list(range(len(zh)))
    if not bad:
        return clause, None
    gaps = ([f"字數 {long[0]}>{long[1]}"] if long else []) + sorted({g for i in bad for g in cr.support_gaps(zh[i] if i < len(zh) else "", quote)
                   + (cr.support_gaps(en[i], quote, names=False) if len(zh) == len(en) and i < len(en) else [])})
    keep = [i for i in range(len(zh)) if i not in bad]
    out = dict(clause)
    if keep and len(zh) == len(en):
        out["text"] = dict(text, **{"zh-Hant": "".join(zh[i] for i in keep), "en": " ".join(en[i] for i in keep)})
        return out, {"action": "trimmed-unsupported", "target": clause.get("target"), "gaps": gaps,
                     "text": "".join(zh[i] for i in bad)[:80]}
    lang = clause.get("quoteLang") or ""
    out["text"] = {"zh-Hant": f"維基百科（{lang}）原文：「{quote}」", "en": f"Wikipedia ({lang}) says: \"{quote}\""}
    out["quoteOnly"] = True
    return out, {"action": "quote-only", "target": clause.get("target"), "gaps": gaps,
                 "text": (text.get("zh-Hant") or "")[:80]}


def wiki_titles(entity):
    """索引（Wikidata）的 sitelinks → {lang: title}。只拿來找 C 級的條目網址。"""
    out = {}
    links = (entity or {}).get("sitelinks") or {}
    for lang in C_WIKI_LANGS:
        item = links.get(f"{lang}wiki")
        if item and item.get("title"):
            out[lang] = item["title"]
    return out


def c_prefilter(agent, row, http=None, fetcher=None, max_pages=3, today=None):
    """第三階段 Python 預查：用索引找這個人的 Wikipedia 條目（原文語言、英文、日文／中文），抓進 RAWDIR，挑段落。"""
    today = today or date.today().isoformat()
    f = files(agent)
    info = pre.parse_line(agent.get("line") or agent.get("name") or "", agent["bioId"])
    http = http or pre.Http(Path(agent["rawDir"]).parents[1] / "_index")
    fetcher = fetcher or fetch_source.cmd_fetch
    pre.LAST_ENTITY.clear()
    qid, aliases, _urls = pre.index_lookup(http, info)
    entity = pre.LAST_ENTITY.get("entity") or {}
    titles = {}
    if qid:
        data = http.get_json(f"{pre.WD_API}?action=wbgetentities&format=json&props=sitelinks&ids={qid}") or {}
        titles = wiki_titles((data.get("entities") or {}).get(qid))
    natives = pre.native_names(entity)
    order = []
    for lang in list(natives) + ["en", "ja", "zh"]:
        lang = "zh" if lang == "zh-hant" else lang
        if lang in titles and lang not in order:
            order.append(lang)
    sources = {}
    log = []
    for lang in order[:max_pages]:
        title = titles[lang]
        url = f"https://{lang}.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"
        key = f"c-wp-{lang}-{hashlib.sha1(url.encode('utf-8')).hexdigest()[:6]}"
        status = "cached"
        if fetch_source.existing_text(Path(agent["rawDir"]), f["rawmap"], key) is None:
            http.wait(url)
            report = pre.parse_report(fetcher(str(agent["rawDir"]), str(f["rawmap"]), key, url, [], 600))
            status = report.get("RESULT", "error")
        sources[key] = {"url": url, "title": f"{title} – Wikipedia（{lang}）", "publisher": "Wikipedia", "lang": lang,
                        "grade": "C", "status": status, "accessedOn": today}
        log.append(f"{lang}:{status}")
    names = pre.name_variants(info, list(natives.values()) + list(aliases), deep=True)
    extras = list(info.get("years") or []) + list(info.get("titles") or [])
    for term in row.get("openTerms") or []:
        extras.append(str(term.get("key") or "").replace("-", " "))
    lines = [f"# C 級段落（Wikipedia，只能寫進 supplementC）：{info.get('name')}",
             "段落是快取原文的逐字片段。quote 只能從這裡或 lookup 輸出逐字取。"]
    total = 0
    for key, src in sources.items():
        if src["status"] not in ("fetched", "cached", "copied"):
            continue
        path = fetch_source.existing_text(Path(agent["rawDir"]), f["rawmap"], key)
        if path is None:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        picked = pre.select_snippets(text, names, extras, budget=3500, whole_limit=0)
        if not picked:
            continue
        lines.append(f"\n## [{key}] C｜{src['title']}｜{src['url']}")
        for offset, snippet in picked:
            if total + len(snippet) > 9000:
                break
            lines.append(f"@{offset}: {snippet}")
            total += len(snippet)
    f["cjson"].write_text(dump({"bioId": agent["bioId"], "qid": qid, "sources": sources, "log": log}), encoding="utf-8")
    f["cmd"].write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"pages": len(sources), "log": log, "snippetChars": total}


# ---------------------------------------------------------------- agent 用的 check

def find_agent(spec, agent_id):
    for agent in load(spec).get("agents") or []:
        if agent.get("id") == agent_id:
            return agent
    raise SystemExit(f"spec 裡沒有 {agent_id}")


def build_current(agent):
    """依 agent 種類把草稿套到 base，寫回單人檔。回傳 (doc, problems)。"""
    f = files(agent)
    base = load(f["base"]) if f["base"].exists() else load(f["person"])
    kind = agent["kind"]
    own = f["stage2"] if kind == "deep" else f["supp"]
    if not own.exists():
        return base, [f"還沒有草稿 {own.name}"]
    try:
        patch = load(own)
    except json.JSONDecodeError as exc:
        return base, [f"草稿不是合法 JSON：{exc}"]
    doc, problems = (apply_stage2 if kind == "deep" else apply_csupp)(agent, base, patch)
    f["person"].write_text(dump(doc), encoding="utf-8")
    return doc, problems


def cmd_check(args):
    agent = find_agent(args.spec, args.id)
    doc, problems = build_current(agent)
    errors, c_errors, row = draft.check_person_full(doc, agent["rawDir"], agent.get("batchId"))
    lines = [f"ASSEMBLE {p}" for p in problems] + [f"VERIFY {e}" for e in errors] + [f"VERIFY_C {e}" for e in c_errors]
    if agent["kind"] == "deep" and needs_of(row) and not agent.get("browserOnly"):
        patch = load(files(agent)["stage2"]) if files(agent)["stage2"].exists() else {}
        queries = [e for e in patch.get("searchLog") or [] if (e.get("query") or "").strip()
                   and not str(e.get("query")).startswith("預查")]
        if len(queries) < 3:
            lines.append(f"SEARCH 還沒解決，但 searchLog 只記了 {len(queries)} 次實際搜尋；要 WebSearch 3–5 次"
                         "（至少 2 次用原文姓名），每次照實記一筆，真的查不到再收手")
        if any(".end" in n.split("（")[0] for n in needs_of(row)):
            gate = candidate_gate(agent, patch)
            if gate:
                lines.append(gate)
    print(f"SELFCHECK {'ok' if not lines else 'fail'} 錯誤 {len(lines)}")
    for line in lines[:25]:
        print(line[:240])
    print(draft.summary_line(row))
    if agent["kind"] == "csupp":
        for entry in (doc["person"].get("supplementC") or {}).get("auditLog") or []:
            print(f"SCREEN {entry['action']} {entry.get('target')} {entry.get('value') or ''} {entry.get('reason') or entry.get('gaps') or ''}"[:240])
    gone = uncited.find_uncited(doc["person"])
    if gone and agent["kind"] == "deep":
        print(f"UNCITED {len(gone)}（新寫的句子要有 claimSpan）：" + "；".join(f"段{g['ord']}句{g['s']}" for g in gone[:8]))
    if args.done:
        files(agent)["done"].write_text(dump({"stage": agent["kind"], "bioId": agent["bioId"], "ok": True,
                                              "note": f"selfcheck {'ok' if not lines else 'fail'}"}), encoding="utf-8")
        print(f"DONE {agent['kind']}")
    return 0


# ---------------------------------------------------------------- 搜尋結果收割（2026-11-19，pilot5 診斷 fix 3）
# agent 搜完之後跑 `tiers.py harvest`：從它這次的 WebSearch 結果抽網址，只留 A／B 型網域，
# Python 自動抓前 3 頁（同一 host 間隔 ≥1 秒），只回「姓名＋年份」都對上的片段。不繞過擋頁、不用 Wayback。

HARVEST_EXTRA = [
    ("gob.mx", "official", "A", "Gobierno de México"),
    ("unam.mx", "academic", "B", "UNAM（學術出版）"),
    ("colmex.mx", "academic", "B", "El Colegio de México（學術期刊）"),
    ("inah.gob.mx", "academic", "B", "INAH（學術期刊）"),
    ("kgparl.de", "academic", "B", "Kommission für Geschichte des Parlamentarismus"),
    ("paperspast.natlib.govt.nz", "newspaper", "B", "Papers Past（同時代報紙；報導日不是任免日）"),
]
HARVEST_KIND_ORDER = {"official": 0, "national_dictionary": 0, "academic": 1, "named_encyclopedia": 1, "newspaper": 2}
WIKI_LIKE_RE = re.compile(r"wiki|ipfs|cavac\.at|llmpedia|worddisk|generals\.dk|fandom|kiwix|freedombox|hispanopedia|"
                          r"timenote|cyclowiki|riteme|krisyotam|g\.co$|imdb\.com|scribd\.com|issuu\.com|blogspot", re.I)
MIRROR_PREFIXES = ("mail.", "m.", "old.", "web.", "ww2.")
PREFIX_LANGS = {
    "jp": ["ja"], "cn": ["zh", "zh-hant"], "tw": ["zh-hant", "zh"], "hk": ["zh-hant"], "ir": ["fa"], "mx": ["es"],
    "ar": ["es"], "cl": ["es"], "co": ["es"], "pe": ["es"], "ve": ["es"], "ec": ["es"], "bo": ["es"], "py": ["es"],
    "uy": ["es"], "cu": ["es"], "ni": ["es"], "cr": ["es"], "pa": ["es"], "sv": ["es"], "gt": ["es"], "hn": ["es"],
    "do": ["es"], "es": ["es"], "pt": ["pt"], "br": ["pt"], "de": ["de"], "at": ["de"], "ch": ["de", "fr", "it"],
    "fi": ["fi", "sv"], "se": ["sv"], "no": ["no", "nb"], "dk": ["da"], "is": ["is"], "nl": ["nl"], "be": ["nl", "fr"],
    "lu": ["fr", "de", "lb"], "fr": ["fr"], "it": ["it"], "gr": ["el"], "tr": ["tr"], "ot": ["tr"], "pl": ["pl"],
    "cz": ["cs"], "sk": ["sk"], "hu": ["hu"], "ro": ["ro"], "bg": ["bg"], "yu": ["sr", "hr"], "hr": ["hr"],
    "al": ["sq"], "lt": ["lt"], "lv": ["lv"], "ee": ["et"], "ru": ["ru"], "su": ["ru"], "ua": ["uk"], "ge": ["ka"],
    "mn": ["mn"], "eg": ["ar"], "af": ["fa", "ps"], "ht": ["fr"], "kr": ["ko"],
}


def own_langs(person):
    """本人的語言（索引原文姓名只用這些＋英文）。key 前綴對不上時，看中文名＋威妥瑪／拼音判斷華人；都不行回 None。"""
    key = str(person.get("key") or "")
    prefix = key.split("-", 1)[0]
    if prefix in PREFIX_LANGS:
        return PREFIX_LANGS[prefix]
    name = str(person.get("name") or "")
    if person.get("nameZh") and (re.search(r"[ǎǐǒǔāēīōūáéíóúàèìòù]", name) or re.search(r"\b\w+-\w+\b", key)):
        return ["zh-hant", "zh"]
    return None


def native_names_for(person, natives):
    langs = own_langs(person)
    if not langs:
        return dict(natives or {})
    return {k: v for k, v in (natives or {}).items() if k in langs}


def harvest_host(url):
    """A／B 型網域 → (sourceType, 建議等級, 說明)；wiki／鏡像／權威檔（沒有任期資料）回 None。"""
    host = (urlparse(url).hostname or "").lower()
    if not host or WIKI_LIKE_RE.search(host) or WIKI_LIKE_RE.search(url):
        return None
    for suffix, kind, grade, label in sorted(HARVEST_EXTRA + list(pre.HOSTS), key=lambda h: -len(h[0])):
        if host == suffix or host.endswith("." + suffix):
            if kind == "authority":
                return None
            return kind, grade, label
    return None


def search_links(log_paths):
    """agent 對話紀錄裡 WebSearch 的結果網址（依出現順序、去重），附查詢字串。"""
    seen, out = set(), []
    for path in log_paths:
        try:
            lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") != "user":
                continue
            message = event.get("message") if isinstance(event, dict) else None
            content = message.get("content") if isinstance(message, dict) else None   # system 事件的 message 可能是字串
            for item in content if isinstance(content, list) else []:
                if not isinstance(item, dict) or item.get("type") != "tool_result":
                    continue
                text = item.get("content")
                if isinstance(text, list):
                    text = " ".join(x.get("text", "") for x in text if isinstance(x, dict))
                if not isinstance(text, str) or not text.startswith("Web search results"):
                    continue
                query = text.split("\n", 1)[0].split(":", 1)[-1].strip().strip('"')
                match = re.search(r"Links: (\[.*?\])\s*\n", text, re.S)
                try:
                    links = json.loads(match.group(1)) if match else []
                except json.JSONDecodeError:
                    links = []
                for link in links:
                    url = (link or {}).get("url")
                    if url and url not in seen:
                        seen.add(url)
                        out.append({"url": url, "title": link.get("title"), "query": query})
    return out


def _resolves(host):
    import socket
    try:
        socket.getaddrinfo(host, 443)
        return True
    except (socket.gaierror, UnicodeError, OSError):
        return False


def same_site_url(url, resolves=_resolves):
    """host 解析不到時，只換成同一網站的 www. 主機（mail.iranicaonline.org → www.iranicaonline.org）；
    不換到別的網域、不用鏡像或 Wayback。回傳 (url, 說明) 或 (None, 原因)。"""
    parts = urlparse(url)
    host = (parts.hostname or "").lower()
    if resolves(host):
        return url, None
    alt = None
    for prefix in MIRROR_PREFIXES:
        if host.startswith(prefix):
            alt = "www." + host[len(prefix):]
            break
    if alt is None and not host.startswith("www."):
        alt = "www." + host
    if alt and alt != host and resolves(alt):
        return parts._replace(netloc=parts.netloc.lower().replace(host, alt)).geturl(), f"{host} 解析不到，改用同站 {alt}"
    return None, f"dead host（{host} 解析不到）"


def name_tokens(person, natives):
    tokens = set()
    for word in re.split(r"[\s,()（）·・]+", str(person.get("name") or "")):
        if len(word) >= 4:
            tokens.add(word)
            tokens.add(unicodedata.normalize("NFKD", word).encode("ascii", "ignore").decode())
    for value in list((natives or {}).values()) + [person.get("nameZh") or ""]:
        value = str(value or "")
        if re.search(r"[\u3400-\u9fff]", value):
            core = re.sub(r"[・·\s]", "", value)
            if len(core) >= 2:
                tokens.add(core)
                tokens.add(cr.norm(core))
        else:
            tokens |= {w for w in re.split(r"[\s,]+", value) if len(w) >= 4}
    return {t for t in tokens if t}


def target_years(person, needs):
    years = set()
    units = {f"{k}:{u.get('key')}": u for k, f in (("position", "positions"), ("role", "roleCandidates"))
             for u in person.get(f) or []}
    for need in needs:
        target = need.split(".end")[0]
        unit = units.get(target)
        start = str(((unit or {}).get("period") or {}).get("start") or "")[:4]
        if start.isdigit():
            years |= set(range(int(start), int(start) + 21))
    return years


END_WORDS = ("licencia", "renunci", "dejó", "dejo", "terminó", "concluy", "relev", "sustitu", "entregó", "hasta",
             "until", "resign", "replaced", "succeeded", "dismiss", "relieved", "bis ", "rücktritt", "abgelöst",
             "entlassen", "eronnut", "erosi", "asti", "辭", "免", "解任", "退任", "離任", "卸任", "調任", "繼任", "後任",
             "استعفا", "برکنار")


def _fold(text):
    """逐字去重音＋小寫，長度不變（索引可對回原文）。"""
    return "".join((unicodedata.normalize("NFKD", ch)[:1] or ch).casefold()[:1] or ch for ch in text)


def post_words(person, needs):
    words = set()
    units = {f"position:{u.get('key')}": u for u in person.get("positions") or []}
    for need in needs:
        unit = units.get(need.split(".end")[0]) or {}
        for field in ("title", "organization"):
            value = unit.get(field) or {}
            for text in (value.values() if isinstance(value, dict) else [value]):
                for w in re.split(r"[\s,()（）/·・]+", str(text or "")):
                    if len(w) >= 5 or re.search(r"[\u3400-\u9fff]{2,}", w):
                        words.add(_fold(w)[:8])
    return words - {"government", "gobierno", "mexican", "national", "regierung"}


def harvest_snippets(text, tokens, years, radius=220, limit=3, posts=()):
    """原文裡同時有姓名與目標年份（含民國／和曆換算）的片段；含職稱字、卸任用語的排前面。"""
    flat = re.sub(r"\s+", " ", text)
    low = _fold(flat)
    scored = []
    for token in sorted(tokens, key=len, reverse=True):
        t, start = _fold(token), 0
        while len(scored) < 400:
            i = low.find(t, start)
            if i < 0:
                break
            a, b = max(0, i - radius), i + len(token) + radius
            window, wlow = flat[a:b], low[a:b]
            if set(cr.years(window)) & years:
                score = 2 * sum(1 for w in posts if w and w in wlow) + sum(1 for w in END_WORDS if w in wlow)
                scored.append((score, a, window.strip()))
            start = i + len(token)
    out, used = [], []
    for score, a, window in sorted(scored, key=lambda x: (-x[0], x[1])):
        if any(abs(a - u) < radius for u in used):
            continue
        used.append(a)
        out.append(window)
        if len(out) >= limit:
            break
    return out


def harvest(agent, log_dir, max_fetch=3, gap_seconds=1.0, resolves=_resolves, fetcher=None, sleep=None):
    """收割：回傳報告 dict，並寫 <bio>.harvest.json。"""
    import time
    sleep = sleep or time.sleep
    fetcher = fetcher or fetch_source.cmd_fetch
    f = files(agent)
    doc = load(f["person"])
    person = doc["person"]
    deep = load(f["deep"]) if f["deep"].exists() else {}
    natives = native_names_for(person, deep.get("nativeNames"))
    row = _row(doc, agent) or {}
    needs = [n for n in needs_of(row) if ".end" in n.split("（")[0]]
    safe = f"deep-{agent['batch']}-{agent['bioId']}"
    logs = sorted(Path(log_dir).glob(f"{safe}.*.jsonl"), key=lambda p: p.stat().st_mtime)
    links = search_links(logs)
    non_wiki = [l for l in links if not WIKI_LIKE_RE.search(urlparse(l["url"]).hostname or "")]
    graded = []
    for link in links:
        info = harvest_host(link["url"])
        if info:
            graded.append(dict(link, kind=info[0], grade=info[1], label=info[2]))
    graded.sort(key=lambda c: HARVEST_KIND_ORDER.get(c["kind"], 3))
    tokens, years = name_tokens(person, natives), target_years(person, needs)
    posts = post_words(person, needs)
    rawmap = Path(agent["outDir"]) / "rawmap.json"
    out_path = f["person"].parent / f"{agent['bioId']}.harvest.json"
    previous = {c.get("url"): c for c in (load(out_path).get("candidates") or [])} if out_path.exists() else {}
    last_hit, blocked_hosts, new_fetches, seen_text = {}, {}, 0, {}
    report = {"bioId": agent["bioId"], "searchLinks": len(links), "nonWikiLinks": len(non_wiki),
              "candidates": [], "needs": needs}
    for cand in graded:
        entry = {k: cand[k] for k in ("url", "title", "query", "kind", "grade", "label")}
        old = previous.get(cand["url"])
        if old and old.get("status") in ("fetched", "cached", "skipped"):   # 上一輪已處理：沿用，不重抓、不佔名額
            report["candidates"].append(dict(old, status="cached" if old["status"] != "skipped" else "skipped"))
            continue
        if new_fetches >= max_fetch:
            entry.update(status="not_fetched", reason=f"這一輪已抓滿 {max_fetch} 頁")
            report["candidates"].append(entry)
            continue
        host0 = (urlparse(cand["url"]).hostname or "").lower()
        if host0 in blocked_hosts:
            entry.update(status="skipped", reason=f"同站先前被擋（{blocked_hosts[host0]}），不再試")
            report["candidates"].append(entry)
            continue
        url, note = same_site_url(cand["url"], resolves)
        if url is None:
            entry.update(status="skipped", reason=note)
            report["candidates"].append(entry)
            continue
        host = urlparse(url).hostname
        wait = gap_seconds - (time.time() - last_hit.get(host, 0))
        if wait > 0:
            sleep(wait)
        key = "h-" + re.sub(r"[^a-z0-9]+", "-", host.lower()).strip("-")[:30] + "-" + \
              hashlib.sha1(url.encode()).hexdigest()[:8]
        out = fetcher(agent["rawDir"], str(rawmap), key, url, [], 1200)
        last_hit[host] = time.time()
        new_fetches += 1
        result = (re.search(r"RESULT=(\S+)", out) or [None, "error"])[1]
        if result.startswith("blocked") or "redirects followed" in out:   # 403／挑戰頁／Incapsula 轉址迴圈：不繞過
            result = result if result.startswith("blocked") else "blocked_bot_protection"
            blocked_hosts[host0] = result
        entry.update(url=url, sourceKey=key, note=note)
        if result in ("fetched", "cached"):
            text_path = Path(agent["rawDir"]) / f"{key}.txt"
            text = text_path.read_text(encoding="utf-8", errors="replace") if text_path.exists() else ""
            digest = hashlib.sha1(text.encode()).hexdigest()
            if text and digest in seen_text:                      # 同一頁的別名網址：不重複給片段、不佔名額
                new_fetches -= 1
                entry.update(url=url, sourceKey=key, status="skipped", reason=f"與 {seen_text[digest]} 同一頁")
                report["candidates"].append(entry)
                continue
            seen_text[digest] = key
            entry.update(status=result, textChars=len(text),
                         snippets=harvest_snippets(text, tokens, years, posts=posts))
        else:
            reason = (re.search(r"note=(.*)", out) or [None, result])[1]
            entry.update(status="skipped", reason=f"{result}：{reason}"[:160])
        report["candidates"].append(entry)
    out_path.write_text(dump(report), encoding="utf-8")
    return report


def harvest_text(report):
    lines = [f"HARVEST 搜尋結果網址 {report['searchLinks']}、非 wiki {report['nonWikiLinks']}、A／B 型候選 {len(report['candidates'])}"]
    for c in report["candidates"]:
        head = f"- {c['status']} {c.get('grade')}｜{c.get('label')}｜{c['url']}"
        if c.get("sourceKey"):
            head += f"｜sourceKey={c['sourceKey']}"
        if c.get("reason"):
            head += f"｜{c['reason']}"
        lines.append(head[:300])
        for s in c.get("snippets") or []:
            lines.append(f"    「{s[:300]}」")
        if c.get("status") in ("fetched", "cached") and not c.get("snippets"):
            lines.append("    （沒有姓名＋年份同時出現的片段；可用 lookup 換關鍵字）")
    if not report["candidates"]:
        lines.append("沒有 A／B 型網域的結果：自己挑非 wiki 網址 fetch，或在 searchLog 寫明略過原因。")
    return "\n".join(lines)


def cmd_harvest(args):
    agent = find_agent(args.spec, args.id)
    report = harvest(agent, agent.get("logDir") or args.log_dir or ".")
    print(harvest_text(report))
    return 0


def candidate_gate(agent, patch):
    """缺迄日還沒解決時：至少 2 個非 wiki 候選網址已抓或寫明略過原因（harvest 自動記的也算）。
    搜尋結果本來就沒有那麼多非 wiki 網址時，要求降到實際數量。回傳錯誤字串或 None。"""
    path = files(agent)["person"].parent / f"{agent['bioId']}.harvest.json"
    if not path.exists():
        return ("HARVEST 缺迄日還沒解決，但還沒跑 harvest：搜完後執行 "
                f"python3 -I tools/b3v3/tiers.py harvest --spec {agent.get('specPath')} --id {agent['id']}")
    report = load(path)
    if agent.get("logDir"):
        safe = f"deep-{agent['batch']}-{agent['bioId']}"
        live = search_links(sorted(Path(agent["logDir"]).glob(f"{safe}.*.jsonl")))
        known = {c.get("url") for c in report.get("candidates") or []} | set(report.get("seenUrls") or [])
        fresh = [l for l in live if harvest_host(l["url"]) and l["url"] not in known]
        if fresh:
            return (f"HARVEST harvest 之後又搜到 {len(fresh)} 個 A／B 網域的新網址：再跑一次 "
                    f"python3 -I tools/b3v3/tiers.py harvest --spec {agent.get('specPath')} --id {agent['id']}")
    handled = [c for c in report.get("candidates") or []
               if c.get("status") in ("fetched", "cached") or (c.get("status") == "skipped" and c.get("reason"))]
    for entry in patch.get("searchLog") or []:
        url, result = entry.get("url"), str(entry.get("result") or "")
        if url and not WIKI_LIKE_RE.search(url) and (result.startswith("fetched") or
                                                     (result.startswith("skipped") and len(result) > 10)):
            if url not in {c.get("url") for c in handled}:
                handled.append({"url": url})
    need = min(2, report.get("nonWikiLinks") or 0)
    if len(handled) < need:
        return (f"FETCH 缺迄日還沒解決：非 wiki 候選網址只處理了 {len(handled)} 個（要 {need} 個）。"
                "再 fetch 搜尋結果裡的機構／學術／官方頁，或在 searchLog 每筆寫 url 與 result=fetched／skipped:具體原因")
    return None


def in_final_unit(day, unit):
    """迄日是 month／year 精度（寫成下一個月／年的 1 日）時，day 落在任期最後那個月／年 → True。"""
    end = str((unit.get("period") or {}).get("end") or "")
    prec = unit.get("endPrecision")
    try:
        y, m = int(end[:4]), int(end[5:7])
    except ValueError:
        return False
    if prec == "month" and end[8:10] == "01":
        last = f"{y - 1:04d}-12" if m == 1 else f"{y:04d}-{m - 1:02d}"
        return str(day)[:7] == last
    if prec == "year" and end[5:10] == "01-01":
        return str(day)[:4] == f"{y - 1:04d}"
    return False


def cmd_terms(args):
    """任期中斷檢查（唯讀）：research.json 或單人檔裡，任期中間有免職／辭職／復任記載的職位。"""
    data = load(args.file)
    people = data.get("people") or ([data["person"]] if "person" in data else [])
    hits = 0
    for person in people:
        for field in ("positions", "roleCandidates"):
            for unit in person.get(field) or []:
                for b in cr.term_breaks(person, unit):
                    if in_final_unit(b["date"], unit):    # 月／年精度迄日寫成下一單位首日：最後那個月／年本身不算中斷
                        continue
                    hits += 1
                    print(f"TERM_BREAK {person.get('key')} {unit.get('key')} {unit.get('period')} ← {b['date']} 段{b['ord']}「{b['text'][:50]}」")
    print(f"TERM_BREAK {hits} 筆")
    return 0


def cmd_screen(args):
    data = load(args.file)
    log = screen_supplement(data["person"])
    for entry in log:
        print(f"SCREEN {json.dumps(entry, ensure_ascii=False)}")
    print(f"SCREEN {len(log)} 筆")
    if not args.dry_run:
        Path(args.file).write_text(dump(data), encoding="utf-8")
    return 0


# ---------------------------------------------------------------- 併回正式批次

def _unit_map(person):
    out = {}
    for field in ("positions", "roleCandidates"):
        for unit in person.get(field) or []:
            out[f"{field}:{unit.get('key')}"] = unit
    return out


def person_diff(old, new):
    """兩份 person 的摘要差異（給 dry-run 看）。"""
    def chars(person):
        return sum(len([ch for ch in ((p.get("body") or {}).get("zh-Hant") or "") if not ch.isspace()])
                   for p in person.get("paragraphs") or [])
    oldp = {str(p.get("ord")): p for p in old.get("paragraphs") or []}
    changed = sum(1 for p in new.get("paragraphs") or [] if str(p.get("ord")) in oldp and oldp[str(p.get("ord"))] != p)
    lines = [f"段落 {len(old.get('paragraphs') or [])}→{len(new.get('paragraphs') or [])}、中文字 {chars(old)}→{chars(new)}"
             f"、既有段落有改 {changed} 段（含補 claimSpan）"]
    olds, news = _unit_map(old), _unit_map(new)
    for key in sorted(set(olds) | set(news)):
        a, b = olds.get(key), news.get(key)
        if a is None:
            lines.append(f"+ {key} {b.get('period')}")
        elif b is None:
            lines.append(f"- {key}")
        elif (a.get("period") or {}) != (b.get("period") or {}):
            lines.append(f"~ {key} {a.get('period')} → {b.get('period')}")
        elif len(a.get("citations") or []) != len(b.get("citations") or []):
            lines.append(f"~ {key} 引文 {len(a.get('citations') or [])}→{len(b.get('citations') or [])}")
    og = {g.get("target") for g in old.get("gaps") or []}
    ng = {g.get("target") for g in new.get("gaps") or []}
    if og - ng:
        lines.append(f"gaps 移除 {sorted(og - ng)}")
    if ng - og:
        lines.append(f"gaps 新增 {sorted(ng - og)}")
    supp = new.get("supplementC") or {}
    if supp:
        lines.append(f"supplementC：clauses {len(supp.get('clauses') or [])}、dates {len(supp.get('dates') or [])}、"
                     f"conflictNotes {len(supp.get('conflictNotes') or [])}（{supp.get('status')}／{supp.get('displayFlag')}）")
    return lines


def merge_back(people, work_root, out_root=OUT_ROOT, apply=False):
    """工作目錄的結果寫回正式批次：research.json（換掉那個人、合併來源）、people/<bioId>.json、rawmap.json。
    dry-run（預設）在暫存複本上做同樣的事，跑 verify 與 check_min，正式檔一個字都不動。回傳報告 dict。"""
    import shutil
    import subprocess
    import tempfile
    report = {"apply": apply, "batches": {}}
    by_batch = {}
    for item in people:
        nn, bio = item.split(":", 1)
        by_batch.setdefault(nn, []).append(bio)
    for nn, bios in sorted(by_batch.items()):
        src = Path(out_root) / f"batch{nn}"
        work = Path(work_root) / f"batch{nn}"
        tmp = Path(tempfile.mkdtemp(prefix=f"tiers-merge-{nn}-"))
        target = src if apply else tmp / f"batch{nn}"
        if not apply:
            target.mkdir(parents=True)
            for name in ("research.json", "rawmap.json"):
                if (src / name).exists():
                    shutil.copyfile(src / name, target / name)
        research = load(target / "research.json")
        rawmap = load(target / "rawmap.json") if (target / "rawmap.json").exists() else {}
        index = {p.get("bioId"): i for i, p in enumerate(research.get("people") or [])}
        entry = {"people": [], "sourcesAdded": [], "sourceConflicts": [], "rawmapAdded": 0}
        for bio in bios:
            doc = load(work / "people" / f"{bio}.json")
            new = doc["person"]
            if bio not in index:
                entry["people"].append({"bioId": bio, "error": "正式 research.json 沒有這個人"})
                continue
            old = research["people"][index[bio]]
            entry["people"].append({"bioId": bio, "name": new.get("name"), "diff": person_diff(old, new)})
            research["people"][index[bio]] = new
            for key, value in (doc.get("sources") or {}).items():
                if key not in research["sources"]:
                    entry["sourcesAdded"].append(key)
                elif research["sources"][key] != value:
                    entry["sourceConflicts"].append(key)
                    continue   # 既有來源以正式檔為準
                research["sources"][key] = value
            for key, name in (doc.get("rawMap") or {}).items():
                if isinstance(name, str) and key not in rawmap:
                    rawmap[key] = name
                    entry["rawmapAdded"] += 1
            if apply:
                (target / "people").mkdir(exist_ok=True)
                (target / "people" / f"{bio}.json").write_text(dump(doc), encoding="utf-8")
        (target / "research.json").write_text(dump(research), encoding="utf-8")
        (target / "rawmap.json").write_text(dump(rawmap), encoding="utf-8")
        verify_report = (target if apply else tmp) / "verify-report.json"
        proc = subprocess.run([sys.executable, "-I", str(draft.VERIFY), str(target / "research.json"),
                               "--report", str(verify_report)], capture_output=True, text=True)
        vr = load(verify_report) if verify_report.exists() else {}
        check_min = plan.load_check_min()
        rows = check_min.report_for(research)["people"]
        mine = {p.get("key") for p in research["people"] if p.get("bioId") in bios}
        entry["verify"] = {"exit": proc.returncode, "errors": len(vr.get("errors") or []),
                           "cErrors": len(vr.get("supplementCErrors") or []),
                           "errorSample": (vr.get("errors") or [])[:5] + (vr.get("supplementCErrors") or [])[:5]}
        entry["checkMin"] = {r["key"]: r["verdict"] for r in rows if r["key"] in mine}
        entry["checkMinBatch"] = {v: sum(1 for r in rows if r["verdict"] == v) for v in sorted({r["verdict"] for r in rows})}
        if not apply:
            entry["tmp"] = str(tmp)
        report["batches"][nn] = entry
    return report


def cmd_merge(args):
    people = [p.strip() for p in args.people.split(",") if p.strip()]
    report = merge_back(people, Path(args.work_root), Path(args.out_root), apply=args.apply)
    print(f"MERGE {'APPLY' if args.apply else 'DRY-RUN（正式檔沒動）'}")
    for nn, entry in report["batches"].items():
        print(f"batch{nn}：verify exit {entry['verify']['exit']}、主錯 {entry['verify']['errors']}、C 錯 {entry['verify']['cErrors']}；"
              f"新來源 {len(entry['sourcesAdded'])}、來源衝突（保留正式檔）{entry['sourceConflicts']}、rawmap 新增 {entry['rawmapAdded']}")
        for err in entry["verify"]["errorSample"]:
            print(f"  ! {err[:200]}")
        print(f"  check_min（這些人）：{entry['checkMin']}；全批：{entry['checkMinBatch']}")
        for person in entry["people"]:
            print(f"  ● {person.get('name') or person['bioId']}" + (f" {person['error']}" if person.get("error") else ""))
            for line in person.get("diff") or []:
                print(f"     {line[:200]}")
    if args.report:
        Path(args.report).write_text(dump(report), encoding="utf-8")
    return 0


def cmd_prune(args):
    data = load(args.file)
    removed = prune_supplement(data["person"], None)
    Path(args.file).write_text(dump(data), encoding="utf-8")
    print(f"PRUNE 刪除 {removed} 筆 C")
    return 0


# ---------------------------------------------------------------- 提示詞用的現況摘要

def state_text(person, sources, limit=5000):
    lines = []
    for para in person.get("paragraphs") or []:
        sents = uncited.zh_sentences((para.get("body") or {}).get("zh-Hant"))
        lines.append(f"段{para.get('ord')}：" + "".join(f"[{i}]{s}" for i, s in enumerate(sents, 1)))
        for i, c in enumerate(para.get("citations") or []):
            lines.append(f"  c{i} {c.get('sourceKey')}（{c.get('grade')}）claimSpan={c.get('claimSpan')}："
                         f"{(c.get('quote') or '')[:60]}")
    for kind, items in (("職位", person.get("positions") or []), ("角色", person.get("roleCandidates") or [])):
        for x in items:
            per = x.get("period") or {}
            lines.append(f"{kind} {x.get('key')}：{(x.get('title') or {}).get('zh-Hant') or ''} "
                         f"{per.get('start')}～{per.get('end')}")
    for g in person.get("gaps") or []:
        lines.append(f"gap {g.get('target')}：{(g.get('note') or '')[:80]}")
    lines.append("已有來源：" + "、".join(f"{k}({(v or {}).get('grade')})" for k, v in sources.items()))
    text = "\n".join(lines)
    return text[:limit] + ("…" if len(text) > limit else "")


def uncited_text(person, items):
    by_ord = {}
    for item in items:
        by_ord.setdefault(item["ord"], []).append(item)
    lines = []
    for para in person.get("paragraphs") or []:
        if para.get("ord") not in by_ord:
            continue
        lines.append(f"段{para.get('ord')}：")
        for item in by_ord[para.get("ord")]:
            lines.append(f"  句{item['s']}：{item['zh']}")
        for i, c in enumerate(para.get("citations") or []):
            lines.append(f"  c{i} {c.get('sourceKey')} claimSpan={c.get('claimSpan')}：{(c.get('quote') or '')[:80]}")
    return "\n".join(lines)


# ---------------------------------------------------------------- 驅動

def next_month_first(day):
    """YYYY-MM-DD → 下一個月的第一天（month 精度終點的寫法：到 1917-11 → 1917-12-01）。"""
    y, m = int(day[:4]), int(day[5:7])
    y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return f"{y:04d}-{m:02d}-01"


def review_extras(person, stage1=None):
    """審查切片的補充：每個職位／角色的精度與 evidenceNote、任期中斷記載，以及相對第一階段快照的改動。"""
    units = []
    for kind, field in (("職位", "positions"), ("候選角色", "roleCandidates")):
        for unit in person.get(field) or []:
            notes = [c.get("evidenceNote") for c in unit.get("citations") or [] if c.get("evidenceNote")]
            units.append({"where": f"{kind} {unit.get('key')}", "period": unit.get("period"),
                          "startPrecision": unit.get("startPrecision"), "endPrecision": unit.get("endPrecision"),
                          "evidenceNote": unit.get("evidenceNote"), "citationNotes": notes,
                          "termBreaks": cr.term_breaks(person, unit)})
    changes = []
    if stage1:
        olds = {}
        for kind, field in (("職位", "positions"), ("候選角色", "roleCandidates")):
            for unit in stage1.get(field) or []:
                olds[f"{kind} {unit.get('key')}"] = unit
        for kind, field in (("職位", "positions"), ("候選角色", "roleCandidates")):
            for unit in person.get(field) or []:
                where = f"{kind} {unit.get('key')}"
                old = olds.get(where)
                if old is None:
                    changes.append(f"新增 {where} {unit.get('period')}")
                    continue
                for name in ("period", "startPrecision", "endPrecision", "evidenceNote"):
                    if old.get(name) != unit.get(name):
                        changes.append(f"{where}.{name}：{old.get(name)} → {unit.get(name)}")
                added = len(unit.get("citations") or []) - len(old.get("citations") or [])
                if added:
                    changes.append(f"{where}：引文 +{added}")
        old_paras = {str(x.get("ord")): x for x in stage1.get("paragraphs") or []}
        for para in person.get("paragraphs") or []:
            old = old_paras.get(str(para.get("ord")))
            if old is None:
                changes.append(f"新增 段{para.get('ord')}")
            elif (old.get("body") or {}) != (para.get("body") or {}):
                changes.append(f"改寫 段{para.get('ord')}")
        og = {g.get("target") for g in stage1.get("gaps") or []}
        ng = {g.get("target") for g in person.get("gaps") or []}
        changes += [f"gap 移除 {t}" for t in sorted(og - ng)] + [f"gap 新增 {t}" for t in sorted(ng - og)]
    return {"units": units, "stage2Changes": changes}


REVIEW_STAGE2_RULE = (
    "stage2Changes 列的是第二階段改過的項目，這些日期不適用「維持原日期」：day 精度要引文寫出那一天；"
    "推論迄日要引文寫出後任任命那一天（電報或報導日期不算），否則改 month 精度，或刪掉並留 gap。"
    "termBreaks 有列的職位，任期中間有免職／復任，不要當成一段連續任期。")


def stage_cost(records):
    """一個階段的費用：完成的 attempt 用 modelUsage 的 costUSD（含 Haiku 搜尋子呼叫），
    中斷的 attempt 用 partialUsage 的估計值（另列，Haiku 沒算）。"""
    actual = estimated = 0.0
    for rec in records if isinstance(records, list) else [records]:
        if not isinstance(rec, dict):
            continue
        usage = rec.get("modelUsage") or {}
        if usage:
            actual += sum(float(m.get("costUSD") or 0) for m in usage.values())
        elif rec.get("partialUsage"):
            estimated += float(rec["partialUsage"].get("estCostUSD") or 0)
    return {"actual": round(actual, 4), "estimatedPartial": round(estimated, 4), "total": round(actual + estimated, 4)}


class BrowserMissing(Exception):
    """釘選的瀏覽器不在 bridge 上，或工作被送到別台：整輪停下，不再處理下一個人。"""


class UsageLimited(Exception):
    """額度用完（429 usage_limit／rate_limit）：整輪停下，不把空結果當成「查不到」往下一階段送。"""


def usage_limited(log_path):
    try:
        text = Path(log_path).read_text(encoding="utf-8")
    except OSError:
        return False
    low = text.casefold()
    return ('"usage_limit_reached"' in text or '"error":"rate_limit"' in text
            or bool(re.search(r"hit your [^\"]{0,40}limit", low)))


class Runner:
    def __init__(self, args):
        self.args = args
        self.work_root = Path(args.work_root)
        self.spec_path = self.work_root / "spec.json"
        self.loop = _load("run_loop")
        self.journal = self.loop.Journal(args.log_dir)
        self.results = []

    def write_spec(self, agents):
        self.work_root.mkdir(parents=True, exist_ok=True)
        current = load(self.spec_path).get("agents") if self.spec_path.exists() else []
        by_id = {a["id"]: a for a in current}
        for a in agents:
            by_id[a["id"]] = a
        self.spec_path.write_text(dump({"agents": list(by_id.values())}), encoding="utf-8")

    def agent(self, base, kind):
        a = dict(base)
        a.update({"id": f"{kind}:{base['batch']}:{base['bioId']}", "kind": kind, "model": "sonnet",
                  "specPath": str(self.spec_path.relative_to(REPO)) if str(self.spec_path).startswith(str(REPO))
                  else str(self.spec_path),
                  "doneMarker": str(files(base)["done"]), "logDir": str(self.journal.dir)})
        return a

    def retry_guard(self, agent):
        """重試前把這個 agent 會寫的檔還原成第一次啟動前的樣子（中斷的那輪寫了一半的留一份 .attemptN-partial 備查），
        避免第二輪接著半成品寫、或兩輪內容疊在一起。"""
        f = files(agent)
        people = f["person"].parent
        bio = agent["bioId"]
        paths = [f["person"], f["stage2"], f["supp"], f["done"], people / f"{bio}.review.json"]
        snap = {}

        def before(attempt):
            if attempt == 1:
                snap.update({p: (p.read_bytes() if p.exists() else None) for p in paths})
                return
            for path, data in snap.items():
                now = path.read_bytes() if path.exists() else None
                if now == data:
                    continue
                if now is not None:
                    path.with_name(path.name + f".attempt{attempt - 1}-partial").write_bytes(now)
                if data is None:
                    path.unlink()
                else:
                    path.write_bytes(data)
                self.journal.log("retry_restore", id=agent["id"], attempt=attempt, file=path.name)
        return before

    def launch(self, agent, prompt, attachment=""):
        self.write_spec([agent])
        f = files(agent)
        if f["done"].exists():
            f["done"].unlink()
        records = self.loop.launch(agent, prompt + attachment, self.journal, before_attempt=self.retry_guard(agent))
        for rec in records if isinstance(records, list) else [records]:
            if isinstance(rec, dict) and rec.get("log"):
                rec["toolCalls"] = tool_counts(rec["log"])
                if usage_limited(rec["log"]):
                    self.journal.log("usage_limit_stop", id=agent["id"])
                    raise UsageLimited(agent["id"])
        return records

    def check(self, base):
        doc = load(files(base)["person"])
        errors, c_errors, row = draft.check_person_full(doc, base["rawDir"], base["batchId"])
        return doc, errors, c_errors, row

    def attach(self, path, label, limit=24000):
        if not Path(path).exists():
            return ""
        text = Path(path).read_text(encoding="utf-8")
        return f"\n---{label}（{Path(path).name}）---\n{text[:limit]}\n---end---\n"

    def review(self, base, doc, row, errors):
        """沿用既有 Sonnet 審查（證據切片）。"""
        agent = self.agent(base, "review")
        people = Path(base["outDir"]) / "people"
        tmp_research = Path(base["outDir"]) / "research.json"
        rawmap = Path(base["outDir"]) / "rawmap.json"
        for key in doc.get("sources") or {}:                       # 證據切片只看 rawmap：補登記共用 rawDir 裡已有的原文
            if key not in fetch_source.load_rawmap(rawmap):
                found = fetch_source.existing_text(base["rawDir"], rawmap, key)
                if found is not None:
                    fetch_source.update_rawmap(rawmap, key, found.name)
        research = {
            "batch": base["batchId"], "rawDir": base["rawDir"], "rawMap": "rawmap.json",
            "sources": doc.get("sources") or {}, "people": [doc["person"]],
            "alignedTo": doc.get("alignedTo") or "b0b0e0f", "alignNote": doc.get("alignNote") or draft.ALIGN_NOTE,
        }
        tmp_research.write_text(dump(research), encoding="utf-8")
        pack = evidence.build(tmp_research)
        sliced = evidence.slice_person(pack, doc["person"].get("key"))
        ev = {
            "bioId": base["bioId"], "key": doc["person"].get("key"), "name": doc["person"].get("name"), "rawLoaded": True,
            "checkMin": {k: row.get(k) for k in ("verdict", "paragraphs", "zhChars", "meetsMinimum", "documentedShortfall",
                                                  "openTerms")},
            "verifyErrors": errors, "paths": evidence.unit_paths(doc["person"]), "claims": sliced["claims"],
        }
        stage1_path = people / f"{base['bioId']}.stage1.json"
        extras = review_extras(doc["person"], load(stage1_path)["person"] if stage1_path.exists() else None)
        ev.update(extras)
        (people / f"{base['bioId']}.evidence.json").write_text(dump(ev), encoding="utf-8")
        batch = {"nn": base["batch"], "outDir": base["outDir"], "rawDir": base["rawDir"], "specPath": agent["specPath"]}
        person = {"bioId": base["bioId"], "line": base["line"], "name": base["name"],
                  "shortfallFlag": not row.get("meetsMinimum") and (row.get("zhChars", 0) < MIN_CHARS or row.get("paragraphs", 0) < 3)}
        prompt = specs.review_prompt(batch, person, REPO)
        prompt += "\nperson.supplementC 是 C 級補充區（不在證據切片裡）：不要審、不要搬進主段落。"
        if extras["stage2Changes"] or any(u["termBreaks"] for u in extras["units"]):
            prompt += "\n" + REVIEW_STAGE2_RULE
        text = json.dumps(ev, ensure_ascii=False, separators=(",", ":"))
        return self.launch(agent, prompt, f"\n---證據切片---\n{text[:24000]}\n---end---\n")

    def one(self, nn, bio):
        base = prepare(nn, bio, self.work_root)
        f = files(base)
        res = {"batch": nn, "bioId": bio, "name": base["name"], "stages": {}}
        doc, errors, c_errors, row = self.check(base)
        res["stage1"] = {"verdict": row["verdict"], "paragraphs": row["paragraphs"], "zhChars": row["zhChars"],
                         "needs": needs_of(row)}
        self.journal.log("tier_start", id=bio, batch=nn, verdict=row["verdict"], needs="；".join(needs_of(row)))
        skip_deep = skips_stage2(self.args, needs_of(row))
        if not stage2_needs(needs_of(row)):
            res["outcome"] = "stage1"
        else:
            # ---- 第二階段
            f["base"].write_text(dump(doc), encoding="utf-8")
            (Path(base["outDir"]) / "people" / f"{bio}.stage1.json").write_text(dump(doc), encoding="utf-8")
        if res.get("outcome") == "stage1":
            pass
        elif skip_deep:
            res["stage2"] = {"skipped": "只缺迄日（--skip-stage2-end-only）", "verdict": row["verdict"],
                             "paragraphs": row["paragraphs"], "zhChars": row["zhChars"], "needs": needs_of(row)}
            self.journal.log("stage2_skipped", id=bio, reason="end-only")
        else:
            summary = pre.run(base, deep=True)
            self.journal.log("deep_prefilter", id=bio, **{k: v for k, v in summary.items() if k != "bioId"})
            deep = load(f["deep"])
            agent = self.agent(base, "deep")
            ctx = {"state": state_text(doc["person"], doc.get("sources") or {}), "needs": "；".join(needs_of(row)),
                   "nativeNames": native_names_for(doc["person"], deep.get("nativeNames") or {}),
                   "japanese": deep.get("japanese")}
            res["stages"]["stage2"] = self.launch(agent, specs.stage2_prompt(agent, ctx, REPO),
                                                  self.attach(Path(base["outDir"]) / "people" / f"{bio}.deep.md", "預查段落"))
            if f["stage2"].exists():
                GAP_LOG.clear()
                build_current(agent)
                res["supportStage2"] = list(SUPPORT_LOG)
                res["gapSync"] = list(GAP_LOG)
            doc, errors, c_errors, row = self.check(base)
            res["stage2"] = {"verdict": row["verdict"], "paragraphs": row["paragraphs"], "zhChars": row["zhChars"],
                             "verifyErrors": len(errors), "needs": needs_of(row)}
            self.journal.log("stage2_end", id=bio, verdict=row["verdict"], zh=row["zhChars"], errors=len(errors))
            if getattr(self.args, "browser", False) and any(".end" in n.split("（")[0] for n in needs_of(row)):
                doc, errors, c_errors, row = self.browser_fallback(base, res, doc, row)
        if res.get("outcome") != "stage1":
            if not skip_deep and not stage2_needs(needs_of(row)):
                res["outcome"] = "stage2"
            elif self.args.no_c:
                res["outcome"] = "stage2-unresolved"
            else:
                # ---- 第三階段（C）
                f["base"].write_text(dump(doc), encoding="utf-8")
                info = c_prefilter(base, row)
                self.journal.log("c_prefilter", id=bio, pages=info["pages"], log=info["log"], snippetChars=info["snippetChars"])
                if info["snippetChars"]:
                    agent = self.agent(base, "csupp")
                    ctx = {"state": state_text(doc["person"], doc.get("sources") or {}, 2500), "needs": "；".join(needs_of(row))}
                    res["stages"]["stage3"] = self.launch(agent, specs.csupp_prompt(agent, ctx, REPO),
                                                          self.attach(f["cmd"], "C 段落", 12000))
                    if f["supp"].exists():
                        build_current(agent)
                doc, errors, c_errors, row = self.check(base)
                supp = doc["person"].get("supplementC") or {}
                res["screenStage3"] = list(supp.get("auditLog") or [])
                res["stage3"] = {"verdict": row["verdict"], "cClauses": len(supp.get("clauses") or []),
                                 "cDates": len(supp.get("dates") or []), "cErrors": len(c_errors)}
                res["outcome"] = "stage3" if supp else "stage3-empty"
        # ---- 審查（主內容或補充區有改過才審）
        stage1 = Path(base["outDir"]) / "people" / f"{bio}.stage1.json"
        start = load(stage1) if stage1.exists() else None
        if res["outcome"] != "stage1" and start is not None and (start != doc or "supplementC" in doc["person"]):
            res["stages"]["review"] = self.review(base, doc, row, errors)
            doc, errors, c_errors, row = self.check(base)
        # ---- 沒有出處的句子
        items = uncited.find_uncited(doc["person"])
        res["uncitedBefore"] = len(items)
        if items:
            agent = self.agent(base, "citefix")
            ctx = {"state": uncited_text(doc["person"], items)}
            res["stages"]["citefix"] = self.launch(agent, specs.citefix_prompt(agent, ctx, REPO))
            data = load(f["person"])
            res["uncitedAfterFix"] = len(uncited.find_uncited(data["person"]))
            removed, marked = uncited.finalize(data["person"])
            f["person"].write_text(dump(data), encoding="utf-8")
            res["uncitedStripped"], res["uncitedMarked"] = removed, marked
        # ---- 最後再套一次 A／B 為準（審查或補引文可能改了主內容）
        data = load(f["person"])
        final_gaps = sync_gaps(data["person"])
        if final_gaps:
            f["person"].write_text(dump(data), encoding="utf-8")
            res["gapSyncFinal"] = final_gaps
        if "supplementC" in data["person"]:
            before = len((data["person"].get("supplementC") or {}).get("auditLog") or [])
            prune_supplement(data["person"], None)
            screen_supplement(data["person"])
            f["person"].write_text(dump(data), encoding="utf-8")
            res["screenFinal"] = ((data["person"].get("supplementC") or {}).get("auditLog") or [])[before:]
        doc, errors, c_errors, row = self.check(base)
        res["final"] = {"verdict": row["verdict"], "paragraphs": row["paragraphs"], "zhChars": row["zhChars"],
                        "verifyErrors": errors[:10], "verifyErrorCount": len(errors), "cErrors": c_errors[:10],
                        "termsFull": row.get("termsFull"), "termsFlagged": row.get("termsFlagged"), "terms": row.get("terms"),
                        "cClauses": row.get("cClauses"), "cDates": row.get("cDates"),
                        "cConflictNotes": len((doc["person"].get("supplementC") or {}).get("conflictNotes") or []),
                        "uncited": len(uncited.find_uncited(doc["person"]))}
        res["cost"] = {name: stage_cost(recs) for name, recs in res["stages"].items()}
        res["costTotal"] = round(sum(c["total"] for c in res["cost"].values()), 4)
        self.journal.log("tier_end", id=bio, outcome=res["outcome"], verdict=row["verdict"], errors=len(errors),
                         cErrors=len(c_errors), cost=res["costTotal"])
        return res

    def browser_fallback(self, base, res, doc, row):
        """第二階段後仍缺迄日：curl 被擋的白名單 A／B 網頁（不含 PDF）用 Claude in Chrome 開一次，再跑只看這些原文的擷取。"""
        bf = _load("browser_fetch")
        bio, nn, f = base["bioId"], base["batch"], files(base)
        urls = blocked_candidates([str(self.work_root)], nn, bio)
        targets = bf.browser_targets(urls)
        info = {"blocked": urls, "skippedPdf": [u for u in targets if bf.pdf_like(u)]}
        targets = bf.order_by_host([u for u in targets if not bf.pdf_like(u)])[:3]
        info["targets"] = targets
        res["browser"] = info
        if not targets:
            return doc, *self.check(base)[1:]
        devices, cost, limited = bf.connected_devices()
        if not devices and not limited:                # 擴充功能閒置時第一次常是空清單：再問一次
            devices, cost2, limited = bf.connected_devices()
            cost += cost2
        res["stages"]["browserCheck"] = [{"modelUsage": {"claude-sonnet-5-5": {"costUSD": cost}}}]
        if limited:
            raise UsageLimited(f"browserCheck:{bio}")
        ids = [d.get("deviceId", "") for d in devices]
        info["devices"] = ids
        pin = self.args.browser_device
        if pin not in ids:
            info["outcome"] = "device-missing"
            self.journal.log("browser_stop", id=bio, reason="device-missing", devices=",".join(ids))
            raise BrowserMissing(f"device-missing:{bio}:{','.join(ids)}")
        log = Path(self.journal.dir) / f"chrome-{nn}-{bio}.jsonl"
        debug = log.with_suffix(".debug.txt")
        info["run"] = bf.run_session(targets, log, budget=self.args.max_browser_cost, device=pin, debug_file=debug)
        pages, result = bf.parse_log(log)
        res["stages"]["browser"] = [{"modelUsage": result.get("modelUsage") or {}, "log": str(log)}]
        if limit_text_hit(result) or usage_limited(log):
            raise UsageLimited(f"browser:{bio}")
        problem = bf.device_problem(log, debug, pin)
        if problem:
            info["outcome"] = problem
            self.journal.log("browser_stop", id=bio, reason=problem)
            raise BrowserMissing(f"{problem}:{bio}")
        saved = bf.save_pages(pages, result, base["rawDir"], Path(base["outDir"]) / "rawmap.json",
                              fetch_source.update_rawmap)
        last = {e["url"]: e for e in saved}
        opened = set(last)
        info["pages"] = list(last.values()) + [{"url": u, "status": "not_opened"} for u in targets if u not in opened]
        self.journal.log("browser_end", id=bio, cost=bf.session_cost(result)["costUSD"],
                         fetched=sum(1 for e in last.values() if e["status"] == "fetched"),
                         blocked=sum(1 for e in last.values() if e["status"] == "blocked"))
        fetched = [e for e in last.values() if e["status"] == "fetched"]
        if not fetched:
            return doc, *self.check(base)[1:]
        needs = needs_of(row)
        snippets = browser_snippets(doc["person"], [n for n in needs if ".end" in n], fetched, base["rawDir"])
        if "「" not in snippets:                       # 沒有姓名＋年份的片段：不花錢跑擷取
            info["extract"] = "no-snippets"
            return doc, *self.check(base)[1:]
        agent = dict(self.agent(base, "deep"), browserOnly=True, id=f"browser:{nn}:{bio}")
        ctx = {"state": state_text(doc["person"], doc.get("sources") or {}), "needs": "；".join(needs),
               "nativeNames": {}, "japanese": None}
        if f["stage2"].exists():
            f["stage2"].rename(f["stage2"].with_suffix(".deep.json"))   # 第二階段的草稿已套進單人檔；留底
        f["base"].write_text(dump(doc), encoding="utf-8")
        res["stages"]["browserExtract"] = self.launch(agent, specs.stage2_prompt(agent, ctx, REPO) + "\n" + BROWSER_PILOT_RULE,
                                                      f"\n---瀏覽器原文片段---\n{snippets}\n---end---\n")
        if f["stage2"].exists():
            build_current(agent)
        doc, errors, c_errors, row = self.check(base)
        info["extract"] = {"needs": needs_of(row), "verifyErrors": len(errors)}
        return doc, errors, c_errors, row

    def run(self, people):
        for item in people:
            nn, bio = item.split(":", 1)
            try:
                self.results.append(self.one(nn, bio))
            except BrowserMissing as exc:
                self.results.append({"batch": nn, "bioId": bio, "name": bio, "outcome": "browser-missing-stop",
                                     "stoppedAt": str(exc), "stages": {}, "final": None})
                (self.journal.dir / "results.json").write_text(dump(self.results), encoding="utf-8")
                print(f"STOPPED 釘選的瀏覽器不在或送錯台（{exc}）")
                self.stopped = "browser"
                break
            except UsageLimited as exc:
                self.results.append({"batch": nn, "bioId": bio, "name": bio, "outcome": "usage-limit-stop",
                                     "stoppedAt": str(exc), "stages": {}, "final": None})
                (self.journal.dir / "results.json").write_text(dump(self.results), encoding="utf-8")
                print(f"STOPPED 額度用完（{exc}）；這個人的工作檔停在中途，重跑請換新的 --work-root")
                break
            (self.journal.dir / "results.json").write_text(dump(self.results), encoding="utf-8")
        return self.results


# ---------------------------------------------------------------- 瀏覽器補抓 pilot（2026-11-20，Tai 核准 t87s346）
BROWSER_PILOT_RULE = (
    "本輪是瀏覽器補抓：不能 WebSearch、不用 harvest、不能 fetch 新頁。只看下面附的「瀏覽器原文片段」（sourceKey 已登記在 rawmap），"
    "需要更多上下文就用 lookup 查同一個 sourceKey。找到迄日就照規則寫 positionsUpdate＋addCitations（quote 逐字含日期）＋gapsRemove，"
    "sources 寫那個 sourceKey（url 用片段標的網址，published_text 註明「經瀏覽器取得（Claude in Chrome）」，等級依頁面類型）。"
    "片段沒有就不要動，維持「待查證：缺迄日」。searchLog 每個頁面記一筆 {query:'browser', url, result:'fetched'}。")


def limit_text_hit(result):
    text = str((result or {}).get("result") or "").casefold()
    return "hit your" in text and "limit" in text


def blocked_candidates(roots, nn, bio):
    """tiers-pilot6（與其 try1）裡被擋的白名單 A／B 網址：harvest.json 的 blocked＋stage2 searchLog 寫 403／blocked 的。"""
    urls = []
    for root in roots:
        people = Path(root) / f"batch{nn}" / "people"
        h = people / f"{bio}.harvest.json"
        for c in (load(h).get("candidates") or []) if h.exists() else []:
            reason = str(c.get("reason") or "")
            if c.get("status") == "skipped" and ("blocked" in reason or "403" in reason) and harvest_host(c["url"]):
                urls.append(c["url"])
        s = people / f"{bio}.stage2.json"
        for e in (load(s).get("searchLog") or []) if s.exists() else []:
            res = str(e.get("result") or "") + str(e.get("note") or "")
            if e.get("url") and re.search(r"403|blocked|擋", res) and harvest_host(e["url"]):
                urls.append(e["url"])
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def copy_person(from_root, work_root, nn, bio):
    """pilot6 的最終狀態當起點（單人檔、快照、預查、C 區、rawmap）。"""
    src, dst = Path(from_root) / f"batch{nn}", Path(work_root) / f"batch{nn}"
    (dst / "people").mkdir(parents=True, exist_ok=True)
    if (src / "rawmap.json").exists() and not (dst / "rawmap.json").exists():
        (dst / "rawmap.json").write_text((src / "rawmap.json").read_text(encoding="utf-8"), encoding="utf-8")
    for path in (src / "people").glob(f"{bio}.*"):
        if path.name.endswith(("agent-done.json",)) or ".attempt" in path.name:
            continue
        target = dst / "people" / path.name
        if not target.exists():
            target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")


def browser_snippets(person, needs, saved, rawdir):
    tokens, years, posts = name_tokens(person, {}), target_years(person, needs), post_words(person, needs)
    parts = []
    for entry in saved:
        if entry["status"] != "fetched":
            continue
        text = (Path(rawdir) / f"{entry['sourceKey']}.txt").read_text(encoding="utf-8", errors="replace")
        snips = harvest_snippets(text, tokens, years, radius=300, limit=5, posts=posts)
        parts.append(f"[{entry['sourceKey']}] {entry['url']}（{entry['textChars']} 字）")
        parts += [f"  「{s}」" for s in snips] or ["  （沒有姓名＋年份同時出現的片段）"]
    return "\n".join(parts)


class BrowserPilot:
    """只跑：瀏覽器補抓 → 擷取（不搜尋的 deep agent）→ 審查 → 補引文 → 最後檢查。"""

    def __init__(self, args):
        self.args = args
        self.runner = Runner(args)
        self.bf = _load("browser_fetch")

    def one(self, nn, bio):
        r = self.runner
        roots = [p for p in self.args.from_roots.split(",") if p]
        copy_person(roots[0], r.work_root, nn, bio)
        base = prepare(nn, bio, r.work_root)
        f = files(base)
        res = {"batch": nn, "bioId": bio, "name": base["name"], "stages": {}}
        doc, errors, c_errors, row = r.check(base)
        res["start"] = {"verdict": row["verdict"], "needs": needs_of(row)}
        urls = self.bf.order_by_host(self.bf.browser_targets(blocked_candidates(roots, nn, bio)))
        if self.args.only_urls:                        # 只開指定的頁（必須本來就在被擋清單裡）
            only = [u.strip() for u in self.args.only_urls.split(",") if u.strip()]
            urls = [u for u in urls if u in only]
        res["blockedUrls"] = urls
        r.journal.log("browser_start", id=bio, urls=len(urls))
        if not urls:
            res["outcome"] = "no-blocked-urls"
            return res
        log = Path(self.args.log_dir) / f"browser-{nn}-{bio}.jsonl"
        res["browserRun"] = self.bf.run_session(urls, log, budget=self.args.max_browser_cost)
        pages, result = self.bf.parse_log(log)
        res["browserCost"] = self.bf.session_cost(result)
        res["browserReply"] = result.get("result")
        saved = self.bf.save_pages(pages, result, base["rawDir"], Path(base["outDir"]) / "rawmap.json",
                                   fetch_source.update_rawmap)
        opened = {p["url"] for p in pages}
        # 同一網址可能先在批次失敗、又逐頁重做：保留最後一筆
        last = {}
        for entry in saved:
            last[entry["url"]] = entry
        saved = list(last.values())
        saved += [{"url": u, "status": "not_opened", "reason": "瀏覽器沒有開這頁"} for u in urls if u not in opened]
        res["pages"] = saved
        r.journal.log("browser_end", id=bio, cost=res["browserCost"]["costUSD"],
                      fetched=sum(1 for s in saved if s["status"] == "fetched"))
        if res["browserCost"]["costUSD"] > self.args.max_browser_cost:
            res["outcome"] = "browser-cost-stop"
            return res
        if not any(s["status"] == "fetched" for s in saved):
            res["outcome"] = "browser-all-blocked"
            return res
        # ---- 擷取：不搜尋的 deep agent，只看瀏覽器原文
        needs = needs_of(row)
        agent = dict(r.agent(base, "deep"), browserOnly=True)
        ctx = {"state": state_text(doc["person"], doc.get("sources") or {}), "needs": "；".join(needs),
               "nativeNames": {}, "japanese": None}
        prompt = specs.stage2_prompt(agent, ctx, REPO) + "\n" + BROWSER_PILOT_RULE
        snippets = browser_snippets(doc["person"], [n for n in needs if ".end" in n], saved, base["rawDir"])
        if f["stage2"].exists():
            f["stage2"].unlink()                       # pilot6 的 stage2 已套進單人檔；這輪重新寫
        f["base"].write_text(dump(doc), encoding="utf-8")
        res["stages"]["extract"] = r.launch(agent, prompt, f"\n---瀏覽器原文片段---\n{snippets}\n---end---\n")
        if f["stage2"].exists():
            build_current(agent)
        doc, errors, c_errors, row = r.check(base)
        res["extract"] = {"verdict": row["verdict"], "needs": needs_of(row), "verifyErrors": len(errors)}
        # ---- 審查、補引文、最後檢查（與 run 相同）
        start = load(Path(base["outDir"]) / "people" / f"{bio}.json")
        res["stages"]["review"] = r.review(base, doc, row, errors)
        doc, errors, c_errors, row = r.check(base)
        items = uncited.find_uncited(doc["person"])
        if items:
            ca = r.agent(base, "citefix")
            res["stages"]["citefix"] = r.launch(ca, specs.citefix_prompt(ca, {"state": uncited_text(doc["person"], items)}, REPO))
            data = load(f["person"])
            uncited.finalize(data["person"])
            f["person"].write_text(dump(data), encoding="utf-8")
        data = load(f["person"])
        sync_gaps(data["person"])
        if "supplementC" in data["person"]:
            prune_supplement(data["person"], None)
            screen_supplement(data["person"])
        f["person"].write_text(dump(data), encoding="utf-8")
        doc, errors, c_errors, row = r.check(base)
        res["final"] = {"verdict": row["verdict"], "needs": needs_of(row), "verifyErrorCount": len(errors),
                        "cErrors": c_errors[:5], "uncited": len(uncited.find_uncited(doc["person"]))}
        res["cost"] = {name: stage_cost(recs) for name, recs in res["stages"].items()}
        res["cost"]["browser"] = {"total": res["browserCost"]["costUSD"]}
        res["outcome"] = "done"
        return res


def cmd_browser_pilot(args):
    pilot = BrowserPilot(args)
    out = Path(args.log_dir) / "browser-results.json"
    results = load(out) if out.exists() else []
    if isinstance(results, dict):
        results = [results]
    for item in [p for p in args.people.split(",") if p]:
        nn, bio = item.split(":", 1)
        res = pilot.one(nn, bio)
        results = [r for r in results if r.get("bioId") != bio] + [res]
        out.write_text(dump(results), encoding="utf-8")
        print(f"BROWSER {nn} {res['name']} {res['outcome']} browser=${(res.get('browserCost') or {}).get('costUSD')} "
              f"pages={[(p['status'], p['url'][:60]) for p in res.get('pages') or []]}")
        if res["outcome"] == "browser-cost-stop":
            print("STOP 瀏覽器費用超過上限")
            break
    return 0


def cmd_run(args):
    people = [p.strip() for p in args.people.split(",") if p.strip()]
    results = Runner(args).run(people)
    for r in results:
        if not r.get("final"):
            print(f"TIER {r['batch']} {r['bioId']} {r['outcome']}")
            continue
        print(f"TIER {r['batch']} {r['name']} {r['outcome']} → {r['final']['verdict']} "
              f"{r['final']['paragraphs']}段/{r['final']['zhChars']}字 verify錯{r['final']['verifyErrorCount']} "
              f"C錯{len(r['final']['cErrors'])} 無出處句{r['final']['uncited']}")
    return 3 if any(r.get("outcome") == "browser-missing-stop" for r in results) else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="B3 v3 分層補查")
    sub = parser.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("candidates")
    c.add_argument("--out-root", default=str(OUT_ROOT))
    c.add_argument("--reeval", default=str(REEVAL))
    c.add_argument("--json", action="store_true")
    c.add_argument("--exclude-results", default="", help="已跑過的 tiers results.json，逗號分隔；這些人不列")
    r = sub.add_parser("run")
    r.add_argument("--people", required=True, help="NNN:bioId,…")
    r.add_argument("--work-root", default=str(WORK_ROOT))
    r.add_argument("--log-dir", default=str(Path.home() / "wl-b3v3-runs" / "tiers"))
    r.add_argument("--no-c", action="store_true")
    r.add_argument("--browser", action="store_true", help="第二階段後仍缺迄日時，被擋的 A／B 網頁用 Claude in Chrome 補抓")
    r.add_argument("--browser-device", default="44c34180-5202-4f69-9685-907c6a3ea7e2",
                   help="釘選的 bridge deviceId（jack755051 Mac 使用者的 Chrome）；不在清單上就整輪停")
    r.add_argument("--max-browser-cost", type=float, default=0.5)
    r.add_argument("--skip-stage2-end-only", action="store_true",
                   help="只缺迄日（篇幅已夠）的人跳過第二階段，直接進 C 補充")
    k = sub.add_parser("check")
    k.add_argument("--spec", required=True)
    k.add_argument("--id", required=True)
    k.add_argument("--done", action="store_true")
    pr = sub.add_parser("prune")
    pr.add_argument("--file", required=True)
    bp = sub.add_parser("browser-pilot", help="瀏覽器補抓 pilot：被擋的 A／B 頁用 Claude in Chrome 開，再擷取／審查")
    bp.add_argument("--people", required=True)
    bp.add_argument("--from-roots", required=True, help="pilot6 work-root（第一個當起點），逗號分隔")
    bp.add_argument("--work-root", required=True)
    bp.add_argument("--log-dir", required=True)
    bp.add_argument("--max-browser-cost", type=float, default=0.5)
    bp.add_argument("--only-urls", default="", help="只開這些網址（逗號分隔；要在被擋清單裡）")
    bp.add_argument("--no-c", action="store_true")
    bp.add_argument("--skip-stage2-end-only", action="store_true")
    hv = sub.add_parser("harvest", help="從 agent 的搜尋結果挑 A／B 網域自動抓頁，回姓名＋年份片段")
    hv.add_argument("--spec", required=True)
    hv.add_argument("--id", required=True)
    hv.add_argument("--log-dir", default="")
    tb = sub.add_parser("terms", help="任期中斷檢查（唯讀）")
    tb.add_argument("--file", required=True)
    sc = sub.add_parser("screen", help="A／B 為準＋引文支撐，套到一個單人檔")
    sc.add_argument("--file", required=True)
    sc.add_argument("--dry-run", action="store_true")
    m = sub.add_parser("merge", help="工作目錄結果併回正式批次；預設 dry-run，--apply 才寫")
    m.add_argument("--people", required=True, help="NNN:bioId,…")
    m.add_argument("--work-root", required=True)
    m.add_argument("--out-root", default=str(OUT_ROOT))
    m.add_argument("--apply", action="store_true")
    m.add_argument("--report")
    args = parser.parse_args(argv)
    return {"candidates": cmd_candidates, "run": cmd_run, "check": cmd_check, "prune": cmd_prune,
            "screen": cmd_screen, "merge": cmd_merge, "terms": cmd_terms,
            "harvest": cmd_harvest, "browser-pilot": cmd_browser_pilot}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
