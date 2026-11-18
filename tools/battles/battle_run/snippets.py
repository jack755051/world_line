"""從已快取原文抽出關鍵字片段。Agent 只讀片段，不讀全文。

關鍵字：部隊名／別名、番號變體、人名、地名、日期變體。
片段遇到 PDF 換頁符或 HyperWar「--頁碼--」會標成 ⟨分頁⟩，提示引文不可跨頁。
"""
from __future__ import annotations

import re
from pathlib import Path

PAGE_BREAK = "⟨分頁⟩"
MON_EN = "January February March April May June July August September October November December".split()
MON_DE = "Januar Februar März April Mai Juni Juli August September Oktober November Dezember".split()
MON_PL_GEN = "stycznia lutego marca kwietnia maja czerwca lipca sierpnia września października listopada grudnia".split()
ORD_EN = {
    1: "First", 2: "Second", 3: "Third", 4: "Fourth", 5: "Fifth", 6: "Sixth",
    7: "Seventh", 8: "Eighth", 9: "Ninth", 10: "Tenth", 11: "Eleventh",
    12: "Twelfth", 13: "Thirteenth", 14: "Fourteenth", 15: "Fifteenth",
    16: "Sixteenth", 18: "Eighteenth", 19: "Nineteenth",
}
ZH = "〇一二三四五六七八九"


def zhnum(n):
    if n < 10:
        return ZH[n]
    if n < 20:
        return "十" + (ZH[n % 10] if n % 10 else "")
    if n < 100:
        return ZH[n // 10] + "十" + (ZH[n % 10] if n % 10 else "")
    return str(n)


def zh2int(z):
    if z.isdigit():
        return int(z)
    v = 0
    cur = 0
    for ch in z:
        if ch == "十":
            v += (cur or 1) * 10
            cur = 0
        elif ch == "百":
            v += (cur or 1) * 100
            cur = 0
        elif ch in ZH:
            cur = ZH.index(ch)
    return v + cur


def suffix(n):
    return "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def date_kw(iso):
    y, m, d = map(int, iso.split("-"))
    me = MON_EN[m - 1]
    out = [
        f"{d} {me}", f"{me} {d}", f"{d} {me[:3]}", f"{me[:3]} {d}",
        f"May the {d}" if me == "May" else f"{me} the {d}",
        f"{d}nd {me}" if d == 22 else f"{d}{suffix(d)} {me}",
        f"{d}. {MON_DE[m-1]}", f"{d} {MON_PL_GEN[m-1]}",
        f"{m}月{d}日", f"{zhnum(m)}月{zhnum(d)}日",
        f"{d}.{m:02d}.", f"{d}.{m}.",
    ]
    if y:
        out += [f"{y}年{m}月", f"{d} {me} {y}", f"{me} {d}, {y}"]
    return out


def name_parts(s):
    out = []
    for part in re.split(r"[（）()／/,;]", s or ""):
        part = part.strip()
        if len(part) >= 2 and not part.isdigit():
            out.append(part)
    return out


def unit_kw(names):
    kw = []
    for n in names or []:
        kw += name_parts(n)
        for side, ab, de in (
            ("North", ["AGp North", "AGp. North"], "Nord"),
            ("South", ["AGp South", "AGp. South"], "Süd"),
        ):
            if re.search(r"Army Group " + side + r"|Heeresgruppe " + de, n):
                kw += ab
        if re.search(r"\bBEF\b|British Expeditionary Force", n, re.I):
            kw += ["BEF", "British Expeditionary Force"]
        for m in re.finditer(r"(\d+)\.?\s*(Armee|Army|Korps|Corps|Division|Div|Panzer-Division|PzDiv|Panzer)", n, re.I):
            k = int(m.group(1))
            e = m.group(2).lower()
            if e.startswith("arm"):
                kw += [f"{k}. Armee", f"{ORD_EN.get(k, '')} Army".strip(), f"{k}{suffix(k)} Army"]
            elif e.startswith(("korps", "corps")):
                kw += [f"{k}{suffix(k)} Corps", f"{k}. Korps", f"{zhnum(k)}軍"]
            else:
                kw += [
                    f"{k}{suffix(k)} Division", f"{k}. Division",
                    f"{k}{suffix(k)} Panzer Division", f"{k}{suffix(k)} Panzer",
                    f"{k}. Panzer-Division", f"{k}{suffix(k)} Panzer Division",
                ]
        for m in re.finditer(r"第([〇一二三四五六七八九十百]+|\d+)(集團軍|軍|師|旅|師団|旅団|連隊)", n):
            kw.append(m.group(0))
            k = zh2int(m.group(1))
            kw += [f"第{k}{m.group(2)}", f"第{zhnum(k)}{m.group(2)}"]
        # XIX / XXXXI 類羅馬數字軍
        for m in re.finditer(r"\b([IVX]+)\.?\s*(Armeekorps|Korps|Corps|AK)\b", n, re.I):
            kw += [m.group(0), f"{m.group(1)} Corps", f"{m.group(1)} Corps"]
    return [k for k in dict.fromkeys(kw) if len(k.strip()) >= 2]


def gap_keywords(g):
    """(必要關鍵字, 加分關鍵字)：片段至少命中一個必要字。"""
    t = g["type"]
    if t == "R3":
        bonus = []
        for d in (g.get("missingDates") or [])[:12]:
            bonus += date_kw(d)
        return unit_kw(g.get("names") or []), bonus
    if t == "R4":
        return date_kw(g["date"]), [
            "line", "Linie", "linii", "front", "Front", "線", "陣地",
            "reached", "erreicht", "osiągn", "advanced", "退守", "占領", "zone",
            "canal", "perimeter", "perimeter",
        ]
    if t == "R5":
        must = [x for n in (g.get("names") or []) for x in name_parts(n)] + name_parts(g.get("place") or "")
        return must, ["began", "begann", "rozpocz", "ended", "日", "attack", "Angriff", "bitw", "surrender", "kapitul", "defence", "defense", "fell"]
    if t == "R6":
        must = name_parts(g.get("place") or "")
        return must, ["captured", "fell", "occupied", "eingenommen", "besetzt", "zdobyt", "zajęt", "kapitul", "失守", "占領", "陥落", "攻略", "entered"]
    if t == "R7":
        nm = g.get("person") or ""
        must = [nm]
        if nm.split():
            must.append(nm.split()[-1])
        if g.get("nameZh"):
            must.append(g["nameZh"])
        must = [m for m in must if m and (m == nm or len(m) >= 4 or not m.isascii())]
        return must, unit_kw(g.get("unitNames") or []) + [
            "command", "Oberbefehl", "dowódc", "司令官", "親補", "任命", "appointed", "Befehlshaber", "took command",
        ]
    return [], []


def kw_re(k):
    k = k.strip()
    if re.search(r"[\u3000-\u9fff]", k):
        return re.compile(r"\s?".join(map(re.escape, k)))
    parts = [re.escape(x) for x in k.split()]
    return re.compile(r"(?<![A-Za-z0-9])" + r"\s+".join(parts) + r"(?![a-z])", re.I)


HEAD_RE = re.compile(
    r"(?m)^\s*(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|Sept?|Aug|Oct|Nov)\.?\s+19\s?\d\.?\s?\d)"
    r"|(\d{1,2}\.\s*(?:September|Oktober)\s+1939)"
    r"|(昭和十二年[一二三四五六七八九十]+月[一二三四五六七八九十]+日)"
)


def heading_before(text, pos):
    last = None
    for m in HEAD_RE.finditer(text, max(0, pos - 20000), pos):
        last = m
    return re.sub(r"\s+", " ", last.group(0).strip()) if last else None


def mark_page_breaks(text: str) -> str:
    """把換頁符與 HyperWar 頁碼標記換成可見的分頁記號，供抽取員遵守「引文不跨頁」。"""
    t = text.replace("\f", f"\n{PAGE_BREAK}\n")
    t = re.sub(r"--\s*(\d+)\s*--", lambda m: f"\n{PAGE_BREAK} p.{m.group(1)}\n", t)
    t = t.replace("--pagebreak--", f"\n{PAGE_BREAK}\n")
    t = re.sub(r"[ \t]*\n[ \t]*", "\n", t)
    return t


def extract(gaps, corpus, *, win=280, mx=6, existing_keys=None):
    """corpus: iterable of {sourceKey, url, text} 或 (sourceKey, url, text)。
    回傳 [{gap, keywords, snippets}]。"""
    existing_keys = set(existing_keys or [])
    corp = []
    for item in corpus:
        if isinstance(item, dict):
            corp.append((item.get("sourceKey"), item.get("url"), item.get("text") or ""))
        else:
            corp.append(tuple(item))
    res = []
    for g in gaps:
        must, bonus = gap_keywords(g)
        mre = [kw_re(k) for k in must if k]
        bre = [kw_re(k) for k in bonus if k]
        if not mre:
            res.append({"gap": g, "keywords": must[:12], "snippets": []})
            continue
        hits = []
        for skey, url, text in corp:
            if not text:
                continue
            for r in mre:
                for m in r.finditer(text):
                    s, e = max(0, m.start() - win), min(len(text), m.end() + win)
                    w = text[s:e]
                    score = 1 + sum(1 for x in bre if x.search(w)) + sum(1 for x in mre if x.search(w))
                    if g["type"] in ("R3", "R7"):
                        score += 2 * len(re.findall(
                            r"\b\d{1,2} (Sept|Oct|Aug|Nov|May|Jun|Jul|Apr)\b"
                            r"|\d{1,2}月\d{1,2}日"
                            r"|[一二三四五六七八九十]+月[一二三四五六七八九十]+日"
                            r"|\d{1,2}\. (September|Oktober|Mai)"
                            r"|\d{1,2} (września|października)"
                            r"|May the \d{1,2}",
                            w, re.I,
                        ))
                    hd = heading_before(text, s)
                    yr = re.sub(r"\D", "", hd or "")[-4:]
                    if hd and yr.isdigit() and yr[:3] == "194" and g.get("missingDates"):
                        # 日誌類：標頭年份明顯不是本缺口的年 → 丟掉
                        years = {d[:4] for d in g["missingDates"]}
                        if yr not in years and yr not in {"1940", "1939", "1937"}:
                            continue
                    if skey and skey not in existing_keys:
                        score += 3
                    hits.append((score, skey, url, s, e, text))
        hits.sort(key=lambda h: -h[0])
        chosen = []
        for h in hits:
            if any(c[2] == h[2] and not (h[4] < c[3] or h[3] > c[4]) for c in chosen):
                continue
            if sum(1 for c in chosen if c[1] == h[1]) >= 3:
                continue
            chosen.append(h)
            if len(chosen) >= mx:
                break
        snips = []
        for i, (score, skey, url, s, e, text) in enumerate(chosen):
            page = None
            if "\f" in text:
                page = text.count("\f", 0, s) + 1
            else:
                marks = list(re.finditer(r"--\s*(\d+)\s*--", text[:s]))
                if marks:
                    page = int(marks[-1].group(1))
            snips.append({
                "sid": f"{g['id']}#{i}",
                "sourceKey": skey,
                "url": url,
                "pdfPage": page,
                "score": score,
                "dateHeadingBefore": heading_before(text, s),
                "text": mark_page_breaks(text[s:e]),
                "charStart": s,
                "charEnd": e,
            })
        res.append({"gap": g, "keywords": must[:12], "snippets": snips})
    return res


def corpus_from_cache(repo, battle, stage, paths_mod, *, url_substr=None, source_key=None, urls=None):
    """建立 (sourceKey, url, text) 列表。只讀快取，不連網。
    來源：battle.config.json 的 texts.cite（若有）、sources.json 與既有引文的 url、
    以及 ~/wl-source-cache 的 fetch-status。
    """
    out = []
    seen = set()
    cfg = paths_mod.load_battle(repo, battle, "battle.config.json", {}) or {}
    srcs = paths_mod.load_battle(repo, battle, "sources.json", {}) or {}
    texts_cfg = cfg.get("texts") or {}
    work = texts_cfg.get("workDir")
    work_dir = None
    if work:
        # 相對路徑：先試主 repo（上海／波蘭原文在 world_line/.dev/battle/...）
        for root in (Path.home() / "Project/private/world_line", repo):
            cand = (root / work) if not Path(work).is_absolute() else Path(work)
            if cand.exists():
                work_dir = cand
                break
    cite = texts_cfg.get("cite") or {}
    for skey, sp in cite.items():
        if source_key and skey != source_key:
            continue
        kind = sp.get("kind")
        if kind == "paged-html":
            for html, rel in (sp.get("files") or {}).items():
                url = (sp.get("baseUrl") or "") + html
                if url_substr and url_substr not in url:
                    continue
                p = work_dir / rel if work_dir else None
                if p and p.exists():
                    _add(out, seen, skey, url, p.read_text(errors="replace"))
        else:
            url = srcs.get(skey, {}).get("url")
            if url_substr and url and url_substr not in url:
                continue
            p = (work_dir / sp["file"]) if work_dir and sp.get("file") else None
            if p and p.exists():
                _add(out, seen, skey, url, p.read_text(errors="replace"))

    # sources.json 與引文 url：從快取抽文字
    candidates = []
    for k, v in srcs.items():
        if source_key and k != source_key:
            continue
        u = (v.get("url") or "").split("#")[0]
        if u:
            candidates.append((k, u))
    for skey, u in paths_mod.all_citation_urls(repo, battle):
        if source_key and skey and skey != source_key:
            # 引文可能沒帶 sourceKey；仍用 url 過濾
            if source_key not in (skey or ""):
                pass
        candidates.append((skey or source_key, u))
    # 明確指定的 url
    for u in urls or []:
        candidates.append((source_key, u))

    # fetch-status 裡已抓到的新來源
    st = paths_mod.load_json(Path.home() / "wl-source-cache/battles" / battle / "fetch-status.json", {}) or {}
    for url, r in st.items():
        if r.get("status") not in ("fetched", "cached"):
            continue
        candidates.append((r.get("sourceKey") or source_key, url))

    for skey, url in candidates:
        if not url:
            continue
        url = url.split("#")[0]
        if url_substr and url_substr not in url:
            continue
        if url in seen:
            continue
        text, _ = paths_mod.readable_text(url, repo, battle, stage)
        if text:
            _add(out, seen, skey or _guess_source_key(url, srcs), url, text)
    return out


def _guess_source_key(url, srcs):
    for k, v in srcs.items():
        base = (v.get("url") or "").split("#")[0]
        if not base:
            continue
        if url == base or url.startswith(base.rsplit("/", 1)[0] + "/"):
            return k
    return None


def _add(out, seen, skey, url, text):
    url = (url or "").split("#")[0]
    if not url or url in seen or not text:
        return
    seen.add(url)
    out.append({"sourceKey": skey, "url": url, "text": text, "chars": len(text)})


def stats(items, corpus=None):
    n_snip = sum(len(x["snippets"]) for x in items)
    n_chars = sum(len(s["text"]) for x in items for s in x["snippets"])
    n_with = sum(1 for x in items if x["snippets"])
    corp_chars = sum(len(c["text"] if isinstance(c, dict) else c[2]) for c in (corpus or []))
    return {
        "gaps": len(items),
        "gapsWithSnippets": n_with,
        "gapsWithoutSnippets": len(items) - n_with,
        "snippets": n_snip,
        "snippetChars": n_chars,
        "corpusChars": corp_chars,
        "ratio": (n_chars / corp_chars) if corp_chars else None,
    }
