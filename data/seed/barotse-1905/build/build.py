#!/usr/bin/env python3
"""產生 barotse-1905 的幾何與請求檔。只讀開發庫（5442 的容器），不寫任何資料。
問題：安哥拉與巴羅策蘭—西北羅德西亞的界線，資料庫到 1915-03-05 才改用 1905 年仲裁裁決的線（東經 22 度、南緯 13 度、東經 24 度），
      在那之前畫在東經 20 度。裁決是 1905-05-30 作成的，1908 年起就該用裁決線。
做法：三筆撤回重寫，幾何全部取自資料庫裡 1915-03-05 之後的紀錄，不重新取回 OHM。
  ANGOLA_1908   葡屬安哥拉 1908-01-01～1915-03-05：改用 1915 年之後那一筆的形狀
  BAROTSE_1908  巴羅策蘭—西北羅德西亞 1908-01-01～1911-08-17：原形狀扣掉安哥拉（1915 年之後的形狀）
  NR_1911       北羅德西亞 1911-08-17～1915-03-05：改用 1915 年之後那一筆的形狀
用法：python3 -I build/build.py
"""
import json, os, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
REL = {'a08': 2962064, 'a15': 2690861, 'b08': 2803155, 'n11': 2691743, 'n15': 2962062}
def q(sql):
    return subprocess.run(['docker', 'exec', 'worldline-borders-dev-db', 'psql', '-U', 'worldline', '-d', 'worldline_borders_dev', '-At', '-c', sql],
                          check=True, capture_output=True, text=True).stdout.strip()
COLS = "id, regime_id, lower(valid_period) lo, upper(valid_period) hi, geometry_source_id, geometry_locator, geometry_license, attribution, ohm_relation_id, ohm_version, ohm_fetched_at, ohm_start_raw, ohm_end_raw, provenance, round((st_area(geom::geography)/1e6)::numeric,1) km2"
recs = {k: json.loads(q(f"select row_to_json(t) from (select {COLS} from sovereignty_records where retracted_at is null and ohm_relation_id = {r}) t")) for k, r in REL.items()}
g = lambda k: f"(select st_makevalid(geom) from sovereignty_records where id = '{recs[k]['id']}')"
geo = json.loads(q(f"""select json_build_object(
  'ANGOLA_1908', st_asgeojson({g('a15')}, 7)::json, 'NR_1911', st_asgeojson({g('n15')}, 7)::json,
  'BAROTSE_1908', st_asgeojson(st_multi(st_collectionextract(st_difference({g('b08')}, {g('a15')}), 3)), 7)::json,
  'barotse_km2', st_area(st_difference({g('b08')}, {g('a15')})::geography) / 1e6,
  'sliver_km2', (select coalesce(sum(st_area(d.geom::geography)), 0) / 1e6 from st_dump(st_difference({g('b08')}, {g('a15')})) d where st_area(d.geom::geography) < 5e7))"""))
print('巴羅策蘭新面積', round(geo['barotse_km2'], 1), '其中小於 50 平方公里的碎片合計', round(geo['sliver_km2'], 2))
json.dump({'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'id': k, 'properties': {}, 'geometry': geo[k]} for k in ('ANGOLA_1908', 'BAROTSE_1908', 'NR_1911')]},
          open(os.path.join(ROOT, 'barotse-1905-derived.geojson'), 'w'), ensure_ascii=False)
def write(name, obj): json.dump(obj, open(os.path.join(ROOT, 'requests', name), 'w'), ensure_ascii=False, indent=1)
AWARD = '1905-05-30 義大利國王仲裁裁決（The Barotseland Boundary Case）'
LINE = '裁決線：卡蒂馬急流—安達拉直線到寬多河、寬多河東岸到東經 22 度、東經 22 度到南緯 13 度、南緯 13 度到東經 24 度、東經 24 度到剛果自由邦邊界'
write('01-source-riaa-xi-barotse.json', {'_placeholder': 'SRC_RIAA_XI_BAROTSE', '_post': '/api/v1/sources', 'body': {
    'sourceKind': 'official_record',
    'title': 'The Barotseland Boundary Case (Great Britain, Portugal), Award of 30 May 1905, Reports of International Arbitral Awards, vol. XI, pp. 59–69',
    'publisher': 'United Nations', 'licenseCode': 'pd_expired',
    'licenseEvidenceUrl': 'https://legal.un.org/riaa/cases/vol_XI/59-69.pdf', 'url': 'https://legal.un.org/riaa/cases/vol_XI/59-69.pdf',
    'family': 'barotse-award-1905', 'grade': 'A',
    'gradeBasis': '仲裁人（義大利國王維克多·伊曼紐三世）1905-05-30 作成的裁決本文，彙編收錄的是官方法文譯本（原載英國國會文件 Africa No. 5 (1905), Cd. 2584）。裁決本身是 A。',
    'note': '2026-11-14 聯合國網站維護中，本文取自 web.archive.org 2026-01-17 的存檔；PDF 的 SHA-256 為 13e3c3b1e26b61dedf426bf10723c7f14708b73eb5a2f7ce8f035e6cb6481a52。授權：1905 年的裁決本文已屬公有領域；彙編的編排由聯合國出版。'}})
def retract(n, key, why):
    r = recs[key]
    write(f'{n}a-retract-{key}.json', {'_placeholder': f'RETRACTED_{key.upper()}', '_post': f"/api/v1/sovereignty-records/{r['id']}/retraction", '_meta': {'fix': True},
          'body': {'reason': why + '（barotse-1905：撤回後重新新增。）'}})
def create(n, ph, old, shape_from, locator, note_zh, note_en, derived):
    o, s = recs[old], recs[shape_from]
    write(f'{n}b-sovereignty-{ph.lower()}.json', {'_placeholder': ph, '_post': '/api/v1/sovereignty-records', '_geometryFrom': ph, '_meta': {'replaces': o['id'], 'oldKm2': float(o['km2'])}, 'body': {
        'regimeId': o['regime_id'], 'geometry': None, 'validPeriod': {'start': o['lo'], 'end': o['hi']}, 'layerStatus': 'de_jure',
        'geometrySourceId': s['geometry_source_id'], 'geometryLocator': locator, 'geometryLicense': s['geometry_license'], 'attribution': s['attribution'],
        'startEventId': None, 'endEventId': None,
        **({'ohmRelationId': None, 'ohmVersion': None, 'ohmFetchedAt': None, 'ohmStartRaw': None, 'ohmEndRaw': None} if derived else
           {'ohmRelationId': s['ohm_relation_id'], 'ohmVersion': s['ohm_version'], 'ohmFetchedAt': s['ohm_fetched_at'], 'ohmStartRaw': s['ohm_start_raw'], 'ohmEndRaw': s['ohm_end_raw']}),
        'provenance': {**(s['provenance'] or {}), 'fix': {'batch': 'barotse-1905', 'replaces': o['id'], 'replacedLocator': o['geometry_locator'], 'shapeFromRecord': s['id'], 'derived': derived,
                       'reason': f'{AWARD}的界線自 1908-01-01 起適用；OHM 把這條線的起日記為 1915-03-05'}},
        'note': {'zh-Hant': note_zh, 'en': note_en}}})
retract('02', 'a08', '葡屬安哥拉 1908-01-01～1915-03-05：東界畫在東經 20 度，是 1905 年仲裁之前的線；1905-05-30 裁決已把界線定在東經 22 度、南緯 13 度、東經 24 度，兩套 1910 年前後的地圖集也都畫裁決線。')
create('02', 'ANGOLA_1908', 'a08', 'a15', f"relation/{recs['a15']['ohm_relation_id']} v{recs['a15']['ohm_version']}（沿用 1915-03-05 起那一筆的形狀）",
       f'東界用 {AWARD}的界線。{LINE}。幾何沿用 1915-03-05 起那一筆（OHM 把這個形狀的起日記為 1915-03-05；1915 年那個日期是什麼事件還沒查）。',
       'Eastern boundary follows the arbitral award of 30 May 1905. Geometry copied from the record starting 1915-03-05.', False)
retract('03', 'b08', '巴羅策蘭—西北羅德西亞 1908-01-01～1911-08-17：西界畫在東經 20 度，是 1905 年仲裁之前英方的主張線；1905-05-30 裁決已把界線定在東經 22 度、南緯 13 度、東經 24 度。')
create('03', 'BAROTSE_1908', 'b08', 'b08', f"{recs['b08']['geometry_locator']} 扣除 relation/{recs['a15']['ohm_relation_id']} v{recs['a15']['ohm_version']}（安哥拉，裁決線以西）",
       f'西界用 {AWARD}的界線。{LINE}。幾何是原紀錄扣掉裁決線以西歸安哥拉的部分；與東北羅德西亞之間的內部界線沒有變動，也沒有另外查證。',
       'Western boundary follows the arbitral award of 30 May 1905: the retracted geometry minus the part west of the award line (Angola).', True)
retract('04', 'n11', '北羅德西亞 1911-08-17～1915-03-05：西界畫在東經 20 度，是 1905 年仲裁之前的線；1905-05-30 裁決已把界線定在東經 22 度、南緯 13 度、東經 24 度。')
create('04', 'NR_1911', 'n11', 'n15', f"relation/{recs['n15']['ohm_relation_id']} v{recs['n15']['ohm_version']}（沿用 1915-03-05 起那一筆的形狀）",
       f'西界用 {AWARD}的界線。幾何沿用 1915-03-05 起那一筆（與原紀錄扣掉安哥拉後只差 8 平方公里）。',
       'Western boundary follows the arbitral award of 30 May 1905. Geometry copied from the record starting 1915-03-05.', False)
Q = '「Le 22e méridien est de Greenwich jusqu\'au point d\'intersection avec le 13e parallèle; Le 13e parallèle jusqu\'au point d\'intersection avec le 24e méridien est de Greenwich; Le 24e méridien est de Greenwich jusqu\'à la frontière de l\'Etat Indépendant du Congo.」'
def cite(n, ph, target, src, locator, note, grade, basis):
    write(f'{n}-citation-{ph.lower()}.json', {'_placeholder': ph, '_post': '/api/v1/sovereignty-records/{{%s}}/citations' % target,
          'body': {'sourceId': '{{%s}}' % src, 'locator': locator, 'evidenceNote': note, 'grade': grade, 'gradeBasis': basis}})
AW = ('p. 69（裁決主文）', '裁決主文：' + Q + ' 只證明{side}這一段界線；紀錄其餘的輪廓不靠這筆引文。', 'A', '仲裁裁決本文（官方法文譯本）。逐字核對過存檔的 PDF 文字層，2026-11-14。')
SH = ('pp. 174–175, The Partition of Africa（archive.org 掃描頁 n166–n167）', 'B', '具名學者編著的歷史地圖集圖版（學術地圖集為 B）。Claude 目視比對，2026-11-14，待考證複核。')
CM = ('Map 130, Africa in 1910（archive.org 掃描頁 n589–n590）', 'B', '學術機構出版的歷史地圖集圖版（學術地圖集為 B）。Claude 目視比對，2026-11-14，待考證複核。')
cite('05', 'CITE_ANGOLA_AWARD', 'ANGOLA_1908', 'SRC_RIAA_XI_BAROTSE', AW[0], AW[1].format(side='安哥拉東邊'), AW[2], AW[3])
cite('06', 'CITE_ANGOLA_SHEPHERD', 'ANGOLA_1908', 'SRC_SHEPHERD_1911', SH[0], '圖版畫出：葡屬西非（安哥拉），東界是標「1905」的虛線（仲裁線）。本紀錄改用裁決線之後，輪廓與鄰接關係和圖相符。比例尺 1:40,000,000，只能確認到輪廓與鄰接關係，不能確認邊界細節。', SH[1], SH[2])
cite('07', 'CITE_ANGOLA_CMHA', 'ANGOLA_1908', 'SRC_CMHA_1924', CM[0], '圖版畫出：安哥拉以葡萄牙色著色，東界在卡邦波河、尚比西河一帶與西北羅德西亞相接。本紀錄改用裁決線之後，輪廓與鄰接關係和圖相符。只能確認到輪廓與鄰接關係，不能確認邊界細節。', CM[1], CM[2])
cite('08', 'CITE_BAROTSE_AWARD', 'BAROTSE_1908', 'SRC_RIAA_XI_BAROTSE', AW[0], AW[1].format(side='巴羅策蘭西邊'), AW[2], AW[3])
cite('09', 'CITE_BAROTSE_SHEPHERD', 'BAROTSE_1908', 'SRC_SHEPHERD_1911', SH[0], '圖版畫出：巴羅策（Barotse）一帶以英國色著色，西界是標「1905」的虛線（仲裁線）。本紀錄改用裁決線之後，西界與圖相符。圖上沒有畫出它與東北羅德西亞之間的內部界線，那一段不靠這筆引文。比例尺 1:40,000,000。', SH[1], SH[2])
cite('10', 'CITE_BAROTSE_CMHA', 'BAROTSE_1908', 'SRC_CMHA_1924', CM[0], '圖版標「N. Western Rhodesia」，以英國色著色，西界在卡邦波河、尚比西河一帶與安哥拉相接。本紀錄改用裁決線之後，西界與圖相符。圖上沒有畫出它與東北羅德西亞之間的內部界線，那一段不靠這筆引文。', CM[1], CM[2])
# 北羅德西亞 1911–1915 不附裁決引文：裁決只證明西界這一段，其餘輪廓沒有出處，附了會讓整筆變成已查證
for k in recs: print(k, recs[k]['lo'], recs[k]['hi'], recs[k]['km2'], recs[k]['geometry_license'])
