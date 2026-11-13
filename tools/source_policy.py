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


def banned(url):
    """回傳命中的禁用網域（含子網域）或網域中的禁用字段；沒命中回傳 None。"""
    h = host(url or "")
    if not h: return None
    for b in BANNED_HOSTS:
        if h == b or h.endswith("." + b): return b
    for label in h.split("."):
        if label in POLICY["bannedHostLabels"]: return label
    return None


def grade_ok(grade, kind):
    """這個等級能不能當這類資料的出處（kind 見 source-policy.json 的 minGrade）。"""
    return grade in RANK and RANK[grade] <= RANK[POLICY["minGrade"][kind]]
