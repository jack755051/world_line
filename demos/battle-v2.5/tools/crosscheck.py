"""多來源比對：把同一件事的各個說法並列，算出每筆資料的可信度，列出互相矛盾的地方。
用法（在 demo 根目錄）：python tools/crosscheck.py <battle-id>
讀  battles/<id>/battle.json、assignments.json、sourced.json（import_campaign.py 產生）、links.json（人工對照表）
寫  battles/<id>/confidence.json（給頁面用）、battles/<id>/CROSSCHECK.md（給人看）

來源等級（數字小＝強）：1 官方紀錄／官方戰史　2 同行審查研究　3 一般專書　4 百科（維基百科：只算線索）　5 沒有出處（記憶、手擺）
每個欄位的結論：
  verified     有 1–2 級且已查證的說法，而且同級之間沒有矛盾，展示頁用的值也和它一致
  conflict     各說法的值不一樣（含：展示頁的值和官方戰史不同）→ 列出來等人裁決，工具不自己挑
  needs-check  只有 3–4 級的說法（兩個以上互相一致時加註「多來源一致」，但不升級：維基百科條目彼此不獨立）
  estimate     沒有出處，或本來就是推估（位置、控制區、國界）
"""
import json, sys, os, collections

bid = sys.argv[1]; base = f'battles/{bid}/'
B = json.load(open(base + 'battle.json'))
A = json.load(open(base + 'assignments.json')) if os.path.exists(base + 'assignments.json') else {}
S = json.load(open(base + 'sourced.json')) if os.path.exists(base + 'sourced.json') else None
L = json.load(open(base + 'links.json')).get('links', []) if os.path.exists(base + 'links.json') else []
TIER = {'official_record': 1, 'official_history': 1, 'archive': 1, 'peer_reviewed': 2, 'monograph': 3, 'encyclopedia': 4}
TIER_ZH = {1: '官方紀錄／戰史', 2: '同行審查研究', 3: '專書', 4: '百科（線索）', 5: '無出處'}

def wiki(url, value, **kw):
    if url and str(url).startswith('http'):
        return {'value': value, 'tier': 4, 'label': '維基百科：' + url.rsplit('/', 1)[-1].replace('_', ' '), 'url': url, 'verified': False, **kw}
    return {'value': value, 'tier': 5, 'label': '無出處（示例或憑記憶）', 'verified': False, **kw}
def official(change_or_item, value):
    out = []
    for r in change_or_item.get('refs', []):
        s = S['sources'][r['src']]
        out.append({'value': value, 'tier': TIER.get(s['type'], 3), 'label': s['citation'], 'url': s.get('url'), 'quote': r.get('quote'), 'verified': bool(change_or_item.get('verified'))})
    if not out:   # 來源檔自己標待查證、沒有出處
        out.append({'value': value, 'tier': 5, 'label': '主專案考證檔（待查證，未附出處）', 'verified': False, 'note': change_or_item.get('note')})
    return out

def judge(claims, used):
    """claims: 各說法；used: 展示頁實際用的值"""
    top = [c for c in claims if c['tier'] <= 2 and c['verified'] and c['value'] is not None]
    vals = {c['value'] for c in claims if c['value'] is not None}
    if top:
        tv = {c['value'] for c in top}
        if len(tv) > 1 or used not in tv: return 'conflict'
        return 'verified'
    if not any(c['tier'] <= 4 for c in claims): return 'estimate'
    if len(vals) > 1: return 'conflict'
    return 'needs-check'

items, conflicts = {}, []
def put(key, field, claims, used, note=None):
    lv = judge(claims, used); it = items.setdefault(key, {'fields': {}})
    n_ind = len({c['label'] for c in claims if c['tier'] <= 4 and c['value'] == used})
    it['fields'][field] = {'level': lv, 'used': used, 'claims': claims, **({'agree': n_ind} if n_ind > 1 else {}), **({'note': note} if note else {})}
    if lv == 'conflict': conflicts.append((key, field, used, claims, note))

# 交戰：起訖日
site_by = {s['name']: s for s in (S or {}).get('sites', [])}
for e in B.get('engagements', []):
    k = 'eng:' + e['id']
    for f in ('from', 'to', 'date'):
        if e.get(f) is None or (f == 'date' and e.get('from')): continue
        claims = [wiki(e.get('source'), e[f])]; note = None
        for l in L:
            if l.get('engagement') == e['id'] and l.get('field') == f and l['site'] in site_by:
                chs = [c for c in site_by[l['site']]['changes'] if l.get('to') in (None, c.get('to'))]
                for c in chs[-1:]: claims += official(c, c.get('date')); note = l.get('relation')
        put(k, f, claims, e[f], note)
# 部隊：編制（有沒有這個單位、隸屬）、指揮官、位置
cmd = {a['unit_id']: a for a in A.get('assignments', []) if a.get('role') == 'commander'}
for u in B.get('units', []):
    k = 'unit:' + u['id']
    put(k, 'oob', [wiki(u.get('source'), u.get('name_orig') or u['name_zh'])], u.get('name_orig') or u['name_zh'])
    if u['id'] in cmd: c = cmd[u['id']]; put(k, 'commander', [wiki(c.get('source'), c.get('name_orig') or c['name_zh'])], c.get('name_orig') or c['name_zh'])
    mp = [p for p in B['positions'] if p['unit_id'] == u['id'] and p.get('status') == 'map']; allp = [p for p in B['positions'] if p['unit_id'] == u['id']]
    items[k]['fields']['position'] = {'level': 'estimate', 'used': None, 'claims': [], 'note': f"{len(allp)} 個關鍵日的位置中 {len(mp)} 個來自地圖數位化，其餘依文字敘述手擺"}
    for p in mp:
        d = next(x for x in B['meta']['digitized'] if 'map:' + x['file'][:-5] == p['source']); v = f"{p['lng']},{p['lat']}"
        put(k, 'position@' + p['date'], [{'value': v, 'tier': 1, 'label': d['citation'], 'url': d['url'], 'verified': True, 'note': f"圖上標註「{p['map_label']}」，圖的日期 {p['map_date']}，精度約 ±{p['precision_m'] // 1000} 公里"},
                                         {'value': f"{p['was'][0]},{p['was'][1]}", 'tier': 5, 'label': '原本手擺的位置（已被取代）', 'verified': False}], v)
# 整體性的推估
items['map:areas'] = {'fields': {'shape': {'level': 'estimate', 'used': None, 'claims': [], 'note': '控制區與前線：依敘述手描後內插'}}}
if S:
    for p in S['phases']: items[f"phase:{p['seq']}"] = {'fields': {'dates': {'level': 'verified' if p['dates_verified'] else 'needs-check', 'used': f"{p['from']}–{p['to']}", 'claims': []}, 'summary': {'level': 'verified' if p['summary_verified'] else 'needs-check', 'used': None, 'claims': []}}}
    for i, a in enumerate(S['arrows']): items[f'src-arrow:{i}'] = {'fields': {'path': {'level': 'verified' if a['verified'] else 'needs-check', 'used': None, 'claims': []}}}
    for i, a in enumerate(S['lines']): items[f'src-line:{i}'] = {'fields': {'path': {'level': 'verified' if a['verified'] else 'needs-check', 'used': None, 'claims': []}}}
    for s in S['sites']:
        for j, c in enumerate(s['changes']): items.setdefault('src-site:' + s['name'], {'fields': {}})['fields'][f'change{j}'] = {'level': 'verified' if c['verified'] else 'needs-check', 'used': c.get('date'), 'claims': []}

ORDER = ['conflict', 'estimate', 'needs-check', 'verified']   # 一筆資料的整體等級＝最弱的那個欄位（位置另計）
for k, it in items.items():
    lv = [f['level'] for n, f in it['fields'].items() if not n.startswith('position')]
    it['level'] = min(lv, key=ORDER.index) if lv else 'estimate'
cnt = collections.Counter(); kinds = collections.defaultdict(collections.Counter)
for k, it in items.items():
    for n, f in it['fields'].items(): cnt[f['level']] += 1; kinds[k.split(':')[0] + '.' + (n.split('@')[0] + ('@map' if '@' in n else '')).rstrip('0123456789')][f['level']] += 1
summary = {lv: cnt.get(lv, 0) for lv in ['verified', 'needs-check', 'estimate', 'conflict']}
json.dump({'meta': {'generated_by': 'tools/crosscheck.py', 'tiers': TIER_ZH}, 'summary': summary, 'items': items}, open(base + 'confidence.json', 'w'), ensure_ascii=False, separators=(',', ':'))

ZH = {'verified': '已查證', 'needs-check': '待查證', 'estimate': '推估', 'conflict': '說法不一'}
KZ = {'eng.from': '交戰開始日', 'eng.to': '交戰結束日', 'eng.date': '交戰日期', 'unit.oob': '部隊編制', 'unit.commander': '指揮官', 'unit.position': '部隊位置（整條軌跡）', 'unit.position@map': '部隊位置（地圖數位化的那幾天）', 'map.shape': '控制區與前線',
      'phase.dates': '階段起訖（主專案）', 'phase.summary': '階段摘要（主專案）', 'src-arrow.path': '進攻箭頭（主專案）', 'src-line.path': '戰線（主專案）', 'src-site.change': '據點易手（主專案）'}
md = [f"# 多來源比對：{B['meta'].get('title_zh', bid)}", '', '由 `tools/crosscheck.py` 產生，不要手改。', '', '## 總表', '', '| 項目 | 已查證 | 待查證 | 推估 | 說法不一 |', '|---|---|---|---|---|']
for kk in KZ:
    if kk in kinds: c = kinds[kk]; md.append(f"| {KZ[kk]} | {c.get('verified', 0)} | {c.get('needs-check', 0)} | {c.get('estimate', 0)} | {c.get('conflict', 0)} |")
md += [f"| **合計** | {summary['verified']} | {summary['needs-check']} | {summary['estimate']} | {summary['conflict']} |", '', '## 說法不一（等人裁決）', '']
if not conflicts: md.append('沒有。')
name = {('eng:' + e['id']): e['name_zh'] for e in B.get('engagements', [])}
for key, field, used, claims, note in conflicts:
    md += [f"### {name.get(key, key)}：{KZ.get(key.split(':')[0] + '.' + field, field)}", '', f"- 展示頁目前用的值：**{used}**" + (f"（對照關係：{note}）" if note else '')]
    for c in claims: md.append(f"- {TIER_ZH[c['tier']]}｜{c['label']}：**{c['value'] if c['value'] is not None else '未載'}**" + (f"　原文：「{c['quote']}」" if c.get('quote') else '') + ('' if c['verified'] or c['tier'] > 2 else '（來源檔標為待查證）'))
    md.append('')
md += ['## 對照過、結論一致的', '']
ok = [(k, n, f) for k, it in items.items() if k.startswith('eng:') for n, f in it['fields'].items() if f['level'] == 'verified']
md += [f"- {name.get(k, k)}：{KZ.get('eng.' + n)} {f['used']}（{f['claims'][-1]['label']}）" for k, n, f in ok] or ['沒有。']
md += ['', '## 對照表裡有、但主專案也沒有日期的', '']
miss = [(k, n, f) for k, it in items.items() if k.startswith('eng:') for n, f in it['fields'].items() if f.get('note') and f['level'] not in ('verified', 'conflict')]
md += [f"- {name.get(k, k)}：{KZ.get('eng.' + n)} 展示頁用 {f['used']}，主專案考證檔未載或待查證" for k, n, f in miss] or ['沒有。']
open(base + 'CROSSCHECK.md', 'w').write('\n'.join(md) + '\n')
print(bid, summary, '｜衝突', [(name.get(k, k), f) for k, f, *_ in conflicts])
