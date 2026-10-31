#!/usr/bin/env python3
"""由 requests/ 與 qa.json 產生 README.md 的清單段落（說明段落寫在本檔）。"""
import json, os, glob
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
qa = json.load(open(os.path.join(ROOT, 'qa.json')))
man = json.load(open(os.path.join(ROOT, 'ohm-manifest.json')))
R = {}
for sub in ('sub1', 'sub2', 'sub3'):
    for f in sorted(glob.glob(os.path.join(ROOT, 'requests', sub, '*.json'))):
        r = json.load(open(f, encoding='utf-8')); r['_sub'] = sub; R[r['_placeholder']] = r
ev = {k: r for k, r in R.items() if r['_post'] == '/api/v1/events'}
L = []
w = L.append
w('# WW1 第二批：1914-07-29 → 1918-11-11 停戰（DRAFT，待 Tai 檢查）\n')
w('範圍：歐洲、北非、近東（OHM 裁切框 -20,15～60,72）。期間半開區間 [1914-07-29, 1918-11-12)；1918-11-12 是本批試驗期間終點，不是政權迄日（無迄事件）。')
w('**只寫入本機開發庫**（worldline-borders-dev，API 127.0.0.1:5052，DB 5442）；寫入 appdb_ww2（5051）要另取得 Tai 同意。\n')
w('## 子批\n')
w('| 子批 | 紀錄起日 | 請求數 |\n|---|---|---|')
for s, a, b in [('sub1', '1914-07-29', '1916-01-01'), ('sub2', '1916-01-01', '1918-01-01'), ('sub3', '1918-01-01', '1918-11-12')]:
    w(f'| {s} | [{a}, {b}) | {qa["requestCounts"][s]} |')
w('\n每筆紀錄用真實起訖，依起日分子批；來源、政權、事件放在第一個引用它們的子批。子批要依序送（後面的子批引用前面的 id）。'
  'sub1 先撤回第一批迄於 1914-07-29 的 27 筆主權紀錄、義屬愛琴海佔領歸屬與奧匈—塞爾維亞衝突，再以相同內容延長後重送（先撤後增）。\n')
w('## 檔案\n')
w('| 檔案 | 說明 |\n|---|---|')
w('| `build/fetch.py` | 依 relation id 從 OHM Overpass 抓關係（`out meta geom`＋成員線段 tags），存 `raw/`（不進版控；第一批已抓的沿用） |')
w('| `build/build.py` | 組多邊形 → 框裁切 → Natural Earth 10m 陸地裁切 → 簡化 → `borders-ohm-ww1-2.geojson`＋`ohm-manifest.json`；外框小缺口（盧布林、攝政波蘭）以直線接合並記在清單 `repair` |')
w('| `build/make_requests.py` | 優先序引擎（底層國家扣掉同期佔領區／新國家／開發庫既有紀錄並切段）、手繪近似線、QA、產生 `requests/sub{1,2,3}/*.json`、`ww1-1914-1918-derived.geojson`、`qa.json` |')
w('| `build/readme.py` | 產生本檔 |')
w('| `send_seed.py` | 依子批送出（預設 dry-run；拒絕 5051；API key 從 --env 安靜讀取） |')
w('| `db-export/`（不進版控） | 開發庫唯讀匯出：本期間既有主權紀錄、美國 1937 年紀錄；備份在 `~/01_Projects/world_line_backups/` |\n')
w('用法（在本目錄）：\n```')
w('P="--prior ../../../../.dev/sent-ids.borders-dev.json --prior ../../../../.dev/sent-ids.borders-us-dev.json --prior ../../../../.dev/sent-ids.ww1-balkans-1908-1914-dev.json"')
w('python3 send_seed.py --sub sub1 --base http://127.0.0.1:5052 --env ../../../../.env.borders-dev $P --ids ../../../../.dev/sent-ids.ww1-war-1914-1918-dev.json [--send]')
w('```\n')
w(f'OHM Overpass `osm_base`：{man[0]["osm_base"]}（UTC）。\n')
w('## 事件\n')
w('| placeholder | 日期 | 類型 | 摘要 | 出處 | 子批 |\n|---|---|---|---|---|---|')
for k, r in sorted(ev.items(), key=lambda kv: kv[1]['body']['occurred']['start']):
    b = r['body']; c = '；'.join(f"{x['sourceId'][2:-2]} {x['locator']}" for x in b['citations']) or '**待查證**'
    w(f"| {k} | {b['occurred']['start']} | {b['eventKind']} | {b['summary']['zh-Hant']} | {c} | {r['_sub']} |")
w('\n## 主權紀錄\n')
w('| placeholder | 政權 | 期間 | 層級 | 幾何 | 起事件 | 迄事件 | 子批 |\n|---|---|---|---|---|---|---|---|')
for k, r in R.items():
    if r['_post'] != '/api/v1/sovereignty-records': continue
    b = r['body']; vp = b['validPeriod']
    w(f"| {k} | {b['regimeId'][2:-2] if b['regimeId'].startswith('{{') else b['regimeId']} | {vp['start']}～{vp['end']} | {b['layerStatus']} | {b['geometryLocator']} | {(b['startEventId'] or '—').strip('{}')} | {(b['endEventId'] or '—').strip('{}')} | {r['_sub']} |")
w('\n## 佔領歸屬\n')
w('| placeholder | 被佔領 | 佔領方 | 管理 | 期間 | 共同 | 子批 |\n|---|---|---|---|---|---|---|')
for k, r in R.items():
    if r['_post'] != '/api/v1/occupation-attributions': continue
    b = r['body']; vp = b['validPeriod']
    w(f"| {k} | {b['occupiedRegimeId'][2:-2]} | {b['occupierRegimeId'][2:-2]} | {b['controlKind']} | {vp['start']}～{vp['end']} | {'是' if b['coOccupied'] else ''} | {r['_sub']} |")
w('\n## 衝突紀錄\n')
w('| placeholder | A | B | 起 | 迄 | 位置 | 子批 |\n|---|---|---|---|---|---|---|')
for k, r in R.items():
    if r['_post'] != '/api/v1/conflict-records': continue
    b = r['body']
    w(f"| {k} | {b['regimeAId'][2:-2]} | {b['regimeBId'][2:-2]} | {b['startEventId'][2:-2]} | {(b['endEventId'] or '—').strip('{}')} | {b['location']['coordinates']}：{b['locationMethod']} | {r['_sub']} |")
w('\n## 近似與未畫（待查證）\n')
for t in [
 '西線：1914-10-13 起法國北部與比利時佔領區用手繪的 1914 年底穩定前線（`FRONT_1914`），1918-11-11 用手繪停戰線（`ARMISTICE_1918`）。1917 年興登堡防線撤退、1918 年春季攻勢與百日攻勢的前線變化未畫。比利時 8-20～10-10 用六省省界近似。',
 '塞爾維亞：保加利亞佔領（併入）區用經緯度方框粗略近似（北緯 42.35° 以南＋東經 21.5° 以東、北緯 43.9° 以南）；1918 年秋的逐步解放未畫（保加利亞區在薩洛尼卡停戰時、奧匈區在朱斯蒂別墅停戰時整塊歸還）。',
 '羅馬尼亞：多布羅加以多瑙河近似線、未佔領的摩爾達維亞以錫雷特河—奧伊圖茲近似線手繪；1918 年喀爾巴阡山口割讓、1916 年羅軍進入外西凡尼亞未畫。',
 '東線：1914～1915 年俄軍佔領東普魯士與東加利西亞、1916 年布魯西洛夫攻勢、1917-09 德軍佔領里加、1918-02 德軍推進（拉特加萊、白俄羅斯東部）未畫；1918-01-24 起 OHM 俄羅斯蘇維埃共和國不含拉特加萊、維捷布斯克西部與比薩拉比亞，這些地區在 1918-01-24～03-03（比薩拉比亞到 04-09）留白。',
 '烏克蘭、喬治亞的德奧駐軍未設佔領歸屬；烏克蘭國（1918-04-29 起）未另立政權；摩爾達維亞民主共和國未畫。',
 '中東：鄂圖曼在阿拉伯半島、美索不達米亞、巴勒斯坦的失地（巴格達 1917-03、耶路撒冷 1917-12）與 1916～1917 年俄軍佔領土屬亞美尼亞未畫；巴統條約割地未畫。',
 '阿爾巴尼亞 1915～1918 多國分區佔領、義大利 1917 年卡波雷托後失去的威尼托、保加利亞佔領希臘東馬其頓、中立莫雷斯內的德國管理未畫。',
 '德國 1918-11-09 革命、奧匈 1918-10 起的瓦解（德意志奧地利、匈牙利、西烏克蘭、加利西亞）未改政權，只在紀錄說明。',
 '美國紀錄照抄開發庫 1937 年起的幾何（給衝突弧線用），1914～1918 年差異未處理。',
]:
    w(f'- {t}')
open(os.path.join(ROOT, 'README.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print('README lines', len(L))
