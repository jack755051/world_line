#!/usr/bin/env python3
"""接點修補第二輪（F3）：1940-08-05 蘇聯／愛沙尼亞重疊、各細縫（南斯拉夫 1929-10-03、波蘭與蘇聯 1939-10-06、德國 1939-10-26）、
1939-03-14～16 捷克斯洛伐克（波希米亞—摩拉維亞）6.10 平方度缺口與喀爾巴阡烏克蘭。全部先撤後增；幾何在送出時由開發庫 PostGIS 合併／扣除。
輸入 ../exp_all.json（開發庫唯讀匯出）。輸出 ../requests/F3/*.json、../qa-f3.json。"""
import json, os, sys, glob
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from load import *
from shapely.geometry import mapping, box, MultiPolygon, Polygon
from shapely import set_precision
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
TAG = '接點修補第二輪 2026-11-01'
REQ = []; QA = {'fills': [], 'notes': []}
def add(cat, name, ph, post, body, readd=None, meta=None):
    REQ.append(dict(cat=cat, name=name, ph=ph, post=post, body=body, readd=readd, meta=meta))
def mp(g):
    ps = [p for p in pieces(g, 1e-9)]
    return mapping(MultiPolygon(ps))
def ret(rid, reason, ph):
    add('03-retract', 'retract_' + ph.lower(), 'RETRACTED_' + ph, f'/api/v1/sovereignty-records/{rid}/retraction', {'reason': f'{TAG}：{reason}'}, meta={'fix': True})
def readd(ph, base, override, union=None, subtract=None, geom_from=None, note=None):
    add('04-sovereignty', ph.lower(), ph, '/api/v1/sovereignty-records', override, readd={'base': base, 'geomFrom': geom_from or base, 'union': mp(union) if union is not None else None,
        'subtract': mp(subtract) if subtract is not None else None, 'noteAppend': note}, meta={'fix': True})
def n(zh, en): return {'zh-Hant': zh, 'en': en}
FRUS39I = '01a18e71-c987-7510-8664-a2417279307b'
# ── 細縫：往後補進同政權的後繼紀錄（扣掉同期其他紀錄，保證不重疊）──
def gap_of(rid, d):
    r = BYID[rid]; ub = unary_union([x['g'] for x in active(d) if x['g'].intersects(r['g'])])
    return r['g'].difference(ub)
def fill(G, slug, lo_min, label, extra=None):
    """G 補進 slug 自 lo_min 起每筆紀錄：每筆只加「該紀錄期間沒被其他紀錄蓋到」的部分。回傳 {record_id: add_geom}"""
    out = {}
    for r in sorted([r for r in R if r['slug'] == slug and r['lo'] >= lo_min and r['lo'] < '1945-09-03'], key=lambda r: r['lo']):
        oth = [x['g'] for x in R if x['id'] != r['id'] and x['lo'] < r['hi'] and x['hi'] > r['lo'] and x['g'].intersects(G)]
        a = G.difference(r['g'])
        if oth: a = a.difference(unary_union(oth))
        a = MultiPolygon(pieces(a, 1e-7)) if pieces(a, 1e-7) else None
        if a is not None and (a.area > 1e-4 or (r["lo"] == lo_min and a.area > 1e-6)):
            out[r['id']] = a; QA['fills'].append([label, slug, r['lo'], r['hi'], r['id'], round(a.area, 5)])
    return out
YU = fill(gap_of('01a193e1-bf52-7f7a-aa6b-f256f3a113da', '1929-10-03'), 'kingdom-of-yugoslavia', '1929-10-03', '南斯拉夫 1929-10-03 島嶼細縫')
PLg = gap_of('01a18e71-dac6-7fc8-92e8-e05987095847', '1939-10-06')
SPISZ = MultiPolygon([p for p in pieces(PLg, 1e-6) if p.representative_point().x < 22])
PL_N = MultiPolygon([p for p in pieces(PLg, 1e-6) if p.representative_point().x >= 22])
SUg = gap_of('01a193fc-147e-7ac6-bdd4-18f8017973ee', '1939-10-06')
SU = fill(unary_union([PL_N, SUg]), 'soviet-union', '1939-10-06', '波蘭東北與蘇聯 1939-10-06 細縫')
DE = fill(gap_of('01a1920c-f9ce-7e52-a401-4b596fc22512', '1939-10-26'), 'deutsches-reich', '1939-10-26', '德國 1939-10-26 西界細縫')
NOTE_FILL = n('補上前一筆紀錄已有、此筆漏掉的細縫（只補同期沒有其他紀錄的部分）。', 'Slivers present in the preceding record filled in (only where no other record covers them).')
def emit_fill(d, tag):
    for i, (rid, g) in enumerate(sorted(d.items(), key=lambda kv: BYID[kv[0]]['lo']), 1):
        if rid == SU_OVL: continue
        ph = f'{tag}_{i:02d}'
        ret(rid, f'補細縫（{BYID[rid]["slug"]} {BYID[rid]["lo"]}～{BYID[rid]["hi"]}）', ph)
        readd(ph, rid, {}, union=g, note=NOTE_FILL)
# 1940-08-05 蘇聯／愛沙尼亞 SSR 重疊（＋與土耳其 0.001）
SU_OVL = '01a193fc-382c-7bc6-b130-6eabedadafa8'
su = BYID[SU_OVL]
est = [x for x in active('1940-08-05') if x['slug'] == 'estonian-ssr'][0]
tr = [x for x in active('1940-08-05') if x['slug'] == 'republic-of-turkey'][0]
trc = tr['g'].intersection(su['g'])
SUB = unary_union([est['g'], tr['g'].intersection(box(*trc.buffer(0.2).bounds))])
emit_fill(YU, 'SOV_YU_FIX'); emit_fill(SU, 'SOV_SU_FIX'); emit_fill(DE, 'SOV_DE_FIX')
ret(SU_OVL, '1940-08-05～08-06 與愛沙尼亞 SSR（0.111 平方度）及土耳其（0.001）重疊，扣掉後重送', 'SOV_SU_19400805')
readd('SOV_SU_19400805', SU_OVL, {}, union=SU.get(SU_OVL), subtract=SUB,
      note=n('扣掉與愛沙尼亞 SSR（1940-08-06 才併入）及土耳其重疊的部分' + ('，並補細縫' if SU_OVL in SU else '') + '。', 'Overlap with the Estonian SSR (joined 6 Aug 1940) and Turkey removed.'))
QA['notes'].append(['su-1940-08-05 subtract', round(su['g'].intersection(SUB).area, 4)])
# 斯洛伐克：1939-10-06 起取得斯皮什／奧拉瓦（波蘭紀錄止於 10-06 後留白；11-21 正式併入的同一地區）
SK = '01a18e71-dbf1-75e3-812c-176e5e79ae96'; EV_PL_END = '01a18e71-cf18-7d82-985d-e56a0a0fdd8b'
ret(SK, '波蘭紀錄止於 1939-10-06，斯皮什／奧拉瓦（1939-11-21 正式併入斯洛伐克）在 10-06～11-21 留白；拆段補上', 'SOV_SK_1939')
readd('SOV_SK_1939_A', SK, {'validPeriod': {'start': '1939-04-04', 'end': '1939-10-06'}, 'endEventId': EV_PL_END})
readd('SOV_SK_1939_B', SK, {'validPeriod': {'start': '1939-10-06', 'end': '1939-11-21'}, 'startEventId': EV_PL_END}, union=SPISZ,
      note=n('1939-10-06 起含斯洛伐克軍隊 9 月佔領的斯皮什／奧拉瓦（11-21 依德斯協定正式併入；10-06 為波蘭紀錄止日，待查證）。', 'Includes the Spisz/Orava areas occupied by Slovak troops in Sept 1939 (formally annexed 21 Nov).'))
QA['fills'].append(['斯皮什／奧拉瓦', 'slovak-state-1939', '1939-10-06', '1939-11-21', SK, round(SPISZ.area, 4)])
# ── 捷克斯洛伐克 1939-03-14～16、喀爾巴阡烏克蘭 ──
CS = '01a18e71-d251-7d3b-9cce-9198603f0684'; PR = '01a1920c-ff09-726c-9224-6e2a3ea732f6'
H14 = '01a18e71-d7e7-72b2-a9b6-53212d2d9d2d'; H11 = '01a18e71-d7c7-7be3-bf8b-721c2f9d1a85'
EV_SK_INDEP = '01a18e71-ceab-7699-9f82-cf6bb8bda659'; EV_HU_CU = '01a18e71-ceb8-755e-99ed-22a72f7003ec'; EV_CS_END = '01a18e71-cec4-76b5-8377-684b0ab0a984'
CU = MultiPolygon(pieces(BYID[H14]['g'].difference(BYID[H11]['g']), 1e-6))
add('01-regime', 'carpatho-ukraine-1939', 'REGIME_CU', '/api/v1/regimes', {'slug': 'carpatho-ukraine-1939', 'names': [{'nameKind': 'self', 'originalText': 'Карпатська Україна', 'originalLang': 'uk',
    'display': {'zh-Hant': '喀爾巴阡烏克蘭（匈牙利佔領中）', 'en': 'Carpatho-Ukraine (under Hungarian occupation)'}, 'isPrimary': True}]}, meta={'priorPlaceholder': False})
def ev(ph, start, end, kind, zh, en, parts, cites=None, tz=None, te=None):
    b = {'eventKind': kind, 'occurred': {'start': start, 'end': end}, 'datePrecision': 'day', 'summary': n(zh, en), 'participants': parts, 'citations': cites or []}
    if not cites: tz = '未找到正式出處（待查證）。' + (tz or ''); te = 'No formal source located yet (pending). ' + (te or '')
    if tz: b['timeNote'] = n(tz, te or tz)
    add('02-event', ph.lower(), ph, '/api/v1/events', b, meta={'verification': 'verified' if cites else 'pending（待查證）'})
RG_HU = '01a18e71-cbcc-78b3-88e2-758f1e3423ec'; RG_CS = '01a18e71-cbb8-79ec-af68-6ecc0a00e35a'; RG_PR = '01a1920c-f61e-7766-aafd-8df5f800bd89'; RG_DE = '01a18e71-c9ba-719c-bc51-3086edef89bc'
ev('EV_CU_PROCLAIM', '1939-03-15', '1939-03-16', 'political', '喀爾巴阡烏克蘭宣布獨立（沃洛申），匈牙利軍隊同時推進', 'Carpatho-Ukraine proclaims independence (Voloshyn) as Hungarian troops advance',
   [{'regimeId': '{{REGIME_CU}}', 'role': 'other'}, {'regimeId': RG_HU, 'role': 'belligerent'}], None,
   'FRUS 1939 I Doc. 45（布拉格 3/17 電）只記魯塞尼亞「部分被匈牙利軍隊佔領」，未記獨立宣言日期。', 'FRUS 1939 I Doc. 45 (17 Mar) only says Ruthenia was partially occupied by Hungarian troops.')
ev('EV_CU_ANNEX', '1939-03-18', '1939-03-19', 'political', '匈牙利完成佔領喀爾巴阡烏克蘭並併入', 'Hungary completes the occupation of Carpatho-Ukraine and annexes it',
   [{'regimeId': RG_HU, 'role': 'other'}, {'regimeId': '{{REGIME_CU}}', 'role': 'other'}], None,
   '佔領完成日（3/16 攻下胡斯特、3/18 抵波蘭邊界）為通行說法；匈牙利國會併入法案 1939-03-23 前後（未分）。', 'Completion date per common accounts; annexation law not split.')
# 捷克斯洛伐克殘部 1939-03-14～15：保護國範圍＋喀爾巴阡烏克蘭（斯洛伐克 3/14 獨立後）
readd('SOV_CS_19390314', CS, {'validPeriod': {'start': '1939-03-14', 'end': '1939-03-15'}, 'startEventId': EV_SK_INDEP, 'endEventId': EV_CS_END,
      'geometryLocator': '@locator（1939-03-14：斯洛伐克獨立後的波希米亞、摩拉維亞與喀爾巴阡烏克蘭＝保護國紀錄範圍＋喀爾巴阡烏克蘭）'},
      geom_from=PR, union=CU, note=n('1939-03-14 斯洛伐克獨立後、3/15 德軍進佔前，捷克斯洛伐克只剩波希米亞、摩拉維亞與喀爾巴阡烏克蘭（幾何取保護國紀錄與匈牙利 1939-03-14 版多出的部分）。',
      'Rump Czecho-Slovakia on 14 Mar 1939 (Bohemia, Moravia, Carpatho-Ukraine).'))
# 保護國：起日 3/16 → 3/15（德軍 3/15 清晨 6 時開始進佔；保護國命令 3/16）
ret(PR, '1939-03-15 德軍進佔波希米亞、摩拉維亞當天留白；起日提前到 03-15 後重送', 'SOV_PR_1939')
readd('SOV_PR_1939', PR, {'validPeriod': {'start': '1939-03-15', 'end': '1945-05-08'}},
      note=n('1939-03-15 德軍進佔（FRUS 1939 I Doc. 31：清晨 6 時開始），3/16 希特勒命令成立保護國（Doc. 46, p. 52）；03-15 當天另列德國軍事管理。', 'German occupation began 6 a.m. 15 Mar (FRUS 1939 I Doc. 31); Protectorate decree 16 Mar (Doc. 46, p. 52).'))
# 匈牙利：3/14～3/18 扣掉喀爾巴阡烏克蘭，3/18 起原樣
ret(H14, '喀爾巴阡烏克蘭 1939-03-14 起整塊算匈牙利，改為 3/15～3/18 匈牙利佔領中、3/18 併入；拆段後重送', 'SOV_HU_19390314')
readd('SOV_HU_19390314_A', H14, {'validPeriod': {'start': '1939-03-14', 'end': '1939-03-18'}, 'endEventId': '{{EV_CU_ANNEX}}'}, subtract=CU,
      note=n('1939-03-14～03-17 不含喀爾巴阡烏克蘭（3/14 仍屬捷克斯洛伐克，3/15～3/17 為匈牙利佔領中的喀爾巴阡烏克蘭）。', 'Excludes Carpatho-Ukraine until 18 Mar 1939.'))
readd('SOV_HU_19390314_B', H14, {'validPeriod': {'start': '1939-03-18', 'end': '1939-04-04'}, 'startEventId': '{{EV_CU_ANNEX}}'},
      note=n('1939-03-18 起含喀爾巴阡烏克蘭（佔領完成、併入；日期待查證）。', 'Includes Carpatho-Ukraine from 18 Mar 1939.'))
readd('SOV_CU_1939', H14, {'regimeId': '{{REGIME_CU}}', 'layerStatus': 'not_sovereign', 'validPeriod': {'start': '1939-03-15', 'end': '1939-03-18'}, 'startEventId': '{{EV_CU_PROCLAIM}}', 'endEventId': '{{EV_CU_ANNEX}}',
      'geometryLocator': '@locator − 匈牙利 1938-11-02 版（relation/2747872 舊版範圍）＝喀爾巴阡烏克蘭',
      'note': n('非主權：3/15 宣布獨立，未獲承認，同時被匈牙利軍隊佔領（FRUS 1939 I Doc. 45：3/17 時「部分被匈牙利軍隊佔領」）；範圍＝匈牙利 1939-03-14 版減 1938-11-02 版。', 'Not sovereign: proclaimed independence 15 Mar, occupied by Hungary.')},
      subtract=BYID[H11]['g'])
def occ(ph, occd, occr, kind, lo, hi, basis, zh, en, co=False):
    add('05-occupation', ph.lower(), ph, '/api/v1/occupation-attributions', {'occupiedRegimeId': occd, 'occupierRegimeId': occr, 'controlKind': kind, 'validPeriod': {'start': lo, 'end': hi},
        'basisEventId': basis, 'coOccupied': co, 'note': n(zh, en)})
occ('OCC_CU_HU', '{{REGIME_CU}}', RG_HU, 'military_administration', '1939-03-15', '1939-03-18', EV_HU_CU, '匈牙利軍隊佔領中（3/14 越界，3/18 完成；待查證）。', 'Hungarian military occupation in progress.')
occ('OCC_PR_DE_0315', RG_PR, RG_DE, 'military_administration', '1939-03-15', '1939-03-16', EV_CS_END, '德軍進佔當天（保護國命令 3/16 才發布；之後為民政，見既有歸屬）。', 'Day of German military occupation, before the Protectorate decree.')
# ── 輸出 ──
D = os.path.join(ROOT, 'requests', 'F3'); os.makedirs(D, exist_ok=True)
for f in glob.glob(os.path.join(D, '*.json')): os.rename(f, f + '.old')
cnt = {}
for r in sorted(REQ, key=lambda r: r['cat']):
    cnt[r['cat']] = cnt.get(r['cat'], 0) + 1
    o = {'_placeholder': r['ph'], '_post': r['post']}
    if r['meta']: o['_meta'] = r['meta']
    if r['readd']: o['_readd'] = r['readd']
    o['body'] = r['body']
    json.dump(o, open(os.path.join(D, f"{r['cat']}-{cnt[r['cat']]:02d}-{r['name']}.json"), 'w'), ensure_ascii=False, indent=1)
QA['cu_area'] = round(CU.area, 4); QA['spisz'] = round(SPISZ.area, 4); QA['pl_n'] = round(PL_N.area, 4); QA['su_gap'] = round(SUg.area, 4)
json.dump(QA, open(os.path.join(ROOT, 'qa-f3.json'), 'w'), ensure_ascii=False, indent=1)
print(cnt); print(json.dumps(QA, ensure_ascii=False)[:3000])
