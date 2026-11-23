#!/usr/bin/env bash
# 更新正式站的執行期版本檔 VPS:<REMOTE_DIR>/<TILES_DIR>/version.json（nginx 以 /version.json 提供、no-cache；頁首版本與提示讀它）。
#   scripts/set-version.sh --version 0.0.4 [--image-tag v0.0.4] [--commit abc1234]   換映像（程式版本）時
#   scripts/set-version.sh --db [--db-at 2026-11-23T09:19:16+08:00]                  release-db.sh 發佈資料庫後（自動呼叫）
#   scripts/set-version.sh --tiles [--tiles-at ISO]                                    release-tiles.sh 換圖磚後（自動呼叫）：讀 VPS 上的 symlink
#   --dry-run 只印出新內容，不寫入（仍會 ssh 讀現有檔）。可同時給多個選項；沒給的欄位沿用現有檔。
# 環境變數：VPS（預設 sanring-worldline）、REMOTE_DIR（預設 ~/worldline）。寫入是暫存檔＋mv（原子替換）。
set -euo pipefail
cd "$(dirname "$0")/.."
VPS="${VPS:-sanring-worldline}"
REMOTE_DIR="${REMOTE_DIR:-~/worldline}"
NOW="$(TZ=Asia/Taipei date +%Y-%m-%dT%H:%M:%S+08:00)"
DRY=0; VERSION=""; TAG=""; COMMIT=""; DB=0; DB_AT=""; TILES=0; TILES_AT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    --version) VERSION="${2:?}"; shift ;;
    --image-tag) TAG="${2:?}"; shift ;;
    --commit) COMMIT="${2:?}"; shift ;;
    --db) DB=1 ;;
    --db-at) DB=1; DB_AT="${2:?}"; shift ;;
    --tiles) TILES=1 ;;
    --tiles-at) TILES=1; TILES_AT="${2:?}"; shift ;;
    -h|--help) sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "未知參數：$1" >&2; exit 1 ;;
  esac
  shift
done
[ -n "$VERSION$TAG$COMMIT" ] || [ "$DB$TILES" != 00 ] || { echo "至少給一個 --version／--commit／--db／--tiles" >&2; exit 1; }

# 遠端的圖磚目錄（.env.prod 可用 TILES_DIR 覆寫，預設 ./tiles）
TD='T=$(sed -n "s/^TILES_DIR=//p" .env.prod 2>/dev/null); T=${T:-./tiles}'
CUR="$(ssh "$VPS" "cd $REMOTE_DIR && $TD && { cat \"\$T/version.json\" 2>/dev/null || echo '{}'; }; echo; echo '@@'; readlink \"\$T/overlay.json\" || true; readlink \"\$T/boundaries.pmtiles\" || true")"

NEW="$(CUR="$CUR" NOW="$NOW" VERSION="$VERSION" TAG="$TAG" COMMIT="$COMMIT" DB="$DB" DB_AT="$DB_AT" TILES="$TILES" TILES_AT="$TILES_AT" python3 - <<'PY'
import json, os, re
e = os.environ
head, _, links = e['CUR'].partition('\n@@\n')
try: d = json.loads(head.strip() or '{}')
except ValueError: d = {}
if not isinstance(d, dict): d = {}
now = e['NOW']
if e['VERSION']:
    d['version'] = e['VERSION'].lstrip('v')
    d.setdefault('image', {})['tag'] = e['TAG'] or 'v' + d['version']
elif e['TAG']:
    d.setdefault('image', {})['tag'] = e['TAG']
if e['COMMIT']: d.setdefault('image', {})['commit'] = e['COMMIT']
if e['DB'] == '1': d.setdefault('db', {})['releasedAt'] = e['DB_AT'] or now
if e['TILES'] == '1':
    l = (links.strip().splitlines() + ['', ''])[:2]
    for key, target in (('overlay', l[0]), ('boundaries', l[1])):
        m = re.search(r'-v([0-9a-f]+)\.', target or '')
        if not m: continue
        cur = d.get(key) or {}
        if cur.get('version') != m.group(1) or e['TILES_AT']:
            d[key] = {'version': m.group(1), 'releasedAt': e['TILES_AT'] or now}
if 'version' not in d: raise SystemExit('version.json 還沒有 version：第一次請加 --version x.y.z')
d['updatedAt'] = now
order = ['version', 'updatedAt', 'image', 'db', 'overlay', 'boundaries']
print(json.dumps({k: d[k] for k in order + [k for k in d if k not in order] if k in d}, ensure_ascii=False, indent=2))
PY
)"
echo "$NEW"
if [ "$DRY" = 1 ]; then echo "[dry-run] 未寫入 $VPS:$REMOTE_DIR/<tiles>/version.json"; exit 0; fi
printf '%s\n' "$NEW" | ssh "$VPS" "cd $REMOTE_DIR && $TD && cat > \"\$T/.version.json.tmp\" && chmod 644 \"\$T/.version.json.tmp\" && mv -f \"\$T/.version.json.tmp\" \"\$T/version.json\" && echo \"已寫入 \$T/version.json\""
