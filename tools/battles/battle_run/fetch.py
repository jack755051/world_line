"""把新來源原文抓到 ~/wl-source-cache/battles/<battle>/raw/（快取鍵與 verify_quotes.py 相同）。

規則：已在任一快取就不再抓；禁用網域不抓；同站間隔 ≥ 1.1 秒；
不用 curl -k、不換瀏覽器 UA、不繞過：HTTP 401/403/429/503、Cloudflare／Anubis／captcha／登入頁 → 記 blocked，不存檔。
不用 Wayback（web.archive.org）。archive.org 書籍掃描全文可以。
本模組不寫 repo。
"""
from __future__ import annotations

import datetime
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from . import paths

_last = {}
BLOCK_MARKERS = [
    ("cloudflare", r"cf-chl|challenge-platform|Just a moment\.\.\.|Attention Required! \| Cloudflare"),
    ("anubis", r"anubis|Making sure you(&#39;|')re not a bot"),
    ("captcha", r"g-recaptcha|hcaptcha|captcha-delivery|px-captcha|Incapsula|_Incapsula_Resource|distil_r_captcha"),
    ("login", r"<form[^>]+(login|signin|sign-in)[^>]*>.*?type=.password"),
]
MAXB = 40 * 1024 * 1024


def canon(url):
    return urllib.parse.quote(url.split("#")[0], safe=":/?#[]@!$&'()*+,;=%~")


def resolve_archive(u):
    m = re.match(r"https?://archive\.org/details/([^/?#]+)", u)
    if not m:
        return u
    host = "archive.org"
    w = 1.1 - (time.time() - _last.get(host, 0))
    if w > 0:
        time.sleep(w)
    try:
        req = urllib.request.Request(f"https://archive.org/metadata/{m.group(1)}/files", headers={"User-Agent": paths.UA})
        files = json.loads(urllib.request.urlopen(req, timeout=60).read())["result"]
    except Exception:
        return u
    finally:
        _last[host] = time.time()
    txt = [f["name"] for f in files if f["name"].endswith("_djvu.txt")]
    return f"https://archive.org/download/{m.group(1)}/" + urllib.parse.quote(txt[0]) if txt else u


def fetch_one(repo, battle, stage, url, skey, st):
    url = canon(url)
    key = paths.ukey(url)
    d = paths.writable_cache(battle, stage)
    tdir = d.parent / "text" if d.name == "raw" else Path(stage) / "cache" / "text"
    # prefer ~/wl-source-cache/battles/<b>/text
    cache_root = Path.home() / "wl-source-cache/battles" / battle
    tdir = cache_root / "text"
    tdir.mkdir(parents=True, exist_ok=True)
    rec = {"sourceKey": skey, "key": key, "checkedOn": datetime.date.today().isoformat()}
    hit = paths.banned(url)
    if hit:
        rec.update(status="banned", why=f"禁用網域 {hit}")
        st[url] = rec
        return rec
    if "web.archive.org" in url:
        rec.update(status="banned", why="不用 Wayback（web.archive.org）")
        st[url] = rec
        return rec
    p = paths.find_raw(url, repo, battle, stage)
    if p:
        rec.update(status="cached", where=str(p.parent))
    else:
        if st.get(url, {}).get("status") == "blocked":
            return st[url]
        host = url.split("/")[2]
        w = 1.1 - (time.time() - _last.get(host, 0))
        if w > 0:
            time.sleep(w)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": paths.UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read(MAXB + 1)
                final = r.geturl()
                ctype = r.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            _last[host] = time.time()
            rec.update(status="blocked" if e.code in (401, 403, 429, 451, 503) else "error", why=f"HTTP {e.code}")
            st[url] = rec
            return rec
        except Exception as e:
            _last[host] = time.time()
            rec.update(status="error", why=str(e)[:150])
            st[url] = rec
            return rec
        _last[host] = time.time()
        head = raw[:200000].decode("utf-8", "replace")
        for name, pat in BLOCK_MARKERS:
            if raw[:5] != b"%PDF-" and re.search(pat, head, re.I | re.S) and len(re.sub(r"<[^>]+>", "", head)) < 20000:
                rec.update(status="blocked", why=f"{name} 頁面（不繞過）")
                st[url] = rec
                return rec
        if len(raw) > MAXB:
            rec.update(status="error", why="超過 40MB，未存")
            st[url] = rec
            return rec
        if final.split("#")[0] != url:
            rec["redirectedTo"] = final
        (d / (key + ".raw")).write_bytes(raw)
        p = d / (key + ".raw")
        rec.update(status="fetched", bytes=len(raw), contentType=ctype)
    text, is_pdf = paths.readable_text(url, repo, battle, stage)
    if text is not None:
        (tdir / f"{key}.txt").write_text(text, encoding="utf-8")
        rec.update(textChars=len(text), pdf=bool(is_pdf))
        if len(text.strip()) < 500:
            rec["warn"] = "可讀文字少於 500 字元（可能是空殼頁、JS 載入或掃描無文字層）"
    st[url] = rec
    return rec


def run(repo, battle, stage):
    sc = paths.load_json(Path(stage) / "sources-candidates.json", {"sources": []})
    sp = Path.home() / "wl-source-cache/battles" / battle / "fetch-status.json"
    st = paths.load_json(sp, {}) or {}
    rows = []
    for s in sc.get("sources") or []:
        s["urls"] = [canon(resolve_archive(u)) for u in (s.get("urls") or [s.get("url")]) if u]
        for u in s["urls"]:
            r = fetch_one(repo, battle, stage, u, s["sourceKey"], st)
            rows.append(r)
            print(f"{r['status']:8} {s['sourceKey']:32} {u[:90]} {r.get('why','')} {r.get('warn','')}", flush=True)
            paths.write_json(sp, st)
    paths.write_json(sp, st)
    paths.write_json(Path(stage) / "sources-candidates.json", sc)
    return rows
