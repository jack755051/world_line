"""戰役資料引文逐字自檢（可重跑；Tai 2026-11-13 13:39 流程修正第 1 項）。

用法：python3 -I tools/battles/verify_quotes.py <battle>            # 只檢查，寫報告
      python3 -I tools/battles/verify_quotes.py <battle> --apply    # 另把結果寫回各檔（quoteCheck 欄）、失敗者降級並記入 gaps.json

範圍：data/seed/battles/<battle>/ 下所有 *.json 中帶 quote 與 url 的引文物件（含 leads；leads 不影響事實）。
做法：依 url 抓原文（HTML 去標籤；PDF 用 pdftotext），以 utf-8 與 cp1252 兩種解碼；
      比對時兩邊都做 NFC、去除所有空白、統一彎引號與破折號——只容許排版差異，文字必須逐字相同。
      PDF（公報 OCR）另試「去掉行尾連字號」一種寬鬆比對，命中者標 verbatim-pdf-hyphen（仍算通過，但標出）。
結果：quoteCheck = {"status": "verbatim"|"verbatim-pdf-hyphen"|"failed"|"fetch_error", "checkedOn", "tool"}。
      --apply 時 failed／fetch_error 的引文：grade 原值移到 gradeBeforeCheck、grade 改 null（不得當事實用），並在 gaps.json 追加一條。
快取：.dev/battle-cache/（不進版控）。不用 curl -k；同站請求間隔 ≥ 1 秒。
報告：data/seed/battles/<battle>/checks/quote-check.json
"""
import datetime, hashlib, html, json, re, subprocess, sys, time, unicodedata, urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
UA = "WorldLine-research/0.1"
CACHE = REPO / ".dev" / "battle-cache"
TODAY = datetime.date.today().isoformat()
sys.path.insert(0, str(REPO / "tools"))
from source_policy import BANNED_HOSTS as BANNED  # 全專案唯一清單：data/source-policy.json
_last = {}


def fetch(url):
    CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(url.encode()).hexdigest()[:24]
    raw_p = CACHE / (key + ".raw")
    if not raw_p.exists():
        host = url.split("/")[2]
        wait = 1.1 - (time.time() - _last.get(host, 0))
        if wait > 0: time.sleep(wait)
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        raw_p.write_bytes(urllib.request.urlopen(req, timeout=60).read()); _last[host] = time.time()
    raw = raw_p.read_bytes()
    if raw[:5] == b"%PDF-":
        outs = []
        for mode in ("", "-layout"):  # 公報雙欄：預設閱讀順序與 -layout 兩種都試
            txt_p = CACHE / (key + (mode or "-flow") + ".txt")
            if not txt_p.exists():
                subprocess.run(["pdftotext"] + ([mode] if mode else []) + [str(raw_p), str(txt_p)], check=True)
            outs.append(txt_p.read_text(errors="replace"))
        return outs, True
    out = []
    for enc in ("utf-8", "cp1252"):
        t = raw.decode(enc, "replace")
        if url.split("?")[0].lower().endswith(".txt"):   # 純文字檔（例：archive.org 的 OCR 文字）：零散的 < > 不是標籤，不去標籤
            out.append(t); continue
        t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", t)
        out.append(html.unescape(re.sub(r"<[^>]+>", " ", t)))
    return out, False


TR = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-", "\u00a0": " ", "\u00ad": ""})


def norm(s):
    return re.sub(r"\s+", "", unicodedata.normalize("NFC", s).translate(TR))


def cites(o, path=""):
    if isinstance(o, dict):
        if isinstance(o.get("quote"), str) and o.get("quote").strip():
            yield path, o
        for k, v in o.items():
            yield from cites(v, path + "." + k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from cites(v, path + "[%d]" % i)


def main():
    battle = sys.argv[1]; apply = "--apply" in sys.argv
    D = REPO / "data" / "seed" / "battles" / battle
    files = sorted(p for p in D.glob("*.json"))
    rows, docs, qc = [], {}, {}
    for f in files:
        d = json.loads(f.read_text()); docs[f] = d
        for path, c in list(cites(d)):
            url = (c.get("url") or "").split("#")[0]
            r = {"file": f.name, "path": path, "url": url, "locator": c.get("locator"), "quote": c["quote"], "isLead": ".leads" in path}
            if not url:
                r["status"] = "fetch_error"; r["why"] = "無 url"
            elif any(b in url for b in BANNED):
                r["status"] = "failed"; r["why"] = "禁用網域"
            else:
                try:
                    texts, is_pdf = fetch(url)
                    q = norm(c["quote"])
                    if any(q in norm(t) for t in texts):
                        r["status"] = "verbatim"
                    elif is_pdf and any(q.replace("-", "") in norm(t).replace("-", "") for t in texts):
                        r["status"] = "verbatim-pdf-hyphen"
                    else:
                        r["status"] = "failed"; r["why"] = "原文找不到逐字相同字串"
                    if len(c["quote"]) > 80: r["long"] = len(c["quote"])
                except Exception as e:
                    r["status"] = "fetch_error"; r["why"] = str(e)[:120]
            rows.append(r)
            qc[id(c)] = r
    from collections import Counter
    summ = {"battle": battle, "checkedOn": TODAY, "total": len(rows), "byStatus": dict(Counter(r["status"] for r in rows)),
            "facts": dict(Counter(r["status"] for r in rows if not r["isLead"])), "over80": sum(1 for r in rows if r.get("long")),
            "byFile": {f.name: dict(Counter(r["status"] for r in rows if r["file"] == f.name)) for f in files if any(r["file"] == f.name for r in rows)}}
    (D / "checks").mkdir(exist_ok=True)
    (D / "checks" / "quote-check.json").write_text(json.dumps({"summary": summ, "failures": [r for r in rows if r["status"] not in ("verbatim",)]},
                                                             ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    newgaps = []
    for f, d in docs.items():
        for path, c in list(cites(d)):
            r = qc.get(id(c))
            if not (apply and r): continue
            c["quoteCheck"] = {"status": r["status"], "checkedOn": TODAY, "tool": "tools/battles/verify_quotes.py"}
            if r["status"] in ("failed", "fetch_error"):
                if c.get("grade") is not None:
                    c["gradeBeforeCheck"] = c["grade"]; c["grade"] = None
                newgaps.append({"target": f"quote:{f.name}{path}", "kind": "quote_check_failed", "note": f"引文自檢未通過（{r.get('why')}）：{r['quote'][:60]}", "checkedOn": TODAY})
        if apply:
            f.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if apply and newgaps:
        G = D / "gaps.json"; g = json.loads(G.read_text())
        known = {x.get("target") for x in g["gaps"]}
        g["gaps"] += [x for x in newgaps if x["target"] not in known]
        G.write_text(json.dumps(g, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summ, ensure_ascii=False, indent=1))
    sys.exit(0 if summ["facts"].get("failed", 0) + summ["facts"].get("fetch_error", 0) == 0 else 1)


if __name__ == "__main__":
    main()
