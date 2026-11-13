"""把填好的來源評等清單（data/seed/source-grading/*.csv）套用到開發庫與資料建置檔。規則：docs/source-rules.md §2。
用法：python3 -I tools/db/apply_source_grades.py <清單.csv> [--apply]
- 清單一列是一筆引文。等級記在「那一筆引文」上（event_citation_grades），所以可以只填一部分，填了的列就生效。
- 同一筆引文已經有等級且不同 → 依 I5 撤回舊的、另寫一列；相同則不動。可重跑。
- 來源（整冊）層級：某來源的列全部填完時，另把 sources.grade 設成其中最低的一級，當作以後新引文的預設；家族有填就寫入 sources.family。
- 開發庫：只連 5442 的容器（同 tools/battles/db_write.py）；預設交易最後 ROLLBACK，--apply 才 COMMIT。
- 資料建置檔：--apply 時把 grade／gradeBasis 寫進 data/seed/**/requests/** 對應的事件請求檔的那筆引文、把 family 寫進來源請求檔，重建資料庫時才會帶著。
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
    filled, problems = [], []
    for n, r in enumerate(rows, 2):
        g = (r[G] or "").strip().upper()
        if not g: continue
        if g not in RANK: problems.append(f"第 {n} 列（{r['來源編號']}）：等級「{r[G]}」不是 A／B／C"); continue
        if not (r[B] or "").strip(): problems.append(f"第 {n} 列（{r['來源編號']}）：填了等級沒填依據"); continue
        filled.append({**r, "g": g, "b": r[B].strip()})
    print(f"清單 {len(rows)} 列：已填 {len(filled)}、未填 {len(rows) - len(filled) - len(problems)}、有問題 {len(problems)}")
    for p in problems[:40]: print("  " + p)
    if not filled: return 1 if problems else 0
    by = collections.defaultdict(list)
    for r in rows: by[r["source_id"]].append(r)
    src = []   # (source_id, grade or None, basis or None, family or None)
    for sid, rs in by.items():
        fr = [r for r in filled if r["source_id"] == sid]
        fams = {(r[F] or "").strip() for r in fr} - {""}
        if len(fams) > 1: print(f"  {rs[0]['來源編號']}：同一來源填了不同家族 {sorted(fams)}，家族不寫入"); fams = set()
        grade = basis = None
        if fr and len(fr) == len(rs):
            cnt = collections.Counter(r["g"] for r in fr); grade = max(cnt, key=RANK.get)
            basis = f"逐份評等（{path.name}）：" + "、".join(f"{g} {cnt[g]} 筆" for g in "ABC" if cnt[g]) + f"；整冊預設取最低的 {grade}，個別引文以各自的等級為準"
        if fr and (grade or fams): src.append((sid, grade, basis, next(iter(fams), None)))
    cv = ", ".join(f"({q(r['event_id'])}::uuid, {q(r['source_id'])}::uuid, {q(r['引用位置'])}, {q(r['g'])}, {q(r['b'])})" for r in filled)
    sv = ", ".join(f"({q(a)}::uuid, {q(g)}, {q(b)}, {q(f)})" for a, g, b, f in src) or "(NULL::uuid, NULL, NULL, NULL)"
    reason = f"引文等級更正（{path.name}）"
    sql = f"""\\set ON_ERROR_STOP on
BEGIN;
CREATE TEMP TABLE wl_c (event_id uuid, source_id uuid, locator text, grade text, basis text) ON COMMIT DROP; INSERT INTO wl_c VALUES {cv};
CREATE TEMP TABLE wl_s (id uuid, grade text, basis text, family text) ON COMMIT DROP; INSERT INTO wl_s VALUES {sv};
CREATE TEMP TABLE wl_before ON COMMIT DROP AS SELECT record_kind, count(*) n FROM v_record_confidence WHERE confidence = 'verified' GROUP BY 1;
SELECT '對不到引文（資料庫裡沒有這筆引文）', count(*) FROM wl_c w WHERE NOT EXISTS (SELECT 1 FROM event_citations c WHERE c.event_id = w.event_id AND c.source_id = w.source_id AND c.locator = w.locator);
DELETE FROM wl_c w WHERE NOT EXISTS (SELECT 1 FROM event_citations c WHERE c.event_id = w.event_id AND c.source_id = w.source_id AND c.locator = w.locator);
UPDATE event_citation_grades g SET retracted_at = now(), retraction_reason = {q(reason)} FROM wl_c w
  WHERE g.event_id = w.event_id AND g.source_id = w.source_id AND g.locator = w.locator AND g.retracted_at IS NULL AND (g.grade <> w.grade OR g.grade_basis <> w.basis);
WITH ins AS (INSERT INTO event_citation_grades (event_id, source_id, locator, grade, grade_basis)
  SELECT w.event_id, w.source_id, w.locator, w.grade, w.basis FROM wl_c w
  WHERE NOT EXISTS (SELECT 1 FROM event_citation_grades g WHERE g.event_id = w.event_id AND g.source_id = w.source_id AND g.locator = w.locator AND g.retracted_at IS NULL) RETURNING 1)
SELECT '寫入引文等級', count(*) FROM ins;
UPDATE sources s SET grade = coalesce(s.grade, w.grade), grade_basis = CASE WHEN s.grade IS NULL THEN w.basis ELSE s.grade_basis END, family = coalesce(s.family, w.family),
  updated_at = now(), version = s.version + 1 FROM wl_s w WHERE s.id = w.id AND ((s.grade IS NULL AND w.grade IS NOT NULL) OR (s.family IS NULL AND w.family IS NOT NULL));
SELECT '已查證筆數', a.record_kind, coalesce(b.n, 0) || ' → ' || a.n FROM (SELECT record_kind, count(*) n FROM v_record_confidence WHERE confidence = 'verified' GROUP BY 1) a
  LEFT JOIN wl_before b USING (record_kind) ORDER BY 2;
{'COMMIT' if apply else 'ROLLBACK'};
"""
    p = subprocess.run(["docker", "exec", "-i", CONTAINER, "sh", "-c", f'psql -X -q -At -F "｜" -U "$POSTGRES_USER" -d {DB}'], input=sql, capture_output=True, text=True)
    print(p.stdout.strip())
    if p.stderr.strip(): print(p.stderr.strip())
    print(f"[開發庫] {'COMMIT' if apply and p.returncode == 0 else 'ROLLBACK（預演）'}")
    if p.returncode: return p.returncode
    # 資料建置檔：事件請求檔的引文加 grade／gradeBasis；來源請求檔加 family
    want = {(r["來源標題"], r["網址"], r["引用位置"], r["事件日期"]): r for r in filled}
    fam = {(r["來源標題"], r["網址"]): (r[F] or "").strip() for r in filled if (r[F] or "").strip()}
    hit = fhit = 0; found = set()
    batches = collections.defaultdict(list)
    for f in glob.glob(str(REPO / "data" / "seed" / "**" / "requests" / "**" / "*.json"), recursive=True):
        batches[f[:f.index("/requests/")]].append(f)
    loaded = {}
    for batch, files in batches.items():
        for f in files:
            try: d = json.loads(Path(f).read_text(encoding="utf-8"))
            except Exception: continue
            if isinstance(d, dict) and isinstance(d.get("body"), dict): loaded.setdefault(batch, {})[f] = d
    is_src = lambda d: str(d.get("_post", "")).endswith("/sources")
    # 來源代號先在同一批找；找不到（引用別批登記的來源）再用全專案的對照，同名但內容不同的代號不採用
    glob_src, clash = {}, set()
    for docs in loaded.values():
        for d in docs.values():
            if is_src(d):
                k = d.get("_placeholder"); t = (d["body"].get("title"), d["body"].get("url") or "")
                if k in glob_src and glob_src[k] != t: clash.add(k)
                glob_src[k] = t
    by_id = {(r["source_id"], r["引用位置"], r["事件日期"]): r for r in filled}
    for batch, docs in loaded.items():
        local = {d.get("_placeholder"): (d["body"].get("title"), d["body"].get("url") or "") for d in docs.values() if is_src(d)}
        for f, d in docs.items():
            post = str(d.get("_post", "")).split("?")[0]; b = d["body"]; changed = False
            if is_src(d) and fam.get((b.get("title"), b.get("url") or "")) and b.get("family") != fam[(b.get("title"), b.get("url") or "")]:
                b["family"] = fam[(b.get("title"), b.get("url") or "")]; fhit += 1; changed = True
            if post.endswith("/events"):
                day = ((b.get("occurred") or {}).get("start") or "")[:10]
                for c in b.get("citations") or []:
                    k = str(c.get("sourceId") or "").strip("{}"); loc = (c.get("locator") or "").strip()
                    t = local.get(k) or (glob_src.get(k) if k not in clash else None)
                    r = want.get((t[0], t[1], loc, day)) if t else by_id.get((k, loc, day))   # 直接寫 UUID 的引用用來源 id 對
                    if not r: continue
                    found.add((r["event_id"], r["source_id"], r["引用位置"]))
                    if c.get("grade") != r["g"] or c.get("gradeBasis") != r["b"]: c["grade"], c["gradeBasis"] = r["g"], r["b"]; hit += 1; changed = True
            if changed and apply: Path(f).write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    miss = len({(r["event_id"], r["source_id"], r["引用位置"]) for r in filled} - found)
    print(f"[資料建置檔] 引文 {hit} 筆、來源家族 {fhit} 個{'已寫入' if apply else '會寫入（預演，未寫入）'}；清單中 {miss} 筆在資料建置檔裡對不到")
    if apply: print("提醒：國界圖層有日期快取，套用後要重啟開發 API 才會反映。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
