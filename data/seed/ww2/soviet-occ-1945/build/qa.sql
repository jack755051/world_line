SELECT '@@_REGIMES', (SELECT count(DISTINCT regime_id) FROM sovereignty_records WHERE retracted_at IS NULL AND valid_period @> date '1945-08-26'),
 (SELECT count(DISTINCT regime_id) FROM sovereignty_records WHERE retracted_at IS NULL AND valid_period @> date '1945-09-01'),
 (SELECT count(DISTINCT regime_id) FROM sovereignty_records WHERE retracted_at IS NULL AND valid_period @> date '1945-09-15'),
 (SELECT count(DISTINCT regime_id) FROM sovereignty_records WHERE retracted_at IS NULL AND valid_period @> date '1945-09-30');
SELECT '@@_JPOVERLAP', d::date, ra.slug, a.layer_status, rb.slug, b.layer_status, round((ST_Area(ST_Intersection(a.geom,b.geom)::geography)/1e6)::numeric,2)
 FROM (VALUES (date '1945-08-24'),(date '1945-08-26'),(date '1945-09-02'),(date '1945-09-06'),(date '1945-09-15'),(date '1945-09-30')) dd(d)
 JOIN sovereignty_records a ON a.retracted_at IS NULL AND a.valid_period @> dd.d
 JOIN regimes ra ON ra.id=a.regime_id AND ra.slug IN ('empire-of-japan','soviet-occupied-karafuto-kurils')
 JOIN sovereignty_records b ON b.retracted_at IS NULL AND b.valid_period @> dd.d AND b.id<>a.id AND b.regime_id<>a.regime_id AND a.geom && b.geom AND ST_Intersects(a.geom,b.geom)
 JOIN regimes rb ON rb.id=b.regime_id WHERE ST_Area(ST_Intersection(a.geom,b.geom)::geography) > 1e4 ORDER BY 2;
SELECT '@@_XOVERLAP', d::date, ra.slug, rb.slug, round((ST_Area(ST_Intersection(a.geom,b.geom)::geography)/1e6)::numeric,1)
 FROM (VALUES (date '1945-09-15'),(date '1945-09-30')) dd(d)
 JOIN sovereignty_records a ON a.retracted_at IS NULL AND a.valid_period @> dd.d
 JOIN sovereignty_records b ON b.retracted_at IS NULL AND b.valid_period @> dd.d AND a.regime_id<b.regime_id AND a.geom && b.geom AND ST_Intersects(a.geom,b.geom)
 JOIN regimes ra ON ra.id=a.regime_id JOIN regimes rb ON rb.id=b.regime_id
 WHERE ST_Area(ST_Intersection(a.geom,b.geom)::geography) > 1e6 ORDER BY 2,5 DESC;
SELECT '@@_UNCOVERED', d::date, round((ST_Area(ST_Difference(z.geom, (SELECT ST_Union(geom) FROM sovereignty_records s WHERE s.retracted_at IS NULL AND s.valid_period @> dd.d AND s.geom && z.geom))::geography)/1e6)::numeric,2)
 FROM sovereignty_records z, (VALUES (date '1945-08-24'),(date '1945-08-26'),(date '1945-09-02'),(date '1945-09-06'),(date '1945-09-15'),(date '1945-09-30')) dd(d) WHERE z.id='01a1aacc-b342-7718-a9e1-9f9c9e64e421';
SELECT '@@_INVALID', count(*) FROM sovereignty_records WHERE retracted_at IS NULL AND valid_period && daterange('1945-08-01','1945-10-01') AND NOT ST_IsValid(geom);
