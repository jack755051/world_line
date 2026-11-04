#!/bin/zsh
# 疆界圖磚建置（ARCHITECTURE.md §9 遷移步驟 3）：PostGIS → GeoJSONSeq → tippecanoe → boundaries-v{hash}.pmtiles＋manifest.json
# 只讀開發庫；工具一律用 docker image（不做全域安裝）：
#   - tippecanoe：wl-tippecanoe:2.79.0（由 felt/tippecanoe 的 2.79.0 tag 以 docker build 建出，見 README）
# 用法：zsh tools/tiles/build.sh            產物在 tools/tiles/out/
# 環境變數：WL_DB_CONTAINER（預設 worldline-borders-dev-db）、WL_TIPPECANOE_IMAGE、WL_MAXZOOM（預設 8）
set -euo pipefail
export PATH=/usr/local/bin:$PATH
HERE=${0:A:h}
OUT=$HERE/out
DB=${WL_DB_CONTAINER:-worldline-borders-dev-db}
TIPPE=${WL_TIPPECANOE_IMAGE:-wl-tippecanoe:2.79.0}
MAXZOOM=${WL_MAXZOOM:-8}
mkdir -p $OUT
U=$(docker exec $DB printenv POSTGRES_USER); D=$(docker exec $DB printenv POSTGRES_DB)
q() { docker exec -i $DB psql -U $U -d $D -v ON_ERROR_STOP=1 -At -q }
t0=$(date +%s)

echo "[1/4] 匯出 boundaries（boundary_periods）"
q > $OUT/boundaries.geojsonseq <<'SQL'
SELECT json_build_object(
  'type', 'Feature',
  'geometry', ST_AsGeoJSON(geom, 6)::json,
  'properties', json_build_object(
    'regime_id', regime_id, 'start_day', start_day, 'end_day', end_day,
    'color_idx', color_idx, 'disputed', disputed, 'control_type', control_type))
FROM boundary_periods ORDER BY start_day, regime_id;
SQL

echo "[2/4] 匯出 labels（label_points：最大塊國土上的 polylabel）"
{ echo "SELECT json_build_object('type','Feature','geometry',ST_AsGeoJSON(geom,6)::json,'properties',json_build_object("
  echo "'regime_id',regime_id,'start_day',start_day,'end_day',end_day,'name_zh',name_zh,'name_local',name_local,'area',area,'span_x',span_x))"
  echo "FROM ("; cat $HERE/sql/label_points.sql; echo ") lp ORDER BY start_day, regime_id;"; } | q > $OUT/labels.geojsonseq

# 變動日（manifest.changeDays）：所有段落的起訖日
q > $OUT/change-days.txt <<'SQL'
SELECT d FROM (SELECT start_day d FROM boundary_periods UNION SELECT end_day FROM boundary_periods WHERE end_day < 2147483647) x ORDER BY d;
SQL

HASH=$(cat $OUT/boundaries.geojsonseq $OUT/labels.geojsonseq | shasum -a 256 | cut -c1-12)
NAME=boundaries-v$HASH
echo "[3/4] tippecanoe → $NAME（z0–z$MAXZOOM）"
rm -f $OUT/$NAME.mbtiles $OUT/$NAME.pmtiles
# 正確性優先：不因圖磚大小或要素數丟要素（--no-feature-limit／--no-tile-size-limit），小國不以小方塊代替（--no-tiny-polygon-reduction），
# 國名點不抽稀（-r1）；相鄰國界共用簡化（--detect-shared-borders，§9 風險對策）。圖磚大小另行記錄。
docker run --rm -v $OUT:/data $TIPPE tippecanoe -o /data/$NAME.mbtiles -Z0 -z$MAXZOOM \
  --read-parallel --no-feature-limit --no-tile-size-limit --no-tiny-polygon-reduction -r1 \
  --detect-shared-borders --simplification=4 \
  -L boundaries:/data/boundaries.geojsonseq -L labels:/data/labels.geojsonseq \
  --name="World Line boundaries" --attribution="OpenHistoricalMap contributors (CC0) 等，見 API provenance" --quiet
docker run --rm -v $OUT:/data $TIPPE tile-join -o /data/$NAME.pmtiles --no-tile-size-limit --quiet /data/$NAME.mbtiles

echo "[4/4] 圖磚大小與 manifest"
# mbtiles 內是 gzip 後的圖磚（與 PMTiles 內相同）
sqlite3 -json $OUT/$NAME.mbtiles "SELECT zoom_level z, count(*) tiles, sum(length(tile_data)) bytes, max(length(tile_data)) max_tile FROM tiles GROUP BY zoom_level ORDER BY z" > $OUT/tile-stats.json
MAXT=$(sqlite3 $OUT/$NAME.mbtiles "SELECT zoom_level||'/'||tile_column||'/'||((1<<zoom_level)-1-tile_row)||' '||length(tile_data) FROM tiles ORDER BY length(tile_data) DESC LIMIT 1")
SIZE=$(stat -f %z $OUT/$NAME.pmtiles)
python3 - $OUT $NAME $SIZE "$MAXT" <<'PY'
import json, sys, os
out, name, size, maxt = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
days = [int(x) for x in open(os.path.join(out, 'change-days.txt')).read().split()]
stats = json.load(open(os.path.join(out, 'tile-stats.json')))
xyz, b = maxt.split()
m = dict(version=name.split('-v')[1], url=f'{name}.pmtiles', minDay=days[0], maxDay=days[-1], changeDays=days)
json.dump(m, open(os.path.join(out, 'manifest.json'), 'w'))
rep = dict(file=f'{name}.pmtiles', pmtiles_bytes=size, pmtiles_mb=round(size / 1048576, 2), max_tile=dict(zxy=xyz, bytes=int(b)),
           per_zoom=stats, change_days=len(days))
json.dump(rep, open(os.path.join(out, 'build-report.json'), 'w'), indent=1)
print(json.dumps({k: v for k, v in rep.items() if k != 'per_zoom'}, ensure_ascii=False))
for s in stats: print(f"  z{s['z']}: {s['tiles']} 張，合計 {s['bytes']/1048576:.2f} MB，最大 {s['max_tile']/1024:.0f} KB")
PY
ln -sf $NAME.pmtiles $OUT/boundaries.pmtiles
sqlite3 $OUT/$NAME.mbtiles "SELECT count(*) FROM tiles WHERE length(tile_data) > 512000" | xargs -I{} echo "  超過 500 KB 的圖磚：{} 張"
echo "完成，耗時 $(( $(date +%s) - t0 )) 秒；out/boundaries.pmtiles → $NAME.pmtiles"
