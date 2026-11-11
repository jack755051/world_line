"""Shared fetch helpers (stdlib only). Polite: throttled, retry/backoff on 429. Index pages only."""
import hashlib, json, pathlib, time, urllib.parse, urllib.request, urllib.error, datetime
UA = 'WorldLineGeneralsRoster/0.1 (local research index; not a crawler of article prose)'
HERE = pathlib.Path(__file__).resolve().parent
CACHE = HERE / 'cache'
TZ = datetime.timezone(datetime.timedelta(hours=8))
_last = [0.0]

def now():
    return datetime.datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S+08:00')

def api(lang, **p):
    """returns (status, json|None, error|None); never raises."""
    p.update(format='json', formatversion='2')
    url = f'https://{lang}.wikipedia.org/w/api.php?' + urllib.parse.urlencode(p)
    err = None
    for i in range(6):
        wait = 1.2 - (time.time() - _last[0])
        if wait > 0: time.sleep(wait)
        _last[0] = time.time()
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.status, json.load(r), None
        except urllib.error.HTTPError as e:
            err = f'HTTP {e.code}'
            if e.code == 429 or e.code >= 500:
                time.sleep(6 * (i + 1)); continue
            return e.code, None, err
        except Exception as e:
            err = repr(e); time.sleep(4 * (i + 1))
    return 0, None, err

def cpath(kind, lang, key):
    h = hashlib.md5(key.encode()).hexdigest()[:10]
    return CACHE / f'{kind}__{lang}__{h}.json'

def cached(kind, lang, key, fn):
    """fn() -> dict (JSON-able). Only successful results (ok=True) are cached."""
    f = cpath(kind, lang, key)
    if f.exists():
        return json.loads(f.read_text())
    d = fn()
    d['fetched'] = now(); d['key'] = key
    if d.get('ok'):
        f.write_text(json.dumps(d, ensure_ascii=False))
    return d

def wikitext(lang, title):
    def fn():
        st, d, err = api(lang, action='parse', page=title, prop='wikitext', redirects=1)
        if d and 'parse' in d:
            return dict(ok=True, status=st, title=d['parse']['title'], wikitext=d['parse']['wikitext'])
        return dict(ok=False, status=st, error=err or json.dumps(d.get('error') if d else None, ensure_ascii=False)[:200])
    return cached('wt', lang, title, fn)

def catmembers(lang, cat):
    """members (ns0) with zh langlink + page title; via generator to get langlinks in bulk."""
    def fn():
        out = []; cont = {}
        for _ in range(40):
            st, d, err = api(lang, action='query', generator='categorymembers', gcmtitle=cat, gcmnamespace=0,
                             gcmlimit=500, prop='langlinks', lllang='zh', lllimit=500, **cont)
            if not d or 'query' not in d and 'error' in (d or {}):
                return dict(ok=False, status=st, error=err or str((d or {}).get('error'))[:200])
            for p in (d.get('query') or {}).get('pages', []):
                ll = p.get('langlinks') or []
                out.append([p['title'], ll[0]['title'] if ll else None])
            if 'continue' in d: cont = d['continue']
            else: break
        return dict(ok=True, status=200, members=out)
    return cached('cat', lang, cat, fn)
