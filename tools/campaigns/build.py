#!/usr/bin/env python3
"""
戰役模式（ARCHITECTURE.md §11.2）：把考證組的 wl-campaign/0.1-proposal 檔轉成前端用的靜態 campaign JSON。

輸出 frontend/public/campaigns/<key>.json 與 index.json。
圖層寫成「每個 layer 一個 GeoJSON FeatureCollection」（fronts／arrows／sites），每個 feature 帶 phase、verified，
名稱與 MapLibre 的 source-layer 相同：之後要改 PMTiles 時，用 tippecanoe -L fronts:… -L arrows:… -L sites:… 打包，
前端只把 source 換成 pmtiles:// 並設 source-layer，圖層定義與 phase filter 不用改。
不推定：控制方或日期 verified:false 的據點、箭頭照原樣帶 verified:false，前端以虛線／「待考證」呈現。
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'data' / 'campaigns'
OUT = ROOT / 'frontend' / 'public' / 'campaigns'

# 交戰方 → 政權 slug（入口用：在這些政權的面板列出戰役）。考證檔只有中文國名，對照表在這裡維護。
REGIME_SLUGS = {
    '英國': 'united-kingdom', '法國': 'french-third-republic', '比利時（至1940-05-28）': 'kingdom-of-belgium',
    '德國': 'deutsches-reich',
}


def cite(s):
    return {k: s.get(k) for k in ('type', 'citation', 'url', 'quote') if s.get(k)}


def feature(geom, props):
    return {'type': 'Feature', 'geometry': geom, 'properties': props}


def build(src: dict) -> dict:
    fronts, arrows, sites, phases, cites = [], [], [], [], {}

    def keep(srcs):
        out = []
        for s in srcs or []:
            c = cite(s)
            if c.get('citation'):
                cites.setdefault(c['citation'] + (c.get('url') or ''), c)
                out.append(c)
        return out

    xs, ys = [], []
    def bbox(pts):
        for x, y in pts:
            xs.append(x); ys.append(y)

    for p in sorted(src['phases'], key=lambda p: p['seq']):
        seq = p['seq']
        for i, f in enumerate(p.get('front_lines', [])):
            bbox(f['polyline_lonlat'])
            fronts.append(feature({'type': 'LineString', 'coordinates': f['polyline_lonlat']}, {
                'id': f'{p["phase_key"]}-front-{i}', 'phase': seq, 'side': f.get('side'), 'verified': bool(f.get('verified')),
                'precision': f.get('precision'), 'note': f.get('geometry_note'), 'vertices': ' – '.join(f.get('vertices', [])),
                'sources': keep(f.get('sources'))}))
        for i, a in enumerate(p.get('attack_arrows', [])):
            line = [a['from_lonlat'], a['to_lonlat']]
            bbox(line)
            arrows.append(feature({'type': 'LineString', 'coordinates': line}, {
                'id': f'{p["phase_key"]}-arrow-{i}', 'phase': seq, 'from': a.get('from'), 'to': a.get('to'), 'unit': a.get('unit'),
                'verified': bool(a.get('verified')), 'note': a.get('note'), 'sources': keep(a.get('sources'))}))
        for i, s in enumerate(p.get('strongpoints', [])):
            bbox([s['lonlat']])
            ch = (s.get('control_changes') or [])
            last = ch[-1] if ch else {}
            sites.append(feature({'type': 'Point', 'coordinates': s['lonlat']}, {
                'id': f'{p["phase_key"]}-site-{i}', 'phase': seq, 'name': s['name'],
                'controller': last.get('controller_after') or 'unknown', 'date': last.get('date'),
                # 據點本身與該階段最後一次控制方變化都查證過才算查證
                'verified': bool(s.get('verified')) and bool(last.get('verified')),
                'note': last.get('note') or s.get('note'), 'sources': keep(last.get('sources'))}))
        phases.append({
            'seq': seq, 'key': p['phase_key'], 'name_zh': p['name_zh'], 'name_en': p.get('name_en'),
            'start': p['start_date'], 'end': p['end_date'],  # end exclusive（與 regimes 慣例一致）
            'summary_zh': p.get('summary_zh'), 'summary_verified': bool(p.get('summary_verified')),
            'sources': keep((p.get('date_sources') or []) + (p.get('summary_sources') or [])),
            'notes': [n for n in (p.get('front_lines_note'), p.get('arrows_note')) if n],
        })
    pad = 0.15
    bel = src.get('belligerents', {})
    return {
        'schema': 'wl-campaign-web/0.1', 'source_schema': src.get('schema'),
        'key': src['campaign_key'], 'name_zh': src['name_zh'], 'name_en': src.get('name_en'),
        'start': src['start_date'], 'end': src['end_date'], 'end_inclusive': src.get('end_date_inclusive'),
        'scale': src.get('battle_scale'),
        'belligerents': bel,
        'regime_slugs': sorted({REGIME_SLUGS[n] for side in bel.values() for n in side if n in REGIME_SLUGS}),
        'event_ids': src.get('event_ids', []),
        'totals': src.get('totals'),
        'bounds': [[min(xs) - pad, min(ys) - pad], [max(xs) + pad, max(ys) + pad]],
        'phases': phases,
        'layers': {
            'fronts': {'type': 'FeatureCollection', 'features': fronts},
            'arrows': {'type': 'FeatureCollection', 'features': arrows},
            'sites': {'type': 'FeatureCollection', 'features': sites},
        },
        'citations': list(cites.values()),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    index = []
    for f in sorted(SRC.glob('*.json')):
        c = build(json.loads(f.read_text()))
        (OUT / f'{c["key"]}.json').write_text(json.dumps(c, ensure_ascii=False, separators=(',', ':')))
        index.append({k: c[k] for k in ('key', 'name_zh', 'name_en', 'start', 'end', 'end_inclusive', 'scale', 'regime_slugs', 'event_ids')})
        print(f'{c["key"]}: {len(c["phases"])} phases, ' + ', '.join(f'{k} {len(v["features"])}' for k, v in c['layers'].items()))
    (OUT / 'index.json').write_text(json.dumps({'campaigns': index}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    sys.exit(main())
