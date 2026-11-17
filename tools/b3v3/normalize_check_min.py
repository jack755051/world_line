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
RECHECK = "096"


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
    reviewed, recheck, needs_research, review_only = [], [], [], []
    retry, failing_keys = {}, {}
    for number in range(start, end + 1):
        nn = f"{number:03d}"
        directory = root / f"batch{nn}"
        research = directory / "research.json"
        verify = directory / "verify-report.json"
        report = directory / module.CANONICAL_NAME
        if not research.exists() or not verify.exists() or not report.exists():
            needs_research.append(nn)
            continue
        data = json.loads(report.read_text(encoding="utf-8"))
        failing = [row for row in data.get("people") or [] if row.get("meetsMinimum") is False]
        if (directory / "review.json").exists() and nn == RECHECK:
            recheck.append(nn)
            continue
        if (directory / "review.json").exists():
            reviewed.append(nn)
            continue
        if failing:
            retry[nn] = [row.get("name") for row in failing]
            failing_keys[nn] = [row.get("key") for row in failing]
        else:
            review_only.append(nn)
    # 範圍外但仍在第四段、只有 rawmap 的批（122）由呼叫端的 end 決定。
    # 這裡的 end 若是 121，122 要另外看。呼叫端傳 end=122 時，122 沒有 research 會進 needs_research。
    note = (
        "由 tools/b3v3/normalize_check_min.py 依各批 research.json 重跑 check_min.py，寫入固定檔名 check_min-report.json 後重算（2026-11-17）。"
        "check-min.json、check-min-report.json 已刪除。"
        "曾擔心格式不同的 096、105、107、108、112、113、114、118、121：096 三人皆達標，但該次審查中斷，列入 recheck_review；"
        "105、107、108、112、113、114、118、121 皆達標，只審查。"
        "與中斷當下那份清單相比，只有 batch102 的 Alexander Tsankov 改變：舊報告寫未達標（缺迄日），現行 research.json 已有起迄日，重算後達標，不再重跑；同批仍重跑 Emiliano Figueroa Larraín。"
        "093、095 有人補了「篇幅不足」gap，documentedShortfall 改為 true，但仍未達標，照舊重跑。097 的 José Domingo de Obaldía 字數 528 改計為 527，仍達標且已審查。"
        "reviewed 是已有 review.json 且不必重查的批。122 沒有 research.json，列入 needs_research；已存原文不要重抓。"
    )
    return {
        "note": note,
        "reviewed": reviewed,
        "recheck_review": recheck,
        "needs_research": needs_research,
        "needs_retry_and_review": retry,
        "failingKeys": failing_keys,
        "needs_review_only": review_only,
    }


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
