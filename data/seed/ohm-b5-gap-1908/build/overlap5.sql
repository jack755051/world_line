-- 跨政權疊合檢查（唯讀：只用 session 暫存表，最後 ROLLBACK）
\set ON_ERROR_STOP on
BEGIN;
CREATE TEMP TABLE c(cid text, slug text, s date, e date, gj text, layer text);
\copy c FROM pstdin WITH (FORMAT csv)
CREATE TEMP TABLE cg AS SELECT cid, slug, s, e, layer, ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(gj),4326)),3)) g FROM c;
CREATE TEMP TABLE o AS
 SELECT cg.cid, r.id oid, rg.slug oslug, lower(r.valid_period) os, coalesce(upper(r.valid_period),'9999-12-31') oe, r.geom og
 FROM cg JOIN sovereignty_records r ON r.retracted_at IS NULL AND r.valid_period && daterange(cg.s, cg.e) AND ST_Intersects(r.geom, cg.g)
 JOIN regimes rg ON rg.id = r.regime_id WHERE rg.slug <> cg.slug;
-- 第 5 批（沿用既有幾何）不做同批互扣：同批彼此的關係與後續既有紀錄相同
CREATE TEMP TABLE bp AS
 SELECT DISTINCT cid, d FROM (SELECT cid, s d FROM cg UNION SELECT cid, e FROM cg
   UNION SELECT o.cid, o.os FROM o JOIN cg USING (cid) WHERE o.os > cg.s AND o.os < cg.e
   UNION SELECT o.cid, o.oe FROM o JOIN cg USING (cid) WHERE o.oe > cg.s AND o.oe < cg.e) x;
CREATE TEMP TABLE sub AS SELECT cid, d a, lead(d) OVER (PARTITION BY cid ORDER BY d) b FROM bp;
DELETE FROM sub WHERE b IS NULL;
CREATE TEMP TABLE res AS
 SELECT sub.cid, sub.a, sub.b, cg.g,
   (SELECT ST_Union(o.og) FROM o WHERE o.cid = sub.cid AND o.os <= sub.a AND o.oe >= sub.b) u,
   (SELECT string_agg(o.oslug || coalesce(':' || o.oid, ''), ' ' ORDER BY o.oslug) FROM o WHERE o.cid = sub.cid AND o.os <= sub.a AND o.oe >= sub.b) others
 FROM sub JOIN cg USING (cid);
CREATE TEMP TABLE out1 AS
 SELECT cid, a, b, others, g, CASE WHEN u IS NULL THEN g ELSE ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_Difference(g, u)),3)) END rest FROM res;
-- 去掉疊合相減後的細條：每個多邊形 < 50 km² 且內縮 200 m 後消失者丟掉
CREATE TEMP TABLE out2 AS
 SELECT cid, a, b, others, ST_Area(g::geography)/1e6 cand_km2,
   coalesce((SELECT ST_Multi(ST_Collect(p.geom)) FROM ST_Dump(rest) p
      WHERE NOT (ST_Area(p.geom::geography) < 5e7 AND ST_IsEmpty(ST_Buffer(p.geom, -0.002)))), 'MULTIPOLYGON EMPTY'::geometry) rest2
 FROM out1;
\copy (SELECT cid, a, b, coalesce(others,''), round(cand_km2::numeric,1), round((ST_Area(rest2::geography)/1e6)::numeric,1), ST_AsGeoJSON(rest2, 6) FROM out2 ORDER BY cid, a) TO pstdout WITH (FORMAT csv)
ROLLBACK;
