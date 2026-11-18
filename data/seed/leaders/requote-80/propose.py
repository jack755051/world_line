#!/usr/bin/env python3
"""為 > 80 字的 evidence 產生重摘候選（只供人工審核用，不直接當結果）。

候選＝evidence 內以句／子句邊界切出的連續片段（逐字、不改寫），NFC ≤ 80 字；
依與欄位值的字面重疊（年份、日、月名、詞）排序。輸出 proposals/rNN.json：每筆列前幾名候選。
用法：python3 propose.py rNN
"""
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
MAX = 80
# 句／子句邊界：句末標點後接空白、分號、冒號、逗號、破折號、括號；CJK 標點
SPLIT = re.compile(r"(?<=[.;:!?,)\]])\s+|\s+(?=[(\[])|\s+[–—-]\s+|(?<=[。；，、：！？）」』])|(?=[（「『])")
MONTHS = {
    1: "january janvier januar jänner enero gennaio janeiro januari stycznia ledna január ianuarie января ocak tammikuu janúar sausio janvāra jaanuar".split(),
    2: "february février februar febrero febbraio fevereiro februari lutego února február februarie февраля şubat helmikuu febrúar vasario februāra veebruar".split(),
    3: "march mars märz marzo março maart marca března március martie марта mart maaliskuu mars kovo marta märts".split(),
    4: "april avril abril aprile kwietnia dubna április aprilie апреля nisan huhtikuu apríl balandžio aprīļa aprill".split(),
    5: "may mai mayo maggio maio mei maja května május mai мая mayıs toukokuu maí gegužės maija".split(),
    6: "june juin juni junio giugno junho czerwca června június iunie июня haziran kesäkuu júní birželio jūnija juuni".split(),
    7: "july juillet juli julio luglio julho lipca července július iulie июля temmuz heinäkuu júlí liepos jūlija juuli".split(),
    8: "august août agosto augustus sierpnia srpna augusztus august августа ağustos elokuu ágúst rugpjūčio augusta".split(),
    9: "september septembre settembre setembro septiembre września září szeptember septembrie сентября eylül syyskuu september rugsėjo septembra".split(),
    10: "october octobre oktober octubre ottobre outubro października října október octombrie октября ekim lokakuu október spalio oktobra".split(),
    11: "november novembre noviembre novembro listopadu listopada november noiembrie ноября kasım marraskuu nóvember lapkričio novembra".split(),
    12: "december décembre dezember diciembre dicembre dezembro grudnia prosince december decembrie декабря aralık joulukuu desember gruodžio decembra detsember".split(),
}


def nfc(s):
    return unicodedata.normalize("NFC", s)


def tokens_for(field, value):
    v = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    v = nfc(v or "")
    toks = set()
    m = re.match(r"^(\d{3,4})(?:-(\d{2}))?(?:-(\d{2}))?", v)
    if field in ("birthDate", "deathDate") and m:
        toks.add(m.group(1))
        if m.group(2):
            toks.update(MONTHS[int(m.group(2))])
            toks.add(str(int(m.group(2))))
        if m.group(3):
            toks.add(str(int(m.group(3))))
        return toks, {m.group(1)}
    words = [w.lower() for w in re.findall(r"\w+", v) if len(w) >= (3 if field != "summary" else 5)]
    cjk = re.findall(r"[㐀-鿿]{2}", v)
    toks.update(words)
    toks.update(cjk)
    return toks, set()


def units(ev):
    out, pos = [], 0
    for m in SPLIT.finditer(ev):
        if m.end() > pos and m.start() >= pos:
            seg_end = m.start()
            if seg_end > pos:
                out.append((pos, seg_end))
            pos = m.end()
    if pos < len(ev):
        out.append((pos, len(ev)))
    return out


def candidates(ev):
    us = units(ev)
    seen = set()
    for i in range(len(us)):
        for j in range(i, len(us)):
            s, e = us[i][0], us[j][1]
            q = ev[s:e].strip()
            if len(q) > MAX:
                break
            if q and q not in seen:
                seen.add(q)
                yield s, q


def score(field, value, q):
    toks, must = tokens_for(field, value)
    ql = q.lower()
    words = set(re.findall(r"\w+", ql))
    hit = sum(1 for t in toks if (t in words if re.fullmatch(r"\w+", t) else t in ql))
    if must and not all(m in words for m in must):
        hit -= 100
    return hit


def main(group):
    wl = json.load(open(os.path.join(HERE, "worklist.json"), encoding="utf-8"))
    out = []
    for it in wl["items"]:
        if it["group"] != group or it["nfcChars"] <= MAX:
            continue
        ev = nfc(it["evidence"])
        cands = sorted(((score(it["field"], it["value"], q), len(q), s, q) for s, q in candidates(ev)),
                       key=lambda t: (-t[0], -t[1], t[2]))
        out.append({"id": it["citationId"], "field": it["field"], "value": it["value"], "evidence": ev,
                    "cands": [{"score": c[0], "q": c[3]} for c in cands[:4]]})
    os.makedirs(os.path.join(HERE, "proposals"), exist_ok=True)
    json.dump(out, open(os.path.join(HERE, "proposals", f"{group}.json"), "w"), ensure_ascii=False, indent=1)
    print(group, len(out), "無候選", sum(not o["cands"] for o in out))


if __name__ == "__main__":
    main(sys.argv[1])
