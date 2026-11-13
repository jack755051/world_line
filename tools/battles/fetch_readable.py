"""把 HTML 出處轉成保留換行的純文字，供人工找引文與 citelib 定位（由 .dev/battle/poland/readable.py 一般化）。
用法：python3 -I tools/battles/fetch_readable.py <battle>
設定：battle.config.json 的 texts.readable {名稱: 網址}、texts.workDir；輸出 <workDir>/rd/<名稱>.txt。
抓取經 verify_quotes.py 的 fetch（同一快取 .dev/battle-cache/、同站間隔 ≥ 1 秒、不用 curl -k）。
"""
import hashlib, html, json, re, runpy, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def main():
    battle = sys.argv[1]
    cfg = json.loads((REPO / "data/seed/battles" / battle / "battle.config.json").read_text())["texts"]
    vq = runpy.run_path(str(REPO / "tools/battles/verify_quotes.py"), run_name="vq")
    out = REPO / cfg["workDir"] / "rd"; out.mkdir(parents=True, exist_ok=True)
    for name, url in cfg["readable"].items():
        vq["fetch"](url)
        raw = (vq["CACHE"] / (hashlib.sha256(url.encode()).hexdigest()[:24] + ".raw")).read_bytes()
        try:
            t = raw.decode("utf-8")
        except UnicodeDecodeError:
            t = raw.decode("cp1252", "replace")
        t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", t)
        t = re.sub(r"(?i)<(br|p|h\d|tr|li|div|table)[^>]*>", "\n", t)
        t = html.unescape(re.sub(r"<[^>]+>", "", t))
        t = re.sub(r"[ \t]+\n", "\n", t); t = re.sub(r"\n{3,}", "\n\n", t)
        (out / f"{name}.txt").write_text(t)
        print(name, len(t))


if __name__ == "__main__":
    main()
