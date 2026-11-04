-- 國名點 label_points（ARCHITECTURE.md §9 模組表；建置產物）：
-- 每段 boundary_periods（＝每個政權的每個時期）一個點，放在該時期「最大塊國土」上，
-- 位置用 polylabel（pole of inaccessibility；PostGIS 的 ST_MaximumInscribedCircle 圓心即同一點）。
-- 最大塊以球面面積（geography）比較；area 為該塊面積（km²），供標籤排序（symbol-sort-key）。
-- span_x：該塊外框的經度寬 ÷ 360（世界寬＝1），前端「名字裝得下才顯示」（§4 D9，與 label-fit.labelMinZoom 同式）用。
-- 名稱：自稱（name_kind = self，優先 is_primary）；name_zh＝display 的 zh-Hant，name_local＝原文；name＝name_zh，沒有就用原文。
WITH parts AS (
  SELECT bp.record_id, bp.regime_id, bp.regime_slug, bp.start_day, bp.end_day, d.geom AS part,
         ST_Area(d.geom::geography) AS area_m2,
         row_number() OVER (PARTITION BY bp.record_id ORDER BY ST_Area(d.geom::geography) DESC) AS rn
  FROM boundary_periods bp, LATERAL ST_Dump(bp.geom) d
)
SELECT p.record_id, p.regime_id, p.regime_slug, p.start_day, p.end_day,
       (ST_MaximumInscribedCircle(p.part)).center AS geom,
       COALESCE(n.display ->> 'zh-Hant', n.original_text) AS name,
       n.display ->> 'zh-Hant' AS name_zh,
       n.original_text AS name_local,
       round(p.area_m2 / 1e6)::bigint AS area,
       round(((ST_XMax(p.part) - ST_XMin(p.part)) / 360.0)::numeric, 7)::float8 AS span_x
FROM parts p
LEFT JOIN LATERAL (
  SELECT display, original_text FROM regime_names
  WHERE regime_id = p.regime_id AND name_kind = 'self' AND retracted_at IS NULL
  ORDER BY is_primary DESC, created_at
  LIMIT 1
) n ON true
WHERE p.rn = 1
