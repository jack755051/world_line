#!/usr/bin/env python3
"""B3 全量（full）名單與提示（Tai 2026-11-11 21:24 全量；21:25 主要領導人優先）。

不連資料庫，只讀 repo 內檔案：
  - pool-snapshot.tsv：5442 唯讀快照（export_pool_snapshot.sql 產生）：現行 leader_bios 924 人（existing_bios.tsv 923 人＋2026-11-11 重建的邱吉爾）
    與 leader_records 任期數、1908–1945 窗內任期日數
  - ../run100/selection100.json：排除 run100 的 100 人（含已寫入 98 人與零段落 2 人）
  - ../run100/build_selection100.py：沿用其 load()/profile() 推地區、政權類型、年代、厚薄
  - ../run100/PROMPT_research.md、PROMPT_review.md：提示沿用，只替換路徑與批次標籤（見 REPLACE）
排序：PRIORITY（Tai 21:25 指定、庫內存在者，依指定順序）→ 其餘依 1908–1945 窗內元首／首腦任期日數、任期數、厚薄、姓名排序。
每批 5 人（最後一批可少於 5）。輸出：selection-full.json、PROMPT_research.md、PROMPT_review.md（固定、無時間戳，連跑兩次逐位元相同）。
用法：python3 -I data/seed/leaders/b3-trial/full/build_full.py
"""
import csv, importlib.util, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN100 = HERE.parent / "run100"
BATCH_SIZE = 5
# Tai 2026-11-11 21:25 指定（順序照指定）；bioId 已於 2026-11-11 21:3x 以唯讀 SELECT 核對 5442 現行列
PRIORITY = [
    ("邱吉爾", "01a1c86e-c89b-70af-afe0-1ad0f4be2bf8"), ("希特勒", "01a19f15-35f4-7d9a-847a-aeccc98305ec"),
    ("史達林", "01a1b492-3efd-7d05-8a70-3f38fdf9d599"), ("羅斯福", "01a1b48b-c87a-768a-b372-2918df397b6c"),
    ("墨索里尼", "0ff6f55e-8f9c-49aa-b9ba-5858a17c9dc3"), ("裕仁天皇", "01a1b4b2-2f65-7cca-9a4b-ff875f18c192"),
    ("東條英機", "62241525-b2f1-4931-bfb3-30ecf9dd3094"), ("蔣中正", "01a1b490-dcc7-76dc-82d7-da76fb59d7d2"),
    ("孫中山", None), ("袁世凱", None),
    ("列寧", "01a1b492-3ee1-75ee-8fc7-306c07a85a65"), ("威廉二世", "01a19f15-3574-776f-a3e9-348733e035e7"),
    ("法蘭茲·約瑟夫", "01a1b4b5-f9d8-7310-b964-ed7578856680"), ("尼古拉二世", "01a1b4b5-f9bc-7f2f-90ba-f2af428ba89c"),
    ("勞合喬治", "01a19f15-33c3-7fff-a8d9-5521e842fb87"), ("張伯倫", "01a19f15-3507-788a-9d61-83862bf96e28"),
    ("威爾遜", "01a1b48b-c814-7f78-bba8-753c5a5ea41f"), ("克里蒙梭", "ef990cdf-5286-44c4-8e0a-1e8aaa1c629b"),
    ("貝當", None), ("戴高樂", None),
    ("佛朗哥", "01a1b48b-c890-7320-84f4-1442207f5f03"), ("凱末爾", "01a1b492-3f04-7906-a59b-b9bfcc8f374d"),
]
REPLACE = {  # 舊字串 → (新字串, 預期出現次數下限)
    "research": [("B3 run100 batch{{NN}}", "B3 full batch{{NN}}", 1), ("/tmp/b3run100/", "/tmp/b3full/", 1),
                 ("b3-trial/run100/batch{{NN}}", "b3-trial/full/batch{{NN}}", 1),
                 ("`data/seed/leaders/b3-trial/run100/selection100.json`", "`data/seed/leaders/b3-trial/full/selection-full.json`", 1),
                 ("b3-run100-batch{{NN}}", "b3-full-batch{{NN}}", 1),
                 ("⑤T14 建議套用）。", "⑤T14 建議套用）、21:24（全量其餘人物，規格與提示沿用 run100）。", 1)],
    "review": [("B3 run100 batch{{NN}}", "B3 full batch{{NN}}", 1),
               ("data/seed/leaders/b3-trial/run100/PROMPT_research.md", "data/seed/leaders/b3-trial/full/PROMPT_research.md", 1),
               ('"promptVersion": "run100-v1"', '"promptVersion": "full-v1（=run100-v1）"', 1)],
}


def load_run100_builder():
    spec = importlib.util.spec_from_file_location("bs100", RUN100 / "build_selection100.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def render_prompts():
    for kind, fname in (("research", "PROMPT_research.md"), ("review", "PROMPT_review.md")):
        t = (RUN100 / fname).read_text(encoding="utf-8")
        for old, new, n in REPLACE[kind]:
            c = t.count(old)
            if c < n:
                sys.exit(f"{fname}: 找不到預期字串 {old!r}（{c}）")
            t = t.replace(old, new)
        if "run100/batch{{NN}}" in t or "b3run100" in t:
            sys.exit(f"{fname}: 仍有 run100 批次路徑")
        (HERE / fname).write_text(t, encoding="utf-8")


def main():
    bs = load_run100_builder()
    tsv, info, _ = bs.load()
    snap = {}
    with open(HERE / "pool-snapshot.tsv", encoding="utf-8", newline="") as f:
        for row in csv.reader(f, delimiter="\t"):
            if row and row[0].strip():
                snap[row[0]] = {"name": row[1], "nameZh": row[2], "records": int(row[3]), "windowDays": int(row[4]), "firstTerm": row[5] or None}
    run100 = {p["bioId"] for p in json.loads((RUN100 / "selection100.json").read_text(encoding="utf-8"))["people"]}
    missing_tsv = sorted(set(tsv) - set(snap))
    extra = sorted(set(snap) - set(tsv))
    if missing_tsv:
        sys.exit(f"existing_bios.tsv 有 {len(missing_tsv)} 人不在快照（庫內無現行列）")
    pool = [b for b in snap if b not in run100]
    prio_in = [(zh, b) for zh, b in PRIORITY if b]
    for zh, b in prio_in:
        if b not in snap:
            sys.exit(f"PRIORITY {zh} {b} 不在快照")
        if b in run100:
            sys.exit(f"PRIORITY {zh} 已在 run100（不應重跑）")
    prio_ids = [b for _, b in prio_in]
    tier_rank = {"厚": 0, "中": 1, "薄": 2}
    people = []
    for b in pool:
        s = snap[b]
        rec = tsv.get(b) or {"bioId": b, "name": s["name"], "nameZh": s["nameZh"], "birthYear": None, "deathYear": None}
        prof = bs.profile(rec, info.get(b))
        people.append({"bioId": b, "name": s["name"], "nameZh": s["nameZh"] or None, "records": s["records"],
                       "windowDays": s["windowDays"], "firstTerm": s["firstTerm"], **prof,
                       "priority": prio_ids.index(b) + 1 if b in prio_ids else None,
                       "inTsv": b in tsv})
    people.sort(key=lambda p: (0, p["priority"]) if p["priority"] else
                (1, -p["windowDays"], -p["records"], tier_rank.get(p["thickness"], 3), p["name"], p["bioId"]))
    for i, p in enumerate(people):
        p["batch"] = f"{i // BATCH_SIZE + 1:03d}"
        p["order"] = i + 1
    nb = (len(people) + BATCH_SIZE - 1) // BATCH_SIZE
    out = {"run": "b3-full", "decision": "Tai 2026-11-11 21:24 全量（923 扣 run100）；21:25 主要領導人優先", "offlineOnly": True,
           "pool": {"snapshot": len(snap), "existingBiosTsv": len(tsv), "notInTsv": [snap[b]["name"] for b in extra],
                    "excludedRun100": len(run100), "selected": len(people)},
           "priorityRequested": [zh for zh, _ in PRIORITY],
           "priorityNotInDb": [zh for zh, b in PRIORITY if not b],
           "priorityInRun100": [],
           "ordering": "PRIORITY 依指定順序；其餘依 1908–1945 窗內 leader_records 任期日數（降冪）、任期數（降冪）、厚薄（厚→中→薄）、姓名",
           "batchSize": BATCH_SIZE, "batches": nb, "people": people}
    (HERE / "selection-full.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    render_prompts()
    print(f"pool={len(snap)} tsv={len(tsv)} run100={len(run100)} selected={len(people)} batches={nb} priority={len(prio_ids)} notInDb={out['priorityNotInDb']}")


if __name__ == "__main__":
    main()
