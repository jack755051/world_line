#!/usr/bin/env python3
"""
戰役匯入腳本 C1b（ARCHITECTURE.md §19.1、§19.4、§19.5 C1；憲法 §6；World Line 戰役 bot，2026-11-11）。

輸入（全部唯讀）：
- 前端靜態戰役檔 frontend/public/campaigns/<key>.json（wl-campaign-web/0.1）：只取圖形幾何與圖形原 citation。
- 考證輸入 data/seed/battles/<key>.research.json（dynamo-research/0.1，史料考證 bot 產出）：戰役定性、起訖、交戰方、
  目標、範圍、控制變化、六個階段與逐字引文。
- 原文 raw 目錄（預設 .dev/campaign-dynamo/raw）：Ellis 官方戰史各章 HyperWar 轉錄、Gazette 38017 p.3295 OCR。
  每一筆引文都在這裡逐字比對；raw 不存在就停止（不在沒有原文的情況下給等級）。

輸出：data/seed/battles/<key>.seed.json、<key>.dry-run.md。不連任何資料庫。
- 可重跑、輸出可重現：id 一律 uuid5，不寫時間戳，鍵順序固定。連跑兩次逐位元相同。
- 等級規則（Tai 2026-11-11 13:47）：來源本身為 A，且引文在 raw 逐字找得到（只摺疊空白、解 HTML 實體）、NFC 後不超過 80 字，
  才標 grade='A'。超過 80 字者截成 raw 逐字存在的最長子句；截不出來、或找不到原文 → grade=null、verification='pending'。
- 絕不編造：沒有出處的內容（戰役名稱、Bergues／Malo-les-Bains、推估幾何、部隊番號）一律 pending。
- status 一律 pending：寫庫與 verified 判定要 Tai 另行核准；報表另列「符合 verified 門檻」供審。

用法：python3 tools/battles/import_campaign_seed.py [--raw DIR] [campaign_key ...]   （預設 dunkirk_1940）
"""
import hashlib
import html
import json
import re
import sys
import unicodedata
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / 'frontend' / 'public' / 'campaigns'
OUT = ROOT / 'data' / 'seed' / 'battles'
RAW_DEFAULT = ROOT / '.dev' / 'campaign-dynamo' / 'raw'

SEED_SCHEMA = 'wl-battle-seed/0.2'
NS = uuid.uuid5(uuid.NAMESPACE_URL, 'https://worldline.local/battle-seed')
QUOTE_MAX = 80  # §16.4.1：NFC 後字元數
ACCESSED_DEFAULT = '2026-11-11'
GEOMETRY_REF_TYPES = {'gazetteer'}  # 座標參照不是史實出處：放 props.geometry_refs
KIND = {'fronts': 'front', 'arrows': 'arrow', 'sites': 'site'}
CAMPS = {'allied', 'axis', 'soviet', 'contested', 'unknown'}
SOURCE_TEXT_NOTE = '頂點為出處明載之地名'

# 考證輸入的 sourceKey → seed 來源（sources 表）。source_kind 依 ck_sources_source_kind 值域。
SOURCE_KIND = {'ellis': 'official_history', 'ramsay': 'official_record'}
SOURCE_PUBLISHER = {'ellis': 'HMSO', 'ramsay': 'The London Gazette'}
SOURCE_TITLE = {
    'ellis': 'L. F. Ellis, The War in France and Flanders 1939–1940 (History of the Second World War, UK Military Series, ed. J. R. M. Butler)',
    'ramsay': "Vice-Admiral Sir Bertram H. Ramsay, 'The Evacuation of the Allied Armies from Dunkirk and Neighbouring Beaches' "
              '(despatch dated 18 June 1940), Supplement to The London Gazette no. 38017, 17 July 1947',
}
ELLIS_URL = re.compile(r'UK-NWE-Flanders-(\d+)\.html$')
ROMAN = {10: 'X', 11: 'XI', 12: 'XII', 13: 'XIII', 14: 'XIV', 15: 'XV', 16: 'XVI', 17: 'XVII', 24: 'XXIV', 25: 'XXV'}

# 前端舊五段 → 考證六段。舊 P2（05-28–05-30）的圖形 citation 全出自 Ellis ch.XIII（28 May），歸新 P2；
# 新 P3（05-29–05-30）沒有對應圖形。舊 P5 對應新 P6：P6 沒有戰線圖 → 不配地圖要素（Tai 2026-11-11 13:47），圖形移入 deferred。
WEB_PHASE_TO_SEQ = {1: 1, 2: 2, 3: 4, 4: 5}

NAME = {'zh-Hant': '敦克爾克橋頭堡戰役', 'en': 'Battle of Dunkirk bridgehead'}
UNIT_NOTE = '待查證：部隊番號沿用前端 JSON，未逐字對照出處（Tai 2026-11-11 13:47：保留、標待查證）'


def uid(*parts):
    return str(uuid.uuid5(NS, ':'.join(parts)))


def nfc(s):
    return unicodedata.normalize('NFC', s)


def norm(s):
    return re.sub(r'\s+', ' ', nfc(html.unescape(s))).strip()


class Raw:
    """raw 原文：只摺疊空白、解 HTML 實體後做子字串比對（逐字）。頁碼取引文之後第一個 --NNN-- 標記（HyperWar 頁尾頁碼）。"""

    def __init__(self, folder):
        if not folder.is_dir():
            sys.exit(f'raw 目錄不存在：{folder}（逐字比對需要原文；不在沒有原文的情況下產生 seed）')
        self.folder = folder
        self.text, self.sha = {}, {}

    def file_of(self, raw_key):
        return 'gazette-3295.txt' if raw_key == 'ramsay' else f'{raw_key}.txt'

    def load(self, raw_key):
        if raw_key not in self.text:
            p = self.folder / self.file_of(raw_key)
            if not p.is_file():
                self.text[raw_key], self.sha[raw_key] = None, None
            else:
                b = p.read_bytes()
                self.text[raw_key] = norm(b.decode('utf-8', errors='replace'))
                self.sha[raw_key] = hashlib.sha256(b).hexdigest()
        return self.text[raw_key]

    def find(self, raw_key, quote):
        t = self.load(raw_key)
        if not t or not quote:
            return None
        i = t.find(norm(quote))
        return None if i < 0 else i

    def page(self, raw_key, pos):
        if raw_key == 'ramsay':
            return None
        m = re.search(r'--(\d+)--', self.text[raw_key][pos:])
        return int(m.group(1)) if m else None


def clauses(quote, prefer=None):
    """把長引文拆成候選子句（以 …／...／破折號／分號／句點／逗號為界）。只取原文片段，不改字。
    排序：含 prefer 字串者優先 → 專有名詞與數字較多者（地名、番號、人數才是支撐圖形或數字的內容）→ 較長 → 字典序。"""
    parts = set()
    for sep in (r'\s*(?:\.\.\.|…)\s*', r'\s*[—;]\s*', r'(?<=[.!?])\s+', r',\s*'):
        for seg in re.split(sep, quote):
            seg = seg.strip(' ,;')
            if seg:
                parts.add(seg)

    def score(s):
        toks = s.split()
        names = sum(1 for t in toks[1:] if t[:1].isupper() or t[:1].isdigit()) + (1 if toks and toks[0][:1].isdigit() else 0)
        return (0 if prefer and prefer in s else 1, -names, -len(s), s)

    return sorted(parts, key=score)


class Cites:
    def __init__(self, raw):
        self.raw = raw
        self.used_raw = set()

    def _grade(self, source_key, raw_key, quote, prefer=None):
        """回傳 (quote, verbatim, page, grade, reason, truncated_from)。"""
        if source_key not in SOURCE_KIND:
            return quote, None, None, None, '來源不在考證輸入的 A 級清單', None
        if raw_key is None:
            return quote, None, None, None, '找不到對應的 raw 原文檔', None
        self.used_raw.add(raw_key)
        q = norm(quote)
        pos = self.raw.find(raw_key, q)
        if pos is not None and len(q) <= QUOTE_MAX:
            return q, True, self.raw.page(raw_key, pos), 'A', None, None
        if pos is None and len(q) <= QUOTE_MAX:
            return q, False, None, None, 'raw 原文中找不到逐字相符的句子', None
        for seg in clauses(q, prefer):
            if len(seg) <= QUOTE_MAX and len(seg) >= 20:
                p = self.raw.find(raw_key, seg)
                if p is not None:
                    return seg, True, self.raw.page(raw_key, p), 'A', None, q
        reason = f'原引文 {len(q)} 字超過 {QUOTE_MAX}，截不出 raw 逐字存在的子句' if pos is not None \
            else f'原引文 {len(q)} 字超過 {QUOTE_MAX}，且 raw 原文中找不到逐字相符的子句'
        return q, pos is not None, None, None, reason, None

    def make(self, source_key, raw_key, url, locator, quote, accessed_on, extra=None, origin='research', prefer=None):
        q, verbatim, page, grade, reason, trunc = self._grade(source_key, raw_key, quote or '', prefer)
        c = {
            'source_key': f'src-{source_key}' if source_key in SOURCE_KIND else None,
            'url': url,
            'locator': locator,
            'quote': q,
            'quote_len': len(nfc(q)),
            'quote_lang': 'en',
            'accessed_on': accessed_on or ACCESSED_DEFAULT,
            'grade': grade,
            'verification': 'verbatim' if grade else 'pending',
            'verbatim_check': {'raw': raw_key, 'raw_sha256': self.raw.sha.get(raw_key), 'found': verbatim,
                               'page_from_raw': page},
            'origin': origin,
        }
        if trunc:
            c['truncated_from'] = trunc
        if reason:
            c['pending_reason'] = reason
        for k, v in sorted((extra or {}).items()):
            c[k] = v
        return c

    def research(self, r):
        extra = {k: r[k] for k in ('perspective', 'evidenceNote', 'datePrecision') if r.get(k)}
        extra = {{'evidenceNote': 'evidence_note', 'datePrecision': 'date_precision'}.get(k, k): v for k, v in extra.items()}
        return self.make(r['sourceKey'], r.get('raw'), r.get('url'), r.get('locator'), r.get('quote'),
                         r.get('accessedOn'), extra)

    def web(self, s, accessed_on, prefer=None):
        """前端 JSON 的舊 citation：Ellis 依 URL 章號對 raw；頁碼由 raw 推出。"""
        url = s.get('url') or ''
        m = ELLIS_URL.search(url)
        if s.get('type') == 'official_history' and m:
            ch = int(m.group(1))
            c = self.make('ellis', f'ellis-{ch}', url, None, s.get('quote'), accessed_on,
                          {'web_citation': s.get('citation')}, origin='web-json', prefer=prefer)
            pg = c['verbatim_check']['page_from_raw']
            c['locator'] = f"ch. {ROMAN.get(ch, ch)}" + (f', p. {pg}' if pg else '')
            return c
        return self.make(s.get('type') or 'unknown', None, url, s.get('citation'), s.get('quote'), accessed_on,
                         {'web_citation': s.get('citation')}, origin='web-json')


def dedupe(cs):
    seen, out = set(), []
    for c in cs:
        k = (c['source_key'], c['locator'], c['quote'])
        if k not in seen:
            seen.add(k)
            out.append(c)
    return out


def bbox_multipolygon(bounds):
    (x0, y0), (x1, y1) = bounds
    ring = [[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]
    return {'type': 'MultiPolygon', 'coordinates': [[ring]]}


def has_a(cs):
    return any(c['grade'] in ('A', 'B') for c in cs)


def convert(web, res, raw):
    slug = web['key']
    acc = res.get('researchedOn') or ACCESSED_DEFAULT
    cz = Cites(raw)
    rec, f = res['record'], res['record']['fields']
    event_id = uid('event', slug)

    event_cites = dedupe([cz.research(c) for c in f['start']['citations'] + f['end']['citations'] + f['area']['citations']])
    participants = []
    for b in f['belligerents']['value']:
        p = {'regime_slug': b['regime'], 'role': 'belligerent', 'side_camp_hint': b['side'],
             'citations': [cz.research(c) for c in b['citations']]}
        if b.get('until'):
            p['until_exclusive'] = b['until']
            p['until_note'] = b.get('untilNote')
        participants.append(p)
    participants.sort(key=lambda p: p['regime_slug'])

    subs = []
    for s in rec['subEvents']:
        subs.append({
            'id': uid('event', slug, s['key']),
            'key': s['key'],
            'parent_event_id': event_id,
            'name': {'zh-Hant': s['nameZh'], 'en': s['nameEn']},
            'event_kind': None,
            'event_kind_note': "待決：historical_events.event_kind 值域（war/campaign/battle/treaty/armistice/surrender/political/atrocity）"
                               "沒有 operation；考證輸入作「operation（子事件）」。未決前 NULL，不可寫庫。",
            'occurred': {'start': s['start'], 'end': s['endExclusive']},
            'date_precision': 'day',
            'status': 'pending',
            'citations': [cz.research(c) for c in s['citations']],
        })

    profile_cites = {
        'objective': [cz.research(c) for c in f['objective']['citations']],
        'control_change': [cz.research(c) for c in f['controlChange']['citations']],
        'theater_area': [cz.research(c) for c in f['area']['citations']],
        'name': [],
    }

    phases = []
    for p in sorted(res['phases'], key=lambda x: x['seq']):
        maps = [m for m in p.get('maps') or [] if not m.startswith('待查證')]
        pending_maps = [m for m in p.get('maps') or [] if m.startswith('待查證')]
        cs = [cz.research(c) for c in p['citations']]
        phases.append({
            'id': uid('phase', slug, str(p['seq'])),
            'seq': p['seq'],
            'name': {'zh-Hant': p['nameZh'], 'en': None},
            'period': {'start': p['start'], 'end': p['end']},  # 半開（§14.6）
            'start_precision': 'day', 'end_precision': 'day',
            'summary': None,  # 考證輸入沒有逐段 summary；前端舊 summary 無逐字出處，不沿用
            'source_maps': maps,
            'map_status': 'pending' if pending_maps or not maps else 'source_map_listed',
            'map_note': pending_maps[0] if pending_maps else None,
            'status': 'pending',
            'eligible_for_verified': has_a(cs),
            'citations': cs,
        })
    seq_ids = {p['seq']: p['id'] for p in phases}

    features, deferred_features = [], []
    for layer in ('fronts', 'arrows', 'sites'):
        for ft in web['layers'][layer]['features']:
            pr = ft['properties']
            note = pr.get('note') or ''
            basis = 'source_text' if layer == 'fronts' and SOURCE_TEXT_NOTE in note else 'derived'
            props = {k: v for k, v in pr.items()
                     if k not in ('id', 'phase', 'group', 'verified', 'sources') and v is not None}
            refs = [{'citation': x.get('citation'), 'url': x.get('url')}
                    for x in pr.get('sources') or [] if x.get('type') in GEOMETRY_REF_TYPES]
            if refs:
                props['geometry_refs'] = refs
            if props.get('unit'):
                props['verification'] = 'pending'
                props['unit_note'] = UNIT_NOTE
            hist = [cz.web(x, acc) for x in pr.get('sources') or [] if x.get('type') not in GEOMETRY_REF_TYPES]
            group = pr.get('group')
            seq = WEB_PHASE_TO_SEQ.get(pr['phase'])
            row = {
                'id': uid('feature', pr['id']),
                'feature_key': pr['id'],
                'web_phase': pr['phase'],
                'phase_seq': seq,
                'phase_id': seq_ids.get(seq),
                'feature_kind': KIND[layer],
                'side_camp': group if group in CAMPS else 'unknown',
                'side_regime_slug': None,
                'geom': ft['geometry'],
                'label': None,
                'props': dict(sorted(props.items())),
                'geom_basis': basis,
                'status': 'pending',
                'json_flags': {'verified': pr.get('verified')},
                'pending_reasons': (['無任何出處（前端 JSON 即無 citation）'] if not hist else [])
                                   + (['幾何為推估（derived），需以出處圖重畫'] if basis == 'derived' else []),
                'citations': hist,
            }
            if seq is None:
                row['deferred_reason'] = '新 P6 沒有戰線圖（Ellis 無 6/2–6/4 situation map）→ 不配地圖要素（Tai 2026-11-11 13:47）'
                deferred_features.append(row)
            else:
                features.append(row)

    totals = web.get('totals')
    deferred_totals = None
    if totals:
        deferred_totals = {k: v for k, v in totals.items() if k not in ('sources', 'verified')}
        deferred_totals['perspective'] = '英方數字（英國官方戰史 Ellis 所載；非各方共同統計）'
        n = totals.get('evacuated_dynamo')
        deferred_totals['citations'] = [cz.web(s, acc, f'{n:,}' if isinstance(n, int) else None)
                                        for s in totals.get('sources') or []]
        deferred_totals['note'] = 'battle_figures 屬 C3；metric 值域目前沒有 evacuated，C3 時再議，不在 C1 入庫'

    src = res['sources']
    sources = []
    for k in sorted(SOURCE_KIND):
        s = src[k]
        row = {'key': f'src-{k}', 'id': uid('source', f'src-{k}'), 'source_kind': SOURCE_KIND[k],
               'title': SOURCE_TITLE[k], 'url': s['url'], 'publisher': SOURCE_PUBLISHER[k],
               'grade': s['grade'], 'grade_basis': s['gradeBasis'], 'transcription': s.get('publisher'),
               'note': s.get('note')}
        if k == 'ellis':
            row['publication_year'] = None
            row['publication_year_conflict'] = {
                'values': ['1953', '1954'],
                'note': '前端 JSON 作 1953（初版）；HyperWar 封面頁作 LONDON 1954。依考證輸入：出版年待核對，未決前不填。',
            }
        sources.append(row)

    unit_candidates = sorted({x['props']['unit'] for x in features + deferred_features if x['props'].get('unit')})
    gaps = [{'target': g['target'], 'kind': g['kind'], 'note': g['note']} for g in res.get('gaps') or []]
    gaps += [
        {'target': 'phase:3 map', 'kind': 'not_found', 'note': '前端舊圖形沒有對應 5/29–5/30 的要素；Ellis 29 May situation map 已列，待依圖重畫'},
        {'target': 'feature:dunkirk_1940_p4-site-0', 'kind': 'not_found', 'note': 'Bergues：無出處，德軍完全佔領日期待查證'},
        {'target': 'feature:dunkirk_1940_p5-site-1', 'kind': 'not_found', 'note': 'Malo-les-Bains：無出處，日期待查證'},
        {'target': 'unit:arrows', 'kind': 'not_found', 'note': '箭頭部隊番號未逐字對照出處'},
        {'target': 'subevent:operation-dynamo event_kind', 'kind': 'note', 'note': 'event_kind 值域無 operation，待決'},
    ]

    return {
        'schema': SEED_SCHEMA,
        'generated_from': {
            'web': {'path': f'frontend/public/campaigns/{slug}.json', 'schema': web.get('schema'), 'sha256': None},
            'research': {'path': f'data/seed/battles/{slug}.research.json', 'schema': res.get('schema'), 'sha256': None,
                         'researched_on': res.get('researchedOn')},
            'raw_sha256': None,
        },
        'slug': slug,
        'determination': {
            'constitution': '憲法 §6 戰役三條件',
            'conclusion': 'battle：敦克爾克橋頭堡戰役（1940-05-26～06-04）；發電機行動為子事件（parent_event_id），不是階段',
            'conditions': {
                'belligerents': 'A 級出處：英、法、比（至 1940-05-28）、德（見 participants）',
                'objective': 'A 級出處（見 profile.citations.objective）',
                'period_and_area': 'A 級出處（見 event.citations）',
            },
            'name_note': rec.get('nameNote'),
            'decided_by': 'Tai 2026-11-11 13:47（併入考證、橋頭堡戰役、六階段、A 級引文）',
        },
        'event': {
            'id': event_id,
            'event_kind': rec['eventKind'],
            'occurred': {'start': f['start']['value'], 'end': f['end']['valueExclusive']},  # 半開；含終點 06-04
            'occurred_end_inclusive': f['end']['valueInclusive'],
            'date_precision': 'day',
            'status': 'pending',
            'eligible_for_verified': has_a(event_cites),
            'citations': event_cites,
        },
        'sub_events': subs,
        'participants': participants,
        'profile': {
            'event_id': event_id,
            'slug': slug,
            'name': NAME,
            'name_verification': 'pending',
            'name_note': 'Tai 2026-11-11 13:47 指定名稱；' + (rec.get('nameNote') or ''),
            'objective': {'zh-Hant': f['objective']['valueZh']},
            'objective_kind': None,
            'objective_kind_candidate': 'place',
            'objective_kind_note': '分類（place/line/regime）不是史實，由人確認；未決前 NULL，不可寫庫',
            'control_change': {'zh-Hant': f['controlChange']['valueZh']},
            'area_text': {'zh-Hant': f['area']['valueZh']},
            'outcome_kind': None, 'outcome_text': None,
            'conflict_record_id': None,
            'theater_area': bbox_multipolygon(web['bounds']) if web.get('bounds') else None,
            'theater_area_basis': 'derived（由前端 JSON bounds 外框產生，非出處；需依 Ellis 圖重畫）',
            'status': 'pending',
            'citations': profile_cites,
        },
        'phases': phases,
        'features': features,
        'units': [],
        'unit_candidates': unit_candidates,
        'deferred': {
            'features': deferred_features,
            'totals': deferred_totals,
            'map_sources': res.get('mapSources'),
        },
        'gaps': gaps,
        'sources': sources,
        '_raw_used': sorted(cz.used_raw),
    }


def all_cites(seed):
    out = []
    out += [('event', c) for c in seed['event']['citations']]
    out += [(f"participant:{p['regime_slug']}", c) for p in seed['participants'] for c in p['citations']]
    out += [(f"sub_event:{s['key']}", c) for s in seed['sub_events'] for c in s['citations']]
    out += [(f'profile:{k}', c) for k, v in seed['profile']['citations'].items() for c in v]
    out += [(f"phase:{p['seq']}", c) for p in seed['phases'] for c in p['citations']]
    out += [(f"feature:{x['feature_key']}", c) for x in seed['features'] for c in x['citations']]
    out += [(f"deferred:{x['feature_key']}", c) for x in seed['deferred']['features'] for c in x['citations']]
    if seed['deferred']['totals']:
        out += [('deferred:totals', c) for c in seed['deferred']['totals']['citations']]
    return out


def report(seed):
    L = []
    w = L.append
    cs = all_cites(seed)
    graded = [c for _, c in cs if c['grade'] in ('A', 'B')]
    pend = [(o, c) for o, c in cs if not c['grade']]
    g = seed['generated_from']
    ph, fs, pr = seed['phases'], seed['features'], seed['profile']
    w(f"# 戰役 seed dry-run 報表：{seed['slug']}（{pr['name']['zh-Hant']}）")
    w('')
    w(f"- 圖形來源：`{g['web']['path']}`（sha256 `{g['web']['sha256'][:16]}…`）")
    w(f"- 考證輸入：`{g['research']['path']}`（{g['research']['schema']}，sha256 `{g['research']['sha256'][:16]}…`）")
    w('- raw 原文 sha256：' + '、'.join(f"{k} `{v[:12]}…`" for k, v in sorted(g['raw_sha256'].items()) if v))
    w('- 產生：`tools/battles/import_campaign_seed.py`（不連資料庫；不含時間戳，重跑逐位元相同）')
    w(f"- 定性：{seed['determination']['conclusion']}（{seed['determination']['decided_by']}）")
    w('- 全部 status＝pending；寫庫與 verified 判定需 Tai 另行核准。')
    w(f'- 等級規則：來源為 A、raw 逐字找得到、NFC 後 ≤{QUOTE_MAX} 字 → A；其餘 pending。超過 {QUOTE_MAX} 字者截成 raw 逐字子句。')
    w('')
    w('## 摘要')
    w('')
    w('| 項目 | 數量 |')
    w('|---|---|')
    w(f'| citation 總數（含 deferred） | {len(cs)} |')
    w(f"| 　A | {sum(1 for c in graded if c['grade'] == 'A')} |")
    w(f"| 　B | {sum(1 for c in graded if c['grade'] == 'B')} |")
    w(f'| 　pending（無等級） | {len(pend)} |')
    w(f"| 　其中截成逐字子句後標 A | {sum(1 for _, c in cs if c.get('truncated_from'))} |")
    w(f"| 　考證輸入引文（research） | {sum(1 for _, c in cs if c['origin'] == 'research')}（A {sum(1 for _, c in cs if c['origin'] == 'research' and c['grade'])}） |")
    w(f"| 　前端舊引文（web-json） | {sum(1 for _, c in cs if c['origin'] == 'web-json')}（A {sum(1 for _, c in cs if c['origin'] == 'web-json' and c['grade'])}） |")
    w(f"| 　quote 超過 {QUOTE_MAX} 字 | {sum(1 for _, c in cs if c['quote_len'] > QUOTE_MAX)} |")
    w(f"| 　缺 accessed_on | {sum(1 for _, c in cs if not c['accessed_on'])} |")
    w(f'| 階段 | {len(ph)} |')
    for k in ('front', 'arrow', 'site'):
        w(f"| 圖形 {k}（已配階段） | {sum(1 for x in fs if x['feature_kind'] == k)} |")
    w(f"| 圖形 deferred（P6 不配圖） | {len(seed['deferred']['features'])} |")
    w(f"| geom_basis＝derived（推估幾何，pending） | {sum(1 for x in fs + seed['deferred']['features'] if x['geom_basis'] == 'derived')} |")
    w(f"| 無任何 citation 的圖形 | {sum(1 for x in fs + seed['deferred']['features'] if not x['citations'])} |")
    w(f"| 來源（sources） | {len(seed['sources'])}（publisher 已填） |")
    w('')
    w('## 戰役主體（historical_events＋battle_profiles）')
    w('')
    w('| 欄位 | 值 | citation（A／全部） | 狀態 |')
    w('|---|---|---|---|')
    e = seed['event']

    def n(c):
        return f"{sum(1 for x in c if x['grade'])}／{len(c)}"

    w(f"| event_kind | {e['event_kind']} | — | 憲法 §6 三條件皆有 A 級出處 |")
    w(f"| occurred | {e['occurred']['start']}～{e['occurred']['end']}（半開；含終點 {e['occurred_end_inclusive']}） | {n(e['citations'])} | pending（符合 verified 門檻：{'是' if e['eligible_for_verified'] else '否'}） |")
    for p in seed['participants']:
        until = f"（至 {p['until_exclusive']}，半開）" if p.get('until_exclusive') else ''
        w(f"| 交戰方 {p['regime_slug']}{until} | {p['side_camp_hint']} | {n(p['citations'])} | pending |")
    w(f"| name | {pr['name']['zh-Hant']} / {pr['name']['en']} | 0／0 | pending（{pr['name_note']}） |")
    w(f"| objective | {pr['objective']['zh-Hant']} | {n(pr['citations']['objective'])} | pending |")
    w(f"| objective_kind | null（候選 {pr['objective_kind_candidate']}） | — | 待人確認；NOT NULL，未決前不能寫庫 |")
    w(f"| control_change | {pr['control_change']['zh-Hant']} | {n(pr['citations']['control_change'])} | pending |")
    w(f"| 範圍（文字） | {pr['area_text']['zh-Hant']} | {n(pr['citations']['theater_area'])} | pending |")
    w('| theater_area（幾何） | 前端 bounds 外框 | 無（derived） | 待依出處圖重畫 |')
    w('| outcome_kind／outcome_text | null | 無 | 沒有出處就留 NULL |')
    for s in seed['sub_events']:
        w(f"| 子事件 {s['name']['zh-Hant']}（{s['name']['en']}） | {s['occurred']['start']}～{s['occurred']['end']}（半開），parent＝本戰役 | {n(s['citations'])} | pending；event_kind 待決 |")
    w('')
    w('## 階段（battle_phases）')
    w('')
    w('| seq | 名稱 | 期間（半開） | 精度 | citation（A／全部） | 出處圖 | 圖形數 | 狀態 |')
    w('|---|---|---|---|---|---|---|---|')
    for p in ph:
        cnt = sum(1 for x in fs if x['phase_seq'] == p['seq'])
        maps = '；'.join(re.sub(r'（.*?）', '', m) for m in p['source_maps']) or f"**pending**（{p['map_note'] or '無'}）"
        w(f"| P{p['seq']} | {p['name']['zh-Hant']} | {p['period']['start']}～{p['period']['end']} | day | {n(p['citations'])} | {maps} | {cnt} | pending（門檻：{'是' if p['eligible_for_verified'] else '否'}） |")
    w('')
    w('## 圖形（battle_map_features）')
    w('')
    w('| feature_key | 前端舊段→新段 | 種類 | 配色組 | geom_basis | citation（A／全部） | 部隊番號 | 狀態 |')
    w('|---|---|---|---|---|---|---|---|')
    for x in fs + seed['deferred']['features']:
        tgt = f"P{x['phase_seq']}" if x['phase_seq'] else '不配（deferred）'
        unit = f"{x['props']['unit']}（待查證）" if x['props'].get('unit') else '—'
        w(f"| {x['feature_key']} | P{x['web_phase']}→{tgt} | {x['feature_kind']} | {x['side_camp']} | {x['geom_basis']} | {n(x['citations'])} | {unit} | pending{'；**缺出處**' if not x['citations'] else ''} |")
    w('')
    w('## pending 引文明細')
    w('')
    if pend:
        w('| 所屬 | 引文（前 60 字） | 原因 |')
        w('|---|---|---|')
        for o, c in pend:
            q = c['quote'][:60].replace('|', '\\|')
            w(f"| {o} | {q}{'…' if len(c['quote']) > 60 else ''} | {c.get('pending_reason')} |")
    else:
        w('無。')
    w('')
    w('## 截成逐字子句的引文')
    w('')
    for o, c in cs:
        if c.get('truncated_from'):
            w(f"- {o}：「{c['quote']}」（{c['locator']}；原 {len(c['truncated_from'])} 字）")
    w('')
    w('## 來源與註記')
    w('')
    for s in seed['sources']:
        w(f"- `{s['key']}`（{s['source_kind']}，{s['grade']}）：{s['title']}；publisher＝{s['publisher']}。")
        if s.get('publication_year_conflict'):
            w(f"  - 出版年分歧：{' vs '.join(s['publication_year_conflict']['values'])}——{s['publication_year_conflict']['note']}")
    t = seed['deferred']['totals']
    if t:
        w(f"- 撤出人數 {t.get('evacuated_dynamo'):,}：{t['perspective']}；{t['note']}。")
    w(f"- 部隊番號（箭頭文字，保留在 props，verification＝pending，未建 battle_units）：{'；'.join(seed['unit_candidates'])}")
    w('')
    w('## 缺口（→ C3 event_gaps）')
    w('')
    for gp in seed['gaps']:
        w(f"- `{gp['target']}`（{gp['kind']}）：{gp['note']}")
    w('')
    w('## 入庫前還差什麼（blocking）')
    w('')
    w('1. Tai 核准寫庫與 verified 判定（本 seed 全部 pending）。')
    w('2. `objective_kind`（NOT NULL）：候選 place，需人確認。')
    w('3. 子事件「發電機行動」的 event_kind：值域沒有 operation，需決定（或擴值域）。')
    w('4. 戰役名稱的 A／B 出處（Ellis、Ramsay 均未用 “Battle of Dunkirk”）。')
    w('5. 參戰 regime 是否已在開發庫（united-kingdom、french-third-republic、kingdom-of-belgium、deutsches-reich）與比利時 until 的寫法（event_participants 無期間欄，需決定）。')
    w('6. 圖形：derived 幾何需依 Ellis situation map 重畫才能 verified；P3、P6 無圖形；Bergues、Malo-les-Bains 無出處；部隊番號待查證。')
    w('7. Ellis 出版年 1953／1954 分歧待核對；theater_area 待依出處圖重畫。')
    w('')
    return '\n'.join(L)


def dump(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2) + '\n'


def main(argv):
    raw_dir = RAW_DEFAULT
    if argv[:1] == ['--raw']:
        raw_dir, argv = Path(argv[1]).resolve(), argv[2:]
    raw = Raw(raw_dir)
    for key in argv or ['dunkirk_1940']:
        wpath, rpath = WEB / f'{key}.json', OUT / f'{key}.research.json'
        wb, rb = wpath.read_bytes(), rpath.read_bytes()
        web, res = json.loads(wb), json.loads(rb)
        if web.get('schema') != 'wl-campaign-web/0.1':
            sys.exit(f'{wpath}: schema 不是 wl-campaign-web/0.1')
        if not str(res.get('schema', '')).startswith('dynamo-research/0.1'):
            sys.exit(f'{rpath}: schema 不是 dynamo-research/0.1')
        seed = convert(web, res, raw)
        seed['generated_from']['web']['sha256'] = hashlib.sha256(wb).hexdigest()
        seed['generated_from']['research']['sha256'] = hashlib.sha256(rb).hexdigest()
        seed['generated_from']['raw_sha256'] = {k: raw.sha.get(k) for k in seed.pop('_raw_used')}
        (OUT / f'{key}.seed.json').write_text(dump(seed), encoding='utf-8')
        (OUT / f'{key}.dry-run.md').write_text(report(seed), encoding='utf-8')
        print(f'wrote data/seed/battles/{key}.seed.json, {key}.dry-run.md')


if __name__ == '__main__':
    main(sys.argv[1:])
