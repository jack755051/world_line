#!/bin/zsh
# 開發環境：用 Martin docker image 提供 tools/tiles/out/boundaries.pmtiles（ARCHITECTURE.md §9 遷移步驟 4）。
# TileJSON：http://127.0.0.1:3010/boundaries（前端 tiles 模式預設位址）。只綁 127.0.0.1。
# 用法：zsh tools/tiles/martin.sh [start|stop|restart]（預設 restart；重建圖磚後要 restart 才會讀到新檔）
set -euo pipefail
export PATH=/usr/local/bin:$PATH
HERE=${0:A:h}
NAME=wl-martin-tiles
IMAGE=${WL_MARTIN_IMAGE:-ghcr.io/maplibre/martin:latest}
PORT=${WL_MARTIN_PORT:-3010}
cmd=${1:-restart}
if [[ $cmd == stop || $cmd == restart ]]; then docker rm -f $NAME >/dev/null 2>&1 || true; fi
if [[ $cmd == start || $cmd == restart ]]; then
  [[ -e $HERE/out/boundaries.pmtiles ]] || { echo "找不到 out/boundaries.pmtiles，先跑 build.sh"; exit 1; }
  # out/boundaries.pmtiles 是指向 boundaries-v{hash}.pmtiles 的連結，掛整個 out 目錄
  docker run -d --name $NAME -p 127.0.0.1:$PORT:3000 -v $HERE/out:/data:ro -v $HERE/martin.yaml:/config.yaml:ro $IMAGE --config /config.yaml >/dev/null
  for i in {1..30}; do curl -fs http://127.0.0.1:$PORT/health >/dev/null 2>&1 && break; sleep 1; done
  curl -fs http://127.0.0.1:$PORT/boundaries | head -c 300; echo
fi
