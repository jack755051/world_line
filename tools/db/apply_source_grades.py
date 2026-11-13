"""把填好的來源評等清單（data/seed/source-grading/*.csv）套用到開發庫與資料建置檔。規則：docs/source-rules.md §2。
用法：python3 -I tools/db/apply_source_grades.py <清單.csv> [--apply]
- 清單一列是一筆引文；資料庫的等級記在來源（整冊）上，所以取同一來源各列中最低的等級，並把各等級筆數寫進依據。
- 一個來源只要有一列還沒填等級，或填了等級沒填依據，就整個略過並列出。
- 開發庫：只連 5442 的容器（同 tools/battles/db_write.py）；預設交易最後 ROLLBACK，--apply 才 COMMIT。只改 grade 仍是 NULL 的來源。
- 資料建置檔：--apply 時，把 grade／gradeBasis／family 寫進 data/seed/**/requests/**/ 裡標題與網址都相同的來源請求檔，重建資料庫時才會帶著等級。
"""
import collections, csv, glob, json, subprocess, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
CONTAINER, DB = "worldline-borders-dev-db", "worldline_borders_dev"
G, B, F = "這份文件的等級（A／B／C）", "評等依據", "建議家族"
RANK = {"A": 0, "B": 1, "C": 2}


def q(s): return "NULL" if s in (None, "") else "'" + str(s).replace("'", "''") + "'"


def main():
    path = Path(sys.argv[1]); apply = "--apply" in sys.argv
    rows = list(csv.DictReader(path.open(encoding="utf-8-sig")))
    by = collections.defaultdict(list)
    for r in rows: by[r["source_id"]].append(r)
    done, skipped = [], []
    for sid, rs in by.items():
        gs = [(r[G] or "").strip().upper() for r in rs]
        bad = [g for g in gs if g and g not in RANK]
        if bad: skipped.append((rs[0]["來源編號"], f"等級不是 A／B／C：{bad[0]}")); continue
        if not all(gs): skipped.append((rs[0]["來源編號"], f"還有 {gs.count('')}／{len(gs)} 列沒填等級")); continue
        if any(not (r[B] or "").strip() for r in rs): skipped.append((rs[0]["來源編號"], "有的列填了等級沒填依據")); continue
        low = max(gs, key=RANK.get); cnt = collections.Counter(gs)
        fams = {(r[F] or "").strip() for r in rs} - {""}
        if len(fams) > 1: skipped.append((rs[0]["來源編號"], f"同一來源填了不同家族：{sorted(fams)}")); continue
        why = sorted({r[B].strip() for r in rs if r[G].strip().upper() == low})
        basis = f"逐份評等（{path.name}）：" + "、".join(f"{g} {cnt[g]} 筆" for g in "ABC" if cnt[g]) + f"；整冊取最低的 {low}。{low} 的依據：" + "；".join(why[:3]) + ("…" if len(why) > 3 else "")
        done.append({"id": sid, "no": rs[0]["來源編號"], "title": rs[0]["來源標題"], "url": rs[0]["網址"], "grade": low, "basis": basis, "family": next(iter(fams), None)})
    print(f"可套用 {len(done)} 個來源；略過 {len(skipped)} 個")
    for no, why in skipped[:80]: print(f"  略過 {no}：{why}")
    if not done: return 0
    vals = ", ".join(f"({q(x['id'])}::uuid, {q(x['grade'])}, {q(x['basis'])}, {q(x['family'])})" for x in done)
    sql = f"""\\set ON_ERROR_STOP on
BEGIN;
CREATE TEMP TABLE wl_g (id uuid, grade text, basis text, family text) ON COMMIT DROP; INSERT INTO wl_g VALUES {vals};
CREATE TEMP TABLE wl_before ON COMMIT DROP AS SELECT record_kind, confidence, count(*) n FROM v_record_confidence GROUP BY 1, 2;
UPDATE sources s SET grade = g.grade, grade_basis = g.basis, family = coalesce(g.family, s.family), updated_at = now(), version = s.version + 1 FROM wl_g g WHERE s.id = g.id AND s.grade IS NULL;
SELECT 'graded', count(*) FROM sources s JOIN wl_g g ON g.id = s.id WHERE s.grade = g.grade;
SELECT 'verified', a.record_kind, coalesce(b.n, 0) AS before, a.n AS after FROM (SELECT record_kind, count(*) n FROM v_record_confidence WHERE confidence = 'verified' GROUP BY 1) a
  LEFT JOIN wl_before b ON b.record_kind = a.record_kind AND b.confidence = 'verified' ORDER BY 2;
{'COMMIT' if apply else 'ROLLBACK'};
"""
    p = subprocess.run(["docker", "exec", "-i", CONTAINER, "sh", "-c", f'psql -X -q -At -F "|" -U "$POSTGRES_USER" -d {DB}'], input=sql, capture_output=True, text=True)
    print(p.stdout.strip()); print(p.stderr.strip()) if p.stderr.strip() else None
    print(f"[開發庫] {'COMMIT' if apply and p.returncode == 0 else 'ROLLBACK（預演）'}")
    if p.returncode: return p.returncode
    # 資料建置檔
    key = {(x["title"], x["url"]): x for x in done}; hit = 0
    for f in glob.glob(str(REPO / "data" / "seed" / "**" / "requests" / "**" / "*.json"), recursive=True):
        try: d = json.loads(Path(f).read_text(encoding="utf-8"))
        except Exception: continue
        if not isinstance(d, dict) or not str(d.get("_post", "")).endswith("/sources"): continue
        b = d.get("body") or {}; x = key.get((b.get("title"), b.get("url") or ""))
        if not x: continue
        hit += 1
        if apply:
            b["grade"], b["gradeBasis"] = x["grade"], x["basis"]
            if x["family"]: b["family"] = x["family"]
            Path(f).write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[資料建置檔] 對到 {hit} 個來源請求檔{'，已寫入' if apply else '（預演，未寫入）'}")
    print("提醒：國界圖層有日期快取，套用後要重啟開發 API 才會反映。") if apply else None
    return 0


if __name__ == "__main__":
    sys.exit(main())
