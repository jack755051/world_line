"""把「國界 → 起始事件」的判定（data/seed/source-grading/borders-without-event.csv）套用到開發庫。規則：docs/source-rules.md D5。
用法：python3 -I tools/db/apply_border_events.py <清單.csv> [--apply]
只處理「要連的既有事件 event_id」有填的列：把該主權紀錄的來歷紀錄撤回，另寫一筆帶起始事件的（I5：不改原列）。
「起始日可確定到」一欄：出處只能把起始日確定到月或年時填 month／year，畫面會照實標示（docs/source-rules.md §7）。
新事件要先照一般流程建立（附引文與等級），拿到 event_id 之後再填進清單。已經連好的不會重複處理。
只連 5442 開發庫的容器；預設交易最後 ROLLBACK，--apply 才 COMMIT。
"""
import csv, subprocess, sys
from pathlib import Path
CONTAINER, DB = "worldline-borders-dev-db", "worldline_borders_dev"
E, N, PR = "要連的既有事件 event_id", "備註", "起始日可確定到（day／month／year）"


def q(s): return "NULL" if s in (None, "") else "'" + str(s).replace("'", "''") + "'"


def main():
    path = Path(sys.argv[1]); apply = "--apply" in sys.argv
    rows = [r for r in csv.DictReader(path.open(encoding="utf-8-sig")) if (r[E] or "").strip()]
    print(f"清單中有填事件的列：{len(rows)}")
    if not rows: return 0
    for r in rows:
        r["_p"] = (r.get(PR) or "").strip().lower() or None
        if r["_p"] not in (None, "day", "month", "year"): sys.exit(f"{r['政權代號']} {r['起始日']}：起始日精度只能填 day／month／year")
    vals = ", ".join(f"({q(r['record_id'])}::uuid, {q(r[E].strip())}::uuid, {q((r[N] or '').strip() or None)}, {q(r['_p'])})" for r in rows)
    sql = f"""\\set ON_ERROR_STOP on
BEGIN;
CREATE TEMP TABLE wl_e (record_id uuid, event_id uuid, note text, prec text) ON COMMIT DROP; INSERT INTO wl_e VALUES {vals};
SELECT '事件不存在或已撤回', count(*) FROM wl_e w WHERE NOT EXISTS (SELECT 1 FROM historical_events e WHERE e.id = w.event_id AND e.retracted_at IS NULL);
DELETE FROM wl_e w WHERE NOT EXISTS (SELECT 1 FROM historical_events e WHERE e.id = w.event_id AND e.retracted_at IS NULL);
DELETE FROM wl_e w WHERE EXISTS (SELECT 1 FROM sovereignty_record_links l WHERE l.record_id = w.record_id AND l.retracted_at IS NULL AND l.start_event_id = w.event_id AND l.start_date_precision IS NOT DISTINCT FROM w.prec);
CREATE TEMP TABLE wl_before ON COMMIT DROP AS SELECT count(*) n FROM v_record_confidence WHERE record_kind = 'sovereignty' AND confidence = 'verified';
CREATE TEMP TABLE wl_old ON COMMIT DROP AS SELECT l.* FROM sovereignty_record_links l JOIN wl_e w ON w.record_id = l.record_id WHERE l.retracted_at IS NULL;
UPDATE sovereignty_record_links l SET retracted_at = now(), retraction_reason = '補上起始事件（{path.name}）' FROM wl_old o WHERE o.id = l.id;
WITH ins AS (INSERT INTO sovereignty_record_links (record_id, kind, continues_record_id, start_event_id, shape_change_ratio, note, start_date_precision)
  SELECT w.record_id, coalesce(o.kind, 'change'), o.continues_record_id, w.event_id, o.shape_change_ratio, w.note, w.prec FROM wl_e w LEFT JOIN wl_old o ON o.record_id = w.record_id RETURNING 1)
SELECT '連上起始事件', count(*) FROM ins;
SELECT '已查證的國界', (SELECT n FROM wl_before) || ' → ' || count(*) FROM v_record_confidence WHERE record_kind = 'sovereignty' AND confidence = 'verified';
{'COMMIT' if apply else 'ROLLBACK'};
"""
    p = subprocess.run(["docker", "exec", "-i", CONTAINER, "sh", "-c", f'psql -X -q -At -F "｜" -U "$POSTGRES_USER" -d {DB}'], input=sql, capture_output=True, text=True)
    print(p.stdout.strip())
    if p.stderr.strip(): print(p.stderr.strip())
    print(f"[開發庫] {'COMMIT' if apply and p.returncode == 0 else 'ROLLBACK（預演）'}")
    return p.returncode


if __name__ == "__main__":
    sys.exit(main())
