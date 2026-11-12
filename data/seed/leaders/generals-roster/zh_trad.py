#!/usr/bin/env python3
"""將領人名簡→繁（OpenCC s2t，只做字元轉換；不用 s2tw／s2twp 的詞彙替換）。World Line 主管 2026-11-12 10:07。
- OpenCC 裝在使用者層 venv：~/.local/share/wl-opencc-official（pip install opencc==1.4.2；不動系統環境）。
  主迴圈以 `python3 -I` 呼叫 verify.py（-I 不讀使用者 site-packages），所以這裡明確把該 venv 的 site-packages 加進 sys.path。
- PROTECT：本身就是正體字、但 s2t 會依一對多字表改掉而弄錯人名的字（例：里→裏、范→範、余→餘、岳→嶽、于→於、
  征→徵〔板垣征四郎〕、峰→峯、群→羣、岩→巖、涂→塗、占→佔、干→幹）。這些字在人名中保留原字（逐字還原，不是詞彙替換）。
  依據：2026-11-12 對 roster／selection／research 全部 2114 個中文名試轉的結果（patch_name_trad.report.json）。
- to_trad(s) 冪等；is_trad(s) := to_trad(s) == s。
"""
import sys, glob, os
from pathlib import Path

PROTECT = set("里范余岳于征峰群岩涂占干咸采克筑斗布台")
_VENVS = [Path.home() / ".local/share/wl-opencc-official"]
_cc = None

def _load():
    global _cc
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
    return _cc

def to_trad(s):
    if not s:
        return s
    t = _load().convert(s)
    if len(t) != len(s):
        return t  # 長度不同（理論上 s2t 不會發生）：不做逐字還原
    return "".join(a if a in PROTECT else b for a, b in zip(s, t))

def is_trad(s):
    return to_trad(s) == s

if __name__ == "__main__":
    for a in sys.argv[1:]:
        print(a, "→", to_trad(a))
