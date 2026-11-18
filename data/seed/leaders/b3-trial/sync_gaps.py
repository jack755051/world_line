#!/usr/bin/env python3
"""人物生平缺口（leader_bio_gaps）seed → 5442 開發庫同步（Tai 2026-11-14「先處理」）。

用途：seed 只改了 gaps（例：候選引文補等級、移除 X 級候選）時，把庫內對應的缺口換成新版。
B3 有多套 seed（batch*、run100/batch*、full/batch*），同一 bio 可能出現在兩套，所以只在
「庫內有效缺口＝這次修改前（--since）的 seed 版本」時才換：撤回舊列（I5 不刪）＋寫入新列。
庫內對不上（別套 seed 寫的）或庫內沒有的缺口都不動，列在報告裡。
預設 dry-run；--send --allow-write 才在單一交易寫入。寫入前請先 pg_dump 備份。
用法（repo 根目錄）：
  python3 -I data/seed/leaders/b3-trial/sync_gaps.py --since <commit> [--path data/seed/leaders/b3-trial] [--send --allow-write]
"""
import argparse, json, sys, subprocess, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(HERE / "run100"))
import write_b3_paragraphs as W  # noqa: E402

DEV = REPO / ".dev" / "dbwrite"
RUN = "gap-sync-2026-11-14"
WHY = RUN + "：缺口內容更新（候選引文補等級／移除 X 級候選，來源規則 I6／D4），由新列取代"


def qjson(sql):
    r = subprocess.run(["docker", "exec", "-i", W.CONTAINER, "psql", "-U", W.DBUSER, "-d", W.DBNAME, "-At", "-v", "ON_ERROR_STOP=1"],
                       input="select coalesce(json_agg(t),'[]'::json)::text from (%s) t" % sql, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr[:500])
    return json.loads(r.stdout)


def gapmap(person):
    out = {}
    for g in (person or {}).get("gaps") or []:
        t, _ = W.norm_field_target(g.get("target"))
        out[(t or g.get("target"), g.get("gapKind"))] = g
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", required=True); ap.add_argument("--path", default=str(HERE.relative_to(REPO)))
    ap.add_argument("--send", action="store_true"); ap.add_argument("--allow-write", action="store_true")
    a = ap.parse_args()
    files = [f for f in subprocess.run(["git", "diff", "--name-only", a.since, "HEAD", "--", a.path], capture_output=True, text=True, cwd=REPO).stdout.split()
             if f.endswith("research.json")]
    changes = []  # (file, personKey, bio, key, old_gap, new_gap)
    for f in files:
        old = subprocess.run(["git", "show", a.since + ":" + f], capture_output=True, text=True, cwd=REPO)
        if old.returncode:
            continue
        o = {p["key"]: p for p in json.loads(old.stdout).get("people") or []}
        for p in json.loads((REPO / f).read_text()).get("people") or []:
            if not p.get("bioId"):
                continue
            og, ng = gapmap(o.get(p["key"])), gapmap(p)
            for k in set(og) | set(ng):
                if json.dumps(og.get(k), sort_keys=True) != json.dumps(ng.get(k), sort_keys=True):
                    changes.append((f, p["key"], p["bioId"], k, og.get(k), ng.get(k)))
    bios = sorted({c[2] for c in changes}) or ["00000000-0000-0000-0000-000000000000"]
    db = {(r["bio_id"], r["target"], r["gap_kind"]): r for r in qjson(
        "select id,bio_id,target,gap_kind,note,candidate_citations,checked_on from leader_bio_gaps "
        "where retracted_at is null and resolved_at is null and bio_id in ('%s')" % "','".join(bios))}
    plan, skipped, done = [], [], set()
    for f, pk, bio, (t, kind), og, ng in changes:
        r = db.get((bio, t, kind))
        tag = (f.split("leaders/")[-1], pk, t, kind)
        if (bio, t, kind) in done:
            skipped.append(tag + ("同一缺口已由另一套 seed 的變更處理",)); continue
        if r is None:
            skipped.append(tag + ("庫內沒有這個缺口（未寫過或已撤回）",)); continue
        if og is None:
            skipped.append(tag + ("seed 修改前沒有這個缺口，庫內版本來源不明",)); continue
        same_old = (r["note"] == og.get("note") and (r["candidate_citations"] or []) == (og.get("candidateCitations") or [])
                    and str(r["checked_on"])[:10] == str(og.get("checkedOn"))[:10])
        if not same_old:
            skipped.append(tag + ("庫內版本與修改前的 seed 不同（可能由別套 seed 寫入），不動",)); continue
        plan.append((r, bio, t, kind, ng, tag)); done.add((bio, t, kind))
    L = W.sql_lit
    q = ["BEGIN;"]
    for r, bio, t, kind, ng, tag in plan:
        q.append("UPDATE leader_bio_gaps SET retracted_at=now(), retraction_reason=%s WHERE id=%s AND retracted_at IS NULL;" % (L(WHY), L(r["id"])))
        if ng is not None:
            q.append("INSERT INTO leader_bio_gaps (bio_id,target,gap_kind,note,candidate_citations,checked_on) VALUES (%s,%s,%s,%s,%s::jsonb,%s);" %
                     (L(bio), L(t), L(kind), L(ng.get("note")), L(ng.get("candidateCitations") or []), L(ng.get("checkedOn"))))
    q.append("COMMIT;")
    DEV.mkdir(parents=True, exist_ok=True)
    (DEV / "gap-sync.sql").write_text("\n".join(q) + "\n", encoding="utf-8")
    summ = {"seed_gap_changes": len(changes), "replace": sum(1 for x in plan if x[4] is not None), "retract_only": sum(1 for x in plan if x[4] is None),
            "skipped": len(skipped), "skipped_reasons": {}}
    for s in skipped:
        summ["skipped_reasons"][s[-1]] = summ["skipped_reasons"].get(s[-1], 0) + 1
    (DEV / ("gap-sync-result.json" if a.send else "gap-sync-dryrun.json")).write_text(json.dumps(
        {"at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "summary": summ,
         "replace": [x[5] for x in plan], "skipped": skipped}, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(summ, ensure_ascii=False, indent=1))
    if not a.send:
        print("（dry-run；未寫庫；SQL 見 .dev/dbwrite/gap-sync.sql）"); return
    if not a.allow_write:
        raise SystemExit("需 --send --allow-write")
    r = subprocess.run(["docker", "exec", "-i", W.CONTAINER, "psql", "-U", W.DBUSER, "-d", W.DBNAME, "-v", "ON_ERROR_STOP=1", "-1", "-q"],
                       input="\n".join(q) + "\n", capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("寫入失敗（整筆交易回滾）：" + r.stderr[:800])
    print("已寫入。")


if __name__ == "__main__":
    main()
