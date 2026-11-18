"""俄國 1908～1925 國界補完整（解除東經 60 度裁切）＋ 1908～1937 亞洲鄰國與分離政權 ＋ 伊朗 1939～1945 東部補完整。
只寫開發庫（5442／API 5052）。撤回再新增；開發庫既有紀錄（不撤回者）優先。
輸入：/workspace/ru/all_before.jsonl.gz（開發庫唯讀匯出）、/workspace/ru/geoms.pkl（OHM 固定版本全球重組，geoms.py）、OHM raw 檔。
"""
import sys, os, json, pickle, collections, datetime
sys.path.insert(0, '/workspace/ru')
from load import load
from framep import ww1proc, FRAME
import geoms as GM
from shapely.geometry import box, Polygon, MultiPolygon, mapping, shape
from shapely.ops import unary_union
from shapely.validation import make_valid
from shapely import set_precision
import shapely
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
G = pickle.load(open('/workspace/ru/geoms.pkl', 'rb'))
EX = load()
polys, mp = GM.polys, GM.mp
def clean(g, minarea=1e-6): return mp(set_precision(make_valid(g), 1e-4), minarea)

from defs import *
from defs import RG
# ---------- 俄國紀錄：換版與拆段 ----------
def ru_version(old_rid, d):
    if old_rid == 2849760 and d < '1917-11-07':   # 帝國與臨時政府（1917-11-07 以後的蘇俄沿用原版，依指示）
        if d < '1914-04-17': return 2849760
        if d < '1916-09-20': return 2851294
        return 2851158
    if old_rid == 2957450: return 2957450 if d < '1920-01-01' else 2851272
    return old_rid
VBOUND = ['1914-04-17', '1916-09-20', '1920-01-01']
RU_OLD = sorted([r for r in EX if r['slug'] in RU_SLUGS and r['lo'] < '1926-01-01'], key=lambda r: r['lo'])
IR_OLD = sorted([r for r in EX if r['slug'] in IR_SLUGS], key=lambda r: (r['slug'], r['lo']))
RETRACT = {r['id'] for r in RU_OLD + IR_OLD}
P0 = [r for r in EX if r['id'] not in RETRACT]
for r in P0:
    if not r['g'].is_valid: r['g'] = make_valid(r['g'])
P0_tree = shapely.STRtree([r['g'] for r in P0])

# 俄國框外部分：海岸線依 unclip-su-tr 簡化 0.02°；與亞洲鄰國的陸界（遮罩 0.05° 內）用 0.0005° 原幾何，鄰國扣掉後不留縫
NB_RIDS = [2694485, 2957594, 2694664, 2957589, 2889460, 2694471, 2957591, 2942671, 2849759, 2694483, 2694484, 2889768, 2851273, 2889779, 2889894,
           2694889, 2694890, 2961096, 2822863, 2885965, 2828810, 2694487, 2958014, 2961275, 2851359, 2851348, 2851346]
MASK = unary_union([G[r][0].simplify(0.01).boundary for r in NB_RIDS]).buffer(0.05)
def ru_outside(rid):
    full = G[rid][0]
    simp = mp(mp(full.simplify(0.02, preserve_topology=True), 1e-3).difference(FRAME), 1e-6)
    raw = full.difference(FRAME)
    out = unary_union([simp.difference(MASK), raw.intersection(MASK)])
    return clean(out, 1e-6)
# OHM 若干俄國版本漏了新地島（Novaya Zemlya）與新西伯利亞群島：以同政權 1916-09 版本 2851158 的島嶼補上（弗蘭格爾島不補，依各版本原樣）
ARCTIC_GAP = {2849760, 2851294, 2850854, 2957452, 2959041, 2959042, 2957450}
ARCTIC = clean(unary_union([p for p in polys(mp(G[2851158][0].simplify(0.02, preserve_topology=True), 1e-3))
                           if box(48, 70, 70, 77.5).contains(p.representative_point()) or box(130, 73, 160, 77.5).contains(p.representative_point())]))
_ww1 = {}
def W(rid):
    if rid not in _ww1: _ww1[rid] = ww1proc(rid)
    return _ww1[rid]
items = []   # 待解的紀錄
for r in RU_OLD:
    lo, hi = ('1908-10-05' if r['lo'] == '1908-10-06' else r['lo']), r['hi']
    cuts = [lo] + [b for b in VBOUND if lo < b < hi and ru_version(r['ohm_relation_id'], b) != ru_version(r['ohm_relation_id'], lo)] + [hi]
    # 同一 old 期間內換版點（只取真的換版的）
    cuts = sorted(set(cuts))
    for a, b in zip(cuts, cuts[1:]):
        rid = ru_version(r['ohm_relation_id'], a)
        if rid == r['ohm_relation_id']: inside = r['g']
        else:
            X = mp(W(r['ohm_relation_id']).difference(r['g']), 1e-4)
            inside = clean(W(rid).difference(X))
        g0 = clean(unary_union([inside, ru_outside(rid)]))
        patch = rid in ARCTIC_GAP
        if patch: g0 = clean(unary_union([g0, ARCTIC]))
        sev = r['start_event_id'] if a == r['lo'] or (a == lo) else None
        eev = r['end_event_id'] if b == hi else None
        if r['slug'] == 'russian-sfsr-1917' and a == '1922-11-15' and not sev: sev = 'EV_FER_END'
        items.append(dict(key=f"RU_{a}", slug=r['slug'], lo=a, hi=b, rid=rid, layer=r['layer_status'], prio=2, sev=sev, eev=eev, g0=g0, old=r, arctic_patch=patch,
                          basis=(['ussr1922', 'delim1924'] if r['slug'] == 'soviet-union' else []) + ['peking1860', 'ili1881', 'akhal1881', 'afg1885', 'pamir1895']))
# 伊朗 1939～1945：框外（60°E 以東）補完整；英蘇佔領區手繪線東端由 61°E 延伸到 64°E
IR_SU_EXT = Polygon([(43.5, 40.0), (64.0, 40.0), (64.0, 35.0), (59.0, 35.3), (57.0, 35.8), (55.0, 36.2), (53.4, 35.9), (52.5, 35.95), (51.0, 36.0), (49.9, 36.3), (48.5, 36.4), (47.2, 36.5), (46.2, 36.9), (45.6, 36.95), (44.0, 36.9), (43.5, 36.9)])
IR_UK_EXT = Polygon([(43.5, 24.0), (64.0, 24.0), (64.0, 31.0), (57.5, 31.8), (55.0, 32.8), (52.5, 33.8), (51.0, 34.4), (49.5, 34.6), (48.0, 35.0), (46.5, 35.2), (45.0, 35.6), (43.5, 35.6)])
IR_OUT = clean(G[2694890][0].difference(FRAME))
for r in IR_OLD:
    if r['slug'] == 'soviet-occupied-iran-1941': add = IR_OUT.intersection(IR_SU_EXT)
    elif r['slug'] == 'british-occupied-iran-1941': add = IR_OUT.intersection(IR_UK_EXT)
    elif r['lo'] >= '1941-08-25': add = IR_OUT.difference(IR_SU_EXT).difference(IR_UK_EXT)
    else: add = IR_OUT
    items.append(dict(key=f"IR_{r['slug']}_{r['lo']}", slug=r['slug'], lo=r['lo'], hi=r['hi'], rid=2694890, layer=r['layer_status'], prio=2, sev=r['start_event_id'], eev=r['end_event_id'],
                      g0=clean(unary_union([r['g'], add])), old=r, basis=['akhal1881']))
NSAKH = clean(unary_union([p for p in polys(G[2851273][0].difference(G[2889779][0])) if box(140, 48, 146, 55).contains(p.representative_point()) and p.area > 0.01]))
for (key, slug, lo, hi, rid, layer, prio, sev, eev, basis, nz, ne) in NEW:
    g0 = NSAKH if rid == 'NSAKH' else G[rid][0]
    items.append(dict(key=key, slug=slug, lo=lo, hi=hi, rid=(2851273 if rid == 'NSAKH' else rid), layer=layer, prio=prio, sev=sev, eev=eev, g0=g0, old=None, basis=basis, nz=nz, ne=ne))

# ---------- 解算：優先序（P0 既有 > 1 > 2 俄國／伊朗 > 3），高優先起訖日切段 ----------
CUT_MIN = 0.005
MERGE_TOL = 0.003
done = []
def overl(a_lo, a_hi, b_lo, b_hi): return a_lo < b_hi and b_lo < a_hi
for it in sorted(items, key=lambda x: (x['prio'], x['lo'])):
    g0 = it['g0']
    blockers = []
    for idx in P0_tree.query(g0):
        r = P0[idx]
        if overl(it['lo'], it['hi'], r['lo'], r['hi']) and r['g'].intersects(g0):
            x = r['g'].intersection(g0).area
            if x > 1e-7: blockers.append((r['lo'], r['hi'], r['g'], x, r['start_event_id'], r['end_event_id'], r['slug']))
    for d in done:
        if d['prio'] < it['prio'] and overl(it['lo'], it['hi'], d['lo'], d['hi']) and d['g'].intersects(g0):
            x = d['g'].intersection(g0).area
            if x > 1e-7: blockers.append((d['lo'], d['hi'], d['g'], x, d['sev'], d['eev'], d['slug']))
    cuts = {it['lo'], it['hi']}
    for b in blockers:
        if b[3] > CUT_MIN:
            for t in (b[0], b[1]):
                if it['lo'] < t < it['hi']: cuts.add(t)
    cuts = sorted(cuts)
    segs = []
    for a, z in zip(cuts, cuts[1:]):
        act = [b for b in blockers if overl(a, z, b[0], b[1])]
        sub = unary_union([make_valid(b[2]) for b in act]) if act else None
        g = clean(g0.difference(sub)) if sub is not None else clean(g0)
        sev = it['sev'] if a == it['lo'] else next((b[4] for b in blockers if b[0] == a and b[3] > CUT_MIN), None) or next((b[5] for b in blockers if b[1] == a and b[3] > CUT_MIN), None)
        eev = it['eev'] if z == it['hi'] else next((b[4] for b in blockers if b[0] == z and b[3] > CUT_MIN), None) or next((b[5] for b in blockers if b[1] == z and b[3] > CUT_MIN), None)
        small = sorted({b[6] for b in act if b[3] <= CUT_MIN})
        big = sorted({b[6] for b in act if b[3] > CUT_MIN})
        segs.append({**it, 'lo': a, 'hi': z, 'g': g, 'sev': sev, 'eev': eev, 'cut_big': big, 'cut_small': small, 'seg_of': it['key']})
    # 合併幾何幾乎相同的相鄰段（差異 < MERGE_TOL），合併後扣除整段期間所有阻擋者，避免無意義切段
    merged = []
    for sg in segs:
        if merged and merged[-1]['g'].symmetric_difference(sg['g']).area < MERGE_TOL:
            m = merged[-1]
            act = [b for b in blockers if overl(m['lo'], sg['hi'], b[0], b[1])]
            sub = unary_union([make_valid(b[2]) for b in act]) if act else None
            m['g'] = clean(g0.difference(sub)) if sub is not None else clean(g0)
            m['hi'] = sg['hi']; m['eev'] = sg['eev']
            m['cut_big'] = sorted(set(m['cut_big']) | set(sg['cut_big'])); m['cut_small'] = sorted(set(m['cut_small']) | set(sg['cut_small']))
        else:
            merged.append(sg)
    done.extend(merged)
    print(it['key'], it['slug'], it['lo'], it['hi'], 'segments', len(cuts) - 1, '->', len(merged), flush=True)
pickle.dump(done, open(os.path.join(HERE, 'done.pkl'), 'wb'))
print('records', len(done))
