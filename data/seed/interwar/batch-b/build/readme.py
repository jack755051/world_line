#!/usr/bin/env python3
"""由 requests/ 與 qa.json（兩次大戰之間 B 批） 產生 README.md 的清單段落（說明段落寫在本檔）。"""
import json, os, glob
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
qa = json.load(open(os.path.join(ROOT, 'qa.json')))
man = json.load(open(os.path.join(ROOT, 'ohm-manifest.json')))
R = {}
for sub in ('B1', 'B2', 'B3'):
    for f in sorted(glob.glob(os.path.join(ROOT, 'requests', sub, '*.json'))):
        r = json.load(open(f, encoding='utf-8')); r['_sub'] = sub; R[r['_placeholder']] = r
ev = {k: r for k, r in R.items() if r['_post'] == '/api/v1/events'}
L = []
w = L.append
w('# 兩次大戰之間 B 批：1924 → 1938（DRAFT，待 Tai 檢查）\n')
w('範圍：歐洲、北非、近東（OHM 裁切框同 A 批，北緯 15° 以北、西經 20°～東經 60°）。把 A 批迄於 1924-01-01（試驗終點）的 34 筆主權紀錄與魯爾佔領歸屬**先撤後增**延長迄日，'
  '接上開發庫既有 1924～1939 紀錄（波蘭 1924-06-22、土耳其 1924-08-06、挪威 1925-08-14、蘇聯 1926-01-01、阿爾巴尼亞王國 1928-09-01、義大利 1929-06-07、南斯拉夫 1929-10-03、丹麥與瑞典 1932-01-30、'
  '德國與捷克斯洛伐克 1936-07-03、希臘 1936-09-17、美國 1937-07-07、愛爾 1937-12-29、西班牙國 1939-04-01、土耳其 1939-06-29 起）。沒有後續資料的北非、近東、冰島暫迄 1939-01-01（本批試驗終點，不是政權迄日）。')
w('**只寫入本機開發庫**（worldline-borders-dev，API 127.0.0.1:5052，DB 5442）；寫入 appdb_ww2（5051）要另取得 Tai 同意。安卡拉／鄂圖曼 1920～1922 年紀錄未動（等 Tai 決定）。\n')
w('## 子批\n')
w('| 子批 | 紀錄起日 | 請求數 |\n|---|---|---|')
for s_, a, b in [('B1', '（A 批延長紀錄的原起日）', '1929-01-01'), ('B2', '1929-01-01', '1936-01-01'), ('B3', '1936-01-01', '（1939-06-29）')]:
    w(f'| {s_} | [{a}, {b}) | {qa["requestCounts"][s_]} |')
w('\n每筆紀錄用真實起訖，依起日分子批；來源、政權、事件放在第一個引用它們的子批。子批要依序送。撤回請求放在重送紀錄最早的子批：B1 撤回 A 批 34 筆主權紀錄與 OCC_RUHR，B2 撤回開發庫既有西班牙共和國紀錄 SOV_R2860484（起日 1931-01-01 是 OHM 年份）後以 1931-04-14 起重送。\n')
w('## 檔案\n')
w('| 檔案 | 說明 |\n|---|---|')
w('| `build/fetch.py` | 依 relation id 從 OHM Overpass 抓關係，存 `raw/`（不進版控） |')
w('| `build/build.py` | 組多邊形 → 框裁切 → Natural Earth 陸地裁切 → 簡化 → `borders-ohm-interwar-b.geojson`＋`ohm-manifest.json` |')
w('| `build/make_requests.py` | 優先序引擎（高優先紀錄扣出低優先、低優先在高優先起訖日切段；開發庫既有紀錄為最高優先）、手繪近似、QA（每個切點日檢查重疊）、產生 `requests/B{1,2,3}/*.json`、`interwar-b-derived.geojson`、`qa.json`；需要 A 批目錄（`../batch-a`，或環境變數 IWA） |')
w('| `build/readme.py` | 產生本檔 |')
w('| `send_seed.py` | 依子批送出（預設 dry-run；拒絕 5051；API key 從 --env 安靜讀取） |')
w('| `db-export/`（不進版控） | 開發庫唯讀匯出：1918-11～1939-07 間既有主權紀錄、西班牙共和國紀錄、A 批 id 表；備份在 `~/01_Projects/world_line_backups/` |\n')
w('用法（在本目錄）：\n```')
w('P="--prior ../../../../.dev/sent-ids.borders-dev.json --prior ../../../../.dev/sent-ids.borders-us-dev.json --prior ../../../../.dev/sent-ids.ww1-balkans-1908-1914-dev.json --prior ../../../../.dev/sent-ids.ww1-war-1914-1918-dev.json --prior ../../../../.dev/sent-ids.interwar-a-dev.json"')
w('python3 send_seed.py --sub B1 --base http://127.0.0.1:5052 --env ../../../../.env.borders-dev $P --ids ../../../../.dev/sent-ids.interwar-b-dev.json [--send]')
w('```\n')
w(f'OHM Overpass `osm_base`：{man[0]["osm_base"]}（UTC）。來源：條約原文（國際聯盟條約集 LNTS 第 2、28、54 卷 PDF）、FRUS 巴黎和會第 XIII 卷（凡爾賽和約）、FRUS 1925 第 I 卷、1931 第 II 卷、1936 第 I、II 卷；找不到正式出處的事件標 **待查證**。\n')
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
 '萊茵蘭三個佔領區（科隆、科布倫茨、美因茲）與魯爾佔領區：萊茵河線、分區線與橋頭堡圓都是手繪粗略近似，再與 OHM 德國外框求交；從 1924-01-01（B 批起點）起畫，1918-12～1923 未畫。杜塞道夫、杜伊斯堡等 1921 年制裁佔領未另分。',
 '西班牙內戰國民軍控制區：八個階段（1936-07-17、11-07、1937-02-08、06-19、08-26、10-21、1938-04-15、1939-02-10）各用手繪多邊形與西班牙範圍求交，只是粗略近似；1938-06 卡斯特利翁、1938-07 拉塞雷納口袋等中間變化未分。共和國控制區＝西班牙減國民軍區。西屬撒哈拉、伊夫尼 1936-07 起歸國民軍；西屬摩洛哥維持原紀錄。革命加泰隆尼亞等自治未另列。',
 '開發庫既有西班牙共和國紀錄缺西屬撒哈拉、伊夫尼與特內里費、富埃特文圖拉等加那利島嶼；重送時從 OHM 2862762 補上。但開發庫既有「西班牙國」紀錄（1939-04-01 起，二戰資料）同樣缺這些地方，1939-04-01 接點在那裡會留白（既有資料，本批未改，待 Tai 決定是否修）。',
 '蘇聯 1925-01-20～1926-01-01 用 OHM 2851271（框外裁掉），1926 年起接開發庫既有紀錄；海岸與北極島嶼有零星細縫（合計約 0.44 平方度）。蘇聯內部各加盟共和國（1924 中亞劃界、1929 塔吉克、1936 新憲法）只記事件，未分範圍。',
 '土耳其 1924-08-06、阿爾巴尼亞 1925-01-21、南斯拉夫 1929-10-03 接點有 OHM 版本間的小細縫（各 0.01～0.04 平方度），沒有重疊。',
 '義大利—衣索比亞戰爭（1935～1936）不在地圖框內（框南界北緯 15°），未做。沙烏地、葉門、伊朗、蘇丹、里奧德奧羅等 A 批也沒畫的地方仍未畫。',
 '北非、近東、冰島、埃及、突尼西亞、茅利塔尼亞沒有後續資料，暫迄 1939-01-01。哈塔伊國 1938-09-02 起，1939-06-29 接開發庫既有土耳其紀錄；1938-07 起法土共同駐軍未另列佔領。',
 '德國 1935-03-01 起用含薩爾的 OHM 2694638；萊茵蘭再軍事化（1936-03-07）只記事件，不改範圍。德奧合併（1938-03-13）與蘇台德（1938-10）沿用開發庫既有紀錄。',
 '希臘 1924-03-25～1935-11-03 為希臘第二共和國；1926 潘加洛斯獨裁未分。阿爾巴尼亞共和國依 FRUS 從 1925-01-21 起（OHM 為 01-31）。',
 '事件標待查證者（見上表）只有日期與摘要，沒有正式出處，送出時不附引用。',
]:
    w(f'- {t}')
open(os.path.join(ROOT, 'README.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print('README lines', len(L))
