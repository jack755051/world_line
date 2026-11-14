"""替沒有起始事件的主權紀錄判定「來歷」，寫進 sovereignty_record_links（docs/source-rules.md D5）。
用法：python3 -I tools/db/classify_sovereignty_origin.py [--apply]
只處理：未撤回、沒有 start_event_id、而且還沒有來歷紀錄的主權紀錄。判定全由資料算出，不查資料、不推測事件：
  baseline        起始日在第一階段起點（1908-01-01）或更早：期初既有
  continuation    同一政權有前一筆在同一天結束，兩者形狀相同（對稱差 < 0.1%）：只是資料分段，可信程度沿用前一筆
  minor_revision  同上但形狀差在 0.1%–2% 之間：多半是資料版本差異，也可能是小幅調整，要人看
  change          同上但形狀差 ≥ 2%：疆界有變動，需要有出處的事件
  new             同一政權沒有前一筆：新出現的政權或領地，需要有出處的事件
主權紀錄被撤回重寫後，指向舊紀錄的來歷會先被撤回再重新判定；事後補上的起始事件（start_event_id）若在被撤回的來歷上，要用 apply_border_events.py 重新連。
只連 5442 開發庫的容器；預設交易最後 ROLLBACK，--apply 才 COMMIT。可重跑。重建資料庫後要重跑一次。
"""
import subprocess, sys
CONTAINER, DB = "worldline-borders-dev-db", "worldline_borders_dev"
PHASE_START = "1908-01-01"
SQL = f"""\\set ON_ERROR_STOP on
BEGIN;
-- 主權紀錄被撤回重寫後（例：補回被裁切的幾何），指向舊紀錄的來歷已經失效：先撤回，下面再替新紀錄重新判定
WITH stale AS (UPDATE sovereignty_record_links l SET retracted_at = now(), retraction_reason = '所指的主權紀錄已撤回重寫，重新判定'
  WHERE l.retracted_at IS NULL AND (EXISTS (SELECT 1 FROM sovereignty_records v WHERE v.id = l.record_id AND v.retracted_at IS NOT NULL)
     OR EXISTS (SELECT 1 FROM sovereignty_records v WHERE v.id = l.continues_record_id AND v.retracted_at IS NOT NULL)) RETURNING 1)
SELECT '撤回失效的來歷', count(*) FROM stale;
CREATE TEMP TABLE wl_t ON COMMIT DROP AS
SELECT v.id, v.regime_id, lower(v.valid_period) AS s, v.geom
FROM sovereignty_records v
WHERE v.retracted_at IS NULL AND v.start_event_id IS NULL
  AND NOT EXISTS (SELECT 1 FROM sovereignty_record_links l WHERE l.record_id = v.id AND l.retracted_at IS NULL);
CREATE TEMP TABLE wl_c ON COMMIT DROP AS
SELECT t.id, t.s, p.id AS prev, p.ratio
FROM wl_t t LEFT JOIN LATERAL (
  SELECT p.id, ST_Area(ST_SymDifference(ST_MakeValid(t.geom), ST_MakeValid(p.geom))::geography) / NULLIF(ST_Area(ST_MakeValid(p.geom)::geography), 0) AS ratio
  FROM sovereignty_records p
  WHERE p.regime_id = t.regime_id AND p.retracted_at IS NULL AND p.id <> t.id AND upper(p.valid_period) = t.s
  ORDER BY 2 NULLS LAST LIMIT 1) p ON true;
INSERT INTO sovereignty_record_links (record_id, kind, continues_record_id, shape_change_ratio, note)
SELECT id,
       CASE WHEN s <= DATE '{PHASE_START}' THEN 'baseline' WHEN prev IS NULL THEN 'new'
            WHEN ratio < 0.001 THEN 'continuation' WHEN ratio < 0.02 THEN 'minor_revision' ELSE 'change' END,
       CASE WHEN s <= DATE '{PHASE_START}' THEN NULL ELSE prev END,
       CASE WHEN s <= DATE '{PHASE_START}' THEN NULL ELSE ratio END,
       'tools/db/classify_sovereignty_origin.py 依起始日與形狀比對自動判定'
FROM wl_c;
SELECT '判定', kind, count(*) FROM sovereignty_record_links WHERE retracted_at IS NULL GROUP BY 2 ORDER BY 3 DESC;
SELECT '可信程度', confidence, basis, count(*) FROM v_record_confidence WHERE record_kind = 'sovereignty' GROUP BY 2, 3 ORDER BY 4 DESC;
__END__;
"""


def main():
    apply = "--apply" in sys.argv
    p = subprocess.run(["docker", "exec", "-i", CONTAINER, "sh", "-c", f'psql -X -q -At -F "｜" -U "$POSTGRES_USER" -d {DB}'],
                       input=SQL.replace("__END__", "COMMIT" if apply else "ROLLBACK"), capture_output=True, text=True)
    print(p.stdout.strip())
    if p.stderr.strip(): print(p.stderr.strip())
    print(f"[開發庫] {'COMMIT' if apply and p.returncode == 0 else 'ROLLBACK（預演）'}")
    return p.returncode


if __name__ == "__main__":
    sys.exit(main())
