"""C 級補充區的兩條 Python 規則（data/seed/leaders/b3-trial/verify.py 與 tools/b3v3/tiers.py 共用）。

1. A／B 為準（Tai 2026-11-18）：C 條目和主內容（A／B）的日期、任期、年份對不上，就以 A／B 為準。
   衝突的 C 不得留在 clauses／dates（不得當事實顯示），只能移到 supplementC.conflictNotes，附 conflictsWithAB（A／B 的 ref 與理由），或直接刪。
   判定（date_conflict／clause_conflict）：
   - C 日期的同一端 A／B 已有值且不同；
   - C 迄日早於 A／B 起日，或 C 起日晚於 A／B 迄日；
   - C 引文寫的是一段任期（年–年），和 A／B 這個職位的任期完全不重疊（多半是另一任期）；
   - C 日期落在另一筆同名 A／B 職位的任期裡；
   - C 句子提到某個 A／B 職位名稱，但句中所有年份都在那個職位任期之外（前後各寬 1 年）。
   - C 迄日的引文只寫就任、當選這類起點事件（沒有任期範圍、也沒有辭職／解散／去世這類結束字樣）→ 不算迄日的依據（end_quote_ok）。
2. 引文支撐（support_gaps）：C 句子裡的年份、數字（含月日、歲數、次數）、拉丁字母專名、「」《》『』裡的詞，
   都要出現在它的引文裡。比對前先把民國、明治／大正／昭和／平成紀年換成西元，漢數字換阿拉伯數字，常見新舊字形與簡繁字統一。
   外文月名（英德法義西俄波）也換成數字。
   另有長度上限（overreach）：C 句子的中文字數不得超過引文份量的 1.6 倍＋12 字（外文引文以 2.5 個字母折 1 字），
   免得一句 20 字的引文被寫成 60 字的敘述。
   限制：中文句子裡的漢字人名、地名沒辦法自動認出來，所以只查上面幾種；譯名（例如德文引文、中文句子）也比對不到。
"""
import re
import unicodedata

ERA_BASE = {"明治": 1867, "大正": 1911, "昭和": 1925, "平成": 1988, "民國": 1911, "民国": 1911}
KANJI_DIGIT = {"〇": 0, "零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
               "两": 2, "兩": 2}
KANJI_UNIT = {"十": 10, "百": 100, "千": 1000}
# 新舊字形、簡繁：只收比對常用字，兩邊都轉成同一形
_PAIRS = ("禮礼 國国 國國 澤沢 濱浜 邊辺 邉辺 齋斎 齊斉 龍竜 廣広 德徳 榮栄 義义 與与 會会 學学 長长 軍军 總总 議议 內内 閣阁 "
          "黨党 臺台 灣湾 東东 華华 爲為 為为 來来 對对 時时 後后 從从 發发 戰战 爭争 鬥斗 歲歳 歳岁 實実 實实 團団 團团 傳伝 傳传 "
          "區区 區區 縣県 縣县 驛駅 鐵鉄 鐵铁 權権 權权 氣気 氣气 圖図 圖图 價価 價价 舊旧 變変 變变 關関 關关 選选 舉挙 舉举 "
          "務务 歷歴 歷历 曆暦 衆眾 眾众 樞枢 樞樞 隊队 陸陆 職职 員员 統统 領领 書书 記记 參参 參參 謀谋 辭辞 辭辞 職職 "
          "數数 數數 豐豊 豐丰 萬万 億亿 號号 處処 處处 譯訳 譯译 讀読 讀读 帥帅 將将 將將 劍剣 敗败 滿満 滿满 盧卢 蘇苏 聯联 "
          "葉叶 擧挙 竝並 濟済 濟济 醫医 營営 營营 壽寿 惠恵 戀恋 嶋島 嶌島 﨑崎 髙高 邨村 冨富 條条 條條")
_FROM, _TO = [], []
for pair in _PAIRS.split():
    if len(pair) == 2 and pair[0] not in _FROM:
        _FROM.append(pair[0]); _TO.append(pair[1])
_MAP = dict(zip(_FROM, _TO))
for _k in list(_MAP):   # 收斂成單一標準字（歲→歳→岁 一律到岁），轉兩次結果也不變
    _v, _seen = _MAP[_k], {_k}
    while _v in _MAP and _v not in _seen:
        _seen.add(_v)
        _v = _MAP[_v]
    _MAP[_k] = _v
_MAP = {k: v for k, v in _MAP.items() if k != v}
COMMON = str.maketrans(_MAP)

YEAR_RE = re.compile(r"(?<!\d)(1[5-9]\d\d|20\d\d)(?!\d)")
ERA_RE = re.compile(r"(明治|大正|昭和|平成|民國|民国)\s*(元|\d{1,2})\s*年")
KANJI_NUM_RE = re.compile(r"[〇零一二三四五六七八九十百千两兩]+(?=\s*(?:年|月|日|歳|歲|岁|人|名|回|期|代|次|届|屆|号|號|万|萬|%))")
DIGITS_RE = re.compile(r"\d+")
LATIN_NAME_RE = re.compile(r"(?<![A-Za-z\u00C0-\u024F])[A-Z][A-Za-z\u00C0-\u024F'\-]{2,}")
BRACKET_RE = re.compile(r"[「『《〈]([^」』》〉]{1,30})[」』》〉]")
RANGE_RE = re.compile(r"(?<!\d)(1[5-9]\d\d|20\d\d)(?!\d)[^\n]{0,16}?(?:[-–—～~〜至到]|から|bis|to|until)[^\n]{0,8}?(?<!\d)(1[5-9]\d\d|20\d\d)(?!\d)")


def norm(text):
    return unicodedata.normalize("NFKC", text or "").translate(COMMON)


def kanji_number(s):
    total, current = 0, 0
    if all(ch in KANJI_DIGIT for ch in s):   # 一九二六 這種逐位寫法
        return int("".join(str(KANJI_DIGIT[ch]) for ch in s))
    for ch in s:
        if ch in KANJI_DIGIT:
            current = KANJI_DIGIT[ch]
        elif ch in KANJI_UNIT:
            total += (current or 1) * KANJI_UNIT[ch]
            current = 0
    return total + current


def westernize(text):
    """漢數字 → 阿拉伯數字，紀年 → 西元年（「大正7年」→「1918年」）。"""
    text = norm(text)
    # 單獨的「一」多半是「一名」「一回」這類虛詞（不是數字），只有接年月日時才換
    text = KANJI_NUM_RE.sub(lambda m: m.group(0) if m.group(0) == "一" and text[m.end():m.end() + 1] not in "年月日"
                            else str(kanji_number(m.group(0))), text)
    text = ERA_RE.sub(lambda m: f"{ERA_BASE[m.group(1)] + (1 if m.group(2) == '元' else int(m.group(2)))}年", text)
    return text


def years(text):
    return {int(y) for y in YEAR_RE.findall(westernize(text))}


MONTHS = {}
for _n, _names in enumerate((
        "january jan januar janvier gennaio enero января январь styczeń stycznia",
        "february feb februar février febbraio febrero февраля февраль lutego",
        "march mar märz mars marzo марта март marca",
        "april apr avril aprile abril апреля апрель kwietnia",
        "may mai maggio mayo мая май maja",
        "june jun juni juin giugno junio июня июнь czerwca",
        "july jul juli juillet luglio julio июля июль lipca",
        "august aug août agosto августа август sierpnia",
        "september sep sept septembre settembre septiembre сентября сентябрь września",
        "october oct oktober octobre ottobre octubre октября октябрь października",
        "november nov novembre noviembre ноября ноябрь listopada",
        "december dec dezember décembre dicembre diciembre декабря декабрь grudnia"), 1):
    for _w in _names.split():
        MONTHS[_w] = _n
MONTH_WORD_RE = re.compile(r"(?<![A-Za-zА-Яа-яÀ-ž])(" + "|".join(sorted(map(re.escape, MONTHS), key=len, reverse=True))
                           + r")\.?(?![A-Za-zА-Яа-яÀ-ž])", re.I)


def numbers(text):
    """(年份, 其他數字)。年份另列；其他數字含月（外文月名也換成數字）、日、歲數、次數。"""
    text = westernize(text)
    ys = {int(y) for y in YEAR_RE.findall(text)}
    rest = YEAR_RE.sub(" ", text)
    out = {int(n) for n in DIGITS_RE.findall(rest)}
    out |= {MONTHS[m.lower()] for m in MONTH_WORD_RE.findall(text)}
    return ys, out


def support_gaps(sentence, quote, names=True):
    """句子裡有、引文裡沒有的年份／數字／專名。空清單＝有支撐。"""
    sy, sn = numbers(sentence)
    qy, qn = numbers(quote)
    gaps = [str(y) for y in sorted(sy - qy)]
    gaps += [str(n) for n in sorted(sn) if n not in qn and n not in qy]
    if names:
        q = norm(quote).lower()
        for token in LATIN_NAME_RE.findall(norm(sentence)):
            if token.lower() not in q:
                gaps.append(token)
        for token in BRACKET_RE.findall(norm(sentence)):
            if norm(token) not in norm(quote):
                gaps.append(f"「{token}」")
    return gaps


# ---------------------------------------------------------------- A／B 為準

TARGET_RE = re.compile(r"(position|role):([\w-]+)\.(start|end)")


def _units(person):
    out = []
    for kind, field in (("position", "positions"), ("role", "roleCandidates")):
        for unit in person.get(field) or []:
            out.append((kind, unit))
    return out


def _year(value):
    m = re.match(r"(\d{4})", str(value or ""))
    return int(m.group(1)) if m else None


def _title(unit):
    title = unit.get("title") or {}
    zh = title.get("zh-Hant") if isinstance(title, dict) else str(title)
    return re.sub(r"[（(].*?[）)]", "", zh or "").strip()


def date_conflict(person, item):
    """C 日期和 A／B 衝突 → {"ref", "abValue", "reason"}；沒有衝突 → None。"""
    m = TARGET_RE.fullmatch(str(item.get("target") or ""))
    value = str(item.get("value") or "")
    if not m or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None
    kind, key, side = m.groups()
    unit = next((u for k, u in _units(person) if k == kind and u.get("key") == key), None)
    if unit is None:
        return None
    period = unit.get("period") or {}
    start, end = period.get("start"), period.get("end")
    reasons = []
    own = period.get(side)
    if own and str(own) != value:
        prec = unit.get(f"{side}Precision")
        same = (prec == "year" and str(own)[:4] == value[:4]) or (prec == "month" and str(own)[:7] == value[:7])
        if not same:
            reasons.append(f"A／B 已有 {side}={own}")
    if side == "end" and start and value < str(start)[:10]:
        reasons.append(f"C 迄日 {value} 早於 A／B 起日 {start}")
    if side == "start" and end and value > str(end)[:10]:
        reasons.append(f"C 起日 {value} 晚於 A／B 迄日 {end}")
    sy, ey = _year(start), _year(end)
    vy = int(value[:4])
    for a, b in RANGE_RE.findall(westernize(item.get("quote"))):
        a, b = int(a), int(b)
        if (side == "end" and b == vy) or (side == "start" and a == vy):
            if (sy and b < sy) or (ey and a > ey):
                reasons.append(f"C 引文的任期 {a}–{b} 和 A／B 任期 {start}～{end or '（未填）'} 不重疊（多半是另一任期）")
    title = _title(unit)
    for k, other in _units(person):
        if other is unit or not title or _title(other) != title:
            continue
        op = other.get("period") or {}
        if op.get("start") and str(op["start"])[:10] <= value <= str(op.get("end") or "9999")[:10]:
            reasons.append(f"C 日期落在另一筆同名 A／B 任期 {k}:{other.get('key')}")
    if not reasons:
        return None
    return {"ref": f"{kind}:{key}.{side}", "abValue": {"start": start, "end": end}, "reason": "；".join(reasons)}


def clause_conflict(person, clause):
    """C 句子提到 A／B 職位、但年份全在那個任期外 → 衝突。"""
    text = clause.get("text") or {}
    zh = text.get("zh-Hant") if isinstance(text, dict) else ""
    ys = years(zh)
    if not zh or not ys:
        return None
    for kind, unit in _units(person):
        title = _title(unit)
        if len(title) < 2 or norm(title) not in norm(zh):
            continue
        period = unit.get("period") or {}
        sy, ey = _year(period.get("start")), _year(period.get("end"))
        if not sy:
            continue
        lo, hi = sy - 1, (ey or sy) + 1 if ey else 9999
        if all(y < lo or y > hi for y in ys):
            return {"ref": f"{kind}:{unit.get('key')}", "abValue": {"start": period.get("start"), "end": period.get("end")},
                    "reason": f"C 句子寫「{title}」的年份 {sorted(ys)}，不在 A／B 任期 {period.get('start')}～{period.get('end') or '（未填）'}"}
    return None


CJK_CHAR_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff]")


def quote_units(quote):
    text = norm(quote)
    cjk = len(CJK_CHAR_RE.findall(text))
    latin = len(re.findall(r"[^\W\d_]", CJK_CHAR_RE.sub("", text)))
    digits = len(re.findall(r"\d", text))
    return cjk + latin / 2.5 + digits / 2


def overreach(zh, quote):
    """C 句子比引文多講太多 → (句子字數, 上限)；沒有 → None。"""
    n = len([ch for ch in norm(zh) if not ch.isspace() and not unicodedata.category(ch).startswith("P")])
    limit = int(quote_units(quote) * 1.6 + 12)
    return (n, limit) if n > limit else None


END_WORDS = re.compile(r"辞任|辭任|辞職|辭職|辞め|解散|廃止|廢止|消滅|死去|逝世|去世|病死|卒|没|退任|離任|免職|罷免|失脚|下野|総辞職|總辭|"
                       r"resign|dissol|died|death|abolish|until|ended|dismiss|removed|replaced|succeeded by|"
                       r"rücktritt|aufgelöst|starb|bis |démission|dissous|mort|отставк|распущ|умер|скончал", re.I)
START_WORDS = re.compile(r"就任|となった|となる|任命|選出|当選|當選|出任|擔任|担任|became|appointed|elected|named|"
                         r"wurde|ernannt|gewählt|devint|nommé|élu|избран|назначен|стал", re.I)


def end_quote_ok(quote):
    """C 迄日的引文要像「結束」：有年–年範圍，或有辭職／解散／去世之類的字；只寫就任／當選的不算。"""
    text = westernize(quote)
    if RANGE_RE.search(text) or END_WORDS.search(text):
        return True
    return not START_WORDS.search(text)


# ---------------------------------------------------------------- A／B 任期：中斷與推論迄日（2026-11-19）

BREAK_WORDS = re.compile(r"免職|免去|被免|撤職|辭職|辞職|辭去|辞任|罷免|下野|去職|解職|復任|復職|再任|再度任命|重新任命|重任|"
                         r"dismiss|resign|reappoint|reinstat|removed from office|ousted", re.I)
APPOINT_WORDS = re.compile(r"任命|就任|繼任|継任|接任|署理|出任|appointed|succeeded|took office|sworn in|ernannt|nommé|назначен", re.I)
_EN_MONTH_DAY = re.compile(r"(?<![A-Za-z])([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(1[5-9]\d\d|20\d\d)")
_DAY_EN_MONTH = re.compile(r"(?<!\d)(\d{1,2})\s+([A-Za-z]{3,9})\.?\s+(1[5-9]\d\d|20\d\d)")
_ZH_DATE = re.compile(r"(?:(1[5-9]\d\d|20\d\d)年)?\s*(\d{1,2})月(?:\s*(\d{1,2})日)?")


def text_dates(text, year=None):
    """句子裡的日期（YYYY-MM-DD；沒寫年就沿用同段前一個年份）。回傳 (日期清單, 最後的年份)。"""
    t = westernize(text)
    out = []
    for m in _ZH_DATE.finditer(t):
        y = int(m.group(1)) if m.group(1) else year
        if y:
            year = y
            out.append(f"{y:04d}-{int(m.group(2)):02d}-{int(m.group(3) or 1):02d}")
    for m in _EN_MONTH_DAY.finditer(t):
        mon = MONTHS.get(m.group(1).lower())
        if mon:
            out.append(f"{int(m.group(3)):04d}-{mon:02d}-{int(m.group(2)):02d}")
    for m in _DAY_EN_MONTH.finditer(t):
        mon = MONTHS.get(m.group(2).lower())
        if mon:
            out.append(f"{int(m.group(3)):04d}-{mon:02d}-{int(m.group(1)):02d}")
    for y in YEAR_RE.findall(t):
        year = int(y)
    return out, year


def _title_tokens(unit):
    title = unit.get("title") or {}
    zh = title.get("zh-Hant") if isinstance(title, dict) else str(title)
    parts = [p for p in re.split(r"[（）()兼、・／/\s]+", zh or "") if len(p) >= 2]
    tokens = set(parts) | {p[-2:] for p in parts}
    orig = title.get("orig") if isinstance(title, dict) else ""
    tokens |= {w for w in re.findall(r"[A-Za-z]{4,}", orig or "") if w.lower() not in ("minister", "concurrently", "member")}
    return {norm(t).lower() for t in tokens}


def term_breaks(person, unit, period=None):
    """任期中間有免職／辭職／復任的記載（本人段落句子）→ [{date, text}]。可能是兩段任期被合成一段。
    中斷詞和職稱（或其末兩字）要在同一子句；日期取該子句的，沒有就取同句前面最近的子句。
    日期要嚴格落在任期起訖之間。迄日空白就不查。"""
    period = period or unit.get("period") or {}
    start, end = str(period.get("start") or ""), str(period.get("end") or "")
    if not start or not end:
        return []
    tokens = _title_tokens(unit)
    out = []
    for para in person.get("paragraphs") or []:
        year = None
        zh = (para.get("body") or {}).get("zh-Hant") or ""
        for sent in re.split(r"(?<=[。！？；])", zh):
            last = []   # 同一句裡最近一個有日期的子句
            for clause in re.split(r"[，,、：:]", sent):
                dates, year = text_dates(clause, year)
                if dates or YEAR_RE.search(westernize(clause)):   # 子句只寫到年：不沿用前面的日期
                    last = dates
                if not BREAK_WORDS.search(clause):
                    continue
                low = norm(clause).lower()
                if tokens and not any(t in low for t in tokens):   # 中斷詞和職稱要在同一子句
                    continue
                for d in last:
                    if start < d < end:
                        out.append({"date": d, "text": sent.strip()[:80], "ord": para.get("ord")})
    return out


def successor_day_quote(end, cites):
    """推論迄日要有一筆引文同時寫出「任命／就任」和那一天（月、日都在）；電報、報導日期不算。"""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(end or "")):
        return False
    month, day = int(end[5:7]), int(end[8:10])
    for cite in cites or []:
        q = cite.get("quote") or ""
        if APPOINT_WORDS.search(q):
            _ys, nums = numbers(q)
            if month in nums and day in nums:
                return True
    return False
