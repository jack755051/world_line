#!/usr/bin/env python3
"""1940 波羅的海三國：修正空白與重疊（DRAFT，待 Tai 檢查）。
- 拉脫維亞共和國止於 1940-06-16（OHM），拉脫維亞蘇維埃共和國 07-21 才開始 → 06-16～07-21 空白。
  依愛沙尼亞、立陶宛的既有處理（共和國到 07-21 宣布蘇維埃制度為止），補一筆拉脫維亞共和國 [06-16, 07-21)，幾何同原紀錄。
- 立陶宛共和國到 08-03，與立陶宛蘇維埃共和國（07-21 起）重疊 → 撤回後改為到 07-21。
- 立陶宛蘇維埃共和國到 08-04，但蘇聯 08-03 起已含立陶宛（接納加入，事件 08-03）→ 改為到 08-03。
- 拉脫維亞蘇維埃共和國到 08-04，蘇聯 08-05 才含拉脫維亞（接納加入，事件 08-05）→ 08-04 一天空白，改為到 08-05。
幾何、來源、OHM 釘選資訊沿用舊紀錄（old-records.jsonl，唯讀 SQL 匯出）。撤回再新增，不刪除。
"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); OUT = os.path.join(ROOT, 'requests')
OLD = {}
for l in open(os.path.join(ROOT, 'old-records.jsonl'), encoding='utf-8'):
    d = json.loads(l); OLD[d['slug']] = d
json.dump({'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'id': 'OLD_' + d['slug'], 'properties': {}, 'geometry': d['geom']} for d in OLD.values()]},
          open(os.path.join(ROOT, 'baltic-1940-fix-derived.geojson'), 'w'), separators=(',', ':'))
def write(name, ph, post, body, meta=None, geom=None):
    req = {'_placeholder': ph, '_post': post, **({'_geometryFrom': geom} if geom else {}), **({'_meta': meta} if meta else {}), 'body': body}
    with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f:
        json.dump(req, f, ensure_ascii=False, indent=1); f.write('\n')
EV_LV_OCC, EV_LV_SSR, EV_LT_SSR, EV_LT_ADM, EV_LV_ADM = ('01a18e71-cf94-7d88-ba34-9466fe588d4d', '01a18e71-cfba-795e-808a-e19913bfd477',
    '01a18e71-cfae-7691-a03a-a5de63e7c3ee', '01a18e71-cfe8-73b0-b456-4310148c21f7', '01a18e71-cff5-7837-a7a4-8e89a2bba55d')
def rec(i, ph, slug, start, end, sev, eev, nzh, nen, replaces=True):
    o = OLD[slug]
    body = {'regimeId': o['regimeId'], 'geometry': None, 'validPeriod': {'start': start, 'end': end}, 'layerStatus': o['layer'],
            'geometrySourceId': o['src'], 'geometryLocator': o['loc'], 'geometryLicense': o['lic'], 'attribution': o['attr'],
            'startEventId': sev, 'endEventId': eev, 'ohmRelationId': o['rel'], 'ohmVersion': o['ver'], 'ohmFetchedAt': o['fetched'],
            'ohmStartRaw': o['sraw'], 'ohmEndRaw': o['eraw'],
            'provenance': {**o['prov'], ('supersedes' if replaces else 'extends'): o['id'], 'fixBatch': 'baltic-1940-fix'},
            'note': {'zh-Hant': nzh, 'en': nen}}
    write(f'02-sovereignty-{i:02d}-{ph.lower()}.json', ph, '/api/v1/sovereignty-records', body, {'fix': True}, geom='OLD_' + slug)
RET = [('republic-of-lithuania', '與立陶宛蘇維埃共和國 1940-07-21～08-03 重疊；改為到 07-21（宣布蘇維埃制度）。'),
       ('lithuanian-ssr', '止於 08-04，但蘇聯 08-03 起已含立陶宛（接納加入）而重疊一天；改為到 08-03。'),
       ('latvian-ssr', '止於 08-04，蘇聯 08-05 才含拉脫維亞（接納加入）而空白一天；改為到 08-05。')]
for i, (slug, why) in enumerate(RET, 1):
    write(f'01-retract-{i:02d}-{slug}.json', f'RETRACTED_{slug.upper().replace("-", "_")}_1940', f'/api/v1/sovereignty-records/{OLD[slug]["id"]}/retraction',
          {'reason': f'{slug}：{why}同一幾何重新新增。'}, {'fix': True})
rec(1, 'SOVBL_LT', 'republic-of-lithuania', '1939-10-28', '1940-07-21', OLD['republic-of-lithuania']['sev'], EV_LT_SSR,
    '立陶宛共和國，至 1940-07-21「人民議會」宣布蘇維埃制度為止（與愛沙尼亞同樣處理）。OHM 結束日為 08-03，這裡提前以免與立陶宛蘇維埃共和國重疊。1940-06-15 起蘇軍進駐，未另分段。',
    'Republic of Lithuania until the proclamation of Soviet rule on 21 Jul 1940 (OHM end 3 Aug moved earlier to avoid overlapping the Lithuanian SSR).')
rec(2, 'SOVBL_LT_SSR', 'lithuanian-ssr', '1940-07-21', '1940-08-03', EV_LT_SSR, EV_LT_ADM,
    '立陶宛蘇維埃共和國，至 1940-08-03 蘇聯接納加入（之後劃入蘇聯紀錄）。OHM 結束日 08-04，配合事件日改為 08-03。',
    'Lithuanian SSR until admission to the USSR on 3 Aug 1940.')
rec(3, 'SOVBL_LV_SSR', 'latvian-ssr', '1940-07-21', '1940-08-05', EV_LV_SSR, EV_LV_ADM,
    '拉脫維亞蘇維埃共和國，至 1940-08-05 蘇聯接納加入（之後劃入蘇聯紀錄）。OHM 結束日 08-04，配合事件日改為 08-05，補一天空白。',
    'Latvian SSR until admission to the USSR on 5 Aug 1940.')
rec(4, 'SOVBL_LV_FILL', 'republic-of-latvia', '1940-06-16', '1940-07-21', EV_LV_OCC, EV_LV_SSR,
    '拉脫維亞共和國 1940-06-16～07-21：OHM 共和國止於 06-16（蘇聯最後通牒、蘇軍進駐，待查證），蘇維埃共和國 07-21 才開始；依愛沙尼亞、立陶宛的處理，共和國畫到 07-21 宣布蘇維埃制度為止，幾何同 06-16 前的紀錄。蘇軍佔領期間未另標非主權（三國一致，簡化）。',
    'Republic of Latvia 16 Jun–21 Jul 1940 filled to match Estonia and Lithuania (republic until the proclamation of Soviet rule); same geometry as before 16 Jun.',
    replaces=False)
print('ok')
