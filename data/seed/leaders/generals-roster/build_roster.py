#!/usr/bin/env python3
"""WWI/WWII generals roster builder (index only). Python 3 stdlib.

只讀維基「列表頁／分類頁」做索引（不是出處）；不抓個人傳記頁。
重跑：python3 data/seed/leaders/generals-roster/build_roster.py   （有 cache 時不會再打 API，排序固定）
產出：roster.json、index_pages.json、SUMMARY.md
"""
import json, re, sys, unicodedata, urllib.parse, collections, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import wikilib as W
import parse_cmdlist as CMDLIST

HERE = W.HERE
ROOT = HERE.parents[3]
BIOS_TSV = ROOT / 'data/seed/leaders/b3-trial/full/pool-snapshot.tsv'
OLD_TSV = ROOT / 'data/seed/leaders/gap-830/existing_bios.tsv'

# ---------------------------------------------------------------- sources
D = dict  # shorthand
# scoped=True：列表／分類本身已限定 1908–1945 相關（WWI/WWII 分類或明確的將級頁）；False＝時期未限定（window_status=unverified）
S = []
def cat(title, country, branch='unknown', rank='待查證', war='待查證', scoped=False, regime=None, lang='en', subs=None, **kw):
    S.append(D(type='cat', lang=lang, title=title, country=country, branch=branch, rank=rank, war=war,
               scoped=scoped, regime=regime, subs=subs, **kw))
def zhlist(title, country, branch='army', rank='待查證', war='待查證', scoped=True, rules=None, regime=None, url=None, lang='zh', **kw):
    S.append(D(type='zhlist', lang=lang, title=title, country=country, branch=branch, rank=rank, war=war,
               scoped=scoped, regime=regime, rules=rules or [], url=url, **kw))

DE, UK, FR, IT, US, JP = '德國', '英國', '法國', '義大利', '美國', '日本'
KMT, BEI, CCP = '中華民國-國民政府', '中華民國-北洋', '中國共產黨'
RU, SU, AH = '俄羅斯帝國', '蘇聯', '奧匈帝國'
EMP, NAZI, WEI = '德意志帝國', '納粹德國', '威瑪共和國'

# --- 德國
zhlist('德国大将', DE, rank='大將', url='https://zh.wikipedia.org/zh-tw/%E5%BE%B7%E5%9B%BD%E5%A4%A7%E5%B0%86', plain=True, rules=[
    (r'奧匈|奥匈', D(country=AH, regime=None, war='待查證')),
    (r'德意志帝國|德意志帝国', D(country=DE, regime=EMP, war='WWI')),
    (r'威瑪|魏玛', D(country=DE, regime=WEI, war='待查證')),
    (r'納粹|纳粹', D(country=DE, regime=NAZI, war='WWII')),
    (r'陆军大将|陸軍大將', D(branch='army')), (r'海军大将|海軍大將', D(branch='navy')), (r'空军大将|空軍大將', D(branch='air_force')),
    (r'警察大将|警察大將', D(branch='unknown')), (r'党卫军|黨衛軍', D(branch='unknown')),
    (r'東德|东德', None)])
zhlist('德国陆军元帅列表', DE, rank='元帥', min_promo_year=1895, rules=[
    (r'選侯國|选侯国|勃兰登堡|勃蘭登堡', None),
    (r'德意志帝国|德意志帝國', D(regime=EMP, war='WWI')),
    (r'納粹|纳粹', D(regime=NAZI, war='WWII'))])
cat('Category:German Army generals of World War I', DE, 'army', war='WWI', scoped=True, regime=EMP)
cat('Category:German Army generals of World War II', DE, 'army', war='WWII', scoped=True, regime=NAZI)
cat('Category:Luftwaffe World War II generals', DE, 'air_force', war='WWII', scoped=True, regime=NAZI)
cat('Category:Kriegsmarine admirals', DE, 'navy', war='WWII', scoped=True, regime=NAZI, expand_subs=r'.')
cat('Category:Field marshals of Nazi Germany', DE, 'army', '元帥', 'WWII', True, regime=NAZI)
# --- 英國
cat('Category:British Army generals of World War I', UK, 'army', war='WWI', scoped=True)
cat('Category:British Army generals of World War II', UK, 'army', war='WWII', scoped=True)
cat('Category:Royal Navy admirals of World War I', UK, 'navy', war='WWI', scoped=True)
cat('Category:Royal Navy admirals of World War II', UK, 'navy', war='WWII', scoped=True)
cat('Category:Royal Air Force air marshals of World War II', UK, 'air_force', war='WWII', scoped=True)
cat('Category:Royal Air Force air marshals', UK, 'air_force')
# --- 法國
cat('Category:French Army generals of World War I', FR, 'army', war='WWI', scoped=True)
cat('Category:French Army generals of World War II', FR, 'army', war='WWII', scoped=True)
cat('Category:French Navy admirals', FR, 'navy')
# --- 義大利
zhlist('意大利陆军元帅', IT, rank='元帥', rules=[])
cat('Category:Field marshals of Italy', IT, 'army', '元帥')
cat('Category:Italian Army generals', IT, 'army')
cat('Category:Italian Air Force generals', IT, 'air_force')
cat('Category:Italian admirals', IT, 'navy')
cat('Category:Italian generals', IT, 'army')
# --- 美國
cat('Category:United States Army generals of World War I', US, 'army', war='WWI', scoped=True)
cat('Category:United States Army generals of World War II', US, 'army', war='WWII', scoped=True)
cat('Category:United States Army Air Forces generals', US, 'air_force', war='WWII', scoped=True)
cat('Category:United States Navy World War I admirals', US, 'navy', war='WWI', scoped=True)
cat('Category:United States Navy World War II admirals', US, 'navy', war='WWII', scoped=True)
cat('Category:美国五星上将', US, 'unknown', '五星上將', 'WWII', True, lang='zh')
cat('Category:美国陆军五星上将', US, 'army', '五星上將', 'WWII', True, lang='zh')
# --- 日本
zhlist('日本陆军大将列表', JP, rank='大將', rules=[(r'参见|參見', None)])
zhlist('日本元帅', JP, rank='元帥', rules=[(r'海軍|海军', D(branch='navy')), (r'陸軍|陆军', D(branch='army')), (r'註解|注解', None)])
cat('Category:Imperial Japanese Navy admirals', JP, 'navy', expand_subs=r'.')
cat('Category:Japanese generals', JP, 'army')
cat('Category:Marshals of Japan', JP, 'unknown', '元帥')
# --- 中國
cat('Category:中華民國陸軍一級上將', KMT, 'army', '一級上將', lang='zh')
cat('Category:国民革命军将领', KMT, 'army', lang='zh')
cat('Category:中国远征军将领', KMT, 'army', war='WWII', scoped=True, lang='zh')
cat('Category:National Revolutionary Army generals', KMT, 'army', expand_subs=r'from |Expeditionary')
cat('Category:Republic of China Army generals', KMT, 'army')
cat('Category:Warlords from the Republic of China (1912–1949)', BEI, 'army', regime='軍閥分類（政權歸屬未核）')
cat('Category:Beiyang Army personnel', BEI, 'army')
cat('Category:中华人民共和国元帅', CCP, 'army', '元帥', lang='zh')
cat('Category:中国人民解放军大将', CCP, 'army', '大將', lang='zh')
cat('Category:八路军将领', CCP, 'army', war='WWII', scoped=True, lang='zh')
cat('Category:新四军将领', CCP, 'army', war='WWII', scoped=True, lang='zh')
# --- 俄／蘇
zhlist('苏联元帅', SU, rank='元帥', rules=[(r'^列表$', D()), (r'.', None)], default_skip=True)
cat('Category:Marshals of the Soviet Union', SU, 'army', '元帥', expand_subs=r'branch')
cat('Category:Soviet admirals', SU, 'navy', expand_subs=r'Admirals of the Fleet|vice admirals')
cat('Category:Imperial Russian Army generals', RU, 'army', expand_subs=r'Generals of the')
cat('Category:Imperial Russian Navy admirals', RU, 'navy')
# --- 奧匈
cat('Category:Austro-Hungarian generals', AH, 'army')
cat('Category:Austro-Hungarian admirals', AH, 'navy')
# --- 宜做
cat('Category:Ottoman Army generals', '鄂圖曼帝國', 'army')
cat('Category:Polish generals of the Second Polish Republic', '波蘭', 'army')
cat('Category:Polish Air Force generals', '波蘭', 'air_force')
cat('Category:Romanian generals', '羅馬尼亞', 'army')
cat('Category:Romanian Army World War I generals', '羅馬尼亞', 'army', war='WWI', scoped=True)
cat('Category:Romanian Air Force generals', '羅馬尼亞', 'air_force')
cat('Category:Finnish generals', '芬蘭', 'army', expand_subs=r'.')
cat('Category:Canadian generals', '加拿大', 'army')
cat('Category:Australian generals', '澳洲', 'army')

# --- 補漏：元帥／艦隊司令常被放在將領分類的子分類或獨立名單，不會出現在 "generals of WWI/WWII" 直屬成員裡
# 英國（蒙哥馬利、黑格、基奇納、斯利姆、艾倫比、亞歷山大等）
cat('Category:British field marshals', UK, 'army', '元帥')
cat('Category:Field marshals of the United Kingdom', UK, 'army', '元帥')
cat('Category:Marshals of the Royal Air Force', UK, 'air_force', '元帥')
cat('Category:Admirals of the Fleet of the Royal Navy', UK, 'navy', '元帥')
cat('Category:Admirals of the Fleet (Royal Navy)', UK, 'navy', '元帥')
cat('Category:Royal Navy admirals of the fleet', UK, 'navy', '元帥')
zhlist('List of British field marshals', UK, rank='元帥', lang='en', scoped=False, rules=[
    (r'Napoleonic|eighteenth|17th|18th|Commonwealth of England|Restoration', None),
])
zhlist('List of field marshals of the British Army', UK, rank='元帥', lang='en', scoped=False, rules=[])
zhlist('英國陸軍元帥列表', UK, rank='元帥', rules=[])
zhlist('Field marshal (United Kingdom)', UK, rank='元帥', lang='en', scoped=False, rules=[
    (r'List of field marshals', D()), (r'Napoleonic|Restoration|Commonwealth', None),
], default_skip=True)
# 德國海軍（提爾皮茨、舍爾 Scheer 不在陸軍大將／陸軍將領分類）
cat('Category:Imperial German Navy admirals', DE, 'navy', regime=EMP, expand_subs=r'.')
cat('Category:German admirals of World War I', DE, 'navy', war='WWI', scoped=True, regime=EMP)
cat('Category:Grand admirals of Germany', DE, 'navy', '元帥')
cat('Category:Grand admirals of the German Empire', DE, 'navy', '元帥', war='WWI', scoped=True, regime=EMP)
zhlist('德國海軍元帥', DE, branch='navy', rank='元帥', rules=[])
zhlist('德意志帝国海军将领', DE, branch='navy', rules=[])
# 義大利空軍元帥（巴爾博）
cat('Category:Marshals of Italy', IT, 'unknown', '元帥')
cat('Category:Marshals of the Air of Italy', IT, 'air_force', '元帥')
cat('Category:Italian Air Force marshals', IT, 'air_force', '元帥')
zhlist('意大利元帅', IT, rank='元帥', rules=[(r'空軍|空军|空軍元帥', D(branch='air_force')), (r'陸軍|陆军', D(branch='army'))])
# 波蘭元帥（畢蘇斯基）
cat('Category:Marshals of Poland', '波蘭', 'army', '元帥')
cat('Category:Polish field marshals', '波蘭', 'army', '元帥')
# 奧匈：康拉德若只出現在德國「外國榮譽元帥」名單，另外再從奧匈分類收
cat('Category:Chiefs of the General Staff of the Austro-Hungarian Army', AH, 'army')

# Tai 22:51：第二次世界大戰各國指揮官列表（只當索引）。頁上各國將領至少 A，最高軍階（元帥／五星／特級上將）升 S。
S.append(D(type='cmdlist', lang='zh', title='第二次世界大戰各國指揮官列表',
           url='https://zh.wikipedia.org/zh-tw/%E7%AC%AC%E4%BA%8C%E6%AC%A1%E4%B8%96%E7%95%8C%E5%A4%A7%E6%88%B0%E5%90%84%E5%9C%8B%E6%8C%87%E6%8F%AE%E5%AE%98%E5%88%97%E8%A1%A8',
           war='WWII', scoped=True, country=None, branch='unknown', rank='待查證'))


RANK_ORDER = {'待查證': 0, '將官': 1, '一級上將': 4, '上將': 3, '大將': 4, '元帥': 6, '五星上將': 6}
EXCLUDE_NAMES = {  # 純政治／非將級（索引誤入者）；例：邱吉爾、希特勒、墨索里尼不進本名單
    'winstonchurchill', 'adolfhitler', 'benitomussolini', 'heinrichhimmler', 'josephgoebbels', 'reinhardheydrich', 'josephstalin'}
# 德國／日本元帥名單上的外國君主或榮譽授予（不當該國將領；若另有本國分類仍可從那邊進入）
HONORARY_FOREIGN = {
    'constantineiofgreece', 'ferdinandiofbulgaria', 'franzjosephi', 'franzjosephiofaustria',
    'georgev', 'mehmedv', 'louisiiiofmonaco', 'louisiiofmonaco', 'nicholasii', 'nicholasiiiofrussia',
}
HONORARY_NAME = re.compile(r'\bof (Greece|Bulgaria|Monaco|the United Kingdom)\b', re.I)
# 國籍覆寫（索引第一個來源不一定是其主要身分）
COUNTRY_OVERRIDE = {
    'carlgustafemilmannerheim': '芬蘭',
    'zhude': '中國共產黨',
    'pengdehuai': '中國共產黨',
    'linbiao': '中國共產黨',
    'franzconradvonhotzendorf': '奧匈帝國',
}
# Tai 22:51：S+A 若超過 280，不自動降級；停下游生平、先回報重估。
NON_PERSON = re.compile(r'^(List of|Lists of|Template:|Category:)|^(Generalleutnant|Generalmajor|Generaloberst)$')
SKIP_HEAD = re.compile(r'參見|参见|參考|参考|註解|注释|注解|相關|相关|外部|資料來源|来源|歷史|出身|制服|概要|腳註|脚注')
NS = re.compile(r'^(file|image|category|檔案|文件|文件|分類|分类|圖像|图像|template|模板|wikipedia|help|special|媒體|media)\s*:', re.I)

# ---------------------------------------------------------------- helpers
def norm(s):
    s = unicodedata.normalize('NFKD', s or '')
    s = ''.join(c for c in s if not unicodedata.combining(c)).lower()
    return ''.join(c for c in s if c.isalnum())

def en_clean(t):
    return re.sub(r'\s*\([^)]*\)\s*$', '', t or '').strip() or None

def key_name(s):  # tier key：去重音／忽略逗號後稱號與 Sir/Lord 前綴
    s = re.sub(r',.*$', '', s or '')
    s = re.sub(r'^(sir|lord|the)\s+', '', s, flags=re.I)
    return norm(s)

# 簡繁常見字（僅供合併／比對，不是譯名校正）
_S2T = str.maketrans('蒋东门马冯龙国军陈卢刘历亚尔罗诺纳伦贝帅级将齐经线战从会为与于后发对开关顿韦维纪铁齐钟赵吴郑沈韩邓萧谢苏顾潘戴薛阎余傅卫龙龚蓝齐鲁晋陕赣粤琼岛门车马鱼鸟齐怀张杨黄应乐当号广'+'餘',
                     '蔣東門馬馮龍國軍陳盧劉歷亞爾羅諾納倫貝帥級將齊經線戰從會為與於後發對開關頓韋維紀鐵齊鐘趙吳鄭沈韓鄧蕭謝蘇顧潘戴薛閻余傅衛龍龔藍齊魯晉陝贛粵瓊島門車馬魚鳥齊懷張楊黃應樂當號廣'+'餘')
PEER_RE = re.compile(r',\s*\d+(st|nd|rd|th)\s+(Earl|Viscount|Baron|Barony|Marquess|Duke|Count|Prince|Baronet)\b.*$', re.I)

def zh_key(s):
    return norm((s or '').translate(_S2T))

def merge_key_en(s):
    s = PEER_RE.sub('', s or '')
    s = re.sub(r'^(sir|lord|the)\s+', '', s, flags=re.I)
    return norm(s)

def person_key(nm_en, nm_zh):
    ce = merge_key_en(nm_en) if nm_en else ''
    if ce:
        ce = ALIASES.get(ce, ce)
        return 'en:' + ce
    cz = zh_key(nm_zh)
    return ('zh:' + cz) if cz else ''

def wikiurl(lang, title, path=None):
    return f'https://{lang}.wikipedia.org/wiki/' + urllib.parse.quote(title.replace(' ', '_'))

def strip_markup(s):
    s = re.sub(r'<!--.*?-->', '', s, flags=re.S)
    s = re.sub(r'<ref[^>/]*/>', '', s)
    s = re.sub(r'<ref[^>]*>.*?</ref>', '', s, flags=re.S)
    return s

def parse_zhlist(wt, src):
    """回傳 [(name_target, display, branch/regime overrides dict, years)]"""
    wt = strip_markup(wt)
    rules = [(re.compile(p), v) for p, v in src['rules']]
    out = []; cur = {}; skip = False
    recs = []
    row = []
    def flush():
        nonlocal row
        if row: recs.append((cur.copy(), skip, ' '.join(row))); row = []
    for line in wt.split('\n'):
        m = re.match(r'^(=+)\s*(.+?)\s*\1\s*$', line)
        if m:
            flush()
            h = m.group(2)
            matched = False
            for pat, v in rules:
                if pat.search(h):
                    matched = True
                    if v is None: skip = True
                    else: skip = False; cur.update(v)
                    break
            if not matched and SKIP_HEAD.search(h): skip = True
            elif not matched and src.get('default_skip'): skip = True
            elif not matched: skip = skip if False else skip  # inherit
            continue
        s = line.strip()
        if s.startswith('{|') or s.startswith('|}'): flush(); continue
        if s.startswith('|-'): flush(); continue
        if re.match(r'^[#*]', s):
            flush(); recs.append((cur.copy(), skip, s)); continue
        if s.startswith('|') or s.startswith('!'):
            row.append(s)
    flush()
    for ov, sk, text in recs:
        if sk: continue
        body = re.sub(r'\{\{(?:legend|Legend)[^}]*\}\}', '', text)
        m = None
        for mm in re.finditer(r'\[\[([^\]|#]+)(?:\|([^\]]*))?\]\]', body):
            tgt = mm.group(1).strip()
            if NS.match(tgt) or re.match(r'^\d', tgt): continue
            m = mm; break
        years = re.search(r'(\d{4})\s*[–\-－—~～]\s*(\d{4})', body)
        pm = re.match(r'^[#*\s]*(\d{4})年', body)
        if m:
            out.append((m.group(1).strip(), (m.group(2) or m.group(1)).strip(), ov, years.groups() if years else None, int(pm.group(1)) if pm else None))
        elif src.get('plain') and text.startswith('#'):
            nm = re.split(r'[（(]', re.sub(r'^[#*\s]+', '', text))[0].strip()
            if nm and len(nm) < 40: out.append((nm, nm, ov, years.groups() if years else None, None))
    return out

def resolve_zh(titles):
    """zh 標題 → (canonical zh, en title|None, found)。只用頁面標題／langlink 元資料。"""
    res = {}
    titles = sorted(set(titles))
    for i in range(0, len(titles), 50):
        chunk = titles[i:i + 50]
        def fn(chunk=chunk):
            st, d, err = W.api('zh', action='query', titles='|'.join(chunk), redirects=1, prop='langlinks', lllang='en', lllimit=500)
            if not d or 'query' not in d: return dict(ok=False, error=err or 'no query')
            q = d['query']
            m = {}
            for r in q.get('normalized', []) + q.get('redirects', []): m.setdefault(r['from'], r['to'])
            pages = {p['title']: [p.get('missing', False), (p.get('langlinks') or [{}])[0].get('title')] for p in q.get('pages', [])}
            return dict(ok=True, map=m, pages=pages)
        r = W.cached('res', 'zh', '|'.join(chunk), fn)
        if not r.get('ok'):
            for t in chunk: res[t] = (t, None, False)
            continue
        for t in chunk:
            c = t
            for _ in range(3): c = r['map'].get(c, c)
            pg = r['pages'].get(c)
            res[t] = (c, pg[1] if pg else None, bool(pg and not pg[0]))
    return res

def load_bios():
    idx = []
    for f in (BIOS_TSV,):
        for line in f.read_text(encoding='utf-8').splitlines():
            p = line.split('\t')
            if len(p) >= 3: idx.append((p[0], p[1], p[2]))
    return idx

ALIASES = {  # 別名 → 庫內常用名（僅供 in_leader_bios 比對；不確定者在 SUMMARY 註明）
    '蔣介石': '蔣中正', '蒋介石': '蒋中正', 'tojohideki': '東條英機', 'hidekitojo': '東條英機',
    '东条英机': '東條英機', '曼納海姆': '曼納海姆', 'carlgustafmannerheim': 'carlgustafemilmannerheim',
    'chiangkaishek': 'jiangzhongzheng', '蔣介石': '蔣中正', '蒋介石': '蔣中正',
    'louismountbatten': 'mountbatten', 'lordmountbatten': 'mountbatten'}

# ---------------------------------------------------------------- main
def main():
    index_pages = []
    recs = []   # raw records: dict(name_en, name_zh, src_idx, ...)
    # 展開子分類
    expanded = []
    for s in S:
        expanded.append(s)
        if s.get('expand_subs'):
            def fn(s=s):
                st, d, err = W.api(s['lang'], action='query', list='categorymembers', cmtitle=s['title'], cmtype='subcat', cmlimit=100)
                if not d or 'query' not in d: return dict(ok=False, error=err)
                return dict(ok=True, subs=[m['title'] for m in d['query']['categorymembers']])
            r = W.cached('subs', s['lang'], s['title'], fn)
            for t in (r.get('subs') or []):
                if re.search(s['expand_subs'], t):
                    c = dict(s); c.update(title=t, expand_subs=None, parent=s['title']); expanded.append(c)
    seen_titles = set(); sources = []
    for s in expanded:
        k = (s['lang'], s['title'])
        if k in seen_titles: continue
        seen_titles.add(k); sources.append(s)

    zh_pending = []
    for si, s in enumerate(sources):
        ent = dict(url=s.get('url') or wikiurl(s['lang'], s['title']), title=s['title'], lang=s['lang'], kind=s['type'],
                   country=s['country'], regime=s.get('regime'), branch=s['branch'], rank_class=s['rank'], parent=s.get('parent'))
        if s['type'] == 'cmdlist':
            r = W.wikitext(s['lang'], s['title'])
            ent.update(http_status=r.get('status'), fetched_at=r.get('fetched'), ok=bool(r.get('ok')), failure=r.get('error'),
                       fetched_via='MediaWiki API action=parse (wikitext); 姓名欄＋{{tsl}}，戰役欄不收入')
            if r.get('ok'):
                rows = CMDLIST.parse_cmdlist(r['wikitext'])
                ent['extracted'] = len(rows)
                for row in rows:
                    recs.append(dict(si=si, zh_target=row['tgt'], zh_disp=row['zh'] or row['tgt'],
                                     en=row['en'], zh=row['zh'],
                                     ov=dict(country=row['country'], branch=row['branch'],
                                             rank=row['rank'], min_tier=row['min_tier'],
                                             war=s.get('war','WWII'), scoped=True),
                                     years=None, promo=None))
                    zh_pending.append(row['tgt'])
        elif s['type'] == 'zhlist':
            r = W.wikitext(s['lang'], s['title'])
            ent.update(http_status=r.get('status'), fetched_at=r.get('fetched'), ok=bool(r.get('ok')), failure=r.get('error'), fetched_via='MediaWiki API action=parse (wikitext)')
            if r.get('ok'):
                rows = parse_zhlist(r['wikitext'], s)
                ent['extracted'] = len(rows)
                for tgt, disp, ov, years, promo in rows:
                    if s['lang'] == 'en':
                        recs.append(dict(si=si, en=tgt, zh=None, ov=ov, years=years, promo=promo))
                    else:
                        recs.append(dict(si=si, zh_target=tgt, zh_disp=disp, ov=ov, years=years, promo=promo)); zh_pending.append(tgt)
        else:
            r = W.catmembers(s['lang'], s['title'])
            ent.update(http_status=r.get('status'), fetched_at=r.get('fetched'), ok=bool(r.get('ok')), failure=r.get('error'), fetched_via='MediaWiki API generator=categorymembers (+langlinks lllang=zh)' if s['lang'] == 'en' else 'MediaWiki API generator=categorymembers')
            if r.get('ok'):
                ent['extracted'] = len(r['members'])
                for title, zh in r['members']:
                    if s['lang'] == 'en': recs.append(dict(si=si, en=title, zh=zh))
                    else: recs.append(dict(si=si, zh_target=title, zh_disp=title, ov={}, years=None, promo=None)); zh_pending.append(title)
        index_pages.append(ent)

    res = resolve_zh(zh_pending)
    # ---- 合併
    people = {}     # key -> dict
    by_zh = {}      # zh canonical -> key
    excluded = collections.Counter(); excl_ex = collections.defaultdict(list)
    def excl(reason, name):
        excluded[reason] += 1
        if len(excl_ex[reason]) < 6: excl_ex[reason].append(name)
    for r in recs:
        s = sources[r['si']]; ov = r.get('ov') or {}
        if 'en' in r:
            en_t, zh_t = r['en'], r['zh']
        else:
            c, en_t, found = res.get(r['zh_target'], (r['zh_target'], None, False))
            zh_t = c if found else r['zh_disp']
        if en_t and NON_PERSON.search(en_t): excl('非人物頁（List／Template）', en_t); continue
        nm_en = en_clean(en_t); nm_zh = en_clean(zh_t) if zh_t else None
        if r.get('years') and int(r['years'][1]) < 1908: excl('列表所見卒年早於 1908', nm_zh or nm_en); continue
        if r.get('promo') and s.get('min_promo_year') and r['promo'] < s['min_promo_year'] and ov.get('regime', s.get('regime')) in (EMP,):
            excl('晉升年早於 1895 之普魯士／帝國元帥（窗外）', nm_zh or nm_en); continue
        if norm(nm_en or '') in EXCLUDE_NAMES or norm(nm_zh or '') in {'邱吉爾', '丘吉爾', '希特勒', '墨索里尼', '溫斯頓邱吉爾', '温斯顿·丘吉尔'}:
            excl('純政治人物', nm_en or nm_zh); continue
        if (norm(nm_en or '') in HONORARY_FOREIGN or (nm_en and HONORARY_NAME.search(nm_en))) and s['country'] in (DE, JP, '日本'):
            excl('外國君主／榮譽元帥（不當該國將領）', nm_en or nm_zh); continue
        k = person_key(nm_en, nm_zh)
        if not k: continue
        if k not in people and nm_zh and zh_key(nm_zh) and by_zh.get('zh:' + zh_key(nm_zh)):
            k = by_zh['zh:' + zh_key(nm_zh)]
        p = people.setdefault(k, dict(name_en=None, name_zh=None, srcs=[]))
        if nm_en and not p['name_en']: p['name_en'] = nm_en
        if nm_zh and not p['name_zh']: p['name_zh'] = nm_zh
        if nm_zh and zh_key(nm_zh): by_zh.setdefault('zh:' + zh_key(nm_zh), k)
        p['srcs'].append((r['si'], ov))
    # ---- 欄位彙整
    bios = load_bios()
    bidx = collections.defaultdict(list)
    for bid, n, z in bios:
        for x in (n, z):
            if x:
                bidx[norm(x)].append(bid)
                bidx[merge_key_en(x)].append(bid)
                bidx[zh_key(x)].append(bid)
                ax = ALIASES.get(x) or ALIASES.get(norm(x))
                if ax:
                    bidx[norm(ax)].append(bid); bidx[zh_key(ax)].append(bid)
    tiers = json.loads((HERE / 'fame_tiers.json').read_text())
    tmap = {}
    for t in ('S', 'A'):
        for n in tiers[t]: tmap.setdefault(key_name(n), t)
    used_tier = set()
    out = []
    for k, p in people.items():
        srcs = [(sources[si], ov) for si, ov in sorted(p['srcs'], key=lambda x: (x[0], json.dumps(x[1], sort_keys=True)))]
        first, fov = srcs[0]
        country = fov.get('country', first['country'])
        countries = [ov.get('country', s['country']) for s, ov in srcs]
        cmd_countries = [ov.get('country') for s, ov in srcs if s.get('type')=='cmdlist' and ov.get('country')]
        if cmd_countries:
            country = cmd_countries[0]
        # 若同時出現在本國分類與德國／日本榮譽元帥名單，採本國
        if country in (DE, JP, '日本') and any(c not in (DE, JP, '日本') for c in countries):
            country = next(c for c in countries if c not in (DE, JP, '日本'))
        ovkey = key_name(p['name_en'] or '') or key_name(p['name_zh'] or '')
        if ovkey in COUNTRY_OVERRIDE:
            country = COUNTRY_OVERRIDE[ovkey]
        regimes = sorted({(ov.get('regime') or s.get('regime')) for s, ov in srcs if (ov.get('regime') or s.get('regime'))})
        branch = next((ov.get('branch', s['branch']) for s, ov in srcs if ov.get('branch', s['branch']) != 'unknown'), 'unknown')
        rank = max((ov.get('rank', s['rank']) for s, ov in srcs), key=lambda x: RANK_ORDER.get(x, 0))
        wars = {ov.get('war', s['war']) for s, ov in srcs} - {'待查證'}
        war = 'both' if ('both' in wars or {'WWI', 'WWII'} <= wars) else (next(iter(wars)) if wars else '待查證')
        scoped = any(ov.get('scoped', s['scoped']) for s, ov in srcs)
        urls = sorted({(s.get('url') or wikiurl(s['lang'], s['title'])) for s, ov in srcs})
        main_url = (first.get('url') or wikiurl(first['lang'], first['title']))
        other_countries = sorted({ov.get('country', s['country']) for s, ov in srcs} - {country})
        # tier（fame_tiers 與指揮官列表最低級取較高者：S > A > B，不降級）
        tier = 'B'
        page_tiers = [ov.get('min_tier') for s, ov in srcs if ov.get('min_tier') in ('S', 'A')]
        if 'S' in page_tiers: tier = 'S'
        elif 'A' in page_tiers: tier = 'A'
        def hit_tier(nm):
            if not nm: return None
            k = key_name(nm)
            if k in tmap:
                return k, tmap[k]
            # 別名／封號：fame key 的每個 token 都出現在人名裡（避免只對上姓氏）
            nk = norm(nm)
            for fk, tv in tmap.items():
                if len(fk) >= 8 and (fk in nk or nk in fk):
                    return fk, tv
            return None
        for nm in (p['name_en'], p['name_zh']):
            h = hit_tier(nm)
            if h:
                used_tier.add(h[0])
                if h[1] == 'S' or (h[1] == 'A' and tier == 'B'):
                    tier = h[1]
                break
        # bios：有原文名時必須對上原文名（避免「威廉二世」把符騰堡的威廉二世對到德皇）
        bid = None
        cands = []
        def bios_keys(nm, zh=False):
            if not nm: return []
            keys = [norm(nm), merge_key_en(nm) if not zh else zh_key(nm), zh_key(nm) if zh else norm(nm)]
            keys += [norm(ALIASES.get(nm, '')), norm(ALIASES.get(norm(nm), '')), zh_key(ALIASES.get(nm, ''))]
            return [k for k in keys if k]
        for n in bios_keys(p['name_en'], False) + bios_keys(p['name_zh'], True):
            cands += bidx.get(n, [])
        # also index bios names with zh_key / merge_key
        if cands: bid = sorted(set(cands))[0]
        rec = dict(name_zh=p['name_zh'] or '待查證', name_original=p['name_en'], country=country,
                   branch=branch, highest_rank=rank, war=war, fame_tier=tier,
                   in_leader_bios=bid is not None, bio_id=bid, index_url=main_url, index_urls=urls,
                   source_status='index_only', window_status='category_scoped' if scoped else 'unverified')
        if regimes: rec['regime'] = '／'.join(regimes)
        notes = []
        if other_countries: notes.append('另見於：' + '、'.join(other_countries))
        if branch == 'unknown': notes.append('軍種列表未標示')
        if notes: rec['notes'] = '；'.join(notes)
        out.append(rec)
    COUNTRY_ORDER = [DE, UK, FR, IT, US, JP, BEI, KMT, CCP, RU, SU, AH, '鄂圖曼帝國', '波蘭', '羅馬尼亞', '芬蘭', '加拿大', '澳洲',
                     '紐西蘭', '希臘', '荷蘭', '南斯拉夫', '捷克斯洛伐克', '南非', '泰國', '斯洛伐克', '自由印度臨時政府', '緬甸', '瑞士', '烏克蘭反抗軍']
    tr = {'S': 0, 'A': 1, 'B': 2}
    out.sort(key=lambda r: (COUNTRY_ORDER.index(r['country']) if r['country'] in COUNTRY_ORDER else 99, tr[r['fame_tier']], r['name_original'] or '~', r['name_zh']))
    unmatched = sorted({n for t in ('S', 'A') for n in tiers[t] if key_name(n) not in used_tier})

    roster = dict(meta=dict(
        title='WWI/WWII generals roster (index only)', created='2026-11-11（Asia/Taipei）', source_status='index_only',
        disclaimer='維基列表／分類僅作索引，不是出處；未以 A/B 來源查證。fame_tier 為編輯分級，非出處。',
        window='1908-1945', bios_snapshot='data/seed/leaders/b3-trial/full/pool-snapshot.tsv',
        branch_values='英文枚舉 army / navy / air_force / unknown（全檔一致）', name_missing='name_zh 缺時為「待查證」；name_original 缺時為 null',
        window_status_note='category_scoped＝所在分類／列表已限 WWI/WWII 或 1908–1945 將級頁；unverified＝分類時期未限定（可能含窗外人物），war 多為待查證',
        total=len(out)), people=out)
    (HERE / 'roster.json').write_text(json.dumps(roster, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    (HERE / 'index_pages.json').write_text(json.dumps(dict(
        user_agent=W.UA, timezone='Asia/Taipei', pages=index_pages), ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    write_summary(out, index_pages, excluded, excl_ex, unmatched, bios)
    print('people', len(out), 'pages', len(index_pages), 'failed', sum(1 for p in index_pages if not p['ok']))

# ---------------------------------------------------------------- summary
def cost_table(n_s, n_sa, n_all, n_sc):
    base_c = 7.7597 / 15; base_t = 26 / 15
    rows = []
    for label, n in (('只做 S', n_s), ('S + A', n_sa), ('全部（含 unverified）', n_all), ('全部（僅 category_scoped，已排除時期未驗者）', n_sc)):
        main_c = n * base_c * 1.5; lo = n * base_c * 1.3; hi = n * base_c * 1.8
        main_t = n * base_t * 1.5 / 60; tlo = n * base_t * 1.3 / 60; thi = n * base_t * 1.8 / 60
        rows.append(f'| {label} | {n} | ${main_c:,.0f}（${n*base_c:,.0f} 為未加成基準） | ${lo:,.0f}–${hi:,.0f} | 約 {main_t:.1f} 小時（{tlo:.1f}–{thi:.1f}） |')
    return '\n'.join(rows)

def write_summary(out, pages, excluded, excl_ex, unmatched, bios):
    n = len(out)
    cc = collections.Counter(r['country'] for r in out)
    tier = collections.defaultdict(collections.Counter)
    for r in out: tier[r['country']][r['fame_tier']] += 1
    tt = collections.Counter(r['fame_tier'] for r in out)
    inb = sum(r['in_leader_bios'] for r in out)
    nozh = sum(r['name_zh'] == '待查證' for r in out); noen = sum(r['name_original'] is None for r in out)
    unv = sum(r['window_status'] == 'unverified' for r in out)
    warc = collections.Counter(r['war'] for r in out)
    brc = collections.Counter(r['branch'] for r in out)
    ok = [p for p in pages if p['ok']]; bad = [p for p in pages if not p['ok']]
    L = []
    A = L.append
    A('# 一戰／二戰主要參戰國將領名單（roster，僅索引）\n')
    A('產出時間：2026-11-11（Asia/Taipei）。由 `build_roster.py` 產生；本檔、`roster.json`、`index_pages.json` 皆為腳本輸出。\n')
    A('## 1. 方法、限制與聲明\n')
    A('- **維基列表／分類頁只當索引，不是出處。** 每筆 `source_status="index_only"`，未以 A/B 來源查證，不得直接當作生平事實使用。')
    A('- Tai 22:51 增列索引頁 [第二次世界大戰各國指揮官列表](https://zh.wikipedia.org/zh-tw/%E7%AC%AC%E4%BA%8C%E6%AC%A1%E4%B8%96%E7%95%8C%E5%A4%A7%E6%88%B0%E5%90%84%E5%9C%8B%E6%8C%87%E6%8F%AE%E5%AE%98%E5%88%97%E8%A1%A8)：只取「军队指挥官」節之姓名欄（含 {{tsl}} 模板），戰役欄不收入。該頁各國將領至少 A，最高軍階（元帥／五星上將／特級上將等）升 S；與 fame_tiers 取較高者，不降級。純政治人物仍排除。中文維基沒有對應的「第一次世界大戰各國指揮官列表」，一戰未用同類名單頁補（英文 Allied leaders of World War I、Leaders of the Central Powers of World War I 是元首與將領混編，不當對應頁）。')
    A('- 抓取：MediaWiki API（`/w/api.php`），UA `WorldLineGeneralsRoster/0.1 (local research index; not a crawler of article prose)`，限速約 1.2 秒／請求、429 退避重試；未抓任何個人傳記頁，未用 `curl -k`、未登入。')
    A('- 資料來源兩類：(1) zh.wikipedia 列表頁（解析 wikitext 的列表／表格列，取每列第一個人名連結；德國起點 `德国大将` 在內）；(2) 分類頁成員（en 為主、經 langlinks 取中文標題；zh 分類取成員標題）。zh 列表人名再以頁面標題／langlink 元資料解析成英文標題以便合併（只用標題元資料，不讀傳記內文）。')
    A('- 合併鍵：英文標題正規化（去重音、去括號消歧）；僅有中文者用中文標題。同人跨多頁已合併，`index_urls` 列全部。')
    A('- **完整度聲明：本名單是「所採用之列表／分類頁上的將級人物索引」，不是全世界將官普查。** 分類頁對准將／少將不保證完整（例如未採用美國海軍陸戰隊、法國空軍、德國 Waffen-SS 專類、蘇聯一般將官等分類）；不宣稱收齊任何國家的准將／少將。')
    A('- **時期說明：** `window_status=category_scoped`（所在分類／列表已限 WWI/WWII 或 1908–1945 將級頁）共 {} 人；`unverified`（分類時期未限定，例如「Italian generals」「Imperial Russian Army generals」「Royal Air Force air marshals」「Warlords from the Republic of China」）共 {} 人，這些人可能完全在窗外（列表看不出者依規定仍列入，`war` 多為待查證），**進入生平階段前建議先人工篩一遍 unverified**。'.format(n - unv, unv))
    A('- `branch` 使用英文枚舉：army / navy / air_force / unknown（全檔一致；unknown＝列表未標示軍種，含警察／黨衛軍／混合列表）。`highest_rank` 多數分類只能看出「將官」類別，無具體軍階時為「待查證」；有明確頁面軍階的（元帥、大將、一級上將、五星上將）才填。')
    A('- 排除（腳本規則）：')
    for r, c in excluded.most_common(): A(f'  - {r}：{c} 筆（例：{"、".join(x for x in excl_ex[r] if x)}）')
    A('  - 純政治人物以固定清單排除（邱吉爾、希特勒、墨索里尼、希姆萊、戈培爾、海德里希、史達林）；僅在索引上看到才有實際排除。')
    A('  - 窗外判斷只用列表上明示的卒年（< 1908）與德意志帝國元帥列表的晉升年；其餘看不出者仍列入。')
    A('')
    A('### 採用的列表／分類頁（完整明細見 `index_pages.json`）\n')
    A(f'成功 {len(ok)} 頁；失敗 {len(bad)} 頁。\n')
    A('| 頁面 | 語言 | 類型 | 國家／政權 | 軍種 | 取得筆數 |\n|---|---|---|---|---|---|')
    for p in pages:
        A(f"| {'✅' if p['ok'] else '❌'} {p['title']} | {p['lang']} | {p['kind']} | {p['country']} | {p['branch']} | {p.get('extracted', '—')} |")
    if bad:
        A('\n**失敗頁：**')
        for p in bad: A(f"- {p['title']}（{p['lang']}）：HTTP {p['http_status']}；{p['failure']}")
    else:
        A('\n失敗頁：無。')
    A('\n未做／跳過：Waffen-SS 專類、美國海軍陸戰隊、法國空軍、波蘭／加拿大／澳洲／芬蘭等僅採分類頁（未逐子分類展開，除非在上表）；比利時、塞爾維亞、保加利亞等未另建專類；荷蘭、希臘、泰國、加拿大、紐西蘭等若出現在二戰指揮官列表則已收入。zh 德國元帥衍生頁（`德国元帅衔大将`）因列首為頭銜連結、易誤抓，未採用。\n')
    A('## 2. 人數\n')
    A(f'**總人數 {n}**；`in_leader_bios=true` **{inb}** 人（比對快照 924 人：name 或 name_zh 正規化全等＋少量別名；繁簡字差異可能漏判，見第 5 節）。\n')
    A(f'全體：S **{tt["S"]}**／A **{tt["A"]}**／B **{tt["B"]}**，S+A 合計 **{tt["S"]+tt["A"]}**（Tai 22:47／22:51 門檻 280：超過則生平先不跑，重估後再定）。war：' + '、'.join(f'{k} {v}' for k, v in warc.most_common()) + '。branch：' + '、'.join(f'{k} {v}' for k, v in brc.most_common()) + '。\n')
    A('| 國家／政權 | 人數 | S | A | B |\n|---|---|---|---|---|')
    for c, v in sorted(cc.items(), key=lambda x: -x[1]):
        A(f'| {c} | {v} | {tier[c]["S"]} | {tier[c]["A"]} | {tier[c]["B"]} |')
    A(f'| **合計** | **{n}** | {tt["S"]} | {tt["A"]} | {tt["B"]} |')
    A('\n中國三欄：中華民國-北洋、中華民國-國民政府、中國共產黨 分列如上（北洋欄為「Beiyang Army personnel」＋「軍閥」分類，政權歸屬未逐人核實，含後來投入國民政府者；共軍欄僅含元帥、大將與八路軍／新四軍將領分類，未含 1955 年後授銜者的省分類）。\n')
    A('### 分級標準（編輯判斷，非出處）\n')
    A('- **S**：跨國家喻戶曉的將領／艦隊司令／兼元首的將領（手工清單 `fame_tiers.json`，宜精）。\n- **A**：參謀總長、軍種總司令、集團軍／方面軍／戰區司令、艦隊司令、知名戰役主要指揮（手工清單，未達家喻戶曉）。\n- **B**：其餘列表上的將級人物（預設）。\n- 分級只對真實進 roster 者生效；`fame_tiers.json` 中未命中索引者共 {} 個鍵（多為該人不在所採分類或標題寫法不同；不是補人，只是未使用）。'.format(len(unmatched)))
    A('\n## 3. 生平費用與時間估價\n')
    A('依 v3 最低標準（≥3 段、≥300 字、職位要有任期）。**單價採實測**：B3 full batches 001–003（15 人，Sonnet 研究＋Opus 審查，未寫庫）合計 **$7.7597**（`.dev/cc-b3full-b00[123]-*.json` 的 `total_cost_usd` 之和）＝ **約 $0.517／人**；牆上時間約 26 分鐘／15 人 ≈ 1.7 分／人（每批 5 人約 7–11 分鐘；API duration_api_ms 合計約 25.3 分鐘）。')
    A('v3 樣本沒有可用成本數據；v3 因要求更高，**假設**單價為實測的 1.5×（主估 ≈ **$0.78／人、≈ 2.6 分／人**），區間假設 1.3×–1.8×（$0.67–$0.93／人）。以下以既有「5 人一批、Sonnet＋Opus 迴圈」循序執行為前提；若併行則時間可縮短，費用不變。\n')
    A('| 檔位 | 人數 | 主估費用（1.5×） | 區間（1.3×–1.8×） | 牆上時間（主估；區間） |\n|---|---|---|---|---|')
    A(cost_table(tt['S'], tt['S'] + tt['A'], n, n - unv))
    A(f'\n註：「全部」含 {unv} 位 `unverified`（時期未驗）人物；若先人工篩掉窗外者，實際人數與費用會顯著下降。已在庫（`in_leader_bios=true`）{inb} 人若沿用既有生平可免做，上表未扣除。\n')
    A('## 4. 將領入庫 schema 提案（僅提案；未改任何程式、資料或 ARCHITECTURE.md）\n')
    A('### 現況（已對照 repo）')
    A('- `leader_records.role` CHECK 只有 `head_of_state`／`head_of_government`，且必有 `regime_id`：是地圖／時間軸上「誰統治這個政權」的名簿。')
    A('- `leader_bios` 是人物卡生平（約 924 人，幾乎都是元首／首腦）。')
    A('- `person_positions.position_kind` 已含 `military_command`（另有 military_education 等；見 ARCHITECTURE §16.3、`BioParagraphsPositionsRolesTests.cs`）。')
    A('- `person_roles.role_kind` 目前僅 `head_of_state`／`head_of_government`／`de_facto_leader`／`cabinet_minister`；`military_commander` 在 `.dev/person-role-kind.md` 草案列為 P2、ARCHITECTURE §16.3.1／§19.3.2 已訂其收錄條件（G5：國家最高軍職固定清單，或 verified 戰役 `commander`／`staff` 參與），但**尚未進 CHECK**。')
    A('\n| 方案 | 做法 | 優點 | 缺點 |\n|---|---|---|---|')
    A('| **一（建議）** | 不擴大 `leader_records`；生平沿用 `leader_bios`；任期職位用 `person_positions`（`military_command`）；`person_roles.role_kind` 增列 `military_commander`（對齊草案 P2／G5）。已是元首的將領（蔣、曼納海姆、東條）維持一張人物卡、多角色。 | 不碰地圖元首邏輯；與既有三層（人物／角色／經歷）一致；只需一個 CHECK 值＋寫入層 G5 檢查；一人多角色自然成立 | 需先決定 `leader_bios` 是否更名；G5 門檻（固定職位清單）要 Tai 確認，Tier B 將領多半只進「經歷」不出卡 |')
    A('| 二 | 放寬 `leader_records.role` 加入軍職 | 表少、查詢單一 | 該表綁 `regime_id` 並用於「誰在統治這個政權」；戰場指揮官常對不到單一政權列，會污染地圖元首邏輯與既有查詢／測試 |')
    A('| 三 | 新建 `military_commands` 專表 | 軍職欄位可客製（戰區、部隊、軍階） | 與已有 `person_positions.military_command` 重複；遷移與雙寫成本高；與 T11「角色分表」決議重疊 |')
    A('\n**建議方案一。** 門檻沿用草案：國家級最高軍職，或有出處的戰役 participant 連結（G5）；本 roster 的 S／A 即為首批候選，B 級先只做「經歷」層。\n')
    A('## 5. 注意事項\n')
    A(f'- 失敗頁：{len(bad)}（{"；".join(p["title"] for p in bad) if bad else "無"}）。')
    A(f'- 中文名缺失：`name_zh="待查證"` 共 {nozh} 人（en 分類成員無 zh langlink）；`name_original=null` 共 {noen} 人（zh 列表人名無對應 en 連結）。')
    A('- 同名風險：合併靠標題正規化；同英文標題（去括號後）不同人（如多位 John Smith）會被誤併，反之同一人在 zh／en 標題寫法不同可能重複列兩筆。未逐筆查重，建議入庫前以 name_zh＋生卒年人工核對。')
    A('- 別名不確定：`in_leader_bios` 以 name／name_zh 正規化全等＋少量別名（蔣介石→蔣中正、東條英機等）；快照名稱簡繁混用，簡繁字差異（如「蒋／蔣」）可能漏判。抽查：曼納海姆、蔣中正、東條英機應為 true；貝當、戴高樂、孫中山、袁世凱應為 false（見下）。')
    chk = {r['name_zh']: r['in_leader_bios'] for r in out}
    chk_en = {(r['name_original'] or ''): r['in_leader_bios'] for r in out}
    def show(en): return f'{en}={chk_en.get(en, "未在名單")}'
    A('  - 抽查結果：' + '；'.join(show(x) for x in ['Carl Gustaf Emil Mannerheim', 'Chiang Kai-shek', 'Hideki Tojo', 'Philippe Pétain', 'Charles de Gaulle', 'Sun Yat-sen', 'Yuan Shikai', 'Winston Churchill']) + '。')
    A('- 預算：本任務使用 MediaWiki API 無費用；session 預算未用盡。')
    A('- 重跑：`python3 data/seed/leaders/generals-roster/build_roster.py`（有 `cache/` 時不再打 API、排序固定；刪除 `cache/` 則重抓）。')
    (HERE / 'SUMMARY.md').write_text('\n'.join(L) + '\n', encoding='utf-8')

if __name__ == '__main__':
    main()
