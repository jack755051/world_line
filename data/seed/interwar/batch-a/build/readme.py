#!/usr/bin/env python3
"""由 requests/ 與 qa.json（兩次大戰之間 A 批） 產生 README.md 的清單段落（說明段落寫在本檔）。"""
import json, os, glob
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
qa = json.load(open(os.path.join(ROOT, 'qa.json')))
man = json.load(open(os.path.join(ROOT, 'ohm-manifest.json')))
R = {}
for sub in ('A1', 'A2', 'A3'):
    for f in sorted(glob.glob(os.path.join(ROOT, 'requests', sub, '*.json'))):
        r = json.load(open(f, encoding='utf-8')); r['_sub'] = sub; R[r['_placeholder']] = r
ev = {k: r for k, r in R.items() if r['_post'] == '/api/v1/events'}
L = []
w = L.append
w('# 兩次大戰之間 A 批：1918-11-12 → 1923（DRAFT，待 Tai 檢查）\n')
w('範圍：歐洲、北非、近東（OHM 裁切框同 WW1 第二批）。期間半開區間 [1918-11-12, 1924-01-01)；1924-01-01 是本批試驗期間終點，不是政權迄日。接 WW1 第二批（迄 1918-11-12）與開發庫既有 1918～1938 紀錄（例如法國 1918-11-22、保加利亞 1919-11-27、比利時 1920-01-10、匈牙利 1921-11-10、奧地利 1922-10-01、立陶宛 1923-01-19 起；波蘭 1924-06-22、土耳其 1924-08-06 起不在本批窗內）。')
w('**只寫入本機開發庫**（worldline-borders-dev，API 127.0.0.1:5052，DB 5442）；寫入 appdb_ww2（5051）要另取得 Tai 同意。\n')
w('## 子批\n')
w('| 子批 | 紀錄起日 | 請求數 |\n|---|---|---|')
for s, a, b in [('A1', '1918-11-12', '1920-01-10'), ('A2', '1920-01-10', '1921-03-18'), ('A3', '1921-03-18', '1924-01-01')]:
    w(f'| {s} | [{a}, {b}) | {qa["requestCounts"][s]} |')
w('\n每筆紀錄用真實起訖，依起日分子批；來源、政權、事件放在第一個引用它們的子批。子批要依序送。'
  'A1 先撤回第二批的德意志帝國主權紀錄 SOV_DE_EMP_R（迄 1918-11-12 試驗終點），再以迄 1918-11-09（EV_DE_REV）重送 SOV_DE_EMP_R2，11-09 起由德意志國 SOV_DE_A 接續（先撤後增）。\n')
w('## 檔案\n')
w('| 檔案 | 說明 |\n|---|---|')
w('| `build/fetch.py` | 依 relation id 從 OHM Overpass 抓關係，存 `raw/`（不進版控） |')
w('| `build/build.py` | 組多邊形 → 框裁切 → Natural Earth 陸地裁切 → 簡化 → `borders-ohm-interwar-a.geojson`＋`ohm-manifest.json` |')
w('| `build/make_requests.py` | 優先序引擎（高優先紀錄扣出低優先、低優先在高優先起訖日切段；開發庫既有紀錄為最高優先）、手繪近似、QA（每個切點日檢查重疊）、產生 `requests/A{1,2,3}/*.json`、`interwar-a-derived.geojson`、`qa.json`；需要 WW1 第二批目錄（`../../ww1/war-1914-1918`，或環境變數 WW1B2） |')
w('| `build/readme.py` | 產生本檔 |')
w('| `send_seed.py` | 依子批送出（預設 dry-run；拒絕 5051；API key 從 --env 安靜讀取） |')
w('| `db-export/`（不進版控） | 開發庫唯讀匯出：本期間既有主權紀錄；備份在 `~/01_Projects/world_line_backups/` |\n')
w('用法（在本目錄）：\n```')
w('P="--prior ../../../../.dev/sent-ids.borders-dev.json --prior ../../../../.dev/sent-ids.borders-us-dev.json --prior ../../../../.dev/sent-ids.ww1-balkans-1908-1914-dev.json --prior ../../../../.dev/sent-ids.ww1-war-1914-1918-dev.json"')
w('python3 send_seed.py --sub A1 --base http://127.0.0.1:5052 --env ../../../../.env.borders-dev $P --ids ../../../../.dev/sent-ids.interwar-a-dev.json [--send]')
w('```\n')
w(f'OHM Overpass `osm_base`：{man[0]["osm_base"]}（UTC）。來源：條約原文（國際聯盟條約集 LNTS 各卷 PDF）、FRUS 巴黎和會第 II、XII、XIII 卷、FRUS 1918 補編一、FRUS 1922 第 II 卷、1923 第 II 卷；找不到正式出處的事件標 **待查證**。\n')
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
 '波蘭：1918-11～1922-06 用 OHM 1922 年波蘭外框（2855672）扣掉同期較高優先的德國、西烏克蘭、切欣、中立陶宛、白俄、烏克蘭；OHM 1920～1921 年波蘭關係是未閉合環，不能用。波蘇戰爭 1920 年前線往返（基輔、華沙）未畫。',
 '西烏克蘭人民共和國（ZUNR）、中立陶宛（Central Lithuania）、魯爾佔領區：經緯度點手繪近似，再與 OHM 外框求交。',
 '色佛爾條約未生效，不照它畫：鄂圖曼 [1918-11-12, 1920-08-10) 沿用第二批停戰後外框，之後用 OHM 2958040 到 1922-11-01 蘇丹制廢除；安卡拉大國民議會政府用 OHM 2958039 到 1923-10-29，之後由土耳其共和國接續。士麥那與東色雷斯從希臘 1920 年外框（2863750 − 2863749）依代表點切出（北緯 40.45° 以北，或 39.95° 以北且東經 26.9° 以西算東色雷斯）。',
 '匈牙利 1918-11～1921 全期用特里亞農條約界線；羅馬尼亞軍 1919 年進佔布達佩斯、塞爾維亞軍佔領佩奇—巴蘭尼亞（到 1921-08）未畫。',
 '外西凡尼亞與布科維納 1918-11-12～12-01（阿爾巴尤利亞決議前）、亞爾薩斯—洛林 11-12～11-22、伏伊伏丁那的歸屬過渡用最接近的政權，日期待查證。',
 '開發庫既有法國紀錄（1918-11-22 起）只到北緯 34°，阿爾及利亞南部撒哈拉在 1918-11-22 後留白（既有資料，本批未改）。',
 '高加索：喬治亞、亞美尼亞、亞塞拜然 1920～1921 年蘇維埃化用政權切換，1920 年土亞戰爭的卡爾斯割讓以 1921 年卡爾斯條約線一次處理；阿布哈茲、巴統另立。',
 '北非里夫共和國用 OHM 外框（1921-09-18 起）；敘利亞託管地內畫大馬士革、阿勒坡、德魯茲山、大黎巴嫩與 1922 年敘利亞聯邦，阿拉維國未另立（併在黎凡特／聯邦外框，待查證）。',
 '阿爾巴尼亞與希臘在北伊庇魯斯的小片重疊以阿爾巴尼亞優先；保加利亞西部邊區在納伊條約生效（1919-11-27）前歸保加利亞。',
 '事件標待查證者（見上表）只有日期與摘要，沒有正式出處，送出時不附引用。',
]:
    w(f'- {t}')
open(os.path.join(ROOT, 'README.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print('README lines', len(L))
