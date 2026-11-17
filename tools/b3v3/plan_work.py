#!/usr/bin/env python3
"""列出這次工作流要跑的批與階段。stdout 只印 JSON。

有 research.json 與 verify-report.json 就略過研究，除非 --force-research。
--resume 決定重跑哪些人、審查哪些批（已審查且不在 recheck_review 的批不列入）。
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

RECHECK_DEFAULT = ("096",)


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


def describe(nn, paths, people, research, reason, retry, review, recheck):
    item = dict(paths)
    item.update({
        "research": research,
        "skipResearchReason": reason,
        "retry": retry,
        "review": review,
        "recheck": recheck,
        "people": people,
    })
    return item


def from_chunk(repo, prompt_dir, out_root, raw_root, chunk, force):
    items = []
    for nn in chunk:
        paths = batch_paths(repo, prompt_dir, out_root, raw_root, nn)
        people = load_people(paths)
        research, reason = decide_research(paths["outDir"], force)
        items.append(describe(
            nn, paths, people, research, reason,
            {"mode": "auto", "people": []}, True, False,
        ))
    return items


def from_resume(repo, prompt_dir, out_root, raw_root, resume_path, chunk, force):
    data = json.loads(Path(resume_path).read_text(encoding="utf-8"))
    want = set(chunk or [])
    failing = data.get("failingKeys") or {}
    retry_map = data.get("needs_retry_and_review") or {}
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
        if retry_mode == "list":
            names = retry_map.get(nn) or []
            keys = failing.get(nn) or []
            chosen = match_retry(paths, people, names, keys)
            retry = {"mode": "list", "people": chosen}
        elif retry_mode == "auto":
            retry = {"mode": "auto", "people": []}
        else:
            retry = {"mode": "none", "people": []}
        ordered.append(describe(nn, paths, people, research, reason, retry, review, recheck))

    for nn in data.get("needs_research") or []:
        add(str(nn), "auto", True, False)
    for nn in sorted(retry_map):
        add(str(nn), "list", True, False)
    for nn in data.get("needs_review_only") or []:
        add(str(nn), "none", True, False)
    for nn in data.get("recheck_review") or list(RECHECK_DEFAULT):
        add(str(nn), "none", True, True)
    return ordered


def main(argv=None):
    parser = argparse.ArgumentParser(description="規劃 B3 v3 工作流這次要跑的批")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--prompt-dir", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--raw-root", required=True)
    parser.add_argument("--resume")
    parser.add_argument("--chunk", help="逗號分隔批號，例如 122,093,105")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--force-research", action="store_true")
    parser.add_argument("--concurrency", type=int, default=3)
    args = parser.parse_args(argv)
    chunk = [part.strip() for part in (args.chunk or "").split(",") if part.strip()]
    if args.resume:
        items = from_resume(
            args.repo, args.prompt_dir, args.out_root, args.raw_root,
            resolve(args.repo, args.resume), chunk, args.force_research,
        )
    else:
        if not chunk:
            raise SystemExit("沒有 --resume 時需要 --chunk")
        items = from_chunk(
            args.repo, args.prompt_dir, args.out_root, args.raw_root, chunk, args.force_research,
        )
    if args.limit is not None:
        if args.limit < 0:
            raise SystemExit("--limit 不可為負")
        items = items[:args.limit]
    plan = {"concurrency": args.concurrency, "batchCount": len(items), "batches": items}
    json.dump(plan, sys.stdout, ensure_ascii=False, indent=1)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
