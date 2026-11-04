#!/usr/bin/env bash
# World Line 正式映像建置／推送（介面同 sanring_tech_site）
#   scripts/prod-images.sh build      [api|web]   只建置（linux/amd64）
#   scripts/prod-images.sh push       [api|web]   只推送（需先 docker login）
#   scripts/prod-images.sh build-push [api|web]   建置後推送
# 不指定服務＝api 與 web 都做，沿用 .env.prod 裡的標籤；
# 只指定單一服務時，build／build-push 會先把 .env.prod 對應標籤改成年月日時分（如 202611042130）。
# 環境檔預設 .env.prod，可用 ENV_FILE=... 覆寫。
set -euo pipefail

cd "$(dirname "$0")/.."
export DOCKER_DEFAULT_PLATFORM=linux/amd64
ENV_FILE="${ENV_FILE:-.env.prod}"
COMPOSE=(docker compose -f docker-compose.prod.yml --env-file "$ENV_FILE")

usage() { sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }

cmd="${1:-}"; svc="${2:-}"
case "$cmd" in build|push|build-push) ;; *) usage ;; esac
case "$svc" in ""|api|web) ;; *) echo "未知服務：${svc}（只接受 api、web）" >&2; exit 1 ;; esac
[ -f "$ENV_FILE" ] || { echo "找不到 ${ENV_FILE}（先 cp env.prod.example .env.prod 並填值）" >&2; exit 1; }

services=(api web); [ -n "$svc" ] && services=("$svc")

set_tag() {  # set_tag API_IMAGE_TAG 202611042130：改 .env.prod 的值（沒有該行就加上）
  local key="$1" val="$2"
  if grep -q "^${key}=" "$ENV_FILE"; then
    sed -i.bak "s/^${key}=.*/${key}=${val}/" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
  else
    printf '%s=%s\n' "$key" "$val" >> "$ENV_FILE"
  fi
  echo "${ENV_FILE}：$key=$val"
}

if [ -n "$svc" ] && [ "$cmd" != push ]; then
  key="$(echo "$svc" | tr '[:lower:]' '[:upper:]')_IMAGE_TAG"
  set_tag "$key" "$(date +%Y%m%d%H%M)"
fi

if [ "$cmd" != push ]; then
  "${COMPOSE[@]}" build "${services[@]}"
fi
if [ "$cmd" != build ]; then
  "${COMPOSE[@]}" push "${services[@]}"
fi

# 結果：映像名稱與平台
case "$ENV_FILE" in /*) ef="$ENV_FILE" ;; *) ef="./$ENV_FILE" ;; esac
set -a; . "$ef"; set +a
for s in "${services[@]}"; do
  if [ "$s" = api ]; then img="${API_IMAGE:-registry.digitalocean.com/sanring/worldline-api}:${API_IMAGE_TAG:-latest}"
  else img="${WEB_IMAGE:-jackdai850817/worldline-web}:${WEB_IMAGE_TAG:-latest}"; fi
  echo "$s → ${img}（$(docker image inspect -f '{{.Os}}/{{.Architecture}}' "$img" 2>/dev/null || echo 未在本機)）"
done
