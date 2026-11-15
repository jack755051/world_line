"""把主線（feature/person-cards）的戰役資料夾 data/seed/battles/<slug>/ 轉成展示頁要讀的檔。
用法（在 demo 根目錄）：python3 -I tools/import_battle_data.py <battle-id> [資料夾]
  預設資料夾＝../../data/seed/battles/<battle-id 的 - 換成 _>/；同層的 <slug>.research.json 提供主期階段。

原則：只搬運、不補、不推定。這支程式不產生任何史實——
  · 來源檔標 gap 的不輸出；partial 的照樣帶「待查證」。
  · 態勢圖上的標註（digitized/*.json 的 features）若來源檔沒有填 unitKey，就當成獨立的「圖上標註」畫出來，
    不自動對到名冊（同號的步兵師／裝甲師、英軍／法軍無法只靠數字分辨）。來源檔之後補上 unitKey，重跑就會併到名冊單位。
  · 同一張圖系列裡「陣營＋層級＋標號」相同的標註視為同一個標註的前後位置（只用來畫移動，不代表已對到單位）。
  · 名冊單位的文字位置（R3）多半只到「某地一帶」：該單位當天沒有圖上位置時，用地名座標畫上地圖（±5 公里）；其餘放在單位卡片裡。
  · 地名座標取自態勢圖控制點（OSM）與 battles/<id>/gazetteer.json（OSM 物件編號查得）；座標是地理參照，不是史料。
  · 未通過配準門檻（threshold.passes=false）的圖不使用。

輸入：r1-units、r3-unit-positions、r4-fronts、r4-leadin-fronts、r5-engagements、r6-site-control、r7-commanders、
      phase-leadin、sources、digitized/*.json、../<slug>.research.json；battles/<id>/view.json（鏡頭等畫面設定）。
輸出：battles/<id>/battle.json、assignments.json、sourced.json、confidence.json、IMPORT-REPORT.md
"""
import json, sys, os, re, glob, datetime, collections

bid = sys.argv[1]
slug = bid.replace('-', '_')
SRC = sys.argv[2] if len(sys.argv) > 2 else f'../../data/seed/battles/{slug}/'
OUT = f'battles/{bid}/'
REL = os.path.normpath(SRC).replace(os.path.normpath('../..') + os.sep, '') + '/'
def L(n, dflt=None):
    p = SRC + n
    if not os.path.exists(p):
        if dflt is not None: return dflt
        raise SystemExit('缺檔：' + p)
    return json.load(open(p))
def day(s): return datetime.date.fromisoformat(s)
def plus(s, n): return (day(s) + datetime.timedelta(days=n)).isoformat()

VIEW = json.load(open(OUT + 'view.json'))
SOURCES = L('sources.json')
R1 = L('r1-units.json')['units']
R3 = L('r3-unit-positions.json', {'positions': []})['positions']
R4 = L('r4-fronts.json', {'fronts': []})
R4L = L('r4-leadin-fronts.json', {'fronts': []})['fronts']
R5 = L('r5-engagements.json', {'engagements': []})['engagements']
R6 = L('r6-site-control.json', {'sites': []})['sites']
R7 = L('r7-commanders.json', {'commanders': []})['commanders']
LEAD = L('phase-leadin.json', {'phases': []})['phases']
RES = json.load(open(os.path.normpath(SRC) + '.research.json'))
MAPS = [json.load(open(f)) for f in sorted(glob.glob(SRC + 'digitized/*.json')) if not f.endswith('.readings.json')]

# ---------- 出處 ----------
src_out = {}
def sid(key, url=None, label=None):
    if key not in src_out:
        s = SOURCES.get(key) or (RES.get('sources') or {}).get(key) or {}
        src_out[key] = {'type': 'official' if s.get('grade') == 'A' else 'study', 'grade': s.get('grade'), 'citation': label or s.get('title') or key, 'url': s.get('url') or url}
    return key
def refs(cits):
    return [{'src': sid(c['sourceKey'], c.get('url')), 'quote': c.get('quote'), 'loc': c.get('locator'), 'url': c.get('url'), 'grade': c.get('grade'),
             'checked': (c.get('quoteCheck') or {}).get('status') == 'verbatim'} for c in (cits or [])]
def n_src(cits): return len({c['sourceKey'] for c in (cits or [])})
def claims(cits, value):
    return [{'value': value, 'tier': 1 if c.get('grade') == 'A' else 2, 'label': (SOURCES.get(c['sourceKey']) or {}).get('title', c['sourceKey']) + '，' + (c.get('locator') or ''),
             'url': c.get('url'), 'verified': True, 'quote': c.get('quote')} for c in (cits or [])]

# ---------- 地名座標 ----------
GAZ = {}
for m in MAPS:
    for n, c in m['control_points'].items():
        if c.get('osm'): GAZ[f"{c['osm']['type']}/{c['osm']['id']}"] = c['lonlat']
for k, v in json.load(open(OUT + 'gazetteer.json'))['items'].items() if os.path.exists(OUT + 'gazetteer.json') else []:
    GAZ.setdefault(k, v['lonlat'])
no_coord = collections.Counter()
def lonlat(place, why):
    o = (place or {}).get('osm')
    if not o: return None
    ll = GAZ.get(f"{o['type']}/{o['id']}")
    if not ll: no_coord[f"{place.get('nameOsm')} ({o['type']}/{o['id']})"] += 1
    return ll

# ---------- 階段、關鍵日 ----------
phases = []
for p in LEAD:
    phases.append({'seq': len(phases) + 1, 'key': p['key'], 'name_zh': p['nameZh'], 'from': p['period']['start'], 'to': p['period']['end'], 'dates_verified': True,
                   'date_refs': refs(p['citations']), 'summary_zh': p.get('summaryZh'), 'summary_verified': True, 'summary_refs': refs(p['citations']), 'part': 'leadin'})
for p in RES['phases']:   # 研究檔的 end 是「不含」
    phases.append({'seq': len(phases) + 1, 'key': f"main-{p['seq']}", 'name_zh': p['nameZh'], 'from': p['start'], 'to': plus(p['end'], -1) if p['end'] > p['start'] else p['start'],
                   'dates_verified': True, 'date_refs': refs(p['citations']), 'summary_zh': None, 'summary_verified': False, 'summary_refs': [], 'maps': p.get('maps'), 'part': 'main'})
D0, D1 = phases[0]['from'], max(p['to'] for p in phases)
usable = [m for m in MAPS if m['threshold']['passes']]
skipped_maps = [m['mapKey'] for m in MAPS if not m['threshold']['passes']]
by_date = collections.defaultdict(list)
for m in usable: by_date[m['mapDate']].append(m)
# 同一天有兩張圖：部隊標註取標註較多的那張（另一張的前線仍會用）
mark_map = {d: max(ms, key=lambda m: len(m['features'])) for d, ms in by_date.items()}
TEXT_REL = {'holding', 'attacking', 'withdrew_to', 'at', 'within_perimeter', 'rearguard', 'evacuating', 'fighting', 'surrounded', 'reserve', 'surrendered', 'capturing', 'supporting', 'reinforcing'}
TEXT_ST = {'attacking': 'attack', 'capturing': 'attack', 'holding': 'defend', 'rearguard': 'defend', 'within_perimeter': 'defend', 'fighting': 'defend', 'withdrew_to': 'retreat', 'evacuating': 'evacuating', 'surrounded': 'encircled', 'surrendered': 'surrendered'}
# 有文字位置的日期也當關鍵日（否則 5/31、6/2 這些沒有態勢圖的日子，出處明明寫到部隊在哪，卻畫不出來）
kdates = sorted({p['from'] for p in phases} | set(mark_map) | {D1} | {p['date'] for p in R3 if p.get('relation') in TEXT_REL and D0 <= (p.get('date') or '') <= D1}
                | {f['date'] for f in R4L if D0 <= f['date'] <= D1})   # 文字防線生效的日期也當關鍵日（示意領地要在那一天換線）
def cam(d):
    c = VIEW['camera_from'][0][1]
    for dd, name in VIEW['camera_from']:
        if d >= dd: c = name
    return c
def first_sentence(s): return (re.split(r'(?<=。)', s or '')[0]) if s else ''
keyframes = []
for d in kdates:
    ph = next((p for p in phases if p['from'] == d), None); cur = [p for p in phases if p['from'] <= d <= p['to']]
    m = mark_map.get(d); c = cam(d)
    title = ph['name_zh'] if ph else (f"{int(d[5:7])}/{int(d[8:])} 傍晚態勢" if m else (cur[-1]['name_zh'] if cur else ''))
    line = first_sentence(ph.get('summary_zh')) if ph and ph.get('summary_zh') else (f"部隊位置讀自 {len(m['features'])} 個圖上標註（{m['source']['citation'].split(', Situation Map ')[-1]}）。" if m else '')
    keyframes.append({'date': d, 'camera': c, 'event_zh': title, 'event_en': '', 'major': bool(ph), 'focus': ['places', 'engagements'], 'focus_units': [], 'places': VIEW['places'][c], 'event_line': line})

# ---------- 單位：名冊（R1）＋圖上標註 ----------
ECH = {'army_group': 'front', 'army': 'army', 'corps': 'corps', 'division': 'division', 'naval_command': 'corps', 'air_command': 'corps', 'other': 'corps'}
def branch(name, ech):
    n = name.lower()
    if ech == 'naval_command': return 'naval'
    if ech == 'air_command' or 'flieger' in n or 'luftflotte' in n: return 'air'
    if 'panzer' in n: return 'armor'
    if '(mot' in n or 'motoris' in n or 'mécanique' in n or ' mot' in n: return 'motorized'
    return 'infantry'
def label_of(u):
    m = re.search(r'-(\d+|[ivxl]+)-', u['unitKey'] + '-')
    return (m.group(1).upper() if m else u['nameOrig'].split(' (')[0])[:10]
cmd_by = collections.defaultdict(list)
for c in R7: cmd_by[c['unitKey']].append(c)
txt_by = collections.defaultdict(list)
for p in R3: txt_by[p['unitKey']].append(p)
units, conf, gaps_units = [], {}, []
roster_ids = set()

def level_of(rec, fallback):
    """可信程度取主線 crosscheck 寫回的 confidence.level（docs/source-rules.md）；沒有才退回舊的 status 對照。"""
    lv = (rec.get('confidence') or {}).get('level')
    return lv if lv in ('verified', 'needs-check', 'estimate') else fallback
def why_of(rec):
    c = rec.get('confidence') or {}
    return (c.get('why') or '') + ('（只有對手方的說法）' if c.get('opposingOnly') and '對手方' not in (c.get('why') or '') else '')

for u in R1:
    if u['status'] == 'gap': gaps_units.append(u['unitKey']); continue
    roster_ids.add(u['unitKey'])
for u in R1:
    if u['unitKey'] not in roster_ids: continue
    ech = u['echelon']
    units.append({'id': u['unitKey'], 'side': u['side'], 'name_zh': u['nameZh'], 'name_orig': u['nameOrig'], 'echelon': ECH.get(ech, 'corps'), 'echelon_src': ech, 'branch': branch(u['nameOrig'], ech),
                  'parent_id': u['parentKey'] if u['parentKey'] in roster_ids else None, 'label': label_of(u), 'display': 'both', 'domain': 'sea' if ech == 'naval_command' else 'air' if ech == 'air_command' else 'ground',
                  'roster': True, 'status': u['status'], 'period': u.get('period'), 'period_note': u.get('periodNote'), 'note': u.get('note'), 'refs': refs(u['citations']),
                  'text_positions': [{'date': p['date'], 'place': p['placeAsInSource'], 'relation': p.get('relation'), 'note': p.get('attributionNote'), 'refs': refs(p['citations'])}
                                     for p in sorted(txt_by[u['unitKey']], key=lambda p: p['date'])]})
    lv = level_of(u, 'verified' if u['status'] == 'sourced' else 'needs-check')
    f = {'oob': {'level': lv, 'used': u['nameOrig'], 'claims': claims(u['citations'], u['nameOrig']), 'note': f"{n_src(u['citations'])} 個來源" + ('；' + why_of(u) if why_of(u) else '')}}
    if cmd_by[u['unitKey']]:
        c = cmd_by[u['unitKey']][0]
        f['commander'] = {'level': level_of(c, 'verified' if c['citations'] else 'needs-check'), 'used': c['name'], 'claims': claims(c['citations'], c['name'])}
    conf['unit:' + u['unitKey']] = {'fields': f, 'level': lv}

SIDE = {'german': 'axis', 'allied': 'allied'}
def slugify(s): return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-') or 'x'
SUB_DIV = re.compile(r'\b(RI|RA|AR|RAD|Regt|Rgt|Bde|Bn|GRD|GRCA|DBLE|Zouaves|Ter|Regional|Recce|Gds B)', re.I)
sub_div = collections.Counter()
marks, positions, digitized, linked = {}, [], [], 0
for d in sorted(mark_map):
    m = mark_map[d]
    digitized.append({'file': m['mapKey'] + '.json', 'citation': m['source']['citation'], 'short_zh': 'Ellis 態勢圖 ' + m['source']['citation'].split("Situation Map ")[-1], 'url': m['source']['url'],
                      'map_date': d, 'loo_p95_km': m['threshold']['loo_p95_km'], 'precision_m': m['precision_m'], 'control_points': m['georef']['control_points']})
    seen = collections.Counter((f.get('sideGuess'), f.get('echelon'), f['label']) for f in m['features'])
    idx = collections.Counter()
    for f in m['features']:
        if not f.get('usable', True) or f.get('sideGuess') not in SIDE: continue
        # 憲法 Decision 5：部隊最細只到師。圖上的旅、團、營級標註（來源檔層級是 other，標號看得出是旅／團）不上圖。
        if f.get('unitKey') not in roster_ids and f.get('echelon') not in ('army_group', 'army', 'corps', 'division') and SUB_DIV.search(f['label']): sub_div[f['label']] += 1; continue
        if f.get('unitKey') in roster_ids: uid = f['unitKey']; linked += 1
        else:
            key = (f['sideGuess'], f.get('echelon'), f['label'])
            uid = f"mk-{SIDE[f['sideGuess']][:2]}-{(f.get('echelon') or 'x')[:3]}-{slugify(f['label'])}"
            if seen[key] > 1: idx[key] += 1; uid += f"-{d[5:].replace('-', '')}-{idx[key]}"   # 同圖同號兩個以上：無法分辨誰是誰，只在當天出現
            if uid not in marks:
                lab = f['label']
                marks[uid] = {'id': uid, 'side': SIDE[f['sideGuess']], 'name_zh': f'圖上標註「{lab}」', 'name_orig': f"{lab}（{'德軍' if f['sideGuess'] == 'german' else '盟軍'}，尚未對到名冊）", 'echelon': ECH.get(f.get('echelon'), 'corps'),
                              'echelon_src': f.get('echelon'), 'branch': 'motorized' if re.search(r'mot|dlm', lab, re.I) else 'infantry', 'parent_id': None, 'label': lab[:12], 'display': 'detail', 'domain': 'ground',   # detail＝拉遠時不顯示，拉近到它的層級才出現（沒有上級可以併，否則拉遠會擠成一團）
                              'map_mark': True, 'note': '這是態勢圖上的一個標註，陣營依圖例的符號樣式判讀，還沒有對到名冊裡的單位。', 'mark_notes': []}
            if f.get('note') or f.get('sideNote'): marks[uid]['mark_notes'].append({'date': d, 'note': f.get('note'), 'side_note': f.get('sideNote')})
        positions.append({'unit_id': uid, 'date': d, 'lng': f['lonlat'][0], 'lat': f['lonlat'][1], 'state': 'move', 'status': 'map', 'precision_m': m['precision_m'], 'place_zh': None,
                          'source': 'map:' + m['mapKey'], 'map_label': f['label'], 'map_date': d})
# 文字位置（R3）上圖（Tai 2026-11-15）：名冊單位在某個關鍵日沒有圖上位置、但出處文字寫到它「在某地」時，用那個地名的座標畫出來。
# 只收表示部隊本身所在的關係；開會、指派防區、出發、指揮這類不代表部隊位置的不收。座標是地名中心，精度標 ±5 公里。
have = {(p['unit_id'], p['date']) for p in positions}
n_text = 0
for p in R3:
    if p.get('unitKey') not in roster_ids or p.get('date') not in kdates or p.get('relation') not in TEXT_REL or (p['unitKey'], p['date']) in have: continue
    ll = lonlat(p.get('place'), 'r3')
    if not ll: continue
    have.add((p['unitKey'], p['date'])); n_text += 1
    positions.append({'unit_id': p['unitKey'], 'date': p['date'], 'lng': ll[0], 'lat': ll[1], 'state': TEXT_ST.get(p['relation'], 'move'), 'status': 'text', 'precision_m': 5000,
                      'place_zh': p.get('placeAsInSource'), 'source': 'text:' + (p['citations'][0]['sourceKey'] if p.get('citations') else ''), 'relation': p['relation']})
for uid, u in marks.items():
    units.append(u)
    conf['unit:' + uid] = {'level': 'estimate', 'fields': {'oob': {'level': 'needs-check', 'used': None, 'claims': [], 'note': '圖上標註尚未對到名冊單位'},
                                                             'position': {'level': 'estimate', 'used': None, 'claims': [], 'note': '位置讀自官方戰史態勢圖（符號中心），誤差見各日的精度'}}}

# ---------- 交戰（R5） ----------
engs, eng_skip = [], []
for e in R5:
    if e['status'] == 'gap': eng_skip.append((e['key'], '來源檔標為查無')); continue
    ll = lonlat(e.get('place'), 'r5')
    if not ll: eng_skip.append((e['key'], '沒有可定位的地點')); continue
    us = [{'unit_id': k, 'role': 'attacker'} for k in e['attackers'] if k in roster_ids] + [{'unit_id': k, 'role': 'defender'} for k in e['defenders'] if k in roster_ids]
    s, t = max(e['period']['start'], D0), min(e['period']['end'], D1)
    kd = next((k for k in kdates if k >= s), kdates[-1])
    engs.append({'id': 'e-' + e['key'], 'date': kd, 'from': s, 'to': t, 'name_zh': e['nameZh'], 'name_orig': e.get('nameOrig'), 'lng': ll[0], 'lat': ll[1], 'units': us, 'interaction_tag': None,
                 'interaction_zh': (e.get('place') or {}).get('asInSource') or '', 'outcome': None, 'summary_zh': e.get('outcomeNote') or '', 'note': e.get('note'), 'status': e['status'], 'refs': refs(e['citations'])})
    lv = level_of(e, 'verified' if e['status'] == 'sourced' else 'needs-check')
    conf['eng:e-' + e['key']] = {'level': lv, 'fields': {'from': {'level': lv, 'used': s, 'claims': claims(e['citations'][:1], s)}, 'to': {'level': lv, 'used': t, 'claims': claims(e['citations'][:1], t)}}}

# ---------- 史料圖層：前線（R4）、據點（R6） ----------
lines = []
fdates = sorted({f['date'] for f in R4['fronts']})
def ph_of(d): return next((p['seq'] for p in phases if p['from'] <= d <= p['to']), phases[-1]['seq'])
for f in R4['fronts']:
    i = fdates.index(f['date']); to = plus(fdates[i + 1], -1) if i + 1 < len(fdates) and day(fdates[i + 1]) - day(f['date']) <= datetime.timedelta(days=1) else f['date']
    lines.append({'phase': ph_of(f['date']), 'from': f['date'], 'to': to, 'name': f.get('label'), 'side': f.get('side'), 'kind': f.get('lineKind'), 'vertices': [v.get('nearPlace') for v in f['vertices'] if v.get('nearPlace')],
                  'path': [v['lonlat'] for v in f['vertices']], 'precision': f.get('precisionNote'), 'precision_m': f.get('precision_m'), 'verified': False, 'level': 'estimate', 'basis': 'map',
                  'refs': [{'src': sid('map:' + f['mapRef']['mapKey'], f['mapRef'].get('url'), f['mapRef']['citation']), 'quote': None, 'loc': None, 'url': f['mapRef'].get('url'), 'grade': f['mapRef'].get('grade')}],
                  'note': f.get('readNote')})
ldates = sorted({f['date'] for f in R4L})
for f in R4L:
    pts = [(v['placeAsInSource'], lonlat(v.get('place'), 'r4-leadin')) for v in f['vertices']]
    path = [ll for _, ll in pts if ll]
    if len(path) < 2: continue
    i = ldates.index(f['date']); to = plus(ldates[i + 1], -1) if i + 1 < len(ldates) else plus(RES['phases'][0]['start'], -1)
    lines.append({'phase': ph_of(f['date']), 'from': f['date'], 'to': max(to, f['date']), 'name': f.get('label'), 'side': f.get('side'), 'kind': 'front', 'vertices': [n for n, ll in pts if ll], 'path': path,
                  'precision': f.get('precisionNote'), 'verified': False, 'level': 'estimate', 'basis': 'text', 'refs': refs(f['citations']), 'note': f.get('lineNote'),
                  **({'missing_vertices': [n for n, ll in pts if not ll]} if any(not ll for _, ll in pts) else {})})
sites = {}
for s in R6:
    ll = lonlat(s.get('place'), 'r6')
    if not ll: continue
    st = sites.setdefault(s['placeAsInSource'], {'name': s['placeAsInSource'], 'lonlat': ll, 'coord_ref': None, 'changes': []})
    st['changes'].append({'phase': ph_of(s['date']) if s.get('date') else None, 'date': s.get('date'), 'to': s.get('controllerAfter'), 'event': s.get('event'), 'verified': level_of(s, 'verified' if s['status'] == 'sourced' else 'needs-check') == 'verified' and bool(s.get('controllerAfter')),
                          'refs': refs(s['citations']), **({'note': s['timeNote']} if s.get('timeNote') else {})})
for st in sites.values(): st['changes'].sort(key=lambda c: c['date'] or '')
for i, l in enumerate(lines): conf[f'src-line:{i}'] = {'level': l['level'], 'fields': {'path': {'level': l['level'], 'used': None, 'claims': []}}}
for p in phases: conf[f"phase:{p['seq']}"] = {'level': 'verified', 'fields': {'dates': {'level': 'verified', 'used': f"{p['from']}–{p['to']}", 'claims': []}}}

# ---------- 指揮官（R7） ----------
asg = []
for c in R7:
    if c['unitKey'] not in roster_ids: continue
    t = c.get('tenure') or {}
    asg.append({'unit_id': c['unitKey'], 'role': 'commander', 'name_zh': c['nameZh'], 'name_orig': c['name'], 'title_zh': '指揮官', 'from': t.get('start'), 'to': t.get('end'), 'source': (c['citations'] or [{}])[0].get('url'),
                'confidence': 'high' if c['citations'] else 'low', 'status_zh': '官方戰史' if c['citations'] else '需查證', 'person_key': c.get('personKey'), 'bio_id': c.get('bioId'), 'note': c.get('note'), 'refs': refs(c['citations'])})

# ---------- 寫檔 ----------
single = sum(1 for u in R1 if u['status'] != 'gap' and n_src(u['citations']) <= 1)
meta = {'campaign': bid, 'title_zh': VIEW.get('title_zh', bid), 'is_example': False, 'banner': '出處幾乎只有一部官方戰史；部隊位置讀自態勢圖，是推估', 'schema_version': 2, 'generated_by': 'tools/import_battle_data.py', 'from': REL,
        'note': f"資料全部來自主線的考證檔（{REL}），展示頁只搬運、不補。名冊 {len(roster_ids)} 個單位中 {single} 個只有一個來源。地圖上的部隊符號是態勢圖上的標註，還沒有對到名冊。不含傷亡數字。",
        'date_start': D0, 'date_end': D1, 'cameras': VIEW['cameras'], 'cameras_mobile': VIEW['cameras_mobile'], 'digitized': digitized}
# ---------- 示意圖形：進攻箭頭（憲法 Decision 5，2026-11-15）----------
# 來源：主專案考證檔 data/campaigns/<slug>.json 的 attack_arrows。只收來源檔自己標 verified、而且帶有官方戰史／學術專書逐字引文的；
# 方向或番號是推定的（verified=false）不畫，列在匯入報告。箭頭只表示出處敘述的方向，不是實際路線。
schem, schem_skip = [], []
CAMP = os.path.normpath(os.path.join(SRC, '../../../campaigns', slug + '.json'))
GRADE_OF = {'official_history': 'A', 'official_record': 'A', 'academic': 'B', 'monograph': 'B'}
def camp_src(c):
    host = (c.get('url') or '').rsplit('/', 1)[0]
    key = next((k for k, v in SOURCES.items() if host and (v.get('url') or '').startswith(host)), None)
    if key: return sid(key, c.get('url'))
    key = 'campaign:' + slugify(c.get('citation') or c.get('url') or 'x')[:40]
    src_out.setdefault(key, {'type': 'official' if GRADE_OF.get(c.get('type')) == 'A' else 'study', 'grade': GRADE_OF.get(c.get('type')), 'citation': c.get('citation') or key, 'url': c.get('url')})
    return key
if os.path.exists(CAMP):
    for p in json.load(open(CAMP)).get('phases', []):
        for a in p.get('attack_arrows', []):
            cits = [c for c in a.get('sources', []) if GRADE_OF.get(c.get('type')) and c.get('quote')]
            if not a.get('verified') or not cits:
                schem_skip.append(f"{a['from']}→{a['to']}（{a.get('note') or '來源檔標未核實'}）"); continue
            schem.append({'phase': ph_of(p['start_date']), 'from': a['from'], 'to': a['to'], 'path': [a['from_lonlat'], a['to_lonlat']], 'unit': a.get('unit'), 'side': a.get('side'),
                          'verified': True, 'schematic': True, 'date': p['start_date'], **({'note': a['note']} if a.get('note') else {}),
                          'refs': [{'src': camp_src(c), 'quote': c['quote'], 'loc': None, 'url': c.get('url'), 'grade': GRADE_OF[c['type']], 'checked': None} for c in cits]})

# 主線戰役資料夾裡的 schematic.json：示意箭頭與示意航線，每個都帶引文（引文由 tools/battles/verify_quotes.py 逐字核對）
for sh in L('schematic.json', {'shapes': []})['shapes']:
    cits = [c for c in sh.get('citations', []) if c.get('grade') in ('A', 'B') and c.get('quote') and (c.get('quoteCheck') or {}).get('status', 'verbatim') != 'failed']
    if not cits: schem_skip.append(f"{sh['key']}（沒有通過核對的 A／B 引文）"); continue
    schem.append({'phase': ph_of(sh['from']), 'from': sh['path'][0]['place'], 'to': sh['path'][-1]['place'], 'path': [q['lonlat'] for q in sh['path']], 'unit': sh.get('labelZh'), 'side': sh.get('side'),
                  'verified': True, 'schematic': True, 'kind': sh['kind'], 'date': sh['from'], 'date_to': sh['to'], 'note': sh.get('waypointNote'), 'refs': refs(cits)})

battle = {'meta': meta, 'keyframes': keyframes, 'units': units, 'positions': positions, 'fronts': [], 'arrows': [], 'engagements': engs}
W = lambda n, o: json.dump(o, open(OUT + n, 'w'), ensure_ascii=False, indent=1)
W('battle.json', battle)
W('assignments.json', {'meta': {'is_example': False, 'note': f'指揮官取自 {REL}r7-commanders.json；任期只填出處有載的日期。'}, 'assignments': asg, 'engagements': {}})
W('sourced.json', {'meta': {'from': REL, 'schema': 'battle-data', 'campaign_key': slug, 'name_zh': VIEW.get('title_zh'), 'date_start': D0, 'date_end': D1, 'generated_by': 'tools/import_battle_data.py',
                            'note': '由主線考證檔轉出，只搬運不補。前段（5/10–5/25）的戰線是文字地名連線；主期的戰線讀自態勢圖，屬推估。'},
                   'phases': phases, 'arrows': schem, 'lines': lines, 'sites': list(sites.values()), 'sources': src_out})
conf['map:areas'] = {'level': 'estimate', 'fields': {}}   # 控制區是推導圖形（由部隊位置算出），一律推估
summ = collections.Counter(v['level'] for v in conf.values())
W('confidence.json', {'meta': {'generated_by': 'tools/import_battle_data.py', 'tiers': {'1': '官方紀錄／戰史', '2': '同行審查研究', '3': '專書', '4': '百科（線索）', '5': '無出處'},
                               'note': '等級取自主線依 docs/source-rules.md 判定的可信程度：已查證＝一筆 A 或兩個獨立家族的 B；只有對手方說法或不到門檻＝待查證；讀圖＝推估。'},
                      'summary': {k: summ.get(k, 0) for k in ['verified', 'needs-check', 'estimate', 'conflict']}, 'items': conf})
nmark = len(marks); npos_mark = sum(1 for p in positions if p['unit_id'] in marks)
rep = f"""# 匯入報告：{bid}

由 `tools/import_battle_data.py` 產生，來源 `{REL}`。這份報告列出「來源檔有、但展示頁用不上或只能降級使用」的部分，是給主線補資料用的。

| 項目 | 來源檔 | 匯入 | 說明 |
|---|---|---|---|
| 名冊單位（R1） | {len(R1)} | {len(roster_ids)} | 未匯入 {len(gaps_units)} 個標為查無：{'、'.join(gaps_units) or '—'}；只有一個來源的 {single} 個 |
| 指揮官（R7） | {len(R7)} | {len(asg)} | |
| 文字位置（R3） | {len(R3)} | {sum(len(u.get('text_positions', [])) for u in units)} | 其中 {n_text} 筆畫上地圖（該單位當天沒有圖上位置、且關係表示部隊所在）；其餘只顯示在單位卡片 |
| 態勢圖 | {len(MAPS)} | {len(mark_map)} | 未通過配準門檻不用：{'、'.join(skipped_maps) or '—'}；同日多張只取一張的標註 |
| 圖上標註 | {sum(len(m['features']) for m in MAPS)} | {len(positions)} | **已對到名冊 {linked} 個**；其餘 {npos_mark} 個位置歸成 {nmark} 個「圖上標註」 |
| 前線（R4 主期，讀圖） | {len(R4['fronts'])} | {sum(1 for l in lines if l['basis'] == 'map')} | 推估，虛線 |
| 前線（R4 前段，文字） | {len(R4L)} | {sum(1 for l in lines if l['basis'] == 'text')} | |
| 交戰（R5） | {len(R5)} | {len(engs)} | 未匯入：{'；'.join(f'{k}（{w}）' for k, w in eng_skip) or '—'} |
| 據點（R6） | {len(R6)} | {sum(len(s['changes']) for s in sites.values())} 筆／{len(sites)} 處 | 控制方未載的 {sum(1 for s in R6 if not s.get('controllerAfter'))} 筆照樣帶入，標待查證 |

## 沒有上圖的圖上標註

師以下（旅、團、營）不上圖（憲法 Decision 5）：{sum(sub_div.values())} 個位置、{len(sub_div)} 種標號：{'、'.join(sorted(sub_div)) or '—'}。

## 示意圖形

示意箭頭與航線 {len(schem)} 個（取自 `data/campaigns/{slug}.json` 的進攻箭頭與主線資料夾的 `schematic.json`，每個都掛在官方戰史引文上；只表示方向或走向，不是實際路線）。
沒有畫的 {len(schem_skip)} 支：{'；'.join(schem_skip) or '—'}。

## 還缺什麼

1. **圖上標註沒有對到名冊**：{npos_mark} 個位置的 `unitKey` 都是空的。補上之後重跑，這些位置就會直接掛到名冊單位上，卡片才看得到指揮官與出處。
2. **沒有控制區**：來源檔沒有可以圍成面的前線（主期各日是分段的線，5/30 之後沒有線），所以地圖不塗陣營底色。
3. **疆界（R8）只有紀錄編號**，沒有幾何；展示頁離線讀不到，底圖仍是現代國界。
4. **查不到座標的地名**：{'、'.join(f'{k}×{v}' for k, v in no_coord.items()) or '無'}。
5. **主期六個階段沒有摘要文字**（研究檔只有名稱與起訖）。
"""
open(OUT + 'IMPORT-REPORT.md', 'w').write(rep)
print(f"{bid}: 關鍵日 {len(keyframes)}｜名冊 {len(roster_ids)}（單一來源 {single}）｜圖上標註 {nmark}（位置 {npos_mark}，已對名冊 {linked}）｜交戰 {len(engs)}/{len(R5)}｜前線 {len(lines)}｜據點 {len(sites)}｜指揮官 {len(asg)}｜等級 {dict(summ)}｜缺座標 {dict(no_coord)}")
