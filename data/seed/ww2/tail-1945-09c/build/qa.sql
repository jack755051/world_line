SELECT '@@_REGIMES', (SELECT count(DISTINCT regime_id) FROM sovereignty_records WHERE retracted_at IS NULL AND valid_period @> date '1945-09-01') d0901,
 (SELECT count(DISTINCT regime_id) FROM sovereignty_records WHERE retracted_at IS NULL AND valid_period @> date '1945-09-15') d0915,
 (SELECT count(DISTINCT regime_id) FROM sovereignty_records WHERE retracted_at IS NULL AND valid_period @> date '1945-09-30') d0930;
SELECT '@@_XOVERLAP', d::date, ra.slug, a.layer_status, rb.slug, b.layer_status, round((ST_Area(ST_Intersection(a.geom,b.geom)::geography)/1e6)::numeric,1) km2
 FROM (VALUES (date '1945-09-01'),(date '1945-09-15'),(date '1945-09-30')) dd(d)
 JOIN sovereignty_records a ON a.retracted_at IS NULL AND a.valid_period @> dd.d
 JOIN sovereignty_records b ON b.retracted_at IS NULL AND b.valid_period @> dd.d AND a.regime_id<b.regime_id AND a.layer_status=b.layer_status AND a.geom && b.geom AND ST_Intersects(a.geom,b.geom)
 JOIN regimes ra ON ra.id=a.regime_id JOIN regimes rb ON rb.id=b.regime_id
 WHERE ST_Area(ST_Intersection(a.geom,b.geom)::geography) > 1e6 ORDER BY 2,7 DESC;
SELECT '@@_INVALID', count(*) FROM sovereignty_records WHERE retracted_at IS NULL AND valid_period && daterange('1945-08-01','1945-10-01') AND NOT ST_IsValid(geom);
WITH zone AS (SELECT ST_Union(geom) g FROM sovereignty_records WHERE id IN ('01a191c9-0ad1-7d5c-af30-6706db83b998','01a1948d-ad3b-76a3-aaae-9b218b90597f','01a1943f-da30-72bc-a07a-93f344fc6694','01a1943f-d5ab-78aa-a7d4-e119e80510d8','01a1948d-8049-744d-8a2e-6fee6ca01e8d','01a1943f-c3b6-7f13-ab4d-8a7d5b219165','01a1948d-b38d-73df-a3c0-e516b6e2c896','01a1948d-b060-7adc-b11b-4a1f1f3029bc','01a1943f-e8f5-713e-85e7-843c42e468d7','01a191c9-0f2a-7cbb-b019-5961b91deb00','01a19410-0c0a-78b6-876e-3407f764d23e','01a1948d-b6c5-7dec-be84-d4f8e805290b','01a1943f-ccd3-7e21-987e-572f029d9229'))
SELECT '@@_UNCOVERED', d::date, round((ST_Area(ST_Difference(zone.g, (SELECT ST_Union(geom) FROM sovereignty_records s WHERE s.retracted_at IS NULL AND s.valid_period @> dd.d AND s.geom && zone.g))::geography)/1e6)::numeric,1) km2
 FROM zone, (VALUES (date '1945-09-01'),(date '1945-09-15'),(date '1945-09-30')) dd(d);
SELECT '@@_SUNION', (SELECT round((ST_Area(ST_Difference(geom,(SELECT ST_Union(geom) FROM sovereignty_records WHERE retracted_at IS NULL AND valid_period @> date '1945-09-30'))::geography)/1e6)::numeric,1) FROM sovereignty_records WHERE id='01a1942c-aed4-7ac2-ba6d-0c051586a544') su_uncovered_0930;
