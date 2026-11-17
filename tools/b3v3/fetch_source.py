#!/usr/bin/env python3
"""B3 v3 抓取與引文查找。只把短摘要與命中段落印到 stdout，原文留在 RAWDIR。

    python3 -I tools/b3v3/fetch_source.py status --rawdir RAW --rawmap OUT/rawmap.json
    python3 -I tools/b3v3/fetch_source.py fetch --rawdir RAW --rawmap OUT/rawmap.json \\
        --source-key KEY --url URL --keywords '姓名|1920|部長'
    python3 -I tools/b3v3/fetch_source.py lookup --rawdir RAW --rawmap OUT/rawmap.json \\
        --source-key KEY --keywords '原文片段'

curl 不加 -k／--insecure，User-Agent 為 Mozilla/5.0（與研究提示相同）。
已有的 sourceKey（rawmap 或 <key>.txt）不重抓。Cloudflare／Anubis／403 放棄，不寫成來源。
印出的字元數有硬上限（預設 4000）。關鍵字用 | 分隔，當字面字串比對，不是正規表示式。
lookup 的 offset 是 .txt 檔內的字元位置。
"""
import argparse
import fcntl
import html
import json
import re
import subprocess
import sys
import zlib
from pathlib import Path

USER_AGENT = "Mozilla/5.0"
DEFAULT_MAX_CHARS = 4000
KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,80}$")
CHALLENGE_MARKERS = (
    "cf-browser-verification",
    "just a moment",
    "attention required",
    "cdn-cgi/challenge",
    "checking your browser",
    "anubis",
)


def split_keywords(value):
    if not value:
        return []
    if isinstance(value, (list, tuple)):
        parts = []
        for item in value:
            parts.extend(split_keywords(item))
        return parts
    return [part.strip() for part in str(value).split("|") if part.strip()]


def cap_text(text, max_chars):
    if max_chars is None or len(text) <= max_chars:
        return text
    note = "\n…[truncated printed output]\n"
    keep = max(0, max_chars - len(note))
    return text[:keep] + note


def build_curl_command(url, dest):
    """與研究提示相同的抓法：-sS -L、60 秒、UA Mozilla/5.0，沒有 -k。"""
    return [
        "curl", "-sS", "-L", "--proto", "=http,https", "--max-time", "60",
        "-A", USER_AGENT,
        "-o", str(dest),
        "-w", "%{http_code}\t%{content_type}",
        url,
    ]


def html_to_text(data, content_type=""):
    enc = "utf-8"
    match = re.search(r"charset=([\w.-]+)", content_type or "", re.I)
    if match:
        enc = match.group(1)
    try:
        text = data.decode(enc, errors="replace")
    except LookupError:
        text = data.decode("utf-8", errors="replace")
    if not match:
        meta = re.search(r"charset=['\"]?([\w.-]+)", text[:4000], re.I)
        if meta:
            try:
                text = data.decode(meta.group(1), errors="replace")
            except LookupError:
                pass
    text = re.sub(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>", " ", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p>", "\n\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text).replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    return text.strip()


def json_to_text(data):
    try:
        obj = json.loads(data.decode("utf-8", errors="replace"))
    except Exception:
        return data.decode("utf-8", errors="replace")
    return json.dumps(obj, ensure_ascii=False, indent=1)


def _pdf_literal_strings(data):
    out = []
    i = 0
    n = len(data)
    while i < n:
        if data[i] != 0x28:
            i += 1
            continue
        chars = []
        i += 1
        depth = 1
        while i < n and depth:
            c = data[i]
            if c == 0x5C and i + 1 < n:
                i += 1
                e = data[i]
                mapping = {ord(k): v for k, v in {
                    "n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f",
                    "(": "(", ")": ")", "\\": "\\",
                }.items()}
                if e in mapping:
                    chars.append(mapping[e])
                elif 48 <= e <= 55:
                    octs = bytes([e])
                    for _ in range(2):
                        if i + 1 < n and 48 <= data[i + 1] <= 55:
                            i += 1
                            octs += bytes([data[i]])
                        else:
                            break
                    chars.append(chr(int(octs, 8)))
                else:
                    chars.append(chr(e))
            elif c == 0x28:
                depth += 1
                chars.append("(")
            elif c == 0x29:
                depth -= 1
                if depth:
                    chars.append(")")
            elif c < 128:
                chars.append(chr(c))
            i += 1
        text = "".join(chars).strip()
        if any(ch.isalnum() for ch in text):
            out.append(text)
    return out


def pdf_to_text(data):
    """不依賴 pdftotext。只抽出文字繪製運算子裡的字串，足夠做關鍵字摘錄。"""
    parts = []
    for match in re.finditer(rb"stream\r?\n", data):
        start = match.end()
        end = data.find(b"endstream", start)
        if end < 0:
            continue
        raw = data[start:end]
        if raw.endswith(b"\r\n"):
            raw = raw[:-2]
        elif raw.endswith(b"\n"):
            raw = raw[:-1]
        header = data[max(0, match.start() - 400):match.start()]
        if b"FlateDecode" in header:
            try:
                raw = zlib.decompress(raw)
            except zlib.error:
                continue
        strings = _pdf_literal_strings(raw)
        if strings:
            parts.append(" ".join(strings))
    return "\n".join(parts).strip()


def to_plain_text(data, kind, content_type):
    if kind == "pdf":
        return pdf_to_text(data)
    if kind == "json":
        return json_to_text(data)
    if kind == "html":
        return html_to_text(data, content_type)
    return data.decode("utf-8", errors="replace")


def sniff_kind(url, content_type, data):
    ctype = (content_type or "").split(";")[0].strip().lower()
    if "pdf" in ctype or data.startswith(b"%PDF") or url.lower().split("?", 1)[0].endswith(".pdf"):
        return "pdf"
    if "json" in ctype or data[:1] in (b"{", b"["):
        return "json"
    if ctype.startswith("text/") or "html" in ctype or "xml" in ctype or not ctype:
        return "html"
    return "bin"


def matching_snippets(text, keywords, radius=320, limit=8):
    """回傳 (offset, keyword, snippet)。offset 是 text 內的字元位置。"""
    if not text or not keywords:
        return []
    folded = text.casefold()
    hits = []
    for keyword in keywords:
        needle = keyword.casefold()
        if not needle:
            continue
        start = 0
        found = 0
        while found < limit:
            index = folded.find(needle, start)
            if index < 0:
                break
            hits.append((index, keyword, len(needle)))
            found += 1
            start = index + max(1, len(needle))
    hits.sort()
    spans = []
    for index, keyword, length in hits:
        begin = max(0, index - radius)
        end = min(len(text), index + length + radius)
        if spans and begin <= spans[-1][1]:
            prev_begin, prev_end, prev_keyword, prev_index = spans[-1]
            spans[-1] = (prev_begin, max(prev_end, end), prev_keyword, prev_index)
            continue
        spans.append((begin, end, keyword, index))
        if len(spans) >= limit:
            break
    out = []
    for begin, end, keyword, index in spans:
        snippet = re.sub(r"\s+", " ", text[begin:end]).strip()
        out.append((index, keyword, snippet))
    return out


def format_report(header, snippets, max_chars, lead=""):
    lines = list(header)
    if lead:
        lines.append("LEAD=" + lead)
    if not snippets:
        lines.append("NO_HITS")
    for offset, keyword, snippet in snippets:
        lines.append(f"## offset={offset} keyword={keyword}")
        lines.append(snippet)
    return cap_text("\n".join(lines) + "\n", max_chars)


def load_rawmap(path):
    if not path or not Path(path).exists():
        return {}
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def update_rawmap(path, source_key, filename):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    with path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.seek(0)
        raw = handle.read()
        data = json.loads(raw) if raw.strip() else {}
        if not isinstance(data, dict):
            data = {}
        data[source_key] = filename
        handle.seek(0)
        handle.truncate()
        text = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
        handle.write(text)
        handle.flush()


def existing_text(rawdir, rawmap_path, source_key):
    rawdir = Path(rawdir)
    mapping = load_rawmap(rawmap_path)
    name = mapping.get(source_key)
    if isinstance(name, str):
        path = rawdir / name
        if path.is_file() and path.stat().st_size > 0:
            return path
    path = rawdir / f"{source_key}.txt"
    if path.is_file() and path.stat().st_size > 0:
        return path
    return None


def check_source_key(source_key):
    if not KEY_RE.fullmatch(source_key or ""):
        raise SystemExit(f"sourceKey 只允許英數、點、底線、連字號：{source_key!r}")


def check_url(url):
    if not (url.startswith("http://") or url.startswith("https://")):
        raise SystemExit(f"只抓 http/https：{url!r}")


def challenge_reason(status, body, content_type):
    if status in (401, 403, 429):
        return f"blocked_{status}"
    if status != 200:
        return f"http_{status}"
    if "pdf" in (content_type or "").lower() or body.startswith(b"%PDF"):
        return None
    sample = body[:12000].decode("utf-8", errors="replace").casefold()
    if any(marker in sample for marker in CHALLENGE_MARKERS):
        return "challenge_page"
    return None


def cmd_status(rawdir, rawmap_path, max_chars):
    rawdir = Path(rawdir)
    mapping = load_rawmap(rawmap_path)
    lines = ["RESULT=status", f"rawmapEntries={len(mapping)}"]
    for key in sorted(mapping):
        name = mapping[key]
        path = rawdir / name if isinstance(name, str) else None
        size = path.stat().st_size if path and path.is_file() else -1
        lines.append(f"{key}\t{name}\t{size}")
    if rawdir.is_dir():
        known = {name for name in mapping.values() if isinstance(name, str)}
        orphans = sorted(path.name for path in rawdir.glob("*.txt") if path.name not in known)
        if orphans:
            lines.append("unmappedTxt=" + ",".join(orphans[:40]))
    return cap_text("\n".join(lines) + "\n", max_chars)


def cmd_lookup(rawdir, rawmap_path, source_key, keywords, max_chars):
    check_source_key(source_key)
    path = existing_text(rawdir, rawmap_path, source_key)
    if path is None:
        return cap_text(f"RESULT=missing\nsourceKey={source_key}\n", max_chars)
    text = path.read_text(encoding="utf-8", errors="replace")
    snippets = matching_snippets(text, keywords)
    lead = "" if snippets else re.sub(r"\s+", " ", text[:400]).strip()
    header = [
        "RESULT=lookup",
        f"sourceKey={source_key}",
        f"file={path.name}",
        f"textChars={len(text)}",
    ]
    return format_report(header, snippets, max_chars, lead)


def cmd_fetch(rawdir, rawmap_path, source_key, url, keywords, max_chars):
    check_source_key(source_key)
    check_url(url)
    rawdir = Path(rawdir)
    rawdir.mkdir(parents=True, exist_ok=True)
    cached = existing_text(rawdir, rawmap_path, source_key)
    if cached is not None:
        text = cached.read_text(encoding="utf-8", errors="replace")
        snippets = matching_snippets(text, keywords)
        lead = "" if snippets else re.sub(r"\s+", " ", text[:400]).strip()
        header = [
            "RESULT=cached",
            f"sourceKey={source_key}",
            f"file={cached.name}",
            f"textChars={len(text)}",
            "note=已有原文，未重抓",
        ]
        return format_report(header, snippets, max_chars, lead)

    part = rawdir / f".{source_key}.fetch-part"
    cmd = build_curl_command(url, part)
    try:
        proc = subprocess.run(cmd, capture_output=True)
    except FileNotFoundError:
        return "RESULT=error\nnote=找不到 curl\n"
    if proc.returncode != 0:
        part.unlink(missing_ok=True)
        err = proc.stderr.decode("utf-8", errors="replace").strip().splitlines()
        note = err[-1] if err else f"curl exit {proc.returncode}"
        return cap_text(f"RESULT=error\nsourceKey={source_key}\nnote={note}\n", max_chars)
    body = part.read_bytes() if part.exists() else b""
    if not body.strip():
        part.unlink(missing_ok=True)
        return f"RESULT=error\nsourceKey={source_key}\nnote=空內容，未存成來源\n"
    write_out = proc.stdout.decode("utf-8", errors="replace").strip()
    status_text, _, content_type = write_out.partition("\t")
    try:
        status = int(status_text or "0")
    except ValueError:
        status = 0
    reason = challenge_reason(status, body, content_type)
    if reason or status != 200:
        part.unlink(missing_ok=True)
        label = reason or f"http_{status}"
        return (
            f"RESULT={label}\nsourceKey={source_key}\nhttp={status}\n"
            "note=放棄（403／挑戰頁／非 200）。不要加 -k，不要改抓 Wayback。\n"
        )
    kind = sniff_kind(url, content_type, body)
    ext = {"pdf": "pdf", "json": "json", "html": "html", "bin": "bin"}[kind]
    original = rawdir / f"{source_key}.{ext}"
    original.write_bytes(body)
    part.unlink(missing_ok=True)
    text = to_plain_text(body, kind, content_type)
    text_path = rawdir / f"{source_key}.txt"
    text_path.write_text(text, encoding="utf-8")
    if rawmap_path:
        update_rawmap(rawmap_path, source_key, text_path.name)
    snippets = matching_snippets(text, keywords)
    lead = "" if snippets else re.sub(r"\s+", " ", text[:400]).strip()
    header = [
        "RESULT=fetched",
        f"sourceKey={source_key}",
        f"http={status}",
        f"contentType={content_type}",
        f"saved={original.name}",
        f"text={text_path.name}",
        f"bytes={len(body)}",
        f"textChars={len(text)}",
        "rawmap=" + ("updated" if rawmap_path else "skipped"),
    ]
    if keywords and not snippets:
        header.append("note=沒有命中關鍵字；下面 LEAD 只是開頭，換關鍵字再用 lookup")
    return format_report(header, snippets, max_chars, lead)


def main(argv=None):
    parser = argparse.ArgumentParser(description="抓來源並只印命中段落")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def add_common(command):
        command.add_argument("--rawdir", required=True)
        command.add_argument("--rawmap")
        command.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)

    status = sub.add_parser("status")
    add_common(status)

    fetch = sub.add_parser("fetch")
    add_common(fetch)
    fetch.add_argument("--url", required=True)
    fetch.add_argument("--source-key", required=True)
    fetch.add_argument("--keywords", default="")

    lookup = sub.add_parser("lookup")
    add_common(lookup)
    lookup.add_argument("--source-key", required=True)
    lookup.add_argument("--keywords", required=True)

    args = parser.parse_args(argv)
    if args.cmd == "status":
        sys.stdout.write(cmd_status(args.rawdir, args.rawmap, args.max_chars))
        return 0
    keywords = split_keywords(args.keywords)
    if args.cmd == "lookup":
        if not keywords:
            raise SystemExit("lookup 需要 --keywords")
        sys.stdout.write(cmd_lookup(args.rawdir, args.rawmap, args.source_key, keywords, args.max_chars))
        return 0
    sys.stdout.write(cmd_fetch(
        args.rawdir, args.rawmap, args.source_key, args.url, keywords, args.max_chars))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
