#!/usr/bin/env python3
"""列出這次工作流要跑的批與階段。stdout 只印 JSON。

有 research.json 與 verify-report.json 就略過研究，除非 --force-research。
--resume 決定哪些批要跑（已審查且不在 recheck_review 的批不列入）。
每一個人另附 missingFields：可補的缺欄才重跑；篇幅不足或只差長度的人直接送審。

    python3 -I tools/b3v3/plan_work.py --repo "$PWD" ... --resume .dev/b3v3/partial/chunk4-remaining.json
    python3 -I tools/b3v3/plan_work.py --repo "$PWD" --out-root data/seed/leaders/b3-trial/full/v3 \\
        --recompute-remaining .dev/b3v3/partial/chunk4-remaining.json
"""
import argparse
import importlib.util
import json
import re
import sys
import unicodedata
from pathlib import Path

RECHECK_DEFAULT = ("096",)
RETRY_DONE_DEFAULT = ("122",)
REPO = Path(__file__).resolve().parents[2]
CHECK_MIN = REPO / "data" / "seed" / "leaders" / "b3-trial" / "full" / "v3" / "check_min.py"


def resolve(repo, value):
    path = Path(value)
    if not path.is_absolute():
        path = Path(repo) / path
    return path


def people_from_prompt(text):
    people = []
    in_section = False
    for line in text.splitlines():
        if line.startswith("## 本批"):
            in_section = True
            continue
        if not in_section:
            continue
        if line.startswith("- "):
            body = line[2:].strip()
            parts = [part.strip() for part in re.split(r"[|｜]", body)]
            if len(parts) < 3:
                continue
            people.append({
                "nameZh": parts[0],
                "name": parts[1],
                "bioId": parts[2],
                "line": body,
            })
            continue
        if line.strip():
            break
    return people


def batch_paths(repo, prompt_dir, out_root, raw_root, nn):
    prompt_dir = resolve(repo, prompt_dir)
    out_root = resolve(repo, out_root)
    raw_root = Path(raw_root)
    return {
        "nn": nn,
        "batchId": f"b3-full-v3-batch{nn}",
        "outDir": str(out_root / f"batch{nn}"),
        "rawDir": str(raw_root / f"batch{nn}" / "raw"),
        "researchPrompt": str(prompt_dir / f"research-{nn}.md"),
        "retryPrompt": str(prompt_dir / f"retry-{nn}.md"),
        "reviewPrompt": str(prompt_dir / f"review-{nn}.md"),
    }


def load_people(paths):
    prompt = Path(paths["researchPrompt"])
    if not prompt.exists():
        raise SystemExit(f"找不到研究提示：{prompt}")
    people = people_from_prompt(prompt.read_text(encoding="utf-8"))
    if not people:
        raise SystemExit(f"研究提示裡沒有人物清單：{prompt}")
    return people


def have_research(out_dir):
    out = Path(out_dir)
    return (out / "research.json").exists() and (out / "verify-report.json").exists()


def decide_research(out_dir, force):
    if force:
        return True, None
    if have_research(out_dir):
        return False, "已有 research.json 與 verify-report.json"
    return True, None


def load_check_min():
    spec = importlib.util.spec_from_file_location("b3_check_min", CHECK_MIN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_keys(obj, out=None):
    out = set() if out is None else out
    if isinstance(obj, dict):
        key = obj.get("sourceKey")
        if isinstance(key, str):
            out.add(key)
        for value in obj.values():
            source_keys(value, out)
    elif isinstance(obj, list):
        for value in obj:
            source_keys(value, out)
    return out


def _has_gap(person, target, prefix):
    for gap in person.get("gaps") or []:
        if gap.get("target") == target and (gap.get("note") or "").startswith(prefix):
            return True
    return False


def missing_fields(person, row):
    """可補的缺欄（起迄日、引文）與不可補的篇幅。篇幅不拿去重跑。"""
    fields = []
    if row.get("paragraphs", 0) < 3:
        fields.append({
            "field": "paragraphs", "kind": "paragraphs", "fixable": False,
            "detail": f"{row.get('paragraphs', 0)}/3",
        })
    if row.get("zhChars", 0) < 300:
        fields.append({
            "field": "zhChars", "kind": "zh-chars", "fixable": False,
            "detail": f"{row.get('zhChars', 0)}/300",
        })
    for kind, items in (("position", person.get("positions") or []), ("role", person.get("roleCandidates") or [])):
        for item in items:
            key = item.get("key")
            target = f"{kind}:{key}"
            period = item.get("period") or {}
            if not period.get("start"):
                fields.append({
                    "field": f"{target}.start", "kind": "missing-start", "fixable": True, "detail": "缺起日",
                })
            if not period.get("end"):
                noted = _has_gap(person, target, "待查證：缺迄日")
                fields.append({
                    "field": f"{target}.end", "kind": "missing-end", "fixable": True,
                    "detail": "缺迄日（已有待查證：缺迄日）" if noted else "缺迄日",
                })
            citations = item.get("citations") or []
            if not citations:
                fields.append({
                    "field": f"{target}.citations", "kind": "missing-citation", "fixable": True,
                    "detail": "沒有引文",
                })
            else:
                for index, cite in enumerate(citations):
                    if not (cite.get("quote") or "").strip():
                        fields.append({
                            "field": f"{target}.citations[{index}].quote", "kind": "empty-quote",
                            "fixable": True, "detail": "引文空白",
                        })
    for para in person.get("paragraphs") or []:
        where = f"paragraph:{para.get('ord')}"
        citations = para.get("citations") or []
        if not citations:
            fields.append({
                "field": f"{where}.citations", "kind": "missing-citation", "fixable": True,
                "detail": "段落沒有引文",
            })
        else:
            for index, cite in enumerate(citations):
                if not (cite.get("quote") or "").strip():
                    fields.append({
                        "field": f"{where}.citations[{index}].quote", "kind": "empty-quote",
                        "fixable": True, "detail": "引文空白",
                    })
    return fields


def classify_person(person, row):
    fields = missing_fields(person, row)
    fixable = [field for field in fields if field["fixable"]]
    length_only = bool(fields) and not fixable
    if row.get("meetsMinimum"):
        action = "pass"
    elif row.get("documentedShortfall") or length_only:
        action = "shortfall"
    elif fixable:
        action = "retry"
    else:
        action = "shortfall"
    return {
        "action": action,
        "verdict": row.get("verdict"),
        "missingFields": fields,
        "fixableFields": fixable,
        "documentedShortfall": bool(row.get("documentedShortfall")),
        "shortfallFlag": action == "shortfall",
    }


def load_verify_errors(out_dir):
    path = Path(out_dir) / "verify-report.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return list(data.get("errors") or [])


def errors_for_person(errors, person):
    key = person.get("key") or ""
    keys = source_keys(person)
    matched = []
    for error in errors:
        if key and key in error:
            matched.append(error)
            continue
        if any(source and source in error for source in keys):
            matched.append(error)
    return matched


def review_reason(verdict, error_count):
    if error_count:
        return "verify"
    if verdict == "未達":
        return "未達"
    return verdict or "OK"


def annotate(paths, prompt_people, retry_mode):
    """依 research.json 填每個人的缺欄、重跑或篇幅不足、審查要不要升 Opus。

    retry_mode 為 none 時即使有缺欄也不重跑（例如 122 試跑已經重跑過）。
    """
    out_dir = Path(paths["outDir"])
    research_path = out_dir / "research.json"
    details = []
    by_bio = {person["bioId"]: person for person in prompt_people}
    if not research_path.exists():
        return details, {"mode": retry_mode if retry_mode == "auto" else "none", "people": []}, []
    module = load_check_min()
    data = json.loads(research_path.read_text(encoding="utf-8"))
    report = module.report_for(data)
    rows = {row["key"]: row for row in report["people"]}
    errors = load_verify_errors(out_dir)
    retry_people = []
    shortfall = []
    for person in data.get("people") or []:
        row = rows.get(person.get("key"))
        if row is None:
            continue
        info = classify_person(person, row)
        own_errors = errors_for_person(errors, person)
        prompt = by_bio.get(person.get("bioId")) or {
            "nameZh": person.get("nameZh") or person.get("name"),
            "name": person.get("name"),
            "bioId": person.get("bioId"),
            "line": person.get("name") or "",
        }
        detail = dict(prompt)
        detail.update({
            "key": person.get("key"),
            "action": info["action"],
            "verdict": info["verdict"],
            "missingFields": info["missingFields"],
            "fixableFields": info["fixableFields"],
            "documentedShortfall": info["documentedShortfall"],
            "shortfallFlag": info["shortfallFlag"],
            "verifyErrorCount": len(own_errors),
            "escalate": bool(own_errors) or info["verdict"] == "未達",
            "reviewReason": review_reason(info["verdict"], len(own_errors)),
        })
        details.append(detail)
        if info["action"] == "shortfall":
            shortfall.append(detail)
        if retry_mode != "none" and info["action"] == "retry":
            chosen = dict(prompt)
            chosen.update({
                "key": person.get("key"),
                "missingFields": info["fixableFields"],
                "verdict": info["verdict"],
            })
            retry_people.append(chosen)
    if retry_mode == "none":
        retry = {"mode": "none", "people": []}
    elif retry_people:
        retry = {"mode": "list", "people": retry_people}
    elif retry_mode == "auto" and not research_path.exists():
        retry = {"mode": "auto", "people": []}
    else:
        retry = {"mode": "none", "people": []}
    return details, retry, shortfall


def match_retry(paths, people, names, failing_keys):
    by_bio = {person["bioId"]: person for person in people}
    chosen = []
    seen = set()
    research_path = Path(paths["outDir"]) / "research.json"
    if failing_keys and research_path.exists():
        data = json.loads(research_path.read_text(encoding="utf-8"))
        want = set(failing_keys)
        for person in data.get("people") or []:
            if person.get("key") not in want:
                continue
            bio_id = person.get("bioId")
            hit = by_bio.get(bio_id)
            if hit is None:
                raise SystemExit(f"batch{paths['nn']} 的 {person.get('key')} bioId {bio_id} 不在研究提示")
            if bio_id not in seen:
                chosen.append(hit)
                seen.add(bio_id)
        missing_keys = want - {person.get("key") for person in data.get("people") or []}
        if missing_keys:
            raise SystemExit(f"batch{paths['nn']} research.json 沒有 key：{sorted(missing_keys)}")
        return chosen
    by_name = {}
    for person in people:
        for value in (person["name"], person["nameZh"], person["bioId"]):
            by_name[unicodedata.normalize("NFC", value).casefold()] = person
    unmatched = []
    for name in names or []:
        token = name.get("name") if isinstance(name, dict) else name
        hit = by_name.get(unicodedata.normalize("NFC", str(token)).casefold())
        if hit is None:
            unmatched.append(token)
            continue
        if hit["bioId"] not in seen:
            chosen.append(hit)
            seen.add(hit["bioId"])
    if unmatched:
        raise SystemExit(f"batch{paths['nn']} 對不到重跑人物：{unmatched}")
    return chosen


def describe(nn, paths, people, research, reason, retry, review, recheck, details, shortfall, retry_skipped):
    item = dict(paths)
    item.update({
        "research": research,
        "skipResearchReason": reason,
        "retry": retry,
        "review": review,
        "recheck": recheck,
        "people": people,
        "details": details,
        "shortfall": [
            {"bioId": person["bioId"], "name": person["name"], "key": person.get("key"),
             "missingFields": person.get("missingFields") or []}
            for person in shortfall
        ],
        "retrySkipped": retry_skipped,
    })
    return item


def _skipped_retry(details, retry_mode):
    if retry_mode != "none":
        return []
    return [
        {"bioId": person["bioId"], "name": person["name"], "key": person.get("key"),
         "missingFields": person.get("fixableFields") or []}
        for person in details if person.get("action") == "retry"
    ]


def from_chunk(repo, prompt_dir, out_root, raw_root, chunk, force):
    items = []
    for nn in chunk:
        paths = batch_paths(repo, prompt_dir, out_root, raw_root, nn)
        people = load_people(paths)
        research, reason = decide_research(paths["outDir"], force)
        details, retry, shortfall = annotate(paths, people, "none" if research else "list")
        if research:
            retry = {"mode": "auto", "people": []}
        items.append(describe(
            nn, paths, people, research, reason, retry, True, False, details, shortfall,
            _skipped_retry(details, retry["mode"]),
        ))
    return items


def from_resume(repo, prompt_dir, out_root, raw_root, resume_path, chunk, force):
    data = json.loads(Path(resume_path).read_text(encoding="utf-8"))
    want = set(chunk or [])
    retry_map = data.get("needs_retry_and_review") or {}
    retry_done = set(str(nn) for nn in (data.get("retryDone") or []))
    ordered = []
    seen = set()

    def add(nn, retry_mode, review, recheck):
        if want and nn not in want:
            return
        if nn in seen:
            return
        seen.add(nn)
        paths = batch_paths(repo, prompt_dir, out_root, raw_root, nn)
        people = load_people(paths)
        research, reason = decide_research(paths["outDir"], force)
        if nn in retry_done:
            retry_mode = "none"
        if research and retry_mode == "list":
            retry_mode = "auto"
        details, retry, shortfall = annotate(paths, people, "none" if research else retry_mode)
        if research and retry_mode != "none":
            retry = {"mode": "auto", "people": []}
        ordered.append(describe(
            nn, paths, people, research, reason, retry, review, recheck, details, shortfall,
            _skipped_retry(details, retry["mode"]),
        ))

    for nn in data.get("needs_research") or []:
        add(str(nn), "auto", True, False)
    for nn in sorted(retry_map):
        add(str(nn), "list", True, False)
    for nn in data.get("needs_review_only") or []:
        add(str(nn), "none", True, False)
    for nn in data.get("recheck_review") or list(RECHECK_DEFAULT):
        add(str(nn), "none", True, True)
    return ordered, list(data.get("reviewed") or [])


def recompute_chunk(root, start=93, end=122, retry_done=RETRY_DONE_DEFAULT, recheck=RECHECK_DEFAULT):
    """從各批 research.json 重算第四段剩餘清單。不寫 check_min 報告、不改 research.json。"""
    root = Path(root)
    module = load_check_min()
    reviewed, recheck_out, needs_research, review_only = [], [], [], []
    retry, failing_keys = {}, {}
    shortfall, shortfall_keys = {}, {}
    missing = {}
    reviewed_failing = {}
    done = [str(nn) for nn in retry_done]
    recheck_set = {str(nn) for nn in recheck}
    for number in range(start, end + 1):
        nn = f"{number:03d}"
        directory = root / f"batch{nn}"
        research_path = directory / "research.json"
        verify_path = directory / "verify-report.json"
        if not research_path.exists() or not verify_path.exists():
            needs_research.append(nn)
            continue
        data = json.loads(research_path.read_text(encoding="utf-8"))
        report = module.report_for(data)
        rows = {row["key"]: row for row in report["people"]}
        if (directory / "review.json").exists() and nn in recheck_set:
            recheck_out.append(nn)
            continue
        if (directory / "review.json").exists():
            reviewed.append(nn)
            failing = [row.get("name") for row in report["people"] if not row.get("meetsMinimum")]
            if failing:
                reviewed_failing[nn] = failing
            continue
        retry_names, retry_keys = [], []
        short_names, short_keys = [], []
        fields_for = {}
        for person in data.get("people") or []:
            row = rows.get(person.get("key"))
            if row is None:
                continue
            info = classify_person(person, row)
            if info["missingFields"] and info["action"] != "pass":
                fields_for[person["key"]] = info["missingFields"]
            if info["action"] == "retry" and nn not in done:
                retry_names.append(person.get("name"))
                retry_keys.append(person["key"])
            elif info["action"] == "shortfall":
                short_names.append(person.get("name"))
                short_keys.append(person["key"])
        if fields_for:
            missing[nn] = fields_for
        if short_names:
            shortfall[nn] = short_names
            shortfall_keys[nn] = short_keys
        if nn in done or not retry_names:
            review_only.append(nn)
            continue
        retry[nn] = retry_names
        failing_keys[nn] = retry_keys
    note = (
        "2026-11-17 試跑（台北 19:52–20:19，批次 093、105、122，9 人，約 1300 萬 token）之後，"
        "由 tools/b3v3/plan_work.py --recompute-remaining 依各批 research.json 重算，沒有重寫 check_min-report.json。"
        "略過已審查：097、098、100、093（試跑已重跑並審查）、105（試跑已審查）。"
        "093 的佩納被審查拿掉推論迄日，現況是已標註缺迄日；本輪不重跑 093。"
        "122 試跑已做完研究與加強重跑，列入 retryDone，只審查。"
        "096 審查中斷，列入 recheck_review。"
        "needs_retry_and_review 只留可補的缺欄（缺起迄日、缺引文或空白引文）。"
        "documentedShortfall 或只有篇幅不夠的人在 shortfall_review，直接送審並標篇幅不足，不再重跑。"
        "已存原文在 ~/wl-source-cache/b3full-v3，不要重抓。"
    )
    return {
        "note": note,
        "generatedBy": "tools/b3v3/plan_work.py --recompute-remaining",
        "generatedOn": "2026-11-17",
        "reviewed": reviewed,
        "reviewedFailing": reviewed_failing,
        "recheck_review": recheck_out,
        "needs_research": needs_research,
        "needs_retry_and_review": retry,
        "failingKeys": failing_keys,
        "shortfall_review": shortfall,
        "shortfallKeys": shortfall_keys,
        "missingFields": missing,
        "needs_review_only": review_only,
        "retryDone": done,
        "counts": {
            "retryPeople": sum(len(names) for names in retry.values()),
            "shortfallPeople": sum(len(names) for names in shortfall.values()),
            "retryBatches": len(retry),
            "reviewOnlyBatches": len(review_only),
        },
    }


def remaining_summary(payload):
    counts = payload.get("counts") or {}
    lines = [
        f"重算 retry {counts.get('retryPeople', 0)} 人 / {counts.get('retryBatches', 0)} 批，"
        f"篇幅不足 {counts.get('shortfallPeople', 0)} 人，"
        f"只審查 {counts.get('reviewOnlyBatches', 0)} 批",
        "略過 " + "、".join(payload.get("reviewed") or []),
        "重跑 " + "、".join(payload.get("needs_retry_and_review") or []),
        "只審查 " + "、".join(payload.get("needs_review_only") or []),
        "重查 " + "、".join(payload.get("recheck_review") or []),
    ]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="規劃 B3 v3 工作流這次要跑的批")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--prompt-dir")
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--raw-root")
    parser.add_argument("--resume")
    parser.add_argument("--chunk", help="逗號分隔批號，例如 122,093,105")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--force-research", action="store_true")
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--recompute-remaining", help="依 research.json 重寫剩餘清單，不改其他資料檔")
    parser.add_argument("--from", dest="start", type=int, default=93)
    parser.add_argument("--to", dest="end", type=int, default=122)
    args = parser.parse_args(argv)
    if args.recompute_remaining:
        root = resolve(args.repo, args.out_root)
        payload = recompute_chunk(root, args.start, args.end)
        dest = resolve(args.repo, args.recompute_remaining)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        sys.stderr.write(remaining_summary(payload) + "\n")
        sys.stderr.write(f"wrote {dest}\n")
    chunk = [part.strip() for part in (args.chunk or "").split(",") if part.strip()]
    if not args.resume and not chunk:
        if args.recompute_remaining:
            return 0
        raise SystemExit("沒有 --resume 時需要 --chunk")
    if not args.prompt_dir or not args.raw_root:
        raise SystemExit("規劃需要 --prompt-dir 與 --raw-root")
    skipped = []
    if args.resume:
        items, skipped = from_resume(
            args.repo, args.prompt_dir, args.out_root, args.raw_root,
            resolve(args.repo, args.resume), chunk, args.force_research,
        )
    else:
        items = from_chunk(
            args.repo, args.prompt_dir, args.out_root, args.raw_root, chunk, args.force_research,
        )
    if args.limit is not None:
        if args.limit < 0:
            raise SystemExit("--limit 不可為負")
        items = items[:args.limit]
    plan = {
        "concurrency": args.concurrency,
        "batchCount": len(items),
        "skipped": skipped,
        "batches": items,
    }
    json.dump(plan, sys.stdout, ensure_ascii=False, indent=1)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
