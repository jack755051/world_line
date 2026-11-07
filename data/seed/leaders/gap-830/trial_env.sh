#!/bin/zsh
# 每批試跑用的隔離副本：up <dump>＝在同一容器建 worldline_person_dryrun（由該批寫入前的備份還原）＋臨時 API 5062；down＝停 API、刪掉這個暫存庫。
# 不碰 5432／5051；連線字串由 .dev/api.env 讀出後只換資料庫名，不印出。
set -e
C=worldline-borders-dev-db
case $1 in
  up)
    docker exec $C dropdb -U worldline --if-exists worldline_person_dryrun
    docker exec $C createdb -U worldline worldline_person_dryrun
    docker exec -i $C pg_restore -U worldline -d worldline_person_dryrun --no-owner < $2
    nohup /tmp/wlq/run-api-dryrun.sh > /tmp/wlq/api-5062.log 2>&1 &
    echo $! > /tmp/wlq/api-5062.pid
    for i in $(seq 1 40); do curl -sf http://127.0.0.1:5062/healthz >/dev/null && break; sleep 2; done
    curl -s -o /dev/null -w "5062 %{http_code}\n" http://127.0.0.1:5062/healthz ;;
  down)
    kill $(cat /tmp/wlq/api-5062.pid) 2>/dev/null || true; sleep 1
    lsof -ti tcp:5062 -sTCP:LISTEN | xargs kill 2>/dev/null || true; sleep 1
    docker exec $C dropdb -U worldline --if-exists worldline_person_dryrun; echo down ;;
esac
