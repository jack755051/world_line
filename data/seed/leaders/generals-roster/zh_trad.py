#!/usr/bin/env python3
"""將領人名簡→繁→台灣標準字形（OpenCC s2t → t2tw；只做字元／字形轉換，不用 s2twp 的詞彙替換）。
World Line 主管 2026-11-12 10:07（s2t）、10:20（加 t2tw 台灣字形，例 衆→眾、棱→稜；「台」不轉「臺」）。
- t2tw 設定＝TWVariantsPhrases＋TWVariants（異體字表，非 TWPhrases 詞彙表）。2026-11-12 10:25 對全部 3038 個中文名（含原字串）
  比較「官方 t2tw」與「只用 TWVariants.ocd2 的字元版」：兩者結果完全相同（4 筆：衆→眾 ×2、棱→稜 ×2），採官方 t2tw。
- PRE（s2t 之前逐字替換）：s2t 一對多選錯、t2tw 也不會改回的人名用字。冲→沖（s2t 給「衝」；人名用「沖」，例 張沖、彭沖）。
- OpenCC 裝在使用者層 venv：~/.local/share/wl-opencc-official（pip install opencc==1.4.2；不動系統環境）。
  主迴圈以 `python3 -I` 呼叫 verify.py（-I 不讀使用者 site-packages），所以這裡明確把該 venv 的 site-packages 加進 sys.path。
- PROTECT：本身就是正體字、但 s2t 會依一對多字表改掉而弄錯人名的字（例：里→裏、范→範、余→餘、岳→嶽、于→於、
  征→徵〔板垣征四郎〕、峰→峯、群→羣、岩→巖、涂→塗、占→佔、干→幹）。這些字在人名中保留原字（逐字還原，不是詞彙替換）。
  依據：2026-11-12 對 roster／selection／research 全部 2114 個中文名試轉的結果（patch_name_trad.report.json）。
- to_trad(s) 冪等；is_trad(s) := to_trad(s) == s。
"""
import sys, glob, os
from pathlib import Path

PROTECT = set("里范余岳于征峰群岩涂占干咸采克筑斗布台")  # 台：永不轉臺（主管 10:20）
PRE = {"冲": "沖"}
_VENVS = [Path.home() / ".local/share/wl-opencc-official"]
_cc = None
_tw = None

def _load():
    global _cc, _tw
    if _cc is not None:
        return _cc
    try:
        import opencc  # noqa
    except ImportError:
        for v in _VENVS:
            for sp in glob.glob(str(v / "lib/python*/site-packages")):
                if sp not in sys.path:
                    sys.path.append(sp)
        import opencc  # 仍失敗就讓呼叫端得到 ImportError
    _cc = opencc.OpenCC("s2t")
    _tw = opencc.OpenCC("t2tw")
    return _cc

def to_trad(s):
    if not s:
        return s
    s1 = "".join(PRE.get(c, c) for c in s)
    cc = _load()
    t = _tw.convert(cc.convert(s1))
    if len(t) != len(s1):
        return t  # 長度不同（理論上不會發生）：不做逐字還原
    return "".join(a if a in PROTECT else b for a, b in zip(s1, t))

def is_trad(s):
    return to_trad(s) == s

if __name__ == "__main__":
    for a in sys.argv[1:]:
        print(a, "→", to_trad(a))
