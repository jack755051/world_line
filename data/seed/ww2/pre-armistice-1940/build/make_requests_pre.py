"""產生 requests/*.json：停戰前快照 1940-06-04（USMA Map 13）、1940-06-12（USMA Map 14）。DRAFT，待 Tai 檢查，未寫入 appdb_ww2。
先跑 make_prearmistice.py 產生 ../zones-pre-armistice-1940.geojson，再跑本檔。
前置 id：THEATER_WE、REGIME_DE、SRC_TRF（法國那批）；REGIME_FR3（法英那批）。
"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
SEED = os.path.dirname(HERE)
OUT = os.path.join(SEED, 'requests')
os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT):
    if f.endswith('.json'): os.remove(os.path.join(OUT, f))
Z = {}
for f in json.load(open(os.path.join(SEED, 'zones-pre-armistice-1940.geojson')))['features']:
    p = f['properties']; Z[(p['snapshot'], p['zone'])] = (f['geometry'], p)

def w(name, ph, post, body):
    path = os.path.join(OUT, name)
    json.dump({'_placeholder': ph, '_post': post, 'body': body}, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    open(path, 'a').write('\n')

S3 = 'https://s3.amazonaws.com/usma-media/inline-images/academics/academic_departments/history/WWII%20Europe%20Med/'
ARCHIVE = 'https://web.archive.org/web/20230921185042/https://www.westpoint.edu/academics/academic-departments/history/digital-history-center/atlases/world-war-two-europe'
LIC = 'https://commons.wikimedia.org/wiki/Category:World_War_II_maps_of_the_United_States_Military_Academy'
w('01-source-1-src_usma13.json', 'SRC_USMA13', '/api/v1/sources', {
    'sourceKind': 'atlas_map',
    'title': 'Campaign in the West, 1940: Situation 4 June and Operations Since 21 May',
    'publisher': 'United States Military Academy, Department of History',
    'publishedText': 'West Point Atlas, World War II European Theater（USMA 網站版）',
    'licenseCode': 'us_federal_pd', 'licenseEvidenceUrl': LIC,
    'url': S3 + 'WWIIEurope13.jpg', 'archiveUrl': ARCHIVE,
    'catalogId': 'USMA WWII Europe/Med, Map 13',
    'localCopyPath': '/workspace/world-line-ww2/trace/WWIIEurope13.jpg',
    'note': '17 U.S.C. §105 公有領域（美國陸軍官校歷史系製圖，同 Map 15）。5100×3300。粗藍實線＝4 June 戰線（Somme 灣→Montmédy），網格帶＝Maginot 防線；敦克爾克防線註記「Defensive perimeter established 28 May. Evacuation completed night of 4–5 June」。圖框只涵蓋法國北部與比、盧、荷南部。',
})
w('01-source-2-src_usma14.json', 'SRC_USMA14', '/api/v1/sources', {
    'sourceKind': 'atlas_map',
    'title': 'Campaign in the West, 1940: Situation 12 June and Operations Since 4 June',
    'publisher': 'United States Military Academy, Department of History',
    'publishedText': 'West Point Atlas, World War II European Theater（USMA 網站版）',
    'licenseCode': 'us_federal_pd', 'licenseEvidenceUrl': LIC,
    'url': S3 + 'WWIIEurope14.jpg', 'archiveUrl': ARCHIVE,
    'catalogId': 'USMA WWII Europe/Med, Map 14',
    'localCopyPath': '/workspace/world-line-ww2/trace/WWIIEurope14.jpg',
    'note': '17 U.S.C. §105 公有領域。5100×3300。粗藍實線＝12 June 戰線（Seine 河口→Châlons 南，另一段 Second Army 線→Montmédy，兩段之間約 10 km 不連續），網格帶＝Maginot 防線；Pays de Caux 註記「Elements of Tenth Army and British surrendered 12 June」。圖框南緣約北緯 47.3°。',
})
w('01-source-3-src_natural_earth.json', 'SRC_NATURAL_EARTH', '/api/v1/sources', {
    'sourceKind': 'dataset',
    'title': 'Natural Earth 1:10m Cultural Vectors — Admin 0 – Countries',
    'publisher': 'Natural Earth（North American Cartographic Information Society 支援）',
    'licenseCode': 'public_domain',
    'licenseEvidenceUrl': 'https://www.naturalearthdata.com/about/terms-of-use/',
    'url': 'https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-0-countries/',
    'localCopyPath': '/workspace/world-line-ww2/trace/ne_10m_admin_0_countries.geojson',
    'note': '公有領域（官網 terms of use）。現代疆界，只當 auxiliary_geometry：比利時（BEL）、盧森堡（LUX）、荷蘭（NLD）外框。',
})

SNAP = {'1940-06-04': ('SNAP_0604', 'SRC_USMA13', 'Map 13', '4 June'), '1940-06-12': ('SNAP_0612', 'SRC_USMA14', 'Map 14', '12 June')}
TITLE = {'1940-06-04': {'zh-Hant': '法國戰役：敦克爾克撤退結束（1940-06-04）', 'en': 'Campaign in the West: end of the Dunkirk evacuation (1940-06-04)'},
         '1940-06-12': {'zh-Hant': '法國戰役：德軍渡過塞納河、馬恩河（1940-06-12）', 'en': 'Campaign in the West: Germans across the Seine and Marne (1940-06-12)'}}
for i, (d, (ph, src, mapn, label)) in enumerate(SNAP.items(), 1):
    w(f'02-snapshot-{i}-{d}.json', ph, '/api/v1/control-snapshots', {
        'theaterId': '{{THEATER_WE}}', 'asOf': d, 'attestation': 'point', 'title': TITLE[d],
        'asOfNote': {'zh-Hant': f'USMA {mapn}「Situation {label}」：圖上明示的單日戰況。控制紀錄只取這一天（[{d}, 次日)）；與下一個快照之間屬推估（§9），不延長。',
                     'en': f'USMA {mapn}, "Situation {label}": a single dated situation. Control records cover that day only; the span to the next snapshot is interpolation (§9).'}})

def nxt(d): return {'1940-06-04': '1940-06-05', '1940-06-12': '1940-06-13'}[d]

n = 0
for d, (ph, src, mapn, label) in SNAP.items():
    m = Z[(d, 'DE')][1]; tag = d[5:].replace('-', '')
    gcp = f"控制點 {m['gcp']} 個（圖上城市圓點↔經緯度），三次多項式配準，殘差 RMS {m['rms_km']} km、最大 {m['max_km']} km"
    common_aux = [
        {'sourceId': '{{SRC_TRF}}', 'role': 'auxiliary_geometry', 'locator': 'DEPARTEMENTS_1940（doi:10.7910/DVN/ULQYM5）',
         'evidenceNote': '法國 1940 年外框（海岸線、國界）。'},
        {'sourceId': '{{SRC_NATURAL_EARTH}}', 'role': 'auxiliary_geometry', 'locator': 'ne_10m_admin_0_countries，ADM0_A3 = BEL、LUX、NLD',
         'evidenceNote': '比、盧、荷外框（現代疆界；Eupen-Malmedy 仍算在比利時內）。'},
    ]
    n += 1
    w(f'03-control-{n}-de-{tag}.json', f'CR_DE_{tag}', '/api/v1/control-records', {
        'controllerRegimeId': '{{REGIME_DE}}', 'snapshotId': '{{%s}}' % ph, 'controlType': 'military_occupation',
        'validPeriod': {'start': d, 'end': nxt(d)}, 'isDisputed': False, 'geometry': Z[(d, 'DE')][0],
        'citations': [{'sourceId': '{{%s}}' % src, 'role': 'primary',
                       'locator': f'West Point Atlas WWII Europe, {mapn}（Situation {label} 1940）：{label} 粗藍實線與 Maginot 網格帶的北側／西側',
                       'evidenceNote': f'圖上 {label} 戰線以北為德軍控制。描線：線條以顏色門檻＋骨架化自動擷取（build/trace/lines-*.json），{gcp}。扣除：CR_NORD（Nord、Pas-de-Calais，已另有紀錄）、圖框外、Maginot 帶外側狹長地帶與圖上不明處（另列控制資料缺）。'}] + common_aux})
    n += 1
    w(f'03-control-{n}-fr3-{tag}.json', f'CR_FR3_{tag}', '/api/v1/control-records', {
        'controllerRegimeId': '{{REGIME_FR3}}', 'snapshotId': '{{%s}}' % ph, 'controlType': 'direct_rule',
        'validPeriod': {'start': d, 'end': nxt(d)}, 'isDisputed': False, 'geometry': Z[(d, 'FR3')][0],
        'citations': [{'sourceId': '{{%s}}' % src, 'role': 'primary',
                       'locator': f'West Point Atlas WWII Europe, {mapn}（Situation {label} 1940）：{label} 粗藍實線與 Maginot 網格帶的南側／西側',
                       'evidenceNote': f'圖上 {label} 戰線以南為法軍防線後方。{gcp}。只取圖框內；圖框外與圖上不明處列控制資料缺。'}] + common_aux[:1]})

GAPS = {
    'GAP_FRAME': ('not_yet_digitized', '圖框外', 'Outside the map frame',
                  '{map} 圖框外的法國、比、盧、荷領土：本圖沒有畫到，暫無同日的合格地圖。',
                  'Outside the frame of {map}: not shown; no qualified map for this date yet.'),
    'GAP_MAGINOT': ('no_qualified_source', 'Maginot 帶外側', 'Beyond the Maginot belt',
                    '{map} 只畫出 Maginot 要塞帶，沒有標示要塞帶與國界（或萊茵河）之間的狹長地帶由誰控制；以戰線與要塞帶交會點的經線為西界，不推測。',
                    '{map} shows the Maginot belt but not who held the strip between it and the border/Rhine; bounded on the west by the meridian of the junction of the front and the belt.'),
    'GAP_DUNKIRK': ('no_qualified_source', '敦克爾克防線', 'Dunkirk perimeter',
                    'Map 13 註記「Defensive perimeter established 28 May. Evacuation completed night of 4–5 June」：6/4 當日防線內狀態不明。Nord 省內部分已由 CR_NORD 涵蓋（起日不確定 05-28～06-14），這裡只剩比利時境內一小塊。',
                    'Map 13: "Defensive perimeter established 28 May. Evacuation completed night of 4–5 June" — status inside on 4 June unclear. The part in Nord is already covered by CR_NORD.'),
    'GAP_CAUX': ('no_qualified_source', 'Pays de Caux', 'Pays de Caux',
                 'Map 14：12 June 戰線西端以西、8 June 點線以西（Dieppe、St-Valery-en-Caux、Le Havre 一帶），圖註「Elements of Tenth Army and British surrendered 12 June」，Le Havre 未標；6/12 當日控制不明。南界沿塞納河口。',
                 'Map 14: west of the 12 June line and the 8 June dotted line (Dieppe, St-Valery-en-Caux, Le Havre); "Elements of Tenth Army and British surrendered 12 June"; status on 12 June unclear.'),
    'GAP_LINEBREAK': ('no_qualified_source', '戰線不連續處', 'Gap in the front line',
                      'Map 14 的 12 June 戰線在 Châlons 東南斷開（兩段端點相距約 10 km），以兩端點中點為圓心畫圓，列為不明。',
                      'Map 14: the 12 June line breaks south-east of Châlons (~10 km); a circle around the break is left as unclear.'),
}
k = 0
for d, (ph, src, mapn, label) in SNAP.items():
    tag = d[5:].replace('-', '')
    for zone in ['GAP_FRAME', 'GAP_MAGINOT', 'GAP_DUNKIRK', 'GAP_CAUX', 'GAP_LINEBREAK']:
        if (d, zone) not in Z: continue
        reason, zh_t, en_t, zh, en = GAPS[zone]
        k += 1
        w(f'04-coverage-{k}-{zone.lower()}-{tag}.json', f'{zone}_{tag}', '/api/v1/control-coverage-notes', {
            'theaterId': '{{THEATER_WE}}', 'geometry': Z[(d, zone)][0],
            'validPeriod': {'start': d, 'end': nxt(d)}, 'reason': reason,
            'note': {'zh-Hant': f'{zh_t}：' + zh.format(map=f'USMA {mapn}'), 'en': f'{en_t}: ' + en.format(map=f'USMA {mapn}')},
            'researchRef': 'data/seed/ww2/pre-armistice-1940/README.md；build/make_prearmistice.py'})
print(sorted(os.listdir(OUT)))
