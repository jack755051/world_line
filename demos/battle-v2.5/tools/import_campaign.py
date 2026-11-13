"""把主專案考證過的戰役檔（data/campaigns/<key>.json，wl-campaign/0.1-proposal）轉成展示頁用的「史料骨架」。
用法（在 demo 根目錄）：python tools/import_campaign.py <battle-id> [campaign.json 路徑]
  預設路徑＝../../data/campaigns/<battle-id 的 - 換成 _>.json
輸出 battles/<id>/sourced.json：
  sources  出處表（依引文去重）：{id: {type, citation, url}}
  phases   階段：起訖日、摘要、是否已查證、出處（含原文摘句）
  arrows   進攻箭頭；lines 戰線（頂點是出處明載的地名，直線相連，屬近似）；sites 據點與易手日
原則：只搬運，不補、不推定。來源檔標 verified:false 的照樣帶 verified:false。
"""
import json, sys, os, re

bid = sys.argv[1]
src = sys.argv[2] if len(sys.argv) > 2 else f'../../data/campaigns/{bid.replace("-", "_")}.json'
C = json.load(open(src))
sources, order = {}, []
def sid(s):
    key = s.get('citation') or s.get('url')
    if key not in sources:
        sources[key] = {'id': f's{len(sources) + 1}', 'type': s.get('type'), 'citation': s.get('citation'), 'url': s.get('url')}
        if s.get('alt_url'): sources[key]['alt_url'] = s['alt_url']
    return sources[key]['id']
def refs(lst): return [{'src': sid(s), **({'quote': s['quote']} if s.get('quote') else {})} for s in (lst or [])]
def incl(end_exclusive):   # 來源檔的 end_date 是「不含」；展示頁用「含」
    import datetime
    return (datetime.date.fromisoformat(end_exclusive) - datetime.timedelta(days=1)).isoformat()

out = {'meta': {'from': os.path.relpath(src, '../..') if src.startswith('../..') else src, 'schema': C.get('schema'), 'campaign_key': C.get('campaign_key'),
                'name_zh': C.get('name_zh'), 'date_start': C['start_date'], 'date_end': incl(C['end_date']), 'generated_by': 'tools/import_campaign.py',
                'note': '由主專案考證檔轉出，只搬運不補。verified＝該筆有正式出處；false＝來源檔自己標為待查證。'},
       'phases': [], 'arrows': [], 'lines': [], 'sites': []}
sites = {}
for p in C['phases']:
    k = p['seq']
    out['phases'].append({'seq': k, 'key': p['phase_key'], 'name_zh': p['name_zh'], 'from': p['start_date'], 'to': incl(p['end_date']),
                          'dates_verified': p.get('dates_verified', bool(p.get('date_sources'))), 'date_refs': refs(p.get('date_sources')),
                          'summary_zh': p.get('summary_zh'), 'summary_verified': bool(p.get('summary_verified')), 'summary_refs': refs(p.get('summary_sources')),
                          **({'lines_note': p['front_lines_note']} if p.get('front_lines_note') else {})})
    for a in p.get('attack_arrows', []):
        out['arrows'].append({'phase': k, 'from': a['from'], 'to': a['to'], 'path': [a['from_lonlat'], a['to_lonlat']], 'unit': a.get('unit'), 'side': a.get('side'),
                              'verified': bool(a.get('verified')), 'refs': refs(a.get('sources')), **({'note': a['note']} if a.get('note') else {})})
    for f in p.get('front_lines', []):
        out['lines'].append({'phase': k, 'name': f.get('side'), 'vertices': f.get('vertices'), 'path': f.get('polyline_lonlat'), 'precision': f.get('precision'),
                             'verified': bool(f.get('verified')), 'refs': refs(f.get('sources')), **({'note': f.get('geometry_note') or f.get('note')} if (f.get('geometry_note') or f.get('note')) else {})})
    for s in p.get('strongpoints', []):
        st = sites.setdefault(s['name'], {'name': s['name'], 'lonlat': s['lonlat'], 'coord_ref': sid(s['coord_source']) if s.get('coord_source') else None, 'changes': []})
        for c in s.get('control_changes', []):
            st['changes'].append({'phase': k, 'date': c.get('date'), 'to': c.get('controller_after'), 'verified': bool(c.get('verified')), 'refs': refs(c.get('sources')),
                                  **({'note': c.get('note') or s.get('note')} if (c.get('note') or s.get('note')) else {})})
out['sites'] = list(sites.values())
out['sources'] = {v['id']: {k: x for k, x in v.items() if k != 'id'} for v in sources.values()}
json.dump(out, open(f'battles/{bid}/sourced.json', 'w'), ensure_ascii=False, indent=1)
n = lambda xs: f"{sum(1 for x in xs if x['verified'])}/{len(xs)}"
ch = [c for s in out['sites'] for c in s['changes']]
print(f"{bid}: 階段 {len(out['phases'])}｜箭頭 已查證 {n(out['arrows'])}｜戰線 {n(out['lines'])}｜據點 {len(out['sites'])}（易手紀錄 {n(ch)}）｜出處 {len(out['sources'])}")
