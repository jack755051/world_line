#!/usr/bin/env python3
"""舊格式人物生平：一般百科出處逐頁確認具名作者（接 apply_source_grades.py 的 gradePending；Tai 2026-11-14「好」）。

規則（docs/source-rules.md §2）：有個人署名的條目＝B（具名作者的百科條目）；只有編輯部或無署名＝C；判斷不了的維持待評。
各站作者位置：
- encyclopedia.com：同頁可有多部參考書的條目，每條結尾 <p>（縮排）署名＋bylinecontainer 書名；以 seed 的 evidence／locator 文字對到條目，
  對不到時，全頁條目一致（都署名或都不署名）才判，否則待評。
- vle.lt：POST /ajax.php（module=News, action=LoadVleNews, news_id=頁面 data-load-news-id），文章內 .aut 的 id 對回作者名冊。
- snl.no：author-list 的 itemprop=name；只有「Store norske leksikon」或編輯部＝C。
- lex.dk：JSON-LD author；只有「redaktion」＝C。
- encyclopediaofukraine.com：文末「[This article originally appeared…]」前一段若是人名＝署名。
- enciclopedia.cat：頁面只見縮寫「Col·laboració: XXX」或無署名＝C（無全名，不算具名作者）。
原始頁面存 ~/wl-source-cache/old-format-enc/（不進版控），manifest 記 sha256。
用法（repo 根目錄）：python3 -I data/seed/leaders/gap-830/check_encyclopedia_authors.py [--apply]
"""
import json, glob, re, sys, time, html, hashlib, subprocess, collections, unicodedata
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parents[4]
CACHE = Path.home() / "wl-source-cache" / "old-format-enc"
RUN = "old-format-enc-authors-2026-11-14"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"


def fetch(url, post=None):
    key = hashlib.sha256((url + "|" + (post or "")).encode()).hexdigest()[:20]
    p = CACHE / (key + (".json" if post else ".html"))
    if p.exists() and p.stat().st_size > 500:
        return p.read_text(errors="replace")
    CACHE.mkdir(parents=True, exist_ok=True)
    cmd = ["curl", "-sL", "--max-time", "40", "-A", UA, url] + (["-X", "POST", "-d", post] if post else [])
    r = subprocess.run(cmd, capture_output=True)
    time.sleep(0.6)
    if r.returncode or len(r.stdout) < 500:
        return None
    p.write_bytes(r.stdout)
    with open(CACHE / "manifest.jsonl", "a") as m:
        m.write(json.dumps({"url": url, "post": post, "file": p.name, "sha256": hashlib.sha256(r.stdout).hexdigest(), "run": RUN}) + "\n")
    return r.stdout.decode("utf-8", errors="replace")


def text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def norm(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s or "")).strip().lower()


EDITORIAL = re.compile(r"redaktion|redaksjon|redakcija|editors?\b|store norske leksikon|leksikon \(|encyclopedia\.com|gale", re.I)


def judge_ec(page, src):
    parts = page.split('class="bylinecontainer"')
    entries = []
    for i in range(len(parts) - 1):
        body = parts[i]
        book = text(re.search(r"<span>(.*?)</span>", parts[i + 1]).group(1)) if re.search(r"<span>(.*?)</span>", parts[i + 1]) else ""
        last_p = re.findall(r"(?s)<p>(.*?)</p>", body[-3000:])
        author = None
        if last_p:
            raw = last_p[-1]
            if raw.startswith("\xa0") or raw.startswith("&nbsp;"):
                cand = text(raw)
                if cand and len(cand) < 120 and not EDITORIAL.search(cand):
                    author = cand
        start = body.rfind('class="bylinecontainer"')
        entries.append({"book": book, "author": author, "text": norm(text(body[-60000:]))})
    if not entries:
        return None
    ev = norm(src.get("evidence") or "")
    hit = [e for e in entries if ev and len(ev) > 8 and ev[:80] in e["text"]]
    pick = hit[-1:] or [e for e in entries if norm(e["book"]) and norm(e["book"]) in norm((src.get("publisher") or "") + " " + (src.get("title") or ""))][:1]
    if pick:
        e = pick[0]
        return ("B", "具名作者 %s（%s，Encyclopedia.com）" % (e["author"], e["book"])) if e["author"] else ("C", "無署名條目（%s，Encyclopedia.com）" % e["book"])
    if all(e["author"] for e in entries):
        return ("B", "同頁條目皆具名（%s）" % "；".join(sorted({e["author"] for e in entries}))[:200])
    if not any(e["author"] for e in entries):
        return ("C", "同頁條目皆無署名（Encyclopedia.com）")
    return None


def judge_vle(page, src):
    m = re.search(r'data-load-news-id="(\d+)"', page)
    if not m:
        return None
    raw = fetch("https://www.vle.lt/ajax.php", "module=News&action=LoadVleNews&news_id=" + m.group(1))
    if not raw:
        return None
    d = json.loads(raw)
    content = (((d.get("return") or {}).get("article") or {}).get("main_article") or {}).get("news_data") or ""
    ids = re.findall(r'class="aut"[^>]*>\s*([^<]+?)\s*<', content)
    roster = (d.get("return") or {}).get("authors") or {}
    names = [("%s %s" % (roster[i].get("FirstName", ""), roster[i].get("LastName", ""))).strip() for i in dict.fromkeys(ids) if i in roster]
    names = [n for n in names if n and not EDITORIAL.search(n)]
    return ("B", "具名作者 %s（VLE）" % "、".join(names)) if names else ("C", "條目無署名（VLE）")


def judge_snl(page, src):
    names = [text(x) for x in re.findall(r'(?s)class="author-list__author".*?itemprop="name">(.*?)</span>', page)]
    if not names:
        return ("C", "條目無署名（SNL）") if "author-list" not in page else None
    persons = [n for n in names if not EDITORIAL.search(n)]
    return ("B", "具名作者 %s（SNL）" % "、".join(persons)) if persons else ("C", "只有編輯部署名：%s（SNL）" % "、".join(names))


def judge_lex(page, src):
    names = []
    for m in re.finditer(r'(?s)<script type="application/ld\+json">(.*?)</script>', page):
        try:
            j = json.loads(m.group(1))
        except Exception:
            continue
        for x in (j if isinstance(j, list) else [j]):
            a = x.get("author") if isinstance(x, dict) else None
            for y in (a if isinstance(a, list) else [a] if a else []):
                if isinstance(y, dict) and y.get("name"):
                    names.append(text(y["name"]).replace("\xad", ""))
    if not names:
        return None
    persons = [n for n in names if not EDITORIAL.search(n)]
    return ("B", "具名作者 %s（lex.dk）" % "、".join(persons)) if persons else ("C", "只有編輯部署名：%s（lex.dk）" % "、".join(names))


def judge_eu(page, src):
    t = text(page)
    m = re.search(r"\[This article (?:originally appeared|was updated)", t)  # 兩種文末標記
    if not m:
        return None
    tail = t[max(0, m.start() - 200):m.start()].strip()
    last = re.split(r"[.!?)\]]\s+", tail)[-1].strip()  # 署名前可能是書目的括號
    if last and re.fullmatch(r"(?:[A-ZÀ-ŽІЇЄ][\w'’.-]+\s+){1,3}[A-ZÀ-ŽІЇЄ][\w'’.-]+(?:\s*,\s*(?:[A-ZÀ-ŽІЇЄ][\w'’.-]+\s+){1,3}[A-ZÀ-ŽІЇЄ][\w'’.-]+)*", last):
        return ("B", "具名作者 %s（Encyclopedia of Ukraine）" % last)
    return ("C", "條目無署名（Encyclopedia of Ukraine）")


def judge_cat(page, src):
    m = re.search(r"Col·laboració:\s*([^<]{1,60})", page)
    return ("C", "只有縮寫署名 %s，無全名（Enciclopèdia.cat）" % text(m.group(1)) if m else "條目無署名（Enciclopèdia.cat）")


JUDGE = {"encyclopedia.com": judge_ec, "vle.lt": judge_vle, "snl.no": judge_snl, "lex.dk": judge_lex,
         "encyclopediaofukraine.com": judge_eu, "enciclopedia.cat": judge_cat}


def main():
    apply = "--apply" in sys.argv
    files = sorted(glob.glob(str(REPO / "data/seed/leaders/gap-830/*/research.json")) +
                   glob.glob(str(REPO / "data/seed/leaders/batch-p1-20261107/**/research.json"), recursive=True))
    stat, fails, detail = collections.Counter(), collections.Counter(), []
    for f in files:
        raw = Path(f).read_text(); d = json.loads(raw); changed = False
        def walk(o):
            nonlocal changed
            if isinstance(o, dict):
                if "url" in o and o.get("gradePending"):
                    h = (urlparse(o["url"]).hostname or "").lower().removeprefix("www.")
                    page = fetch(o["url"])
                    res = JUDGE[h](page, o) if page and h in JUDGE else None
                    if res is None:
                        fails[h] += 1; detail.append((h, o["url"], "判斷不了"))
                    else:
                        o["grade"], o["gradeBasis"] = res[0], res[1] + "（%s）" % RUN
                        o.pop("gradePending", None); changed = True; stat[(h, res[0])] += 1
                for v in o.values(): walk(v)
            elif isinstance(o, list):
                for v in o: walk(v)
        walk(d)
        if apply and changed:
            ind = 2 if raw.startswith("{\n  ") else 1
            Path(f).write_text(json.dumps(d, ensure_ascii=False, indent=ind) + ("\n" if raw.endswith("\n") else ""))
    print(json.dumps({"apply": apply, "graded": {"%s %s" % k: v for k, v in sorted(stat.items())}, "still_pending": dict(fails),
                      "pending_samples": detail[:15]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
