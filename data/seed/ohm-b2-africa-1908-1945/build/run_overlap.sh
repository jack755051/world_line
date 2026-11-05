#!/bin/zsh
# 用法：run_overlap.sh <cands.csv 在 Mac 上的路徑> <輸出 pieces.csv>
export PATH=/usr/local/bin:/opt/homebrew/bin:$PATH
docker cp /tmp/wl-overlap.sql worldline-borders-dev-db:/tmp/wl-overlap.sql
docker cp "$1" worldline-borders-dev-db:/tmp/wl-cands.csv
docker exec worldline-borders-dev-db sh -c 'psql -q -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /tmp/wl-overlap.sql < /tmp/wl-cands.csv' > "$2"
echo exit $? ; wc -c "$2"
