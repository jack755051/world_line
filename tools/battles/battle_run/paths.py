"""路徑、唯讀載入戰役資料、與 repo 相同的正規化／禁用網域／快取鍵。

放入 repo 後，以 tools/battles/verify_quotes.py 與 tools/source_policy.py 為準，
不重寫規則。任何寫入都只進 staging 或 ~/wl-source-cache，絕不寫進
data/seed/battles 或 repo 的 .dev/battle-cache。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import runpy
import shutil
import sys
import unicodedata
from pathlib import Path

# 在匯入 repo 腳本之前關掉 bytecode，避免在 tools/ 留下 __pycache__。
sys.dont_write_bytecode = True

UA = "WorldLine-research/0.1"
PAGE_BREAK = "⟨分頁⟩"
# HyperWar / Kennedy 類頁碼標記
PAGE_MARK_RE = re.compile(r"--\s*(\d+)\s*--")

_VQ = None
_SP = None
_REPO = None


def detect_repo(explicit=None):
    """找到 world_line-battle-demo。腳本若尚未放進 repo，不要把 skill 目錄當成 repo。"""
    cands = []
    if explicit:
        cands.append(Path(explicit).expanduser().resolve())
    env = os.environ.get("WL_BATTLE_REPO")
    if env:
        cands.append(Path(env).expanduser().resolve())
    cwd = Path.cwd().resolve()
    cands.append(cwd)
    cands.extend(cwd.parents)
    # tools/battles/battle_run/paths.py → parents[3] 在安裝後是 repo
    here = Path(__file__).resolve()
    if len(here.parents) >= 4:
        cands.append(here.parents[3])
    cands.append(Path.home() / "Project/private/world_line-battle-demo")
    seen = set()
    for p in cands:
        if p in seen:
            continue
        seen.add(p)
        if (p / "data/seed/battles").is_dir() and (p / "tools/battles/verify_quotes.py").is_file():
            return p
    raise SystemExit("找不到 world_line-battle-demo，請加 --repo 或設 WL_BATTLE_REPO")


def _load_repo_tools(repo: Path):
    global _VQ, _SP, _REPO
    if _REPO == repo and _VQ is not None:
        return
    sys.path.insert(0, str(repo / "tools"))
    import source_policy as SP  # noqa: E402
    _SP = SP
    _VQ = runpy.run_path(str(repo / "tools/battles/verify_quotes.py"), run_name="vq_battle_run")
    _REPO = repo


def bind_repo(repo: Path):
    """之後的 norm／banned／fetch 都用這個 repo 的腳本。"""
    repo = Path(repo).resolve()
    _load_repo_tools(repo)
    return repo


def norm(s: str) -> str:
    """與 tools/battles/verify_quotes.py 相同。測試若尚未 bind_repo，用同一套規則的本地實作。"""
    if _VQ is not None:
        return _VQ["norm"](s)
    tr = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-", "\u00a0": " ", "\u00ad": ""})
    return re.sub(r"\s+", "", unicodedata.normalize("NFC", s).translate(tr))


def banned(url: str):
    if _SP is None:
        return None
    return _SP.banned(url)


def ukey(url: str) -> str:
    """與 verify_quotes.py 相同的快取鍵：sha256(url)[:24]（先去掉 fragment）。"""
    return hashlib.sha256(url.split("#")[0].encode()).hexdigest()[:24]


def default_stage_root() -> Path:
    return Path.home() / "wl-battle-staging"


def cache_roots(repo: Path, battle: str, stage: Path | None = None):
    """唯讀搜尋原文的目錄，先自己的快取，再兩個 repo 的 .dev/battle-cache。"""
    roots = []
    extra = os.environ.get("WL_BATTLE_CACHE")
    if extra:
        roots.append(Path(extra).expanduser())
    roots.append(Path.home() / "wl-source-cache/battles" / battle / "raw")
    if stage:
        roots.append(Path(stage) / "cache" / "raw")
    roots.append(repo / ".dev/battle-cache")
    main = Path.home() / "Project/private/world_line"
    if main.exists():
        roots.append(main / ".dev/battle-cache")
    return roots


def find_raw(url: str, repo: Path, battle: str, stage: Path | None = None) -> Path | None:
    name = ukey(url) + ".raw"
    for d in cache_roots(repo, battle, stage):
        p = d / name
        if p.is_file():
            return p
    return None


def writable_cache(battle: str, stage: Path | None = None) -> Path:
    """寫入用快取（複製 raw、pdftotext 產品）。不寫 repo。"""
    d = Path.home() / "wl-source-cache/battles" / battle / "raw"
    try:
        d.mkdir(parents=True, exist_ok=True)
        return d
    except OSError:
        d = (stage or default_stage_root() / battle) / "cache" / "raw"
        d.mkdir(parents=True, exist_ok=True)
        return d


def html_to_text(raw: bytes) -> str:
    """HTML → 可搜尋文字。區塊標籤變換行，方便切片段；比對引文時仍走 norm（去空白）。"""
    try:
        t = raw.decode("utf-8")
    except UnicodeDecodeError:
        t = raw.decode("cp1252", "replace")
    looks_html = bool(re.search(r"(?is)<(html|head|body|p|div|h[1-6]|br)\b", t))
    if not looks_html:
        return t
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", t)
    t = re.sub(r"(?i)<(br|p|h[1-6]|tr|li|div|table|hr|blockquote)[^>]*>", "\n", t)
    t = re.sub(r"(?i)</(p|h[1-6]|tr|li|div|table|blockquote)>", "\n", t)
    t = re.sub(r'<[^>]+class="pagebreak"[^>]*>', "\n--pagebreak--\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    import html as htmlmod
    t = htmlmod.unescape(t)
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t


def pdf_to_text(raw_path: Path, dest_dir: Path, key: str) -> list[str]:
    """用 pdftotext 抽 flow 與 layout，產檔寫在 dest_dir，不寫 repo。"""
    import subprocess
    outs = []
    for mode, suf in (("", "-flow"), ("-layout", "-layout")):
        txt = dest_dir / (key + suf + ".txt")
        if not txt.exists():
            cmd = ["pdftotext"] + ([mode] if mode else []) + [str(raw_path), str(txt)]
            subprocess.run(cmd, check=True)
        outs.append(txt.read_text(errors="replace"))
    return outs


def texts_for_url(url: str, repo: Path, battle: str, stage: Path | None = None, allow_fetch=False):
    """回傳 (texts, is_pdf)。預設不連網；raw 不在快取就回 (None, None)。"""
    url = url.split("#")[0]
    src = find_raw(url, repo, battle, stage)
    if not src:
        if not allow_fetch:
            return None, None
        raise FileNotFoundError(f"原文不在快取，且不允許連網：{url}")
    dest = writable_cache(battle, stage)
    key = ukey(url)
    dest_raw = dest / (key + ".raw")
    if src.resolve() != dest_raw.resolve():
        if not dest_raw.exists():
            shutil.copy2(src, dest_raw)
        for suf in ("-flow.txt", "-layout.txt"):
            q = src.parent / (src.name[:-4] + suf)
            if q.exists() and not (dest / q.name).exists():
                shutil.copy2(q, dest / q.name)
    raw = dest_raw.read_bytes()
    if raw[:5] == b"%PDF-":
        return pdf_to_text(dest_raw, dest, key), True
    # 與 verify_quotes 一樣試 utf-8／cp1252；另加一份保留換行的可讀文字供切片段
    texts, _ = None, False
    if _VQ is not None:
        _VQ["fetch"].__globals__["CACHE"] = dest
        vtexts, is_pdf = _VQ["fetch"](url)
        readable = html_to_text(raw)
        # 片段用可讀版（有換行）；verify 仍用 vtexts（與現有腳本一致）
        return {"verify": vtexts, "readable": readable, "is_pdf": is_pdf}, is_pdf
    return {"verify": [html_to_text(raw)], "readable": html_to_text(raw), "is_pdf": False}, False


def readable_text(url: str, repo: Path, battle: str, stage: Path | None = None) -> tuple[str | None, bool | None]:
    packed, is_pdf = texts_for_url(url, repo, battle, stage, allow_fetch=False)
    if packed is None:
        return None, None
    if isinstance(packed, dict):
        t = packed["readable"]
        if not t and packed.get("verify"):
            t = packed["verify"][0]
        return t, packed["is_pdf"]
    # list from pdf_to_text path when _VQ is None
    if isinstance(packed, list):
        return packed[0], is_pdf
    return packed, is_pdf


def verify_texts(url: str, repo: Path, battle: str, stage: Path | None = None):
    packed, is_pdf = texts_for_url(url, repo, battle, stage, allow_fetch=False)
    if packed is None:
        return None, None
    if isinstance(packed, dict):
        return packed["verify"], packed["is_pdf"]
    if isinstance(packed, list):
        return packed, is_pdf
    return [packed], is_pdf


def load_json(path: Path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def battle_dir(repo: Path, battle: str) -> Path:
    return repo / "data/seed/battles" / battle


def load_battle(repo: Path, battle: str, name: str, default=None):
    p = battle_dir(repo, battle) / name
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def iter_cites(o):
    if isinstance(o, dict):
        if isinstance(o.get("quote"), str) and o["quote"].strip():
            yield o
        for v in o.values():
            yield from iter_cites(v)
    elif isinstance(o, list):
        for v in o:
            yield from iter_cites(v)


def existing_citations(repo: Path, battle: str):
    s = set()
    d = battle_dir(repo, battle)
    if not d.exists():
        return s
    for f in d.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        for c in iter_cites(data):
            s.add(((c.get("url") or "").split("#")[0], norm(c["quote"])))
    return s


def all_citation_urls(repo: Path, battle: str):
    urls = []
    seen = set()
    d = battle_dir(repo, battle)
    if not d.exists():
        return urls
    for f in d.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        for c in iter_cites(data):
            u = (c.get("url") or "").split("#")[0]
            if u and u not in seen:
                seen.add(u)
                urls.append((c.get("sourceKey"), u))
    return urls


def source_table(repo: Path, battle: str, extra_candidates=None):
    """既有 sources.json ＋ staging 候選，附 family／side。"""
    srcs = load_battle(repo, battle, "sources.json", {}) or {}
    cfg = load_battle(repo, battle, "battle.config.json", {}) or {}
    fam = cfg.get("sourceFamilies") or {}
    fmap, fsides = fam.get("map") or {}, fam.get("sides") or {}
    out = {}
    for k, v in srcs.items():
        rec = dict(v, sourceKey=k, existing=True)
        rec.setdefault("family", fmap.get(k))
        rec.setdefault("side", fsides.get(rec.get("family")))
        out[k] = rec
    if extra_candidates:
        for s in extra_candidates.get("sources") or []:
            out.setdefault(s["sourceKey"], dict(s, existing=False))
    return out


def s2t(s: str) -> str:
    table = dict(zip(
        "浏罗宝吴场湾诸龙华阴杨泾闵区镇苏兴锡县阳江长桥头张扬顺庙闸北仓东苏广庄桥岭渎岛门汤陆凤刘赵钱孙沪",
        "瀏羅寶吳場灣諸龍華陰楊涇閔區鎮蘇興錫縣陽江長橋頭張揚順廟閘北倉東蘇廣莊橋嶺瀆島門湯陸鳳劉趙錢孫滬",
    ))
    return "".join(table.get(ch, ch) for ch in s)


def strip_accents(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", s) if unicodedata.category(ch) != "Mn").replace("ł", "l").replace("Ł", "L")


def osm_lookup_local(repo: Path, battle: str, name: str):
    """只查戰役已有的 osm-places.json，不連 OSM、不寫檔。"""
    o = load_battle(repo, battle, "osm-places.json", {}) or {}
    if not name:
        return None
    want = {name, s2t(name), strip_accents(name).lower()}
    for q, rs in (o.get("results") or {}).items():
        keys = {q, s2t(q), strip_accents(q).lower(), s2t(q).rstrip("鎮城"), q.rstrip("镇城")}
        if want & keys or s2t(name).rstrip("鎮城") in {s2t(q).rstrip("鎮城")}:
            pick = None
            for r in rs or []:
                if r.get("class") in ("place", "boundary"):
                    pick = r
                    break
            pick = pick or (rs[0] if rs else None)
            if pick:
                return {
                    "nameOsm": q,
                    "osm": {"type": pick["type"], "id": pick["id"]},
                    "lonlat": [pick["lon"], pick["lat"]] if "lon" in pick else None,
                }
    return None
