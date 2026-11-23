#!/usr/bin/env bash
# 換正式站的圖磚／overlay 中繼資料：傳帶版本的檔 → 原子切換 symlink → 有 .pmtiles 時重啟 martin → 更新 version.json。
#   scripts/release-tiles.sh [--dry-run] FILE...
#   FILE 依檔名對應：overlay-v<hash>.json → overlay.json；overlay-v<hash>.pmtiles → overlay.pmtiles；boundaries-v<hash>.pmtiles → boundaries.pmtiles
#   例：scripts/release-tiles.sh ~/wl-release/tiles-v0.0.3/out/overlay-v54e27ac7d35f.json
# 舊版本檔一律保留（不 --delete）；結尾印出回滾指令。環境變數：VPS（預設 sanring-worldline）、REMOTE_DIR（預設 ~/worldline）。
set -euo pipefail
cd "$(dirname "$0")/.."
VPS="${VPS:-sanring-worldline}"
REMOTE_DIR="${REMOTE_DIR:-~/worldline}"
DC="docker compose -f docker-compose.prod.yml --env-file .env.prod"
TD='T=$(sed -n "s/^TILES_DIR=//p" .env.prod 2>/dev/null); T=${T:-./tiles}'
DRY=0; FILES=()
for a in "$@"; do case "$a" in --dry-run) DRY=1 ;; -h|--help) sed -n '2,6p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;; *) FILES+=("$a") ;; esac; done
[ ${#FILES[@]} -gt 0 ] || { echo "要給至少一個檔案" >&2; exit 1; }
remote() { if [ "$DRY" = 1 ]; then printf '  [dry-run] ssh %s %q\n' "$VPS" "cd $REMOTE_DIR && $TD && $1"; else ssh "$VPS" "cd $REMOTE_DIR && $TD && $1"; fi; }

LINKS=(); PMT=0; NAMES=()
for f in "${FILES[@]}"; do
  [ -s "$f" ] || { echo "找不到 $f" >&2; exit 1; }
  b="$(basename "$f")"
  case "$b" in
    overlay-v*.json) l=overlay.json ;;
    overlay-v*.pmtiles) l=overlay.pmtiles; PMT=1 ;;
    boundaries-v*.pmtiles) l=boundaries.pmtiles; PMT=1 ;;
    *) echo "不認得的檔名：$b（要 overlay-v<hash>.json／.pmtiles 或 boundaries-v<hash>.pmtiles）" >&2; exit 1 ;;
  esac
  LINKS+=("$l:$b"); NAMES+=("$b")
done

echo "== 目前的 symlink（回滾用）"
PREV="$(ssh "$VPS" "cd $REMOTE_DIR && $TD && cd \"\$T\" && for l in overlay.json overlay.pmtiles boundaries.pmtiles; do printf '%s:%s\n' \"\$l\" \"\$(readlink \$l)\"; done")"
echo "$PREV" | sed 's/^/  /'

echo "== 上傳（不刪舊檔）＋比對 sha256"
for f in "${FILES[@]}"; do
  b="$(basename "$f")"; sum="$(shasum -a 256 "$f" | cut -d' ' -f1)"
  if [ "$DRY" = 1 ]; then echo "  [dry-run] rsync $f → $VPS:$REMOTE_DIR/<tiles>/$b"; else
    T="$(ssh "$VPS" "cd $REMOTE_DIR && $TD && cd \"\$T\" && pwd")"
    rsync -a --ignore-existing "$f" "$VPS:$T/$b"
  fi
  remote "cd \"\$T\" && test \"\$(sha256sum $b | cut -d' ' -f1)\" = $sum && echo '  $b sha256 OK'"
done

echo "== 切換 symlink（ln＋mv -T，原子替換）"
for x in "${LINKS[@]}"; do l="${x%%:*}"; b="${x#*:}"; remote "cd \"\$T\" && ln -sfn $b $l.next && mv -Tf $l.next $l && ls -l $l"; done
[ "$PMT" = 1 ] && { echo "== 重啟 martin（換了 .pmtiles）"; remote "$DC restart martin"; }

echo "== 檢查（VPS 本機經 nginx）"
remote "P=\$(sed -n 's/^WEB_PORT=//p' .env.prod); P=\${P:-4080}; echo \"overlay.json \$(curl -fsS http://127.0.0.1:\$P/tiles/overlay.json | grep -o '\"version\": *\"[0-9a-f]*\"' | tail -1)\"; curl -s -o /dev/null -w 'tiles/boundaries %{http_code}\n' http://127.0.0.1:\$P/tiles/boundaries"

echo "== 更新 version.json"
if [ "$DRY" = 1 ]; then scripts/set-version.sh --tiles --dry-run; else scripts/set-version.sh --tiles; fi

echo "== 回滾：把 symlink 指回原本的檔"
for x in "${LINKS[@]}"; do l="${x%%:*}"; old="$(echo "$PREV" | sed -n "s/^$l://p")"
  echo "  ssh $VPS 'cd $REMOTE_DIR/tiles && ln -sfn $old $l.next && mv -Tf $l.next $l'"; done
[ "$PMT" = 1 ] && echo "  ssh $VPS 'cd $REMOTE_DIR && $DC restart martin'"
echo "  scripts/set-version.sh --tiles   # 回滾後讓 version.json 跟著改回"
