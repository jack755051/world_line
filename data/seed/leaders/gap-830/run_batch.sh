#!/bin/zsh
# 一批的標準流程：備份 → 隔離副本試跑（5062）→ 比對計數 → 寫入開發庫（5052）→ 比對計數 → 更新缺口清單。
# 用法：./run_batch.sh bNN
set -e
cd ${0:A:h}
B=$1
Q="select count(*) filter (where retracted_at is null)||'/'||count(*) from leader_bios; select count(*) from leader_bio_field_citations; select count(*) from leader_records where retracted_at is null and person_id is not null; select count(*) from sources; select count(*) from leader_bios where retracted_at is null and portrait_url is not null"
cnt() { docker exec worldline-borders-dev-db psql -U worldline -d $1 -tAc "$Q" | tr '\n' ' '; }
TS=$(date +%Y%m%d-%H%M%S); F=~/wl-backups/worldline_borders_dev-$TS-pre-gap-$B.dump
docker exec worldline-borders-dev-db pg_dump -U worldline -d worldline_borders_dev -Fc > $F; echo "backup $F"
./trial_env.sh up $F | tail -1
TB=$(cnt worldline_person_dryrun)
python3 send_batch.py $B --base http://127.0.0.1:5062/api/v1 --db worldline_person_dryrun --send | grep -E '✗|完成' || true
TA=$(cnt worldline_person_dryrun)
./trial_env.sh down >/dev/null
DB=$(cnt worldline_borders_dev)
[[ "$TB" == "$DB" ]] || { echo "試跑起點與開發庫不一致：$TB vs $DB，停止"; exit 1; }
python3 send_batch.py $B --send | grep -E '✗|完成' || true
DA=$(cnt worldline_borders_dev)
echo "trial: $TB → $TA"; echo "dev:   $DB → $DA"
[[ "$TA" == "$DA" ]] || echo "⚠ 試跑與寫入結果不一致"
python3 gap_status.py refresh >/dev/null
python3 gap_status.py log "$(date '+%Y-%m-%d %H:%M') $B：備份 $(basename $F)；生平有效/總、引用、有生平任期、sources、照片：$DB→$DA（試跑 $TB→$TA）"
