#!/bin/zsh
# 開發環境：nginx docker 提供 overlay JSON（http://127.0.0.1:3011/overlay.json，只綁 127.0.0.1；§9 步驟 5）。
# 用法：zsh tools/tiles/overlay-nginx.sh [start|stop|restart]（預設 restart）
set -euo pipefail
export PATH=/usr/local/bin:$PATH
HERE=${0:A:h}
NAME=wl-overlay-nginx
IMAGE=${WL_NGINX_IMAGE:-nginx:1.27-alpine}
PORT=${WL_OVERLAY_PORT:-3011}
cmd=${1:-restart}
if [[ $cmd == stop || $cmd == restart ]]; then docker rm -f $NAME >/dev/null 2>&1 || true; fi
if [[ $cmd == start || $cmd == restart ]]; then
  [[ -e $HERE/out/overlay.json ]] || { echo "找不到 out/overlay.json，先跑 build-overlay.sh"; exit 1; }
  docker run -d --name $NAME -p 127.0.0.1:$PORT:80 -v $HERE/out:/data:ro -v $HERE/overlay-nginx.conf:/etc/nginx/conf.d/default.conf:ro $IMAGE >/dev/null
  for i in {1..30}; do curl -fsI http://127.0.0.1:$PORT/overlay.json >/dev/null 2>&1 && break; sleep 1; done
  curl -fsI http://127.0.0.1:$PORT/overlay.json | head -3
fi
