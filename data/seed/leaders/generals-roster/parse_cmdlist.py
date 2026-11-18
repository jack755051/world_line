"""Parse 第二次世界大戰各國指揮官列表 (index only)."""
import re

HEADING_COUNTRY = [
    ('CHN-1928', '中華民國-國民政府'), ('中华民国', '中華民國-國民政府'), ('中華民國', '中華民國-國民政府'),
    ('英国', '英國'), ('英國', '英國'), ('法国', '法國'), ('法國', '法國'),
    ('美国', '美國'), ('美國', '美國'), ('苏联', '蘇聯'), ('蘇聯', '蘇聯'),
    ('澳大利亚', '澳洲'), ('澳大利亞', '澳洲'), ('新西兰', '紐西蘭'), ('新西蘭', '紐西蘭'),
    ('波兰', '波蘭'), ('波蘭', '波蘭'), ('捷克斯洛伐克', '捷克斯洛伐克'),
    ('希腊', '希臘'), ('希臘', '希臘'), ('荷兰', '荷蘭'), ('荷蘭', '荷蘭'),
    ('南斯拉夫', '南斯拉夫'), ('加拿大', '加拿大'), ('南非', '南非'),
    ('纳粹德国', '德國'), ('納粹德國', '德國'), ('意大利', '義大利'), ('義大利', '義大利'),
    ('日本', '日本'), ('泰国', '泰國'), ('泰國', '泰國'), ('芬兰', '芬蘭'), ('芬蘭', '芬蘭'),
    ('罗马尼亚', '羅馬尼亞'), ('羅馬尼亞', '羅馬尼亞'), ('斯洛伐克', '斯洛伐克'),
    ('自由印度', '自由印度臨時政府'), ('缅甸', '緬甸'), ('緬甸', '緬甸'),
    ('瑞士', '瑞士'), ('乌克兰反抗军', '烏克蘭反抗軍'), ('烏克蘭反抗軍', '烏克蘭反抗軍'),
]
S_RANK = re.compile(
    r'特級上將|特级上将|五星上將|五星上将|帝國元帥|帝国元帅|'
    r'陸軍元帥|陆军元帅|海軍元帥|海军元帅|空軍元帥|空军元帅|'
    r'大元帥|大元帅|元帥|元帅|'
    r'Admiral of the Fleet|Field Marshal|Marshal of the Royal Air Force|'
    r'Generalfeldmarschall|Reichsmarschall|Grand Admiral|Generalissimo'
)
NS = re.compile(
    r'^(file|image|category|檔案|文件|分類|分类|圖像|图像|template|模板|wikipedia|help|special|媒體|media)\s*:',
    re.I,
)
SKIP_TGT = re.compile(r'列表|战役|戰役|行动|行動|战线|戰線|政府|国会|國會|大学|大學|勋章|勳章|司令部|远征军|遠征軍')


def parse_name_cell(cell):
    en = zh = tgt = None
    tm = re.search(
        r'\{\{\s*tsl\s*\|\s*en\s*\|\s*([^|]+?)\s*(?:\|\s*([^}|]+?)\s*)?\}\}',
        cell, re.I,
    )
    if tm:
        en = tm.group(1).strip()
        zh = (tm.group(2) or '').strip() or None
        tgt = zh or en
    for mm in re.finditer(r'\[\[([^\]|#]+)(?:\|([^\]]*))?\]\]', cell):
        t0 = mm.group(1).strip()
        if NS.match(t0) or SKIP_TGT.search(t0):
            continue
        tgt = t0
        zh = (mm.group(2) or t0).strip()
        break
    sm = re.search(r'<small>\s*([^<]+?)\s*</small>', cell)
    if sm:
        en = sm.group(1).strip()
    return tgt, zh, en


def parse_cmdlist(wt):
    """Return list of dicts: tgt, zh, en, country, branch, rank, min_tier."""
    m = re.search(r'^==\s*军队指挥官\s*==', wt, re.M)
    m2 = re.search(r'^==\s*参考文献', wt, re.M)
    if not m:
        return []
    body = wt[m.start(): m2.start() if m2 else None]
    out = []
    for table in re.findall(r'\{\|.*?\|\}', body, re.S):
        pos = body.find(table)
        heads = re.findall(r'^(=+)\s*(.+?)\s*\1\s*$', body[:pos], re.M)
        country = None
        for eq, h in reversed(heads):
            if len(eq) >= 4:
                for k, v in HEADING_COUNTRY:
                    if k in h:
                        country = v
                        break
                if country:
                    break
        branch = 'unknown'
        for raw in re.split(r'\n\s*\|-', table):
            if re.search(r'^\s*!', raw, re.M) and '姓名' in raw:
                continue
            if re.search(r'^\s*\|\s*colspan', raw, re.M):
                continue
            bm = re.search(r"rowspan=\"?\d+\"?[^\n|]*\|'''?([^'|]+)'''?", raw)
            if bm:
                b = re.sub(r"'", '', bm.group(1))
                if '陆军' in b or '陸軍' in b:
                    branch = 'army'
                elif '海军' in b or '海軍' in b:
                    branch = 'navy'
                elif '空军' in b or '空軍' in b:
                    branch = 'air_force'
            cells, buf = [], []
            for line in raw.split('\n'):
                if line.startswith('|') or line.startswith('!'):
                    if buf:
                        cells.append('\n'.join(buf))
                    buf = [line]
                elif buf:
                    buf.append(line)
            if buf:
                cells.append('\n'.join(buf))
            name = rank_cell = None
            for ci, c in enumerate(cells):
                if re.search(r'File:|Image:|文件:|檔案:', c):
                    continue
                tgt, zh, en = parse_name_cell(c)
                if tgt and ('<small>' in c or 'tsl' in c or 'rowspan' in c):
                    name = (tgt, zh, en)
                    for c2 in cells[ci + 1:]:
                        if re.search(r'File:|Image:|文件:|檔案:', c2):
                            continue
                        rank_cell = c2
                        break
                    break
            if not name:
                continue
            tgt, zh, en = name
            if SKIP_TGT.search(tgt or ''):
                continue
            rank = rank_cell or ''
            rank = re.sub(r'\[\[([^\]|]+)\|([^\]]+)\]\]', r'\2', rank)
            rank = re.sub(r'\[\[([^\]]+)\]\]', r'\1', rank)
            rank = re.sub(r"'{2,}", '', rank)
            rank = re.sub(r'<ref[^>]*>.*?</ref>', '', rank, flags=re.S)
            rank = re.sub(r'\{\{[^}]*\}\}', ' ', rank)
            rank = re.sub(r'<[^>]+>', ' ', rank)
            rank = re.sub(r'\s+', ' ', rank).strip().lstrip('| ').strip() or '待查證'
            min_tier = 'S' if S_RANK.search(rank) else 'A'
            out.append(dict(tgt=tgt, zh=zh, en=en, country=country or '未知',
                            branch=branch, rank=rank, min_tier=min_tier))
    return out
