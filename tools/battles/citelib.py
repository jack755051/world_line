"""引文擷取共用庫（由 .dev/battle/poland/build/cite.py 一般化）。
用法（在 builder 內）：
    from citelib import Cites
    C = Cites("poland_1939")
    C("kennedy-dapam-20-255", "逐字片語")  → citation dict（找不到或 > 80 字元即中止）
設定：battle.config.json 的 texts.cite（每個 sourceKey 的本機文字檔、定位方式）、texts.workDir（本機文字所在，.dev 下，不進版控）。
比對：兩邊 NFC、去所有空白、統一引號破折號（與 verify_quotes.py 相同），只容許排版差異。
"""
import json, re, unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TR = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-", "\u00a0": " ", "\u00ad": "", "„": '"'})


def norm(s):
    return re.sub(r"\s+", "", unicodedata.normalize("NFC", s).translate(TR))


class Cites:
    def __init__(self, battle, accessed="2026-11-13"):
        self.D = REPO / "data/seed/battles" / battle
        cfg = json.loads((self.D / "battle.config.json").read_text())["texts"]
        self.spec, self.work = cfg["cite"], REPO / cfg["workDir"]
        self.src = json.loads((self.D / "sources.json").read_text())
        self.accessed, self._t = accessed, {}

    def _txt(self, rel):
        if rel not in self._t:
            self._t[rel] = (self.work / rel).read_text(errors="replace")
        return self._t[rel]

    def __call__(self, key, phrase, note=None):
        if len(phrase) > 80:
            raise SystemExit(f"引文超過 80 字元：{phrase}")
        sp, s, np = self.spec[key], self.src[key], norm(phrase)
        c = {"sourceKey": key, "quote": phrase, "quoteLang": sp["lang"], "accessedOn": self.accessed, "grade": s["grade"]}
        if sp["kind"] == "paged-html":
            for html, rel in sp["files"].items():
                t = self._txt(rel)
                idx = [i for i, ch in enumerate(t) if not ch.isspace()]
                k = norm("".join(t[i] for i in idx)).find(np)
                if k < 0:
                    continue
                m = re.search(sp["pageMarker"], t[idx[min(k, len(idx) - 1)]:])
                loc = f"{sp['unpagedLocator']} (HyperWar {html})" if html in sp.get("unpaged", []) or not m else f"p. {m.group(1)} (HyperWar {html})"
                c.update(locator=loc, url=sp["baseUrl"] + html)
                break
            else:
                raise SystemExit(f"找不到 {key}：{phrase}")
        else:
            t = self._txt(sp["file"])
            if np not in norm(t):
                raise SystemExit(f"找不到 {key}：{phrase}")
            loc = sp["locator"]
            if sp["kind"] == "pdf-text":
                for i, pg in enumerate(t.split("\f")):
                    if np in norm(pg):
                        loc += f"，PDF 第 {i + 1} 頁"; break
            c.update(locator=loc, url=s["url"])
        c = {k: c[k] for k in ("sourceKey", "locator", "quote", "quoteLang", "url", "accessedOn", "grade")}
        if note:
            c["note"] = note
        return c

    def short(self, key):
        return lambda p, n=None: self(key, p, n)
