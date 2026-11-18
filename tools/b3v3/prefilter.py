#!/usr/bin/env python3
"""研究前的 Python 預查：找候選網址、抓進快取、只留命中段落給 agent。

研究 agent 不再自己做 8 次查詢、讀整頁。這支程式先做：
  1. 索引查詢（名稱 → 權威檔與國家級辭典的識別碼）。索引只用來找網址，不當出處，
     索引網址也不寫進任何人物檔。另做 LoC 與 GND（lobid）權威檔查詢。
  2. 用 fetch_source.py 抓候選頁進 RAWDIR（同 host 間隔至少 1 秒；已有的 sourceKey
     或其他批已抓過的同一網址不重抓；403／挑戰頁照規則放棄；禁用網域不抓）。
  3. 只留含人名的段落（前後約 360 字），加上年份、職稱命中排序，總長有上限。

輸出（都在 OUTDIR/people/）：
  <bioId>.snippets.md    給 agent 讀：候選來源清單與命中段落
  <bioId>.prefilter.json 給 person_draft.py：來源建議等級、searchLog、人名資料

    python3 -I tools/b3v3/prefilter.py run --spec SPEC --id research:123:<bioId>
    python3 -I tools/b3v3/prefilter.py run --spec SPEC --id ID --extra-urls urls.json
    python3 -I tools/b3v3/prefilter.py run --spec SPEC --id ID --offline   # 只用快取
stdout 只印一行摘要。
"""
import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from datetime import date
from pathlib import Path
from urllib.parse import quote, urlparse

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
INDEX_UA = "WorldLine-B3v3-prefilter/1.0 (index lookup only; not used as a source)"
HOST_GAP_SECONDS = 1.1
MAX_FETCH = 8
MAX_PER_HOST = 2
SNIPPET_RADIUS = 360
PER_SOURCE_CHARS = 2600
TOTAL_CHARS = 14000


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fetch_source = _load("b3_fetch_source", HERE / "fetch_source.py")
try:
    source_policy = _load("b3_source_policy", REPO_ROOT / "tools" / "source_policy.py")
except Exception:  # 測試用的暫存 repo 沒有政策檔時只靠內建清單
    source_policy = None

# host 尾碼 → (sourceType, 建議等級, 說明)。等級只是建議，agent 依頁面實況確認（具名作者等）。
HOSTS = [
    ("deutsche-biographie.de", "national_dictionary", "A", "Deutsche Biographie（NDB／ADB）"),
    ("biographien.ac.at", "national_dictionary", "A", "Österreichisches Biographisches Lexikon"),
    ("parlament.gv.at", "official", "A", "Parlament Österreich 人物頁"),
    ("lobid.org", "authority", "A", "GND 權威檔（lobid）"),
    ("d-nb.info", "authority", "A", "GND 權威檔（DNB）"),
    ("id.loc.gov", "authority", "A", "LoC Name Authority"),
    ("data.bnf.fr", "authority", "A", "BnF 權威檔"),
    ("catalogue.bnf.fr", "authority", "A", "BnF 權威檔"),
    ("id.ndl.go.jp", "authority", "A", "NDL 權威檔"),
    ("ndl.go.jp", "official", "A", "国立国会図書館"),
    ("jacar.go.jp", "official", "A", "アジア歴史資料センター"),
    ("jacar.archives.go.jp", "official", "A", "アジア歴史資料センター"),
    ("kantei.go.jp", "official", "A", "首相官邸"),
    ("shugiin.go.jp", "official", "A", "衆議院"),
    ("sangiin.go.jp", "official", "A", "参議院"),
    ("nbl.snl.no", "national_dictionary", "A", "Norsk biografisk leksikon"),
    ("snl.no", "named_encyclopedia", "B", "Store norske leksikon（具名條目）"),
    ("stortinget.no", "official", "A", "Stortinget"),
    ("nsd.no", "official", "A", "NSD Politikerarkivet"),
    ("regjeringen.no", "official", "A", "Regjeringen"),
    ("riksarkivet.se", "national_dictionary", "A", "Svenskt biografiskt lexikon"),
    ("lex.dk", "named_encyclopedia", "B", "lex.dk（具名條目）"),
    ("kansallisbiografia.fi", "national_dictionary", "A", "Kansallisbiografia"),
    ("eduskunta.fi", "official", "A", "Eduskunta"),
    ("hls-dhs-dss.ch", "national_dictionary", "A", "Historisches Lexikon der Schweiz"),
    ("dbe.rah.es", "national_dictionary", "A", "DB~e Real Academia de la Historia"),
    ("treccani.it", "national_dictionary", "A", "Treccani（DBI 為 A；百科條目為 B）"),
    ("storia.camera.it", "official", "A", "Camera dei deputati"),
    ("senato.it", "official", "A", "Senato"),
    ("dib.ie", "national_dictionary", "A", "Dictionary of Irish Biography"),
    ("oxforddnb.com", "national_dictionary", "A", "Oxford DNB（公開摘要）"),
    ("biography.wales", "national_dictionary", "A", "Dictionary of Welsh Biography"),
    ("api.parliament.uk", "official", "A", "UK Parliament Historic Hansard"),
    ("bioguide.congress.gov", "official", "A", "Biographical Directory of the U.S. Congress"),
    ("history.state.gov", "official", "A", "Office of the Historian"),
    ("assemblee-nationale.fr", "official", "A", "Assemblée nationale Sycomore"),
    ("senat.fr", "official", "A", "Sénat"),
    ("parlement.com", "official", "B", "Parlement.com"),
    ("huygens.knaw.nl", "national_dictionary", "A", "Biografisch Woordenboek van Nederland"),
    ("odis.be", "academic", "B", "ODIS"),
    ("bs.sejm.gov.pl", "official", "A", "Sejm 議員資料"),
    ("ipsb.nina.gov.pl", "national_dictionary", "A", "Polski Słownik Biograficzny（iPSB）"),
    ("encyclopediaofukraine.com", "named_encyclopedia", "B", "Encyclopedia of Ukraine"),
    ("prlib.ru", "official", "A", "Президентская библиотека"),
    ("bigenc.ru", "named_encyclopedia", "B", "Большая российская энциклопедия"),
    ("iranicaonline.org", "named_encyclopedia", "B", "Encyclopaedia Iranica"),
    ("islamansiklopedisi.org.tr", "named_encyclopedia", "B", "TDV İslâm Ansiklopedisi"),
    ("tbmm.gov.tr", "official", "A", "TBMM"),
    ("1914-1918-online.net", "named_encyclopedia", "B", "1914-1918-online"),
    ("britannica.com", "named_encyclopedia", "B", "Britannica（須具名作者）"),
    ("kotobank.jp", "named_encyclopedia", "B", "コトバンク（只收具名執筆者的辭典條目）"),
    ("sinica.edu.tw", "official", "A", "中央研究院"),
    ("drnh.gov.tw", "official", "A", "國史館"),
    ("bne.es", "authority", "A", "Biblioteca Nacional de España"),
    ("bcn.cl", "official", "A", "Biblioteca del Congreso Nacional de Chile"),
    ("cpdoc.fgv.br", "academic", "B", "FGV CPDOC DHBB"),
    ("viaf.org", "authority", "A", "VIAF"),
    ("isni.org", "authority", "A", "ISNI"),
]
BLOCK_LABELS = ("wiki", "wikipedia", "wikidata", "baidu", "fandom", "blog", "blogs", "forum", "forums", "bbs")
UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
AUTHOR_MARKERS = (
    "Autor", "Verfasser", "Empfohlene Zitierweise", "Zitierweise", "Author", "Written by", "Citation",
    "Forfatter", "Skrevet av", "Författare", "執筆者", "著者", "Auteur", "Autore",
)


def nfc(text):
    return unicodedata.normalize("NFC", text or "")


def host_of(url):
    return (urlparse(url).hostname or "").lower()


def host_info(url):
    host = host_of(url)
    for suffix, kind, grade, label in HOSTS:
        if host == suffix or host.endswith("." + suffix):
            if suffix == "treccani.it" and "dizionario-biografico" not in url.lower():
                # Treccani 只有 Dizionario Biografico 是 A；一般百科條目是 B
                return {"host": host, "sourceType": "named_encyclopedia", "grade": "B", "label": "Treccani 百科條目"}
            return {"host": host, "sourceType": kind, "grade": grade, "label": label}
    return {"host": host, "sourceType": "other", "grade": None, "label": host}


def canonical_url(url):
    """去掉 #片段；Deutsche Biographie 的 <gnd>.html 與 pnd<gnd>.html 是同一頁。"""
    url = url.split("#", 1)[0]
    match = re.match(r"https?://(www\.)?deutsche-biographie\.de/(?:pnd)?(\d{8,10}[\dX]?)\.html$", url)
    if match:
        return f"https://www.deutsche-biographie.de/pnd{match.group(2)}.html"
    return url


def blocked_host(url):
    """禁用網域（政策檔＋維基類字樣）。被擋就不抓、不當來源。"""
    host = host_of(url)
    if not host:
        return "no_host"
    labels = host.split(".")
    if any(label in BLOCK_LABELS for label in labels) or "wikipedia" in host or "wikidata" in host:
        return "banned_label"
    if source_policy is not None:
        try:
            if source_policy.banned(url):
                return "banned_host"
            if source_policy.banned_label(url):
                return "banned_label"
        except Exception:
            pass
    return None


def parse_line(line, bio_id=None):
    """名單一行：中文名｜原名｜bioId｜地區｜年代｜厚薄｜任期…"""
    parts = [part.strip() for part in re.split(r"[|｜]", line or "")]
    name_zh = re.sub(r"（[^）]*）|\([^)]*\)", "", parts[0]).strip() if parts else ""
    name = parts[1] if len(parts) > 1 else name_zh
    region = parts[3] if len(parts) > 3 else ""
    rest = " ".join(parts[4:])
    clean = UUID_RE.sub(" ", rest)
    if bio_id:
        clean = clean.replace(bio_id, " ")
    years = []
    for year in re.findall(r"(?<!\d)(1[89]\d\d|20[0-4]\d)(?!\d)", clean):
        if year not in years:
            years.append(year)
    titles = []
    for title in re.findall(r"「([^」]{2,40})」", rest):
        if title not in titles:
            titles.append(title)
    record_ids = []
    for rid in re.findall(r"recordId\s*([0-9a-f-]{36})", rest):
        if rid not in record_ids:
            record_ids.append(rid)
    return {
        "name": nfc(name), "nameZh": nfc(name_zh), "region": region,
        "years": years, "titles": titles, "recordIds": record_ids,
        "thickness": parts[5] if len(parts) > 5 else "",
    }


def slug(text, fallback="p"):
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return text[:40] or fallback


def person_key(info, bio_id):
    base = slug(info.get("name"), "")
    if not base:
        return f"p-{bio_id[:8]}"
    return base


def name_variants(info, aliases=()):
    out = []

    def add(value):
        value = nfc(value).strip()
        if len(value) < 2 or value in out:
            return
        out.append(value)

    add(info.get("name"))
    add(info.get("nameZh"))
    name = info.get("name") or ""
    tokens = [tok for tok in re.split(r"[\s,]+", name) if tok]
    if len(tokens) >= 2:
        surname = tokens[-1]
        add(f"{surname}, {' '.join(tokens[:-1])}")
        if len(surname) >= 4 and not surname.lower() in ("von", "van", "der", "de"):
            add(surname)
    if CJK_RE.search(info.get("nameZh") or "") and len(info.get("nameZh") or "") >= 3:
        add((info.get("nameZh") or "")[:2])
    # 索引的別名只留拉丁字母與漢字／假名（原文語言姓名），其他文字的譯名對原文頁沒有用
    for alias in aliases:
        if re.fullmatch(r"[\w\s.,'’·・\-()（）]+", alias or "") and (
                re.search(r"[A-Za-zÀ-ž]", alias) or CJK_RE.search(alias)):
            if not re.search(r"[\u0400-\u06ff\u0590-\u05ff]", alias):
                add(alias)
    return out[:10]


def score_snippet(snippet, names, extras):
    folded = snippet.casefold()
    score = sum(2 for name in names if name.casefold() in folded)
    score += sum(1 for extra in extras if extra and extra.casefold() in folded)
    return score


WHOLE_TEXT_CHARS = 2200


def select_snippets(text, names, extras, radius=SNIPPET_RADIUS, budget=PER_SOURCE_CHARS,
                    whole_limit=WHOLE_TEXT_CHARS):
    """回傳 [(offset, snippet)]。必須含人名；依年份／職稱命中排序後取到上限，再照位置排回。
    整頁很短（≤2200 字）又含人名時整頁給，避免把任期表切斷。"""
    hits = fetch_source.matching_snippets(text, names, radius=radius, limit=14)
    if not hits:
        return []
    flat = re.sub(r"\s+", " ", text).strip()
    if len(flat) <= whole_limit:
        return [(0, flat)]
    ranked = sorted(hits, key=lambda hit: (-score_snippet(hit[2], names, extras), hit[0]))
    chosen = []
    used = 0
    for offset, _keyword, snippet in ranked:
        if used and used + len(snippet) > budget:
            continue
        chosen.append((offset, snippet))
        used += len(snippet)
        if used >= budget:
            break
    marker = fetch_source.matching_snippets(text, list(AUTHOR_MARKERS), radius=140, limit=1)
    if marker and all(abs(marker[0][0] - offset) > radius for offset, _ in chosen):
        chosen.append((marker[0][0], marker[0][2]))
    return sorted(chosen)


class Http:
    """索引查詢用 curl（不加 -k），同 host 至少間隔 1.1 秒；回應快取在 index 目錄。"""

    def __init__(self, cache_dir, offline=False):
        self.cache_dir = Path(cache_dir)
        self.offline = offline
        self.last = {}
        self.calls = 0

    def wait(self, url):
        host = host_of(url)
        gap = time.time() - self.last.get(host, 0)
        if gap < HOST_GAP_SECONDS:
            time.sleep(HOST_GAP_SECONDS - gap)
        self.last[host] = time.time()

    def get_json(self, url):
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
        path = self.cache_dir / f"{key}.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        if self.offline:
            return None
        self.wait(url)
        self.calls += 1
        proc = subprocess.run(
            ["curl", "-sS", "-L", "--proto", "=https", "--max-time", "30", "-A", INDEX_UA, url],
            capture_output=True,
        )
        if proc.returncode != 0:
            return None
        try:
            data = json.loads(proc.stdout.decode("utf-8", errors="replace"))
        except json.JSONDecodeError:
            return None
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return data


WD_API = "https://www.wikidata.org/w/api.php"


def wd_search(http, term, lang):
    url = f"{WD_API}?action=wbsearchentities&format=json&type=item&limit=6&language={lang}&uselang={lang}&search={quote(term)}"
    data = http.get_json(url) or {}
    return [hit.get("id") for hit in data.get("search") or [] if hit.get("id")]


def wd_entities(http, ids, props="claims|labels|aliases|descriptions"):
    out = {}
    ids = [i for i in ids if i]
    for start in range(0, len(ids), 40):
        chunk = ids[start:start + 40]
        url = f"{WD_API}?action=wbgetentities&format=json&props={props.replace('|', '%7C')}&ids={'%7C'.join(chunk)}"
        data = http.get_json(url) or {}
        out.update(data.get("entities") or {})
    return out


def _claim_values(entity, pid):
    out = []
    for claim in (entity.get("claims") or {}).get(pid) or []:
        value = ((claim.get("mainsnak") or {}).get("datavalue") or {}).get("value")
        if value is not None:
            out.append(value)
    return out


def _year(entity, pid):
    for value in _claim_values(entity, pid):
        match = re.match(r"[+-](\d{4})", (value or {}).get("time") or "") if isinstance(value, dict) else None
        if match:
            return int(match.group(1))
    return None


def entity_names(entity):
    names = []
    for item in (entity.get("labels") or {}).values():
        names.append(item.get("value"))
    for items in (entity.get("aliases") or {}).values():
        names.extend(item.get("value") for item in items[:3])
    out = []
    for name in names:
        name = nfc(name or "").strip()
        if name and name not in out:
            out.append(name)
    return out


def pick_person(entities, info):
    """只選人類（P31=Q5），任期年份要落在生卒之間。分數不足就不選，避免抓錯人。"""
    years = [int(y) for y in info.get("years") or []]
    first = min(years) if years else None
    want = {nfc(info.get("name")).casefold(), nfc(info.get("nameZh")).casefold()} - {""}
    surname = (info.get("name") or "").split()[-1].casefold() if info.get("name") else ""
    best = None
    for qid, entity in entities.items():
        humans = [v.get("id") for v in _claim_values(entity, "P31") if isinstance(v, dict)]
        if "Q5" not in humans:
            continue
        score = 0
        names = {name.casefold() for name in entity_names(entity)}
        if names & want:
            score += 3
        elif surname and any(surname in name for name in names):
            score += 1
        born, died = _year(entity, "P569"), _year(entity, "P570")
        if first and born:
            if born <= first - 18 and (died is None or died >= first):
                score += 3
            else:
                score -= 4
        if best is None or score > best[0]:
            best = (score, qid)
    if best and best[0] >= 4:
        return best[1]
    return None


def external_urls(http, entity):
    """外部識別碼 → 網址（用屬性的 formatter URL）。只留 HOSTS 白名單內的 host。"""
    pairs = []
    for pid, claims in (entity.get("claims") or {}).items():
        for claim in claims:
            snak = claim.get("mainsnak") or {}
            if snak.get("datatype") != "external-id":
                continue
            value = (snak.get("datavalue") or {}).get("value")
            if isinstance(value, str):
                pairs.append((pid, value))
    if not pairs:
        return []
    props = wd_entities(http, sorted({pid for pid, _ in pairs}), props="claims")
    urls = []
    for pid, value in pairs:
        formatters = [v for v in _claim_values(props.get(pid) or {}, "P1630") if isinstance(v, str)]
        for fmt in formatters[:1]:
            url = canonical_url(fmt.replace("$1", quote(value, safe="/:@")))
            info = host_info(url)
            if info["grade"] and not blocked_host(url) and url not in urls:
                urls.append(url)
    return urls


def authority_searches(http, info):
    """不經索引也能做的權威檔查詢。回傳 (searchLog 項, 候選網址)。"""
    logs, urls = [], []
    name = info.get("name") or ""
    if not name:
        return logs, urls
    loc = f"https://id.loc.gov/authorities/names/suggest2?q={quote(name)}&count=5"
    data = http.get_json(loc)
    hits = (data or {}).get("hits") or []
    logs.append({
        "sourceType": "authority", "query": f"{name}（LoC suggest2）", "url": loc,
        "result": "found_A" if hits else "no_result",
        "note": f"{len(hits)} 筆候選" if hits else "沒有命中",
    })
    for hit in hits[:2]:
        uri = hit.get("uri") or ""
        if uri.startswith("http://"):
            uri = "https://" + uri[len("http://"):]
        if uri and uri not in urls:
            urls.append(uri + ".html" if not uri.endswith(".html") else uri)
    lobid = f"https://lobid.org/gnd/search?q={quote(name)}&filter=type:Person&format=json&size=3"
    data = http.get_json(lobid)
    members = (data or {}).get("member") or []
    logs.append({
        "sourceType": "authority", "query": f"{name}（GND／lobid）", "url": lobid,
        "result": "found_A" if members else "no_result",
        "note": f"{len(members)} 筆候選" if members else "沒有命中",
    })
    for member in members[:2]:
        gnd = member.get("gndIdentifier")
        if gnd:
            for url in (f"https://lobid.org/gnd/{gnd}.json", f"https://www.deutsche-biographie.de/pnd{gnd}.html"):
                if url not in urls:
                    urls.append(url)
    return logs, urls


def index_lookup(http, info):
    ids = []
    terms = []
    for term in (info.get("name"), info.get("nameZh")):
        if not term:
            continue
        # 漢字名用 ja 與 zh 都查（en 搜尋找不到只有漢字標籤的人）
        langs = ("ja", "zh") if CJK_RE.search(term) else ("en",)
        for lang in langs:
            if (term, lang) not in terms:
                terms.append((term, lang))
    for term, lang in terms:
        if term:
            for qid in wd_search(http, term, lang):
                if qid not in ids:
                    ids.append(qid)
    if not ids:
        return None, [], []
    entities = wd_entities(http, ids[:12])
    qid = pick_person(entities, info)
    if not qid:
        return None, [], []
    entity = entities[qid]
    return qid, entity_names(entity), external_urls(http, entity)


def url_index(out_root):
    """其他批已抓過的網址 → 原文檔。抓過就複製，不重抓。"""
    index = {}
    for research in Path(out_root).glob("batch*/research.json"):
        try:
            data = json.loads(research.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        raw_dir = Path(data.get("rawDir") or "")
        rawmap = research.parent / "rawmap.json"
        try:
            mapping = json.loads(rawmap.read_text(encoding="utf-8")) if rawmap.exists() else {}
        except json.JSONDecodeError:
            mapping = {}
        for key, source in (data.get("sources") or {}).items():
            url = (source or {}).get("url")
            name = mapping.get(key) if isinstance(mapping, dict) else None
            if url and isinstance(name, str) and (raw_dir / name).is_file():
                index.setdefault(url, raw_dir / name)
    return index


def source_key_for(url, info, existing):
    site = host_info(url)["host"].replace("www.", "").split(".")[0][:12] or "src"
    who = slug((info.get("name") or "").split()[-1] if info.get("name") else "", "") or "p"
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:4]
    key = f"{site}-{who[:20]}-{digest}"
    key = re.sub(r"[^A-Za-z0-9_.-]", "-", key)
    return key if key not in existing or existing[key] == url else f"{key}x"


def html_title(path):
    try:
        head = Path(path).read_bytes()[:60000].decode("utf-8", errors="replace")
    except OSError:
        return ""
    match = re.search(r"(?is)<title[^>]*>(.*?)</title>", head)
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(1)).strip()[:160]


def parse_report(text):
    out = {}
    for line in text.splitlines():
        if "=" in line and not line.startswith("##"):
            key, _, value = line.partition("=")
            if key.isidentifier() and key not in out:
                out[key] = value
    return out


def result_label(status, grade, relevant):
    if status in ("blocked_401", "blocked_403", "blocked_429"):
        return "blocked_403"
    if status == "challenge_page":
        return "challenge_page"
    if status not in ("fetched", "cached", "copied"):
        return "no_result"
    if not relevant:
        return "not_relevant"
    return {"A": "found_A", "B": "found_B"}.get(grade, "unrated")


def run(agent, offline=False, extra_urls=(), http=None, today=None, fetcher=None):
    today = today or date.today().isoformat()
    out_dir = Path(agent["outDir"])
    raw_dir = Path(agent["rawDir"])
    people = out_dir / "people"
    people.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    rawmap = out_dir / "rawmap.json"
    bio_id = agent["bioId"]
    pre_path = people / f"{bio_id}.prefilter.json"
    previous = json.loads(pre_path.read_text(encoding="utf-8")) if pre_path.exists() else {}
    info = parse_line(agent.get("line") or agent.get("name") or "", bio_id)
    if agent.get("name") and not info.get("name"):
        info["name"] = agent["name"]
    http = http or Http(Path(raw_dir).parents[1] / "_index", offline=offline)
    fetcher = fetcher or fetch_source.cmd_fetch

    logs = list(previous.get("searchLog") or [])
    candidates = list(previous.get("candidates") or [])
    aliases = list(previous.get("aliases") or [])
    if not previous:
        qid, aliases, urls = index_lookup(http, info)
        logs.append({
            "sourceType": "authority",
            "query": f"索引查詢（名稱 → 權威檔／辭典識別碼）：{info.get('name')}",
            "url": None,
            "result": "unrated" if urls else "no_result",
            "note": f"取得 {len(urls)} 個白名單網址；索引只用來找網址，不當出處" if qid else "索引沒有可確認的同名人物",
        })
        candidates.extend(urls)
        auth_logs, auth_urls = authority_searches(http, info)
        logs.extend(auth_logs)
        candidates.extend(url for url in auth_urls if url not in candidates)
    for url in extra_urls:
        if url not in candidates:
            candidates.append(url)
    unique = []
    for url in candidates:
        url = canonical_url(url)
        if url not in unique:
            unique.append(url)
    candidates = unique

    names = name_variants(info, aliases)
    extras = list(info.get("years") or []) + list(info.get("titles") or [])
    mapping = fetch_source.load_rawmap(rawmap)
    sources = dict(previous.get("sources") or {})
    done_urls = {item.get("url") for item in sources.values()}
    done_urls |= {log.get("url") for log in logs if log.get("url")}
    reused = url_index(Path(agent["outDir"]).parent) if not offline else {}
    per_host = {}
    for item in sources.values():
        per_host[item.get("host")] = per_host.get(item.get("host"), 0) + 1
    fetched = sum(1 for item in sources.values() if item.get("status") in ("fetched", "cached", "copied"))
    for url in candidates:
        if url in done_urls:
            continue
        if fetched >= MAX_FETCH + len(extra_urls):
            break
        meta = host_info(url)
        if per_host.get(meta["host"], 0) >= MAX_PER_HOST:
            continue
        banned = blocked_host(url)
        if banned:
            logs.append({"sourceType": meta["sourceType"], "query": "候選網址", "url": None,
                         "result": "not_relevant", "note": f"禁用網域，不抓（{banned}）：{meta['host']}"})
            continue
        key = source_key_for(url, info, {k: v.get("url") for k, v in sources.items()})
        status = None
        if fetch_source.existing_text(raw_dir, rawmap, key) is not None:
            status = "cached"
        elif url in reused and not offline:
            src = reused[url]
            shutil.copyfile(src, raw_dir / f"{key}.txt")
            fetch_source.update_rawmap(rawmap, key, f"{key}.txt")
            status = "copied"
        elif offline:
            status = "offline_skip"
        else:
            http.wait(url)
            report = parse_report(fetcher(str(raw_dir), str(rawmap), key, url, [], 600))
            status = report.get("RESULT", "error")
        text_path = fetch_source.existing_text(raw_dir, rawmap, key)
        text = text_path.read_text(encoding="utf-8", errors="replace") if text_path else ""
        snippets = select_snippets(text, names, extras) if text else []
        title = ""
        for ext in ("html", "htm"):
            if (raw_dir / f"{key}.{ext}").exists():
                title = html_title(raw_dir / f"{key}.{ext}")
        per_host[meta["host"]] = per_host.get(meta["host"], 0) + 1
        if status in ("fetched", "cached", "copied"):
            fetched += 1
        sources[key] = {
            "url": url, "host": meta["host"], "sourceType": meta["sourceType"],
            "suggestedGrade": meta["grade"], "label": meta["label"], "title": title,
            "status": status, "textChars": len(text), "relevant": bool(snippets),
            "accessedOn": today,
        }
        logs.append({
            "sourceType": meta["sourceType"], "query": f"直接開啟候選頁（{meta['label']}）", "url": url,
            "result": result_label(status, meta["grade"], bool(snippets)),
            "note": f"{status}；{len(text)} 字；{'有' if snippets else '沒有'}人名命中段落",
        })
        done_urls.add(url)

    # 重跑時用目前的人名清單重算每個來源的命中，並去掉同一頁的重複來源（只重讀快取，不重抓）
    seen_urls = {}
    for key in sorted(sources):
        item = sources[key]
        canon = canonical_url(item.get("url") or "")
        if canon in seen_urls:
            del sources[key]
            continue
        seen_urls[canon] = key
        meta = host_info(item.get("url") or "")
        item.update(sourceType=meta["sourceType"], suggestedGrade=meta["grade"], label=meta["label"])
        text_path = fetch_source.existing_text(raw_dir, rawmap, key)
        if text_path is not None and item.get("status") in ("fetched", "cached", "copied"):
            text = text_path.read_text(encoding="utf-8", errors="replace")
            item["relevant"] = bool(select_snippets(text, names, extras))

    doc = {
        "bioId": bio_id,
        "generatedOn": today,
        "person": {
            "key": person_key(info, bio_id), "name": info.get("name"), "nameZh": info.get("nameZh"),
            "recordIds": info.get("recordIds"), "years": info.get("years"), "titles": info.get("titles"),
            "thickness": info.get("thickness"),
        },
        "aliases": aliases,
        "names": names,
        "candidates": candidates,
        "sources": sources,
        "searchLog": logs,
        "indexCalls": http.calls,
    }
    pre_path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    md, chars, relevant = render_snippets(doc, raw_dir, rawmap, names, extras)
    (people / f"{bio_id}.snippets.md").write_text(md, encoding="utf-8")
    doc_summary = {
        "bioId": bio_id, "relevant": relevant, "sources": len(sources),
        "snippetChars": chars, "indexCalls": http.calls,
        # 權威檔只有生卒與名稱；有傳記敘述的命中來源才算「夠寫」
        "narrative": sum(1 for item in sources.values()
                         if item.get("relevant") and item.get("sourceType") != "authority"),
    }
    return doc_summary


def render_snippets(doc, raw_dir, rawmap, names, extras):
    grade_order = {"A": 0, "B": 1, None: 2}
    items = sorted(doc["sources"].items(), key=lambda kv: (grade_order.get(kv[1].get("suggestedGrade"), 2), kv[0]))
    lines = [
        f"# 預查段落：{doc['person']['name']}（{doc['person']['nameZh']}）",
        "段落是快取原文的逐字片段（空白已壓縮，verify 也這樣比對）。quote 只能從這裡或 lookup 輸出逐字取。",
        "## 來源（sourceKey｜建議等級｜類型｜狀態｜網址｜頁面標題）",
    ]
    for key, item in items:
        if item.get("status") not in ("fetched", "cached", "copied"):
            continue
        lines.append(
            f"- {key}｜{item.get('suggestedGrade') or '未評'}｜{item.get('sourceType')}｜"
            f"{'命中' if item.get('relevant') else '無人名'}｜{item.get('url')}｜{item.get('title') or item.get('label')}"
        )
    failed = [f"{item.get('host')}:{item.get('status')}" for item in doc["sources"].values()
              if item.get("status") not in ("fetched", "cached", "copied")]
    if failed:
        lines.append("未取得（不要再抓）：" + "、".join(failed))
    total = 0
    relevant = 0
    for key, item in items:
        if not item.get("relevant"):
            continue
        text_path = fetch_source.existing_text(raw_dir, rawmap, key)
        if text_path is None:
            continue
        text = text_path.read_text(encoding="utf-8", errors="replace")
        if item.get("sourceType") in ("national_dictionary", "official"):
            # 國家傳記辭典／官方人物頁通常就是整篇傳記，短的整篇給，長的給較大額度
            picked = select_snippets(text, names, extras, budget=4500, whole_limit=4500)
        else:
            picked = select_snippets(text, names, extras)
        if not picked:
            continue
        relevant += 1
        lines.append(f"\n## [{key}] {item.get('suggestedGrade') or '未評'}｜{item.get('label')}")
        for offset, snippet in picked:
            if total + len(snippet) > TOTAL_CHARS:
                lines.append("（已達總長上限，其餘用 lookup 查）")
                break
            lines.append(f"@{offset}: {snippet}")
            total += len(snippet)
        if total >= TOTAL_CHARS:
            break
    if not relevant:
        lines.append("\n（沒有任何來源含人名段落。）")
    return "\n".join(lines) + "\n", total, relevant


def find_agent(spec_path, agent_id):
    data = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    for agent in data.get("agents") or []:
        if agent.get("id") == agent_id:
            return agent
    raise SystemExit(f"spec 裡沒有 {agent_id}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="研究前的預查與段落篩選")
    sub = parser.add_subparsers(dest="cmd", required=True)
    command = sub.add_parser("run")
    command.add_argument("--spec", required=True)
    command.add_argument("--id", required=True)
    command.add_argument("--offline", action="store_true")
    command.add_argument("--extra-urls")
    args = parser.parse_args(argv)
    agent = find_agent(args.spec, args.id)
    extra = []
    if args.extra_urls:
        data = json.loads(Path(args.extra_urls).read_text(encoding="utf-8"))
        extra = [url for url in (data.get("urls") if isinstance(data, dict) else data) or [] if isinstance(url, str)]
        extra = [url for url in extra if url.startswith(("http://", "https://"))][:6]
    summary = run(agent, offline=args.offline, extra_urls=extra)
    print("PREFILTER " + json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
