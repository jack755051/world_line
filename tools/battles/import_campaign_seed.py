#!/usr/bin/env python3
"""
戰役 C1 匯入腳本（ARCHITECTURE.md §19.1、§19.4、§19.5 C1；World Line 戰役 bot，2026-11-11）。

把前端靜態戰役檔（wl-campaign-web/0.1）轉成 battle 表用的 seed，並輸出 dry-run 報表。
- 只讀前端 JSON、只寫 data/seed/battles/；不連任何資料庫。
- 可重跑、輸出可重現：id 一律 uuid5（由 slug／key 推出），不寫時間戳，JSON 鍵順序固定。連跑兩次逐位元相同。
- 絕不編造：JSON 沒有的內容（目標、控制變化、起訖日出處、accessed_on、出版者、等級）一律留 null 並列入報表「待查證」。
- 等級：JSON 只有 type；依 §19.4.2「官方檔案（含軍方戰史）＝A」給 grade_hint，grade 本身留 null，待考證組確認。
- status 一律 pending（試做範圍＝發電機行動；三條件由史料考證 bot 另行查證中）。

用法：python3 tools/battles/import_campaign_seed.py [campaign_key ...]   （預設 dunkirk_1940）
"""
import hashlib
import json
import re
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'frontend' / 'public' / 'campaigns'
OUT = ROOT / 'data' / 'seed' / 'battles'

SEED_SCHEMA = 'wl-battle-seed/0.1'
NS = uuid.uuid5(uuid.NAMESPACE_URL, 'https://worldline.local/battle-seed')
QUOTE_MAX = 80  # §16.4.1：NFC 後字元數
GRADE_HINT = {'official_history': 'A'}  # §19.4.2：官方檔案（含軍方戰史）＝A；其他 type 不給提示
# 座標參照（OSM 等）只說明「地名座標取自哪裡」，不是史實出處：不進 citation 表，放 props.geometry_refs。
GEOMETRY_REF_TYPES = {'gazetteer'}
KIND = {'fronts': 'front', 'arrows': 'arrow', 'sites': 'site'}
CAMPS = {'allied', 'axis', 'soviet', 'contested', 'unknown'}
# fronts 的 note 明說「頂點為出處明載之地名」時才算 source_text；其餘一律 derived（不得標 verified，§19.1.3）
SOURCE_TEXT_NOTE = '頂點為出處明載之地名'
TRIAL_TODO = ('TODO(考證)：試做範圍＝發電機行動（1940-05-26～06-04）。憲法 §6 三條件（交戰方、目標、起訖與地區）'
              '是否成立由史料考證 bot 查證中；若不成立，改以敦克爾克戰役為 battle、發電機行動為其階段或子事件（§19.5 C1）。'
              '結論出來前 status 一律 pending。')


def uid(*parts):
    return str(uuid.uuid5(NS, ':'.join(parts)))


def nfc_len(s):
    import unicodedata
    return len(unicodedata.normalize('NFC', s))


def locator_of(citation, url):
    m = re.search(r'\),\s*(ch\.\s*\d+.*)$', citation)
    return m.group(1).strip() if m else (url or citation)


class Sources:
    def __init__(self):
        self.by_key = {}

    def cite(self, raw):
        title, url = raw.get('citation') or '', raw.get('url')
        key = 'src-' + hashlib.sha1(f'{title}|{url}'.encode('utf-8')).hexdigest()[:12]
        if key not in self.by_key:
            self.by_key[key] = {
                'key': key, 'id': uid('source', key), 'source_kind': raw.get('type'),
                'title': title, 'url': url,
                'publisher': None,  # sources.publisher 必填；JSON 未拆出出版者，待補（不從字串猜）
            }
        quote = raw.get('quote') or ''
        qlen = nfc_len(quote)
        return {
            'source_key': key,
            'locator': locator_of(title, url),
            'quote': quote,
            'quote_len': qlen,
            'quote_over_limit': qlen > QUOTE_MAX,
            'quote_lang': None,
            'accessed_on': None,
            'grade': None,
            'grade_hint': GRADE_HINT.get(raw.get('type')),
            'date_precision': None,
            'policy_version': None,
        }

    def rows(self):
        return [self.by_key[k] for k in sorted(self.by_key)]


def precision(p):
    """Q6：early-month（上旬）改成 month，上旬寫進 note。"""
    if p in (None, 'day'):
        return 'day', None
    if p == 'early-month':
        return 'month', '上旬（Q6：精度改 month，原 JSON 為 early-month）'
    return p, None


def bbox_multipolygon(bounds):
    (x0, y0), (x1, y1) = bounds
    ring = [[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]
    return {'type': 'MultiPolygon', 'coordinates': [[ring]]}


def convert(d):
    slug = d['key']
    src = Sources()
    event_id = uid('event', slug)

    phases = []
    for p in sorted(d['phases'], key=lambda x: x['seq']):
        sp, sn = precision(p.get('start_precision'))
        ep, en = precision(p.get('end_precision'))
        phases.append({
            'id': uid('phase', slug, str(p['seq'])),
            'seq': p['seq'],
            'name': {'zh-Hant': p.get('name_zh'), 'en': p.get('name_en')},
            'period': {'start': p['start'], 'end': p['end']},  # 半開區間（§14.6）
            'start_precision': sp, 'end_precision': ep,
            'evidence_note': '；'.join(x for x in (sn, en) if x) or None,
            'summary': {'zh-Hant': p['summary_zh']} if p.get('summary_zh') and p.get('sources') else None,
            'status': 'pending',
            'json_flags': {'dates_verified': p.get('dates_verified'), 'summary_verified': p.get('summary_verified')},
            'citations': [src.cite(s) for s in p.get('sources') or []],
        })

    features = []
    for layer in ('fronts', 'arrows', 'sites'):
        for f in d['layers'][layer]['features']:
            pr = f['properties']
            note = pr.get('note') or ''
            basis = 'source_text' if layer == 'fronts' and SOURCE_TEXT_NOTE in note else 'derived'
            props = {k: v for k, v in pr.items()
                     if k not in ('id', 'phase', 'group', 'verified', 'sources') and v is not None}
            group = pr.get('group')
            hist = [x for x in pr.get('sources') or [] if x.get('type') not in GEOMETRY_REF_TYPES]
            refs = [{'citation': x.get('citation'), 'url': x.get('url')}
                    for x in pr.get('sources') or [] if x.get('type') in GEOMETRY_REF_TYPES]
            if refs:
                props['geometry_refs'] = refs
            features.append({
                'id': uid('feature', pr['id']),
                'feature_key': pr['id'],
                'phase_seq': pr['phase'],
                'phase_id': uid('phase', slug, str(pr['phase'])),
                'feature_kind': KIND[layer],
                'side_camp': group if group in CAMPS else 'unknown',
                'side_regime_slug': None,  # 配色組不等於政權；不推導（憲法 §6「陣營」）
                'geom': f['geometry'],
                'label': None,
                'props': dict(sorted(props.items())),
                'geom_basis': basis,
                'status': 'pending',
                'json_flags': {'verified': pr.get('verified')},
                'citations': [src.cite(s) for s in hist],
            })

    totals = d.get('totals')
    deferred_totals = None
    if totals:
        deferred_totals = {k: v for k, v in totals.items() if k != 'sources'}
        deferred_totals['citations'] = [src.cite(s) for s in totals.get('sources') or []]
        deferred_totals['note'] = 'battle_figures 屬 C3；metric 值域目前沒有 evacuated，C3 時再議，不在 C1 入庫'

    unit_candidates = sorted({f['props']['unit'] for f in features if f['props'].get('unit')})

    return {
        'schema': SEED_SCHEMA,
        'generated_from': {
            'path': str((SRC / f'{slug}.json').relative_to(ROOT)),
            'schema': d.get('schema'),
            'sha256': None,  # 由 main() 填
        },
        'slug': slug,
        'todo': [TRIAL_TODO],
        'event': {
            'id': event_id,
            'event_kind': 'battle',
            'occurred': {'start': d['start'], 'end': d['end']},  # 半開；end_inclusive＝d['end_inclusive']
            'date_precision': 'day',
            'status': 'pending',
            'json_flags': {'end_verified': d.get('end_verified')},
            'citations': [],  # web JSON 沒有起訖日／交戰方／地點的出處 → event_citations 待查證
        },
        'participants': {
            'role': 'belligerent',
            'regime_slugs': sorted(d.get('regime_slugs') or []),
            'json_belligerents': d.get('belligerents'),  # 原文照錄（含「至1940-05-28」註記），不拆、不推導
        },
        'profile': {
            'event_id': event_id,
            'slug': slug,
            'name': {'zh-Hant': d.get('name_zh'), 'en': d.get('name_en')},
            'objective': None, 'objective_kind': None,      # JSON 沒有；憲法 §6 條件 (2) 待考證
            'control_change': None,                          # JSON 沒有；條件 (3) 待考證
            'outcome_kind': None, 'outcome_text': None,      # 沒有出處就 NULL（§19.1.1）
            'conflict_record_id': None,
            'theater_area': bbox_multipolygon(d['bounds']) if d.get('bounds') else None,
            'theater_area_basis': 'derived（由 JSON bounds 外框產生，非出處；需考證組以出處重畫）',
            'status': 'pending',
            'citations': [],
        },
        'phases': phases,
        'features': features,
        'units': [],
        'unit_candidates': unit_candidates,  # 箭頭上的部隊文字；沒有獨立出處前不建 battle_units
        'deferred': {
            'totals': deferred_totals,
            'phase_notes': [{'seq': p['seq'], 'fronts_note': p['fronts_note']}
                            for p in d['phases'] if p.get('fronts_note')],  # → C3 event_gaps
        },
        'sources': src.rows(),
    }


def yn(b):
    return '有' if b else '**缺**'


def report(seed):
    L = []
    w = L.append
    ph, fs = seed['phases'], seed['features']
    all_cites = [c for p in ph for c in p['citations']] + [c for f in fs for c in f['citations']]
    w(f"# 戰役 seed dry-run 報表：{seed['slug']}")
    w('')
    w(f"- 來源：`{seed['generated_from']['path']}`（{seed['generated_from']['schema']}，sha256 `{seed['generated_from']['sha256'][:16]}…`）")
    w(f"- 產生：`tools/battles/import_campaign_seed.py`（不連資料庫；本報表不含時間戳，重跑應逐位元相同）")
    w('- 全部 status＝pending。' + seed['todo'][0])
    w('- 等級：JSON 只有 `type`，`grade` 一律 null；`grade_hint` 依 §19.4.2（official_history→A）推出，**未經考證確認，不算已有 A／B citation**。')
    w('')
    w('## 摘要')
    w('')
    w('| 項目 | 數量 |')
    w('|---|---|')
    w(f"| 階段 | {len(ph)} |")
    for k in ('front', 'arrow', 'site'):
        w(f"| 圖形 {k} | {sum(1 for f in fs if f['feature_kind'] == k)} |")
    w(f"| citation（階段＋圖形） | {len(all_cites)} |")
    w(f"| 　其中 grade 已確認 A／B | {sum(1 for c in all_cites if c['grade'] in ('A', 'B'))} |")
    w(f"| 　其中 grade_hint＝A（候選） | {sum(1 for c in all_cites if c['grade_hint'] == 'A')} |")
    w(f"| 　quote 超過 {QUOTE_MAX} 字 | {sum(1 for c in all_cites if c['quote_over_limit'])} |")
    w(f"| 　缺 accessed_on | {sum(1 for c in all_cites if not c['accessed_on'])} |")
    w(f"| 座標參照（gazetteer，不算出處，放 props.geometry_refs） | {sum(len(f['props'].get('geometry_refs', [])) for f in fs)} |")
    w(f"| 無任何 citation 的圖形 | {sum(1 for f in fs if not f['citations'])} |")
    w(f"| geom_basis＝derived（不得 verified） | {sum(1 for f in fs if f['geom_basis'] == 'derived')} |")
    w(f"| 來源（sources） | {len(seed['sources'])}（publisher 全部待補） |")
    w('')
    w('## 戰役主體（historical_events＋battle_profiles）')
    w('')
    w('| 欄位 | 值 | citation | 狀態 |')
    w('|---|---|---|---|')
    e, pr = seed['event'], seed['profile']
    w(f"| occurred | {e['occurred']['start']}～{e['occurred']['end']}（半開） | **缺**（web JSON 無起訖日出處） | pending／待查證 |")
    w(f"| 交戰方 | {', '.join(seed['participants']['regime_slugs'])} | **缺** | pending／待查證（event_citations） |")
    w(f"| name | {pr['name']['zh-Hant']} / {pr['name']['en']} | **缺** | pending |")
    w('| objective／objective_kind | null | **缺**（JSON 無此內容） | 待查證；NOT NULL，補齊前不能寫庫 |')
    w('| control_change | null | **缺**（JSON 無此內容） | 待查證；NOT NULL，補齊前不能寫庫 |')
    w('| outcome_kind／outcome_text | null | 無 | 沒有出處就留 NULL |')
    w('| theater_area | JSON bounds 外框 | 無（derived） | 待以出處重畫 |')
    w('')
    w('## 階段（battle_phases）')
    w('')
    w('| seq | 名稱 | 期間（半開） | 精度 | citation | grade_hint | quote>80 | JSON 原標記 | 狀態 |')
    w('|---|---|---|---|---|---|---|---|---|')
    for p in ph:
        cs = p['citations']
        hints = '/'.join(sorted({c['grade_hint'] or '—' for c in cs})) or '—'
        w(f"| {p['seq']} | {p['name']['zh-Hant']} | {p['period']['start']}～{p['period']['end']} | {p['start_precision']}/{p['end_precision']} "
          f"| {len(cs)}（{yn(cs)}） | {hints} | {sum(c['quote_over_limit'] for c in cs)} "
          f"| dates={p['json_flags']['dates_verified']}, summary={p['json_flags']['summary_verified']} | pending |")
    w('')
    w('## 圖形（battle_map_features）')
    w('')
    w('| feature_key | 種類 | 配色組 | geom_basis | citation | grade_hint | JSON verified | 狀態 |')
    w('|---|---|---|---|---|---|---|---|')
    for f in fs:
        cs = f['citations']
        hints = '/'.join(sorted({c['grade_hint'] or '—' for c in cs})) or '—'
        w(f"| {f['feature_key']} | {f['feature_kind']} | {f['side_camp']} | {f['geom_basis']} | {len(cs)}（{yn(cs)}） | {hints} "
          f"| {f['json_flags']['verified']} | pending{'；**缺出處**' if not cs else ''} |")
    w('')
    w('## 未入 C1 的內容')
    w('')
    t = seed['deferred']['totals']
    if t:
        w(f"- totals（{', '.join(k for k in t if k not in ('citations', 'note', 'verified'))}）：{len(t['citations'])} 筆 citation；{t['note']}。")
    for n in seed['deferred']['phase_notes']:
        w(f"- 階段 {n['seq']} fronts_note「{n['fronts_note']}」→ C3 event_gaps（`phase:{n['seq']}`，not_found），不寫進 battle_phases（I6）。")
    w(f"- 部隊候選（箭頭文字，未建 battle_units）：{'；'.join(seed['unit_candidates'])}")
    w('')
    w('## 寫庫前必補（blocking）')
    w('')
    w('1. 三條件考證結論（史料考證 bot）與 event_citations。')
    w('2. objective／objective_kind／control_change（NOT NULL）與 battle_profile_citations。')
    w('3. 每筆 citation 的 accessed_on、grade（確認 A／B）；quote 超過 80 字者改短引。')
    w('4. sources.publisher。')
    w('5. 無出處圖形補出處或撤除；derived 圖形若要 verified 需改以出處重畫（source_map／source_text）。')
    w('')
    return '\n'.join(L)


def dump(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2) + '\n'


def main(keys):
    OUT.mkdir(parents=True, exist_ok=True)
    for key in keys:
        path = SRC / f'{key}.json'
        raw = path.read_bytes()
        d = json.loads(raw)
        if d.get('schema') != 'wl-campaign-web/0.1':
            sys.exit(f'{path}: schema 不是 wl-campaign-web/0.1')
        seed = convert(d)
        seed['generated_from']['sha256'] = hashlib.sha256(raw).hexdigest()
        (OUT / f'{key}.seed.json').write_text(dump(seed), encoding='utf-8')
        (OUT / f'{key}.dry-run.md').write_text(report(seed), encoding='utf-8')
        print(f'wrote data/seed/battles/{key}.seed.json, {key}.dry-run.md')


if __name__ == '__main__':
    main(sys.argv[1:] or ['dunkirk_1940'])
