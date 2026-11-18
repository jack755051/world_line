#!/usr/bin/env python3
"""抽查：依 md5(id) 排序，從 results/*.json 取直接採用與重摘各 N 筆，抓該筆原本出處 URL（一般 curl，
不加 -k、不登入、不換來源），轉純文字後核對 quote 是否逐字出現（NFC、空白正規化；另記是否需忽略大小寫）。
「是否支持欄位值」由人工判讀後填入 spotcheck.json 的 supports／note。
用法：python3 spotcheck.py fetch [每類筆數，預設 18]
輸出：spotcheck/pages/<sha1(url)>.html（快取，不進版控）、spotcheck.json
"""
import glob
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.join(HERE, "spotcheck", "pages")


def norm(s):
    s = unicodedata.normalize("NFC", html.unescape(s))
    s = s.replace(" ", " ").replace("­", "")
    return re.sub(r"\s+", " ", s).strip()


def page_text(raw):
    raw = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    return norm(raw)


def fetch(url):
    os.makedirs(PAGES, exist_ok=True)
    p = os.path.join(PAGES, hashlib.sha1(url.encode()).hexdigest() + ".html")
    if not os.path.exists(p):
        r = subprocess.run(["curl", "-sSL", "--max-time", "40", "-A", "Mozilla/5.0 (compatible; source-check)",
                            "-o", p, "-w", "%{http_code}", url], capture_output=True, text=True)
        if r.returncode != 0 or not r.stdout.startswith("2"):
            if os.path.exists(p):
                os.remove(p)
            return None, f"curl rc={r.returncode} http={r.stdout} {r.stderr.strip()[:120]}"
    data = open(p, "rb").read()
    if data[:5] == b"%PDF-":  # PDF：pdftotext 抽字（poppler）
        r = subprocess.run(["pdftotext", "-enc", "UTF-8", p, "-"], capture_output=True)
        return norm(r.stdout.decode("utf-8", errors="replace")), "ok(pdf)"
    return page_text(data.decode("utf-8", errors="replace")), "ok"


def main(n):
    rows = [r for f in sorted(glob.glob(os.path.join(HERE, "results", "r*.json")))
            for r in json.load(open(f, encoding="utf-8"))["rows"]]
    pick = []
    for m in ("direct", "requote"):
        rs = sorted((r for r in rows if r["method"] == m), key=lambda r: hashlib.md5(r["id"].encode()).hexdigest())
        pick += rs[:n]
    out = []
    for r in pick:
        text, st = fetch(r["url"])
        q = norm(r["quote"])
        found = None
        if text is not None:
            nows = lambda x: re.sub(r"\s+", "", x)
            found = ("exact" if q in text else
                     "exact_ignoring_whitespace" if nows(q) in nows(text) else  # HTML 去標籤／PDF 換行造成的空白差異
                     "casefold" if q.casefold() in text.casefold() else "not_found")
        out.append({"id": r["id"], "method": r["method"], "field": r["field"], "url": r["url"],
                    "quote": r["quote"], "fetch": st, "verbatimInSource": found,
                    "quoteInStoredEvidence": True if r["method"] == "direct" else norm(r["quote"]) in norm(r["evidence"]),
                    "supports": None, "note": ""})
    json.dump(out, open(os.path.join(HERE, "spotcheck.json"), "w"), ensure_ascii=False, indent=1)
    from collections import Counter
    print(Counter((o["method"], o["verbatimInSource"]) for o in out))


if __name__ == "__main__":
    main(int(sys.argv[2]) if len(sys.argv) > 2 else 18)
