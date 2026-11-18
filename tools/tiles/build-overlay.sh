#!/bin/zsh
# overlay（§9 遷移步驟 5）：build-overlay.py 取第 1 層 API → tippecanoe 做 overlay-v{hash}.pmtiles（control、gaps 圖層）。
# 用法：zsh tools/tiles/build-overlay.sh [API_BASE] [--sections=...]；做完要 zsh tools/tiles/martin.sh restart。
set -euo pipefail
export PATH=/usr/local/bin:$PATH
HERE=${0:A:h}; OUT=$HERE/out
TIPPE=${WL_TIPPECANOE_IMAGE:-wl-tippecanoe:2.79.0}
python3 $HERE/build-overlay.py "$@"
HASH=$(cat $OUT/overlay-control.geojsonseq $OUT/overlay-gaps.geojsonseq | shasum -a 256 | cut -c1-12)
NAME=overlay-v$HASH
rm -f $OUT/$NAME.mbtiles $OUT/$NAME.pmtiles
# 與 boundaries 同一組「正確性優先」參數；控制區互相重疊，不用 shared borders
docker run --rm -v $OUT:/data $TIPPE tippecanoe -o /data/$NAME.mbtiles -Z0 -z8 \
  --read-parallel --no-feature-limit --no-tile-size-limit --no-tiny-polygon-reduction --simplification=4 \
  -L control:/data/overlay-control.geojsonseq -L gaps:/data/overlay-gaps.geojsonseq --name="World Line overlay" --quiet
docker run --rm -v $OUT:/data $TIPPE tile-join -o /data/$NAME.pmtiles --no-tile-size-limit --quiet /data/$NAME.mbtiles
ln -sf $NAME.pmtiles $OUT/overlay.pmtiles
echo "overlay 圖磚：$NAME.pmtiles $(stat -f %z $OUT/$NAME.pmtiles) bytes；最大圖磚 $(sqlite3 $OUT/$NAME.mbtiles 'SELECT max(length(tile_data)) FROM tiles') bytes"
