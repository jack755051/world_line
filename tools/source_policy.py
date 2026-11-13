"""讀 data/source-policy.json（全專案唯一的來源政策）。規則本文：docs/source-rules.md。"""
import json
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parents[1]
POLICY = json.loads((REPO / "data" / "source-policy.json").read_text(encoding="utf-8"))
BANNED_HOSTS = tuple(POLICY["bannedHosts"])
RANK = {"A": 0, "B": 1, "C": 2, "X": 3}


def host(url):
    try:
        return (urlparse(url if "//" in url else "//" + url).hostname or "").lower()
    except Exception:
        return ""


FILE_HOSTS = tuple(POLICY["fileHostsNotSources"])


def banned(url, as_fact_source=True):
    """回傳命中的禁用網域（含子網域）或網域中的禁用字段；沒命中回傳 None。
    as_fact_source=False：只是檔案存放處（地圖、照片掃描）時，不擋 fileHostsNotSources。"""
    h = host(url or "")
    if not h: return None
    for b in BANNED_HOSTS + (FILE_HOSTS if as_fact_source else ()):
        if h == b or h.endswith("." + b): return b
    for label in h.split("."):
        if label in POLICY["bannedHostLabels"]: return label
    return None


def grade_ok(grade, kind):
    """這個等級能不能當這類資料的出處（kind 見 source-policy.json 的 minGrade）。"""
    return grade in RANK and RANK[grade] <= RANK[POLICY["minGrade"][kind]]
