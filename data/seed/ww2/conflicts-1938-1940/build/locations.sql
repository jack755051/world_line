-- 衝突圖示位置：兩國主權圖層（sovereignty_records，OHM 釘版）在開戰日的共同邊界上，取最長一段邊界線的中點。
-- 用法：psql 讀取開發庫（唯讀）；輸出 key、經度、緯度、邊界長度（度）。
WITH pairs(k, a, b, d) AS (VALUES
  ('DE_PL', 'deutsches-reich', 'polish-republic', DATE '1939-09-01'),
  ('FR_DE', 'french-third-republic', 'deutsches-reich', DATE '1939-09-03'),
  ('SU_PL', 'soviet-union', 'polish-republic', DATE '1939-09-17'),
  ('SU_FI', 'soviet-union', 'republic-of-finland', DATE '1939-11-30'),
  ('DE_DK', 'deutsches-reich', 'kingdom-of-denmark', DATE '1940-04-09'),
  ('DE_NL', 'deutsches-reich', 'kingdom-of-the-netherlands', DATE '1940-05-10'),
  ('DE_BE', 'deutsches-reich', 'kingdom-of-belgium', DATE '1940-05-10'),
  ('DE_LU', 'deutsches-reich', 'grand-duchy-of-luxembourg', DATE '1940-05-10'),
  ('IT_FR', 'kingdom-of-italy', 'french-third-republic', DATE '1940-06-10'),
  ('IT_GR', 'albania-under-italy', 'kingdom-of-greece', DATE '1940-10-28')
), g AS (
  SELECT p.k, p.d,
    (SELECT ST_Union(s.geom) FROM sovereignty_records s JOIN regimes r ON r.id = s.regime_id
      WHERE r.slug = p.a AND s.retracted_at IS NULL AND s.valid_period @> p.d) AS ga,
    (SELECT ST_Union(s.geom) FROM sovereignty_records s JOIN regimes r ON r.id = s.regime_id
      WHERE r.slug = p.b AND s.retracted_at IS NULL AND s.valid_period @> p.d) AS gb
  FROM pairs p
), seg AS (
  SELECT k, (ST_Dump(ST_LineMerge(ST_CollectionExtract(ST_Intersection(ST_Boundary(ga), ST_Buffer(gb, 0.02)), 2)))).geom AS l
  FROM g
), best AS (
  SELECT DISTINCT ON (k) k, l FROM seg ORDER BY k, ST_Length(l) DESC
)
SELECT k, round(ST_X(ST_LineInterpolatePoint(l, 0.5))::numeric, 4) AS lon,
       round(ST_Y(ST_LineInterpolatePoint(l, 0.5))::numeric, 4) AS lat, round(ST_Length(l)::numeric, 2) AS len
FROM best ORDER BY k;
