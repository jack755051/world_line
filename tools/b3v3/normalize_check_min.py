#!/usr/bin/env python3
"""把既有批次的最低標準報告收成 check_min-report.json，並重算剩餘工作清單。

    python3 -I tools/b3v3/normalize_check_min.py \\
        --from 093 --to 121 \\
        --root data/seed/leaders/b3-trial/full/v3 \\
        --remaining .dev/b3v3/partial/chunk4-remaining.json

只重寫報告檔與剩餘清單，不改 research.json。
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CHECK_MIN = REPO / "data" / "seed" / "leaders" / "b3-trial" / "full" / "v3" / "check_min.py"


def load_check_min():
    spec = importlib.util.spec_from_file_location("b3_check_min", CHECK_MIN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_old_failing(directory, module):
    names = []
    for path in sorted(directory.iterdir()):
        if path.name != module.CANONICAL_NAME and path.name not in module.ALIAS_NAMES:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for row in data.get("people") or []:
            if row.get("meetsMinimum") is False:
                names.append(row.get("name"))
    return names


def normalize_range(root, start, end, module):
    notes = []
    for number in range(start, end + 1):
        directory = root / f"batch{number:03d}"
        research = directory / "research.json"
        if not research.exists():
            notes.append(f"{number:03d} 沒有 research.json，略過")
            continue
        before = read_old_failing(directory, module)
        data = json.loads(research.read_text(encoding="utf-8"))
        text = module.render(module.report_for(data))
        dest = directory / module.CANONICAL_NAME
        previous = dest.read_text(encoding="utf-8") if dest.exists() else None
        if previous != text:
            dest.write_text(text, encoding="utf-8")
            notes.append(f"{number:03d} 重寫 {module.CANONICAL_NAME}")
        for alias in module.ALIAS_NAMES:
            alias_path = directory / alias
            if alias_path.exists():
                alias_path.unlink()
                notes.append(f"{number:03d} 刪除別名 {alias}")
        after = [
            row.get("name")
            for row in json.loads(dest.read_text(encoding="utf-8")).get("people") or []
            if row.get("meetsMinimum") is False
        ]
        if before != after:
            notes.append(f"{number:03d} 未達標名單改變 {before} -> {after}")
    return notes


def recompute_remaining(root, start, end, module):
    """剩餘清單改由 plan_work.recompute_chunk 決定（篇幅不足不重跑、122 只審查）。"""
    del module
    spec = importlib.util.spec_from_file_location("plan_work", REPO / "tools" / "b3v3" / "plan_work.py")
    module_plan = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module_plan)
    return module_plan.recompute_chunk(root, start, end)


def main(argv=None):
    parser = argparse.ArgumentParser(description="正規化 check_min 報告並重算剩餘清單")
    parser.add_argument("--root", default="data/seed/leaders/b3-trial/full/v3")
    parser.add_argument("--from", dest="start", type=int, default=93)
    parser.add_argument("--to", dest="end", type=int, default=122)
    parser.add_argument("--remaining", default=".dev/b3v3/partial/chunk4-remaining.json")
    parser.add_argument("--repo", default=str(REPO))
    args = parser.parse_args(argv)
    repo = Path(args.repo)
    root = Path(args.root)
    if not root.is_absolute():
        root = repo / root
    module = load_check_min()
    # 報告只正規化有 research.json 的批；122 沒有，迴圈會略過。
    notes = normalize_range(root, args.start, args.end, module)
    remaining = recompute_remaining(root, args.start, args.end, module)
    dest = Path(args.remaining)
    if not dest.is_absolute():
        dest = repo / dest
    dest.write_text(json.dumps(remaining, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {dest}")
    for line in notes:
        print(line)
    print(
        "reviewed", len(remaining["reviewed"]),
        "recheck", remaining["recheck_review"],
        "research", remaining["needs_research"],
        "retry", list(remaining["needs_retry_and_review"]),
        "review_only", remaining["needs_review_only"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
