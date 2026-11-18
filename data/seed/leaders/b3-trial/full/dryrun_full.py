#!/usr/bin/env python3
"""B3 full 寫庫 dry-run：沿用 run100/write_b3_paragraphs.py 的 plan()／summary()（同一套規則），只換 seed 來源為 full/batchNNN。

只讀 5442（SELECT 對帳），沒有寫庫路徑（不呼叫 build_sql、不接受 --send）。
用法：python3 -I data/seed/leaders/b3-trial/full/dryrun_full.py [batch001 batch002 …]（不給＝全部已 commit 的批次）
輸出：.dev/b3full-write-dryrun.txt、.dev/b3full-role-conflicts.md（不 commit）。
"""
import importlib.util, json, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("w3", HERE.parent / "run100" / "write_b3_paragraphs.py")
w3 = importlib.util.module_from_spec(spec); spec.loader.exec_module(w3)
assert w3.WRITE_ENABLED is False

def main():
    want = set(sys.argv[1:])
    repo = HERE.parents[4]
    batches = []
    for d in sorted(HERE.glob("batch[0-9][0-9][0-9]")):
        f = d / "research.json"
        rel = str(f.relative_to(repo))
        committed = subprocess.run(["git", "-C", str(repo), "ls-files", "--error-unmatch", str((d / "review.json").relative_to(repo))], capture_output=True).returncode == 0
        if f.exists() and committed and (not want or d.name in want):
            batches.append((d.name, json.loads(f.read_text(encoding="utf-8"))))
    overrides = json.load(open(w3.OVERRIDES)) if os.path.exists(w3.OVERRIDES) else {}
    st = w3.db_state(None)
    P = w3.plan(batches, st, overrides)
    text = w3.summary(P).replace("B3 分段生平寫入 dry-run（只讀 5442；未寫庫）", "B3 full 寫入 dry-run（只讀 5442；未寫庫；批次：%s）" % "、".join(b for b, _ in batches))
    dev = repo / ".dev"
    (dev / "b3full-write-dryrun.txt").write_text(text + "\n", encoding="utf-8")
    (dev / "b3full-role-conflicts.md").write_text(w3.conflicts_md(P) + "\n", encoding="utf-8")
    print(text + "\n\n（dry-run；未寫庫）")

if __name__ == "__main__":
    main()
