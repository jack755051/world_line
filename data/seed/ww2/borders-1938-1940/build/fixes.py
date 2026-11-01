#!/usr/bin/env python3
"""補 OHM 空白／重疊（Tai 2026-10-31：有合格出處才補；沒有出處的維持空白並標註）。

不原地修改（I5）：每個修正＝撤回原主權紀錄（05-2-*）＋新增（05-3-*）。新事件附出處（05-1-*）。
衍生幾何全由本批已釘版的 OHM 幾何做集合運算，不手繪：輸出 borders-fixes-1938-1940.geojson（feature id＝FIX_*）。

公式：fill = (後一版的國界 ∩ 前一版的擁有者) − 當日其他有效紀錄；新幾何＝原紀錄幾何 ∪ fill。
"""
import glob, json, os
from shapely.geometry import shape, mapping, MultiPolygon, Polygon
from shapely.ops import unary_union
from shapely import set_precision, make_valid

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
G = {f['id']: shape(f['geometry']) for f in json.load(open(os.path.join(ROOT, 'borders-ohm-1938-1940.geojson')))['features']}
REQ = {}
for p in sorted(glob.glob(os.path.join(ROOT, 'requests', '04-sovereignty-*.json'))):
    r = json.load(open(p, encoding='utf-8')); REQ[r['_geometryFrom']] = (os.path.basename(p), r)
MAN = {r['ohm_relation_id']: r for r in json.load(open(os.path.join(ROOT, 'ohm-manifest.json'), encoding='utf-8'))}

def active(day, exclude=()):
    out = []
    for rid, (_, r) in REQ.items():
        vp = r['body']['validPeriod']
        if vp['start'] <= day < (vp['end'] or '9999-12-31') and rid not in exclude: out.append(rid)
    return out

def clean(g, min_area=0.002):
    """去掉集合運算的細縫：面積太小或內縮 0.01° 後就消失的碎片。"""
    g = make_valid(g)
    parts = [p for p in getattr(g, 'geoms', [g]) if isinstance(p, Polygon) and p.area >= min_area and not p.buffer(-0.01).is_empty]
    return MultiPolygon(parts) if parts else MultiPolygon()

def mp(g):
    g = set_precision(make_valid(g), 1e-4)
    parts = [p for p in getattr(g, 'geoms', [g]) if isinstance(p, Polygon) and not p.is_empty]
    return MultiPolygon(parts)

def fill(later, owner, day, exclude=()):
    others = unary_union([G[i] for i in active(day, exclude)])
    return clean(G[later].intersection(G[owner]).difference(others))

FIX = {}
# 1) 蘇台德：德國 1938-10-10 起（佔領大致完成）＝ 2704712 ∪ (2704711 ∩ 捷克斯洛伐克 2692764 − 10-15 當日其他紀錄)
sud = fill(2704711, 2692764, '1938-10-15', exclude=(2704712,))
FIX['FIX_REICH_SUDETEN'] = (mp(G[2704712].union(sud)), sud, [2704712, 2704711, 2692764])
# 2) 但澤：德國 1939-09-01 起 ＝ 2704709 ∪ 但澤 2691478
dz = clean(G[2691478])
FIX['FIX_REICH_DANZIG'] = (mp(G[2704709].union(dz)), dz, [2704709, 2691478])
# 3) 波蘭中部 1939-10-06 → 10-26：德國佔領區軍事管理（非主權）＝ 波蘭 2741574 ∩ 德國 2704716 − 10-15 當日其他紀錄 − 但澤
pl = clean(G[2741574].intersection(G[2704716]).difference(unary_union([G[i] for i in active('1939-10-15')] + [G[2691478]])), 0.01)
FIX['FIX_MILVERW_PL'] = (mp(pl), pl, [2741574, 2704716])
# 4) 比薩拉比亞：蘇聯 1940-03-12 → 06-28 ＝ 2851878 − 羅馬尼亞 2693259
su = clean(G[2851878].difference(G[2693259]), 0.0005)
FIX['FIX_SU_NO_BESSARABIA'] = (mp(su), G[2851878].intersection(G[2693259]), [2851878, 2693259])

feats = []
for fid, (geom, delta, rels) in FIX.items():
    feats.append({'type': 'Feature', 'id': fid, 'properties': {'derivedFrom': [f"relation/{r} v{MAN[r]['ohm_version']}" for r in rels],
                  'deltaAreaDeg2': round(delta.area, 3)}, 'geometry': mapping(geom)})
    print(fid, 'parts', len(geom.geoms), 'area', round(geom.area, 3), 'delta', round(delta.area, 3))
json.dump({'type': 'FeatureCollection', 'features': feats}, open(os.path.join(ROOT, 'borders-fixes-1938-1940.geojson'), 'w'), separators=(',', ':'))

# ───────────── 請求檔（05-*）：事件 → 政權 → 撤回 → 新增 ─────────────
import copy
RQ = os.path.join(ROOT, 'requests')
def w(name, obj):
    json.dump(obj, open(os.path.join(RQ, name), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

EVENTS = [
    ('EV_SUDETEN_OCCUPATION', 'political', '1938-10-01', '1938-10-11',
     {'zh-Hant': '德軍依慕尼黑協定分區佔領蘇台德（10-01 起，10-10 大致完成）', 'en': 'German occupation of the Sudeten areas in stages under the Munich Agreement (from 1 Oct; substantially completed 10 Oct)'},
     [('SRC_FRUS_1938_I', 'Doc. 682, p. 702', 'Carr 9 月 30 日電報：協定規定德國自 10 月 1 日起逐步佔領、10 月 10 日完成。'),
      ('SRC_FRUS_1938_I', 'Doc. 700, pp. 721–722', 'Carr 10 月 7 日電報：國際委員會定出第五佔領區，新邊界與哥德斯堡備忘錄所要求的幾乎相同。'),
      ('SRC_FRUS_1938_I', 'Doc. 710, p. 734', 'Carr 11 月 7 日電報：領土移轉隨德軍佔領逐步發生，佔領於 10 月 10 日大致完成，「實際上」可視為移轉完成日。'),
      ('SRC_FRUS_1938_I', 'Doc. 710, p. 735', '同電：德國已把這些地區交給德國民政機關，在多數方面視為德國本土。')],
     {'zh-Hant': '10-01 至 10-10 分五區逐步佔領；本批沒有分區幾何，這 10 天維持空白（待查證）。11-21 德國併入法另見 EV_DE_CS_BORDER_1938（待查證）。',
      'en': 'Occupied in five zones 1–10 Oct; no zone geometry in this batch, so those ten days stay blank (pending).'}),
    ('EV_DANZIG_ANNEX', 'political', '1939-09-01', '1939-09-02',
     {'zh-Hant': '但澤自由市宣布併入德國（佛斯特宣言）', 'en': 'Free City of Danzig declared part of the Reich (Forster proclamation)'},
     [('SRC_FRUS_1939_I', 'Doc. 402, p. 402', '柏林代辦 Kirk 9 月 1 日上午 7 時電報：已宣布但澤併入德國（Anschluss），佛斯特已通知希特勒。'),
      ('SRC_FRUS_1939_I', 'Doc. 403, pp. 402–403', '駐但澤領事 Kuykendall 9 月 1 日電報：佛斯特當日宣言，但澤是德國的一部分。')],
     {'zh-Hant': 'OHM 但澤自由市止於 1939-09-01，與本事件一致。', 'en': 'OHM ends the Free City on 1939-09-01, matching this event.'}),
    ('EV_GG_CIVIL_ADMIN', 'political', '1939-10-25', '1939-10-27',
     {'zh-Hant': '德佔波蘭軍事管理結束：法蘭克就任總督（10-25），總督府民政開始（OHM 變動日 10-26）', 'en': 'End of German military administration in occupied Poland: Frank assumes office as Governor General (25 Oct; OHM change 26 Oct)'},
     [('SRC_DGFP_D8_GPO', 'Doc. 477, p. 561, nn. 2–3',  # 頁碼誤植，已由 05-4-01 更正為 p. 560（已寫入開發庫，不改原檔）
      '編者註：法蘭克於 10 月 25 日就任波蘭總督府總督；Oberbefehlshaber Ost 為德佔波蘭軍事管理首長。')],
     {'zh-Hant': '只據編者註；1939-10-08、10-12 的元首命令本文尚未取得。', 'en': 'Based on editorial footnotes only; the texts of the decrees of 8 and 12 Oct 1939 are not yet in hand.'}),
]
for i, (ph, kind, s, e, summ, cites, tn) in enumerate(EVENTS, 1):
    w(f'05-1-{i:02d}-{ph.lower()}.json', {'_placeholder': ph, '_post': '/api/v1/events', '_meta': {'verification': 'verified', 'fix': True},
      'body': {'eventKind': kind, 'occurred': {'start': s, 'end': e}, 'datePrecision': 'day', 'summary': summ,
               'citations': [{'sourceId': '{{%s}}' % src, 'locator': loc, 'evidenceNote': note} for src, loc, note in cites], 'timeNote': tn}})

w('05-1-10-regime-milverw-pl.json', {'_placeholder': 'REGIME_MILVERW_PL', '_post': '/api/v1/regimes', '_meta': {'priorPlaceholder': False, 'fix': True,
   'nameSource': 'SRC_DGFP_D8_GPO Doc. 477, p. 560, n. 3（Oberbefehlshaber Ost, the Chief of the military administration in occupied Poland）'},
   'body': {'slug': 'german-military-administration-poland', 'names': [{'nameKind': 'self', 'originalText': 'Oberbefehlshaber Ost', 'originalLang': 'de',
            'display': {'zh-Hant': '德佔波蘭軍事管理（東線總司令）', 'en': 'German military administration in occupied Poland (Oberbefehlshaber Ost)'}, 'isPrimary': True}]}})

RETRACT = {
    'SOV_R2704712': '蘇台德空白修正：拆成 03-13→10-10 與 10-10→11-21（含蘇台德）兩筆',
    'SOV_R2704709': '但澤空白修正：拆成 03-22→09-01 與 09-01→10-26（含但澤）兩筆',
    'SOV_R2691478': '但澤自由市結束事件改指向已查證的 EV_DANZIG_ANNEX（幾何、期間不變）',
    'SOV_R2851878': '比薩拉比亞重疊修正：OHM 2851878 v86 誤含比薩拉比亞，改為扣除羅馬尼亞 2693259 v71 的幾何',
}
for i, (ph, why) in enumerate(RETRACT.items(), 1):
    w(f'05-2-{i:02d}-retract-{ph.lower()}.json', {'_placeholder': 'RETRACTED_' + ph, '_post': '/api/v1/sovereignty-records/{{%s}}/retraction' % ph,
      '_meta': {'fix': True}, 'body': {'reason': why}})

def base(rel):
    return copy.deepcopy(REQ[rel][1])
def derived(rec, fid, rels, extra_note):
    rec['_geometryFrom'] = fid
    b = rec['body']
    parts = [f"relation/{r} v{MAN[r]['ohm_version']}" for r in rels]
    b['provenance']['derivedFrom'] = parts
    b['provenance']['derivation'] = extra_note['formula']
    b['provenance']['osmDerivedWayCount'] = sum(MAN[r]['osm_derived_way_count'] for r in rels)
    if b['provenance']['osmDerivedWayCount'] > 0: b['provenance']['licenseReview'] = 'osm_derived_ways'
    b['note'] = extra_note['note']
    return rec

new = []
r = base(2704712); r['_placeholder'] = 'SOV_R2704712_A'; r['body']['validPeriod']['end'] = '1938-10-10'; r['body']['endEventId'] = '{{EV_SUDETEN_OCCUPATION}}'
r['body']['note'] = {'zh-Hant': '原 SOV_R2704712 拆分（期間縮到 10-10；幾何不變）。', 'en': 'Split of SOV_R2704712 (period shortened to 10 Oct; geometry unchanged).'}
new.append(r)
r = base(2704712); r['_placeholder'] = 'SOV_FIX_REICH_SUDETEN'; r['body']['validPeriod'] = {'start': '1938-10-10', 'end': '1938-11-21'}
r['body']['startEventId'] = '{{EV_SUDETEN_OCCUPATION}}'
r['body']['geometryLocator'] = 'relation/2704712 v208 ∪ (relation/2704711 v199 ∩ relation/2692764 v97 − 1938-10-15 其他紀錄)'
new.append(derived(r, 'FIX_REICH_SUDETEN', [2704712, 2704711, 2692764], {'formula': '2704712 ∪ ((2704711 ∩ 2692764) − 1938-10-15 其他有效紀錄)',
    'note': {'zh-Hant': '蘇台德：OHM 捷克斯洛伐克 09-30 縮小、德國 11-21 才擴大，中間空白。依 FRUS 1938 I Doc. 710（佔領 10-10 大致完成、實際移轉）自 10-10 起畫入德國；邊界取 OHM 2704711（11-21 版）。10-01～10-10 分區佔領無分區幾何，維持空白。',
             'en': 'Sudetenland: drawn as German from 10 Oct (occupation substantially complete, FRUS 1938 I Doc. 710); line from OHM 2704711. 1–10 Oct stays blank (no zone geometry).'}}))
r = base(2704709); r['_placeholder'] = 'SOV_R2704709_A'; r['body']['validPeriod']['end'] = '1939-09-01'; r['body']['endEventId'] = '{{EV_DANZIG_ANNEX}}'
r['body']['note'] = {'zh-Hant': '原 SOV_R2704709 拆分（期間縮到 09-01；幾何不變）。', 'en': 'Split of SOV_R2704709 (period shortened to 1 Sep; geometry unchanged).'}
new.append(r)
r = base(2704709); r['_placeholder'] = 'SOV_FIX_REICH_DANZIG'; r['body']['validPeriod'] = {'start': '1939-09-01', 'end': '1939-10-26'}
r['body']['startEventId'] = '{{EV_DANZIG_ANNEX}}'
r['body']['geometryLocator'] = 'relation/2704709 v195 ∪ relation/2691478 v25'
new.append(derived(r, 'FIX_REICH_DANZIG', [2704709, 2691478], {'formula': '2704709 ∪ 2691478',
    'note': {'zh-Hant': '但澤：OHM 但澤止於 09-01，德國到 10-26 才含但澤。依 FRUS 1939 I Doc. 402–403 自 09-01 起畫入德國。', 'en': 'Danzig drawn as German from 1 Sep 1939 (FRUS 1939 I Docs. 402–403).'}}))
r = base(2691478); r['_placeholder'] = 'SOV_R2691478_B'; r['body']['endEventId'] = '{{EV_DANZIG_ANNEX}}'
r['body']['note'] = {'zh-Hant': '重新新增：結束事件改為已查證的 EV_DANZIG_ANNEX（幾何、期間不變）。', 'en': 'Re-added with the verified end event EV_DANZIG_ANNEX.'}
new.append(r)
r = base(2741574); r['_placeholder'] = 'SOV_FIX_MILVERW_PL'
b = r['body']; b['regimeId'] = '{{REGIME_MILVERW_PL}}'; b['layerStatus'] = 'not_sovereign'; b['validPeriod'] = {'start': '1939-10-06', 'end': '1939-10-26'}
b['startEventId'] = '{{EV_POLAND_PARTITION}}'; b['endEventId'] = '{{EV_GG_CIVIL_ADMIN}}'
b['geometryLocator'] = 'relation/2741574 v118 ∩ relation/2704716 v194 − 1939-10-15 其他紀錄 − relation/2691478 v25'
b['attribution'] = 'OCHA／HDX COD-AB Ukraine（OHM 線段標示 CC BY 4.0）; © Geodetska uprava Republike Slovenije（GURS），CC BY 4.0'
b['ohmEndRaw'] = None
new.append(derived(r, 'FIX_MILVERW_PL', [2741574, 2704716], {'formula': '(2741574 ∩ 2704716) − 1939-10-15 其他有效紀錄 − 2691478',
    'note': {'zh-Hant': '波蘭中部：OHM 波蘭止於 10-06、德國 10-26 才擴大，中間空白。依德蘇邊界暨友好條約（DGFP D/VIII Doc. 157，分界線以西由德國處理）與 DGFP D/VIII Doc. 477 編者註（東線總司令＝德佔波蘭軍事管理；法蘭克 10-25 就任總督），以非主權的軍事管理區畫出。',
             'en': 'Central Poland 6–26 Oct 1939 drawn as a non-sovereign German military administration (DGFP D/VIII Doc. 157; Doc. 477 footnotes).'}}))
r = base(2851878); r['_placeholder'] = 'SOV_FIX_SU_NO_BESSARABIA'
r['body']['geometryLocator'] = 'relation/2851878 v86 − relation/2693259 v71'
new.append(derived(r, 'FIX_SU_NO_BESSARABIA', [2851878, 2693259], {'formula': '2851878 − 2693259',
    'note': {'zh-Hant': '比薩拉比亞：OHM 2851878 v86 自 1940-03-12 誤含比薩拉比亞與北布科維納。蘇聯 1940-06-26 才以最後通牒要求割讓（FRUS 1940 I Docs. 501、502、506，見 EV_BESSARABIA），故 06-28 前扣除羅馬尼亞 2693259 的範圍。',
             'en': 'Bessarabia: OHM 2851878 v86 wrongly includes Bessarabia from 12 Mar 1940; the cession was demanded on 26 Jun 1940 (EV_BESSARABIA), so Romania 2693259 is subtracted until 28 Jun.'}}))
for i, rec in enumerate(new, 1):
    w(f'05-3-{i:02d}-{rec["_placeholder"].lower()}.json', rec)

# ───────────── 05-4：更正 EV_GG_CIVIL_ADMIN 頁碼（已寫入開發庫後發現；事件沒有撤回端點，只能新增更正事件並撤回／重加引用它的紀錄） ─────────────
# DGFP D/VIII Doc. 477 的編者註 2–3 在 p. 560（Doc. 477 自 p. 560 起，p. 561 才是正文續頁）；05-1-03 誤寫成 p. 561。
ev = json.load(open(os.path.join(RQ, '05-1-03-ev_gg_civil_admin.json'), encoding='utf-8'))
ev['_placeholder'] = 'EV_GG_CIVIL_ADMIN_R2'
ev['_meta']['corrects'] = 'EV_GG_CIVIL_ADMIN（locator 頁碼 p. 561 → p. 560）'
ev['body']['citations'][0]['locator'] = 'Doc. 477, p. 560, nn. 2–3'
w('05-4-01-ev_gg_civil_admin_r2.json', ev)
w('05-4-02-retract-sov_fix_milverw_pl.json', {'_placeholder': 'RETRACTED_SOV_FIX_MILVERW_PL', '_post': '/api/v1/sovereignty-records/{{SOV_FIX_MILVERW_PL}}/retraction',
  '_meta': {'fix': True}, 'body': {'reason': '迄事件改指向頁碼更正後的 EV_GG_CIVIL_ADMIN_R2（DGFP D/VIII Doc. 477 編者註在 p. 560）；幾何、期間不變'}})
rec = json.load(open(os.path.join(RQ, '05-3-06-sov_fix_milverw_pl.json'), encoding='utf-8'))
rec['_placeholder'] = 'SOV_FIX_MILVERW_PL_R2'; rec['body']['endEventId'] = '{{EV_GG_CIVIL_ADMIN_R2}}'
w('05-4-03-sov_fix_milverw_pl_r2.json', rec)
RETRACT['SOV_FIX_MILVERW_PL'] = 'locator 更正'
new.append(rec)

# ───────────── 修正後 QA ─────────────
FX = {f: g for f, (g, _, _) in FIX.items()}
eff = {k: (G[v[1]['_geometryFrom']], v[1]['body']['validPeriod']) for k, v in ((r[1]['_placeholder'], r) for r in REQ.values()) if k not in RETRACT}
for rec in new:
    if rec['_placeholder'] in RETRACT: continue
    gid = rec['_geometryFrom']
    eff[rec['_placeholder']] = (FX[gid] if isinstance(gid, str) else G[gid], rec['body']['validPeriod'])
for day in ['1938-10-05', '1938-10-15', '1939-09-15', '1939-10-15', '1939-10-26', '1940-04-01', '1940-06-27']:
    ids = [k for k, (g, vp) in eff.items() if vp['start'] <= day < (vp['end'] or '9999')]
    ov = []
    for i, a in enumerate(ids):
        for c in ids[i + 1:]:
            ar = eff[a][0].intersection(eff[c][0]).area
            if ar > 0.005: ov.append((a, c, round(ar, 3)))
    base0 = unary_union([G[i] for i in active('1938-01-01')])
    gap = base0.difference(unary_union([eff[k][0] for k in ids]))
    gaps = sorted([round(g.area, 3) for g in getattr(gap, 'geoms', [gap]) if g.area > 0.05], reverse=True)[:5]
    print('QA', day, len(ids), 'overlaps', ov, 'gaps', gaps)
