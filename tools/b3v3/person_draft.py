#!/usr/bin/env python3
"""研究 agent 只寫草稿，Python 補齊樣板欄位、組成單人檔並自檢。

草稿 OUTDIR/people/<bioId>.draft.json 只放內容：
  thickness、paragraphs、positions、roleCandidates、gaps、searchLog（agent 自己多查的步驟）、
  sources（只寫要改的欄位，例如 grade、gradeBasis、authors、title；新抓的來源要寫 url）。
citation 只要 sourceKey、quote，可加 quoteLang、datePrecision、evidenceNote、locator、claimSpan。
其餘（accessedOn、grade、policyVersion、locator 預設值、rawMap、searchLog 前段、頂層欄位）由這裡補。
單人檔格式不變（person、sources、rawMap、researchedOn、policyVersion、alignedTo、alignNote、schemaNote）。

    python3 -I tools/b3v3/person_draft.py check --spec SPEC --id research:123:<bioId> [--done]
    python3 -I tools/b3v3/person_draft.py check --spec SPEC --id review:123:<bioId>    # 只檢查單人檔
    python3 -I tools/b3v3/person_draft.py review-done --spec SPEC --id review:123:<bioId> \\
        --verdict pass --note '…' [--changes '["…"]']
stdout 只印錯誤與一行 check_min 摘要。
"""
import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
import unicodedata
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
VERIFY = REPO_ROOT / "data" / "seed" / "leaders" / "b3-trial" / "verify.py"
CHECK_MIN = REPO_ROOT / "data" / "seed" / "leaders" / "b3-trial" / "full" / "v3" / "check_min.py"
POLICY = "bio-2026-11-v0"
ALIGN_NOTE = "直接寫 b0b0e0f 對齊格式；名單5442已有的元首／首腦任期不重建；regimeId 因不連庫一律 null＋organization。"
SCHEMA_NOTE = (
    "結構依 ARCHITECTURE §16.2（paragraphs）、§16.3（positions）、§16.4.1（citation 欄位）、"
    "§16.4.2（gaps）；sources 以 sourceKey 對應 source_id；來源規則依 docs/source-rules.md。"
)
SOURCE_FIELDS = ("title", "authors", "publisher", "published_text", "url", "archive_url",
                 "catalog_id", "license_code", "grade", "gradeBasis")
MAX_LINES = 25


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def dump(data):
    return json.dumps(data, ensure_ascii=False, indent=1) + "\n"


def find_agent(spec_path, agent_id):
    data = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    for agent in data.get("agents") or []:
        if agent.get("id") == agent_id:
            return agent
    raise SystemExit(f"spec 裡沒有 {agent_id}")


def paths(agent):
    people = Path(agent["outDir"]) / "people"
    bio = agent["bioId"]
    return {
        "people": people,
        "draft": people / f"{bio}.draft.json",
        "prefilter": people / f"{bio}.prefilter.json",
        "person": people / f"{bio}.json",
        "done": people / f"{bio}.agent-done.json",
        "review": people / f"{bio}.review.json",
        "rawmap": Path(agent["outDir"]) / "rawmap.json",
    }


def norm(text):
    import re
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text or "")).strip()


def raw_text(raw_dir, rawmap, key):
    name = rawmap.get(key) if isinstance(rawmap, dict) else None
    for candidate in ([name] if isinstance(name, str) else []) + [f"{key}.txt"]:
        path = Path(raw_dir) / candidate
        if path.is_file():
            return candidate, path.read_text(encoding="utf-8", errors="replace")
    return None, None


def fill_citation(cite, sources, texts, today):
    out = {
        "sourceKey": cite.get("sourceKey"),
        "locator": cite.get("locator"),
        "quote": cite.get("quote"),
        "quoteLang": cite.get("quoteLang"),
        "evidenceNote": cite.get("evidenceNote"),
        "accessedOn": cite.get("accessedOn") or (sources.get(cite.get("sourceKey")) or {}).get("_accessedOn") or today,
        "grade": cite.get("grade") or (sources.get(cite.get("sourceKey")) or {}).get("grade"),
        "datePrecision": cite.get("datePrecision"),
        "claimSpan": cite.get("claimSpan"),
        "policyVersion": cite.get("policyVersion") or POLICY,
    }
    if not out["locator"]:
        text = texts.get(out["sourceKey"])
        offset = norm(text).find(norm(out["quote"])) if text and out["quote"] else -1
        out["locator"] = f"正文（正規化後字元位置 {offset}）" if offset >= 0 else "正文"
    for key, value in cite.items():
        if key not in out:
            out[key] = value
    return out


def assemble(agent, today=None):
    """草稿＋預查 → 單人檔。回傳 (doc, problems)。problems 是組裝層的錯誤（verify 之前）。"""
    today = today or date.today().isoformat()
    p = paths(agent)
    draft = json.loads(p["draft"].read_text(encoding="utf-8"))
    pre = json.loads(p["prefilter"].read_text(encoding="utf-8")) if p["prefilter"].exists() else {}
    rawmap_all = json.loads(p["rawmap"].read_text(encoding="utf-8")) if p["rawmap"].exists() else {}
    base = pre.get("person") or {}
    problems = []
    suggested = pre.get("sources") or {}
    overrides = draft.get("sources") or {}
    used = set()

    def collect(obj, candidate=False):
        if isinstance(obj, dict):
            if obj.get("sourceKey"):
                used.add(obj["sourceKey"])
            for value in obj.values():
                collect(value)
        elif isinstance(obj, list):
            for value in obj:
                collect(value)

    for field in ("paragraphs", "positions", "roleCandidates", "gaps"):
        collect(draft.get(field) or [])
    sources = {}
    raw_map = {}
    texts = {}
    for key in sorted(used):
        pre_item = suggested.get(key) or {}
        over = overrides.get(key) or {}
        if not pre_item and not over.get("url"):
            problems.append(f"來源 {key}：預查沒有這個 sourceKey；新抓的來源要在 draft.sources 寫 url、title、grade、gradeBasis")
        entry = {
            "title": over.get("title") or pre_item.get("title") or pre_item.get("label") or key,
            "authors": over.get("authors") if over.get("authors") is not None else [],
            "publisher": over.get("publisher") or pre_item.get("label"),
            "published_text": over.get("published_text") or pre_item.get("label"),
            "url": over.get("url") or pre_item.get("url"),
            "archive_url": over.get("archive_url"),
            "catalog_id": over.get("catalog_id"),
            "license_code": over.get("license_code"),
            "grade": over.get("grade") or pre_item.get("suggestedGrade"),
            "gradeBasis": over.get("gradeBasis") or (
                f"{pre_item.get('label')}（依網域建議等級，agent 未改）" if pre_item.get("suggestedGrade") else None
            ),
        }
        if entry["grade"] not in ("A", "B", "C"):
            problems.append(f"來源 {key}：沒有等級；在 draft.sources.{key} 寫 grade（A／B；C 只能放 gap 候選）與 gradeBasis")
        if not entry["gradeBasis"]:
            problems.append(f"來源 {key}：缺 gradeBasis")
        for extra_key, value in over.items():
            if extra_key not in entry:
                entry[extra_key] = value
        sources[key] = entry
        name, text = raw_text(agent["rawDir"], rawmap_all, key)
        if name is None:
            problems.append(f"來源 {key}：RAWDIR 沒有原文檔（先用 fetch_source.py fetch）")
            name = f"{key}.txt"
        raw_map[key] = name
        texts[key] = text
        sources[key]["_accessedOn"] = pre_item.get("accessedOn")

    def fill_items(items, kind):
        out = []
        for item in items or []:
            item = dict(item)
            field = "candidateCitations" if kind == "gap" else "citations"
            item[field] = [fill_citation(c, sources, texts, today) for c in item.get(field) or []]
            if kind == "gap":
                item.setdefault("checkedOn", today)
                item.setdefault("candidateCitations", [])
            if kind == "paragraph":
                item.setdefault("relatedRecordIds", [])
            out.append(item)
        return out

    person = {
        "key": draft.get("key") or base.get("key") or f"p-{agent['bioId'][:8]}",
        "bioId": agent["bioId"],
        "name": draft.get("name") or base.get("name") or agent.get("name"),
        "nameZh": draft.get("nameZh") or base.get("nameZh"),
        "recordIds": draft.get("recordIds") or base.get("recordIds") or [],
        "thickness": draft.get("thickness") or base.get("thickness") or "中",
        "paragraphs": fill_items(draft.get("paragraphs"), "paragraph"),
        "positions": fill_items(draft.get("positions"), "position"),
        "roleCandidates": fill_items(draft.get("roleCandidates"), "role"),
        "gaps": fill_items(draft.get("gaps"), "gap"),
    }
    logs = []
    for entry in list(pre.get("searchLog") or []) + list(draft.get("searchLog") or []):
        entry = {k: v for k, v in entry.items() if k != "step"}
        logs.append(dict({"step": len(logs) + 1}, **entry))
    person["searchLog"] = logs
    for item in sources.values():
        item.pop("_accessedOn", None)
    doc = {
        "person": person,
        "sources": sources,
        "rawMap": raw_map,
        "researchedOn": today,
        "policyVersion": POLICY,
        "alignedTo": "b0b0e0f",
        "alignNote": ALIGN_NOTE,
        "schemaNote": SCHEMA_NOTE,
    }
    return doc, problems


def check_person(doc, raw_dir, batch_id="b3-full-v3-selfcheck"):
    """把單人檔包成一人的 research.json，跑原本的 verify.py 與 check_min（規則不變）。"""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        research = {
            "batch": batch_id,
            "researchedOn": doc.get("researchedOn"),
            "policyVersion": doc.get("policyVersion") or POLICY,
            "alignedTo": doc.get("alignedTo") or "b0b0e0f",
            "alignNote": doc.get("alignNote") or ALIGN_NOTE,
            "schemaNote": doc.get("schemaNote") or SCHEMA_NOTE,
            "rawDir": str(raw_dir),
            "rawMap": "rawmap.json",
            "sources": doc.get("sources") or {},
            "people": [doc["person"]],
        }
        raw_map = doc.get("rawMap") if isinstance(doc.get("rawMap"), dict) else {}
        (tmp / "rawmap.json").write_text(dump(raw_map), encoding="utf-8")
        (tmp / "research.json").write_text(dump(research), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, "-I", str(VERIFY), str(tmp / "research.json"), "--report", str(tmp / "report.json")],
            capture_output=True, text=True,
        )
        errors = []
        if (tmp / "report.json").exists():
            errors = json.loads((tmp / "report.json").read_text(encoding="utf-8")).get("errors") or []
        elif proc.returncode != 0:
            errors = [(proc.stderr or proc.stdout).strip()[-300:]]
        check_min = _load("b3_check_min_draft", CHECK_MIN)
        row = check_min.report_for(research)["people"][0]
    return errors, row


def summary_line(row):
    return (
        f"CHECKMIN {row.get('verdict')} 段{row.get('paragraphs')} 字{row.get('zhChars')} "
        f"任期{row.get('termsFull')}+{row.get('termsFlagged')}待查/{row.get('terms')} "
        f"缺{row.get('termsMissing')} 篇幅不足標記={'有' if row.get('documentedShortfall') else '無'}"
    )


def write_done(p, agent, stage, ok=True, note=""):
    p["done"].write_text(dump({"stage": stage, "bioId": agent["bioId"], "ok": ok, "note": note[:120]}), encoding="utf-8")


def cmd_check(spec, agent_id, done=False, today=None):
    agent = find_agent(spec, agent_id)
    p = paths(agent)
    problems = []
    if agent.get("kind") == "research":
        if not p["draft"].exists():
            print(f"沒有草稿 {p['draft']}")
            return 1
        try:
            doc, problems = assemble(agent, today=today)
        except json.JSONDecodeError as exc:
            print(f"草稿不是合法 JSON：{exc}")
            return 1
        p["person"].write_text(dump(doc), encoding="utf-8")
    else:
        doc = json.loads(p["person"].read_text(encoding="utf-8"))
    errors, row = check_person(doc, agent["rawDir"], agent.get("batchId") or "b3-full-v3-selfcheck")
    lines = [f"ASSEMBLE {problem}" for problem in problems] + [f"VERIFY {error}" for error in errors]
    status = "ok" if not lines else "fail"
    print(f"SELFCHECK {status} 錯誤 {len(lines)}")
    for line in lines[:MAX_LINES]:
        print(line[:240])
    if len(lines) > MAX_LINES:
        print(f"…另有 {len(lines) - MAX_LINES} 筆")
    print(summary_line(row))
    if done:
        stage = agent.get("kind") if agent.get("kind") in ("research", "retry") else "research"
        write_done(p, agent, stage, ok=True, note=f"selfcheck {status}")
        print(f"DONE {stage}")
    return 0


def cmd_review_done(spec, agent_id, verdict, note, changes):
    agent = find_agent(spec, agent_id)
    p = paths(agent)
    if verdict not in ("pass", "pass_with_changes", "returned", "篇幅不足"):
        raise SystemExit("verdict 只能是 pass、pass_with_changes、returned、篇幅不足")
    try:
        change_list = json.loads(changes) if changes else []
    except json.JSONDecodeError:
        change_list = [changes]
    if not isinstance(change_list, list):
        change_list = [change_list]
    p["review"].write_text(dump({
        "bioId": agent["bioId"], "verdict": verdict, "changes": change_list, "note": note,
        "model": agent.get("model"), "stage": agent.get("kind"),
    }), encoding="utf-8")
    stage = "escalate" if agent.get("kind") == "escalate" else "review"
    write_done(p, agent, stage, ok=True, note=verdict)
    doc = json.loads(p["person"].read_text(encoding="utf-8"))
    errors, row = check_person(doc, agent["rawDir"], agent.get("batchId") or "b3-full-v3-selfcheck")
    print(f"REVIEW_DONE {verdict} verify錯誤 {len(errors)}")
    print(summary_line(row))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="草稿組裝與單人自檢")
    sub = parser.add_subparsers(dest="cmd", required=True)
    check = sub.add_parser("check")
    check.add_argument("--spec", required=True)
    check.add_argument("--id", required=True)
    check.add_argument("--done", action="store_true")
    review = sub.add_parser("review-done")
    review.add_argument("--spec", required=True)
    review.add_argument("--id", required=True)
    review.add_argument("--verdict", required=True)
    review.add_argument("--note", default="")
    review.add_argument("--changes", default="")
    args = parser.parse_args(argv)
    if args.cmd == "check":
        return cmd_check(args.spec, args.id, args.done)
    return cmd_review_done(args.spec, args.id, args.verdict, args.note, args.changes)


if __name__ == "__main__":
    raise SystemExit(main())
