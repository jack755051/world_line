#!/usr/bin/env bash
# World Line 資料發佈：開發庫（5442 worldline_borders_dev）整包取代正式庫（VPS 上 docker-compose.prod.yml 的 postgres）。
#   scripts/release-db.sh --dry-run        只做本機唯讀檢查，列出每一步要跑的指令（不 ssh、不 dump、不寫任何庫）
#   scripts/release-db.sh                  正式執行；動正式庫前兩次要求輸入 release
#   scripts/release-db.sh --yes            不問確認（確定時才用）
#   scripts/release-db.sh --dump FILE      用現成的開發庫 dump（不重新 pg_dump）
# 環境變數：VPS（預設 ssh 別名 sanring-worldline）、REMOTE_DIR（預設 ~/worldline）、BACKUP_DIR（預設 ~/wl-db-backups）
# 流程：檢查 → dump 開發庫 → 備份正式庫（VPS backups/ 一份、拉回本機一份）→ scp 到 restore/ →
#       還原到新資料庫（正式庫不受影響）→ 停 api → 舊庫改名 <db>_prev_<時間>、新庫改成 <db> → 起 api → 健康檢查與筆數對照。
# 不刪任何資料庫或備份；出問題照結尾印的回滾指令把名字改回、起 api。遠端 shell 需為 bash（root 預設）。
set -euo pipefail
cd "$(dirname "$0")/.."

VPS="${VPS:-sanring-worldline}"
REMOTE_DIR="${REMOTE_DIR:-~/worldline}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/wl-db-backups}"
DEV_CONTAINER="worldline-borders-dev-db"
DEV_DB="worldline_borders_dev"
TS="$(date +%Y%m%d-%H%M%S)"; TSU="${TS//-/_}"
DRY=0; YES=0; DUMP=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    --yes) YES=1 ;;
    --dump) DUMP="${2:?--dump 需要檔名}"; shift ;;
    -h|--help) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "未知參數：$1" >&2; exit 1 ;;
  esac
  shift
done

DC="docker compose -f docker-compose.prod.yml --env-file .env.prod"
say()     { printf '\n== %s\n' "$*"; }
run()     { if [ "$DRY" = 1 ]; then printf '  [dry-run] %s\n' "$*"; else bash -c "$*"; fi; }
remote()  { local cmd="cd $REMOTE_DIR && $*"; if [ "$DRY" = 1 ]; then printf '  [dry-run] ssh %s %s\n' "$VPS" "$cmd"; else ssh "$VPS" "$cmd"; fi; }
# 在正式 postgres 容器內跑一行 sh：用容器自己的 ${POSTGRES_USER}／${POSTGRES_DB}，本機不經手密碼
pg()      { remote "$DC exec -T postgres sh -c $(printf %q "$1")"; }
confirm() {
  if [ "$DRY" = 1 ]; then echo "  [dry-run] 確認：$1（需輸入 release）"; return; fi
  [ "$YES" = 1 ] && return
  read -r -p "$1（輸入 release 繼續）：" ans; [ "$ans" = release ] || { echo "已取消。"; exit 1; }
}
dev_q()   { docker exec -i -e PGOPTIONS='-c default_transaction_read_only=on' "$DEV_CONTAINER" sh -c "psql -X -At -U \"\$POSTGRES_USER\" -d $DEV_DB"; }

COUNTS_SQL="select 'leader_bios', count(*) from leader_bios where retracted_at is null union all select 'leader_bio_paragraphs', count(*) from leader_bio_paragraphs where retracted_at is null union all select 'sources', count(*) from sources union all select 'sovereignty_records', count(*) from sovereignty_records"
PSQL='psql -X -At -v ON_ERROR_STOP=1 -U "$POSTGRES_USER"'
DB_EXISTS="$PSQL -d postgres -c 'select datname from pg_database' | grep -qx \"\$POSTGRES_DB\""
NEWDB="worldline_release_$TSU"
NAME="worldline-$TS.dump"
DEV_DUMP="${DUMP:-$BACKUP_DIR/release-$TS-dev.dump}"

say "0) 本機檢查（唯讀）"
docker inspect -f '{{.State.Running}}' "$DEV_CONTAINER" 2>/dev/null | grep -q true || { echo "開發庫容器 $DEV_CONTAINER 沒在跑" >&2; exit 1; }
echo "  開發庫：$(echo 'select version()' | dev_q | cut -c1-30)；PostGIS $(echo 'select postgis_lib_version()' | dev_q)"
echo "  開發庫筆數："; echo "$COUNTS_SQL" | dev_q | sed 's/^/    /'
mkdir -p "$BACKUP_DIR"

say "1) 正式環境檢查（唯讀）"
remote "test -f docker-compose.prod.yml && test -f .env.prod && test -d restore && echo 'compose／.env.prod／restore 都在'"
pg "pg_isready -U \"\$POSTGRES_USER\" -d postgres && $PSQL -d postgres -c 'select version()'"
pg "if $DB_EXISTS; then echo \"prod db \$POSTGRES_DB exists\"; $PSQL -d \"\$POSTGRES_DB\" -c \"select 'postgis', extversion from pg_extension where extname='postgis'\"; $PSQL -d \"\$POSTGRES_DB\" -c \"$COUNTS_SQL\"; else echo \"prod db \$POSTGRES_DB not found (first release)\"; fi"

say "2) dump 開發庫 → $DEV_DUMP"
if [ -n "$DUMP" ]; then
  [ "$DRY" = 1 ] || [ -s "$DUMP" ] || { echo "找不到 $DUMP" >&2; exit 1; }
  echo "  沿用 $DUMP"
else
  run "docker exec $DEV_CONTAINER sh -c 'pg_dump -U \"\$POSTGRES_USER\" -d $DEV_DB -Fc -f /tmp/release.dump' && docker cp $DEV_CONTAINER:/tmp/release.dump '$DEV_DUMP' && docker exec $DEV_CONTAINER rm -f /tmp/release.dump"
fi
run "test -s '$DEV_DUMP' && echo \"  pg_restore --list 項數：\$(docker exec -i $DEV_CONTAINER pg_restore --list < '$DEV_DUMP' | grep -c '^[0-9]')\" && shasum -a 256 '$DEV_DUMP' | tee '$DEV_DUMP.sha256'"

say "3) 備份正式庫（VPS：backups/prod-$TS.dump；本機：$BACKUP_DIR/prod-$TS.dump）"
remote "mkdir -p backups"
pg "rm -f /tmp/prod.dump; if $DB_EXISTS; then pg_dump -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -Fc -f /tmp/prod.dump && echo 'prod db dumped'; else echo 'no prod db, backup skipped'; fi"
remote "if $DC exec -T postgres test -s /tmp/prod.dump; then $DC cp postgres:/tmp/prod.dump backups/prod-$TS.dump && ls -l backups/prod-$TS.dump; fi"
run "scp '$VPS:$REMOTE_DIR/backups/prod-$TS.dump' '$BACKUP_DIR/prod-$TS.dump' 2>/dev/null && ls -l '$BACKUP_DIR/prod-$TS.dump' || echo '  （沒有正式庫備份可拉回：第一次上線）'"

say "4) 上傳開發庫 dump → $VPS:$REMOTE_DIR/restore/$NAME"
run "scp '$DEV_DUMP' '$VPS:$REMOTE_DIR/restore/$NAME'"
remote "(sha256sum restore/$NAME 2>/dev/null || shasum -a 256 restore/$NAME)"
[ "$DRY" = 1 ] || echo "  本機 sha256：$(cut -d' ' -f1 "$DEV_DUMP.sha256")（須與上一行相同）"

confirm "5) 在正式 postgres 建新資料庫 $NEWDB 並還原（現有正式庫不動）"
say "5) 還原到新資料庫 $NEWDB"
pg "createdb -U \"\$POSTGRES_USER\" -T template0 $NEWDB && pg_restore -U \"\$POSTGRES_USER\" -d $NEWDB --no-owner --no-privileges --exit-on-error /restore/$NAME && echo restore-ok && $PSQL -d $NEWDB -c \"$COUNTS_SQL\""

confirm "6) 停 api，正式庫改名為 <db>_prev_${TSU}，$NEWDB 改名為正式庫，再起 api"
say "6) 停 api → 改名對調 → 起 api"
remote "$DC stop api"
pg "$PSQL -d postgres -c \"select pg_terminate_backend(pid) from pg_stat_activity where datname in ('\$POSTGRES_DB','$NEWDB') and pid<>pg_backend_pid()\" >/dev/null; if $DB_EXISTS; then $PSQL -d postgres -c \"ALTER DATABASE \\\"\$POSTGRES_DB\\\" RENAME TO \\\"\${POSTGRES_DB}_prev_$TSU\\\"\"; fi; $PSQL -d postgres -c \"ALTER DATABASE $NEWDB RENAME TO \\\"\$POSTGRES_DB\\\"\" && echo swapped"
remote "$DC up -d api"

say "7) 健康檢查"
remote "P=\$(sed -n 's/^WEB_PORT=//p' .env.prod); P=\${P:-4080}; for i in \$(seq 1 30); do curl -fsS http://127.0.0.1:\$P/api/healthz && break; sleep 2; done; echo; curl -s -o /dev/null -w 'web %{http_code}\n' http://127.0.0.1:\$P/"
pg "$PSQL -d \"\$POSTGRES_DB\" -c \"$COUNTS_SQL\""
echo "  （筆數應與步驟 0 的開發庫相同）"

say "完成。回滾（舊庫保留為 <POSTGRES_DB>_prev_${TSU}）："
cat <<RB
  ssh $VPS
  cd $REMOTE_DIR && $DC stop api
  $DC exec -T postgres sh -c 'psql -U "\$POSTGRES_USER" -d postgres -c "ALTER DATABASE \\"\$POSTGRES_DB\\" RENAME TO \\"\${POSTGRES_DB}_bad_$TSU\\"" -c "ALTER DATABASE \\"\${POSTGRES_DB}_prev_$TSU\\" RENAME TO \\"\$POSTGRES_DB\\""'
  $DC up -d api
確認新版沒問題後，再手動 DROP 舊的 _prev_ 庫（本腳本不刪）。
RB
