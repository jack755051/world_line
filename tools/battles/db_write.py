"""執行 write_battle_sql.py 產生的 SQL：預設 dry-run（單一交易、最後 ROLLBACK），--apply 才 COMMIT。
用法：python3 -I tools/battles/db_write.py <battle> [--apply]
- 只連 5442 開發庫：docker 容器 worldline-borders-dev-db 內的 worldline_borders_dev（帳號取容器環境變數，不印出）；寫死，不接受其他目標。
- 交易內比對 public 全部資料表寫入前後筆數，並檢查新增的戰役列全部掛在本戰役 event_id 下、新增來源只被本戰役引用；任一不符即 ROLLBACK 並報錯。
- 報表寫到 data/seed/battles/<battle>/db/<battle>.{dry-run,apply}.txt。
"""
import json, subprocess, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
CONTAINER, DB = "worldline-borders-dev-db", "worldline_borders_dev"

COUNTS = """SELECT table_name AS t, (xpath('/row/c/text()', query_to_xml(format('SELECT count(*) AS c FROM public.%I', table_name), false, true, '')))[1]::text::bigint AS n
FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"""


def main():
    battle = sys.argv[1]; apply = "--apply" in sys.argv
    D = REPO / "data/seed/battles" / battle / "db"
    plan = json.loads((D / f"{battle}.write-plan.json").read_text()); ev = plan["eventId"]
    body = (D / f"{battle}.write.sql").read_text()
    check = f"""
CREATE TEMP TABLE wl_after AS {COUNTS};
SELECT 'DIFF', a.t, a.n - b.n FROM wl_after a JOIN wl_before b USING (t) WHERE a.n <> b.n ORDER BY 2;
DO $$ DECLARE bad bigint; BEGIN
  SELECT count(*) INTO bad FROM wl_after a JOIN wl_before b USING (t) WHERE a.n <> b.n AND a.t NOT IN
    ('historical_events','battle_profiles','battle_profile_citations','event_participants','battle_phases','battle_phase_citations',
     'battle_map_features','battle_map_feature_citations','battle_units','battle_unit_citations','sources');
  IF bad > 0 THEN RAISE EXCEPTION '寫入觸及戰役以外的資料表：%', bad; END IF;
  SELECT (SELECT count(*) FROM battle_profiles WHERE event_id <> '{ev}') + (SELECT count(*) FROM battle_phases WHERE event_id <> '{ev}')
       + (SELECT count(*) FROM battle_units WHERE event_id <> '{ev}')
       + (SELECT count(*) FROM battle_map_features f JOIN battle_phases p ON p.id = f.phase_id WHERE p.event_id <> '{ev}') INTO bad;
  IF bad > 0 THEN RAISE EXCEPTION '有不屬於本戰役的戰役列：%', bad; END IF;
END $$;
SELECT 'EVENT', id, event_kind, occurred FROM historical_events WHERE id = '{ev}';
SELECT 'PROFILE', slug, status FROM battle_profiles WHERE event_id = '{ev}';
SELECT 'PARTICIPANT', r.slug FROM event_participants p JOIN regimes r ON r.id = p.regime_id WHERE p.event_id = '{ev}' ORDER BY 2;
SELECT 'FEATURES', feature_kind, geom_basis, count(*) FROM battle_map_features f JOIN battle_phases p ON p.id = f.phase_id WHERE p.event_id = '{ev}' GROUP BY 2, 3 ORDER BY 2, 3;
"""
    end = "COMMIT;" if apply else "ROLLBACK;"
    script = f"\\set ON_ERROR_STOP on\nBEGIN;\nCREATE TEMP TABLE wl_before AS {COUNTS};\n{body}\n{check}\n{end}\n"
    p = subprocess.run(["docker", "exec", "-i", CONTAINER, "sh", "-c", f'psql -X -q -At -F "|" -U "$POSTGRES_USER" -d {DB}'],
                       input=script, capture_output=True, text=True)
    out = p.stdout + ("\n[stderr]\n" + p.stderr if p.stderr.strip() else "") + f"\n[exit {p.returncode}] {'COMMIT' if apply and p.returncode == 0 else 'ROLLBACK'}\n"
    (D / f"{battle}.{'apply' if apply else 'dry-run'}.txt").write_text(out)
    print(out[-3000:]); sys.exit(p.returncode)


if __name__ == "__main__":
    main()
