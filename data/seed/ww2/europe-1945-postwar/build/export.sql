-- 開發庫（5442）唯讀匯出；輸出到 ../db-export/（不進版控，見 README）
-- eu45_rows.json
SELECT json_agg(json_build_object('id', s.id, 'slug', r.slug, 'regimeId', s.regime_id, 'start', lower(s.valid_period), 'end', upper(s.valid_period), 'layer', s.layer_status,
  'startEventId', s.start_event_id, 'endEventId', s.end_event_id, 'geometrySourceId', s.geometry_source_id, 'geometryLocator', s.geometry_locator, 'geometryLicense', s.geometry_license,
  'attribution', s.attribution, 'ohmRelationId', s.ohm_relation_id, 'ohmVersion', s.ohm_version, 'ohmFetchedAt', s.ohm_fetched_at, 'ohmStartRaw', s.ohm_start_raw, 'ohmEndRaw', s.ohm_end_raw,
  'provenance', s.provenance, 'note', s.note, 'geometry', ST_AsGeoJSON(s.geom)::json))
FROM sovereignty_records s JOIN regimes r ON r.id = s.regime_id
WHERE s.retracted_at IS NULL AND (s.id IN ('01a1920c-fed8-74b8-ae2f-32e69561f6c8','01a1920c-ff98-7f3b-b937-2d41ffeddd18','01a1920d-0002-7757-8a35-87b34ad55e30','01a191a0-a35a-7b02-80bb-e3f6dbabdbe9')
  OR upper(s.valid_period) = date '1945-05-09');
-- eu45_active0508.json
SELECT ST_AsGeoJSON(ST_Union(s.geom))::json FROM sovereignty_records s WHERE s.retracted_at IS NULL AND s.valid_period @> date '1945-05-08' AND ST_Intersects(s.geom, ST_MakeEnvelope(-12,34,42,72,4326)) AND upper(s.valid_period) <> date '1945-05-09';
-- eu45_active0901.json
SELECT json_agg(json_build_object('slug', r.slug, 'geometry', ST_AsGeoJSON(s.geom)::json)) FROM sovereignty_records s JOIN regimes r ON r.id=s.regime_id WHERE s.retracted_at IS NULL AND s.valid_period @> date '1945-09-01';
