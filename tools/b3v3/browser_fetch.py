#!/usr/bin/env python3
"""瀏覽器補抓（2026-11-20 pilot，Tai 核准 t87s346）：curl 被擋（403／Imperva／Anubis／Cloudflare）的 A／B 白名單網址，
用 Claude in Chrome 以真瀏覽器正常開一次、取頁面文字（get_page_text，不截圖）。
規則：只開新分頁、只關自己開的分頁；遇到 captcha／要解的挑戰／登入／付費牆就停、記 blocked；不點擊、不填表、不跑 JS、
不用 Wayback。原文存進 raw 快取，另寫 <key>.meta.json 記來源網址與「via browser」。"""
import hashlib
import json
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

CHROME_TOOLS = ["mcp__claude-in-chrome__tabs_context_mcp", "mcp__claude-in-chrome__browser_batch",
                "mcp__claude-in-chrome__navigate", "mcp__claude-in-chrome__get_page_text",
                "mcp__claude-in-chrome__tabs_close_mcp"]
# 2026-11-20：不加 --strict-mcp-config 時每輪帶約 12 萬 token 的 MCP／外掛上下文（Reza 一次 $0.69）；加了約 1.3 萬。
STOP_MARKERS = ("captcha", "recaptcha", "hcaptcha", "verify you are human", "verifying you are human", "are you a robot",
                "checking your browser", "just a moment", "attention required", "cf-browser-verification",
                "making sure you're not a bot", "anubis", "incapsula", "request unsuccessful", "access denied",
                "403 forbidden", "sign in to continue", "log in to continue", "please log in", "subscribe to continue",
                "subscribe to read", "this content is for subscribers", "paywall",
                "正在執行安全驗證", "請稍候", "抵禦惡意機器人")
SYSTEM = ("You operate Chrome only through the given claude-in-chrome tools. Never click, type, fill forms, run "
          "JavaScript, or solve anything. Be terse.")


def browser_key(url):
    host = re.sub(r"[^a-z0-9]+", "-", (urlparse(url).hostname or "").lower()).strip("-")[:30]
    return f"b-{host}-{hashlib.sha1(url.encode()).hexdigest()[:8]}"


def order_by_host(urls):
    """交錯不同 host，讓同一 host 的兩次開頁之間隔開（agent 每步本來就要數秒）。"""
    buckets = {}
    for url in urls:
        buckets.setdefault(re.sub(r"^www\.", "", urlparse(url).hostname or ""), []).append(url)
    out = []
    while any(buckets.values()):
        for host in list(buckets):
            if buckets[host]:
                out.append(buckets[host].pop(0))
    return out


def browser_targets(urls):
    """只開真正要看的頁：OJS 的 /article/download/<id>/… 改成同站的 /article/view/<id>（不觸發檔案下載到使用者的
    下載資料夾）；同一篇文章的 OAI 目錄頁（…article-<id>/Description）在已有 view 頁時略過；去重。"""
    out, ids = [], set()
    for url in urls:
        m = re.match(r"(https?://[^/]+/index\.php/[^/]+)/article/download/(\d+)\b", url)
        if m:
            url = f"{m.group(1)}/article/view/{m.group(2)}"
        aid = re.search(r"/article/view/(\d+)|article-(\d+)", url)
        art = aid and (aid.group(1) or aid.group(2))
        if "/Record/oai:" in url and art in ids:
            continue
        if art and "/article/view/" in url:
            ids.add(art)
        if url not in out:
            out.append(url)
    return out


def pdf_like(url):
    """會變成檔案下載的網址（PDF、DSpace bitstream、CMS 附件、OJS download）：瀏覽器不開，免得存進使用者的下載資料夾。"""
    path = (urlparse(url).path or "").lower()
    return (path.endswith((".pdf", ".doc", ".docx", ".epub", ".zip")) or "/bitstream/" in path
            or "/attachment/file/" in path or "/article/download/" in path or "/download/" in path)


def connected_devices(runner=subprocess.run):
    """便宜檢查（約 $0.006）：bridge 上連著哪些瀏覽器。回傳 (devices, costUSD, limited)。"""
    cmd = ["claude", "--chrome", "--model", "sonnet", "--max-turns", "2", "--max-budget-usd", "0.05", "--tools", "",
           "--strict-mcp-config", "--disable-slash-commands", "--system-prompt", "Be terse.",
           "--allowedTools", "mcp__claude-in-chrome__list_connected_browsers", "--permission-mode", "dontAsk",
           "--output-format", "json", "--",
           "Call mcp__claude-in-chrome__list_connected_browsers once and reply with its raw JSON result only."]
    proc = runner(cmd, capture_output=True, text=True, timeout=120)
    try:
        data = json.loads(proc.stdout)
    except (json.JSONDecodeError, TypeError):
        return [], 0.0, limit_text(proc.stdout or "")
    text = str(data.get("result") or "")
    m = re.search(r"\[.*\]", text, re.S)
    try:
        devices = json.loads(m.group(0)) if m else []
    except json.JSONDecodeError:
        devices = []
    return devices, float(data.get("total_cost_usd") or 0), limit_text(text)


def limit_text(text):
    low = (text or "").casefold()
    return ("hit your" in low and "limit" in low) or "usage_limit_reached" in low


def session_prompt(urls, device=None):
    actions = []
    for url in urls:
        actions += [{"name": "navigate", "input": {"url": url, "tabId": "<TAB>"}},
                    {"name": "get_page_text", "input": {"tabId": "<TAB>"}}]
    lines = [
        "Read the text of each URL below in a real browser tab, then close your tab(s). Steps:",
    ] + ([
        f"0. FIRST call select_browser with deviceId {device}. Call no other tool before it. If it does not reply "
        "'Selected browser', reply exactly `ABORT <its output>` and call nothing else.",
    ] if device else []) + [
        "1. tabs_context_mcp with createIfEmpty=true ONCE. Use a tab inside YOUR MCP tab group (it only contains tabs Claude "
        "opened). Never touch tabs outside that group.",
        "2. ONE browser_batch call with exactly these actions, <TAB> replaced by that tab id:",
        json.dumps(actions, ensure_ascii=False),
        "   If browser_batch fails as a whole, do the same actions as individual navigate / get_page_text calls.",
        "3. Never click, type, fill forms, scroll-hunt or solve anything. Captcha, bot challenge, login wall, paywall or error "
        "page = record BLOCKED and move on.",
        "4. tabs_close_mcp on every tab in YOUR MCP tab group.",
        "Reply with exactly one line per URL: `OK <url>` or `BLOCKED <url> <reason>`. Nothing else.",
    ]
    return "\n".join(lines)


def session_command(urls, max_turns=None, budget=0.5, device=None, debug_file=None):
    tools = CHROME_TOOLS + ([SELECT_TOOL] if device else [])
    return ["claude", "--chrome", "--model", "sonnet", "--max-turns", str(max_turns or 2 * len(urls) + 5),
            "--max-budget-usd", f"{budget:.2f}",
            "--tools", "", "--allowedTools", ",".join(tools), "--permission-mode", "dontAsk",
            "--strict-mcp-config", "--disable-slash-commands", "--system-prompt", SYSTEM,
            ] + (["--debug-file", str(debug_file)] if debug_file else []) + [
            "--output-format", "stream-json", "--verbose", "-p", session_prompt(urls, device)]


SELECT_TOOL = "mcp__claude-in-chrome__select_browser"


def routed_devices(debug_path):
    """bridge 的 routing_ack 記下每次工具呼叫實際送到哪台瀏覽器（--debug-file 的內容）。"""
    try:
        text = Path(debug_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return re.findall(r'"routed_to":"([0-9a-f-]+)"', text)


def device_problem(log_path, debug_path, device):
    """釘選瀏覽器檢查：第一個工具必須是成功的 select_browser(device)，且所有呼叫都只送到 device。回傳問題字串或 None。"""
    first, ok = None, False
    for line in Path(log_path).read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        message = event.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        for item in content if isinstance(content, list) else []:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "tool_use" and first is None:
                first = item
            elif item.get("type") == "tool_result" and first is not None and item.get("tool_use_id") == first.get("id"):
                body = item.get("content")
                if isinstance(body, list):
                    body = "\n".join(x.get("text", "") for x in body if isinstance(x, dict))
                ok = "selected browser" in str(body or "").casefold() and not item.get("is_error")
    if first is None:
        return None if not routed_devices(debug_path) else "routed-without-select"
    if not first.get("name", "").endswith("__select_browser") or (first.get("input") or {}).get("deviceId") != device:
        return "first-tool-not-select"
    if not ok:
        return "select-failed"
    wrong = sorted({d for d in routed_devices(debug_path) if d != device})
    return f"routed-to:{','.join(wrong)}" if wrong else None


def run_session(urls, log_path, max_turns=None, runner=subprocess.run, budget=0.5, device=None, debug_file=None):
    cmd = session_command(urls, max_turns, budget, device, debug_file)
    started = time.time()
    with open(log_path, "w", encoding="utf-8") as out:
        proc = runner(cmd, stdout=out, stderr=subprocess.STDOUT, timeout=900)
    return {"rc": getattr(proc, "returncode", None), "seconds": round(time.time() - started, 1)}


def parse_log(log_path):
    """回傳 (pages, result)：pages = [{url, text, toolError}]（navigate 後的 get_page_text），result = 最後的 result 事件。"""
    uses, results, result = {}, {}, {}
    order = []
    for line in Path(log_path).read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "result":
            result = event
        message = event.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        for item in content if isinstance(content, list) else []:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "tool_use":
                uses[item["id"]] = item
                order.append(item["id"])
            elif item.get("type") == "tool_result":
                body = item.get("content")
                if isinstance(body, list):
                    body = "\n".join(x.get("text", "") for x in body if isinstance(x, dict))
                results[item.get("tool_use_id")] = (str(body or ""), bool(item.get("is_error")))
    pages, current = [], None
    for uid in order:
        use = uses[uid]
        name = use.get("name", "")
        if name.endswith("__browser_batch"):
            text, err = results.get(uid, ("", True))
            pages += split_batch((use.get("input") or {}).get("actions") or [], text, err)
            continue
        if name.endswith("__navigate"):
            current = (use.get("input") or {}).get("url")
        elif name.endswith("__get_page_text") and current:
            text, err = results.get(uid, ("", True))
            pages.append({"url": current, "text": text, "toolError": err})
            current = None
    return pages, result


PAGE_HEAD = re.compile(r"Title: [^\n]*\nURL: (\S+)\n")


def _site(url):
    return re.sub(r"^www\.", "", urlparse(url or "").hostname or "")


def split_batch(actions, text, is_error):
    """browser_batch 的結果切成每頁：get_page_text 的輸出以「Title: …\nURL: …」開頭；依順序對回 navigate 的網址，
    順序對不上時用網站比對。批次整體出錯就回空（agent 會改逐頁呼叫）。"""
    wanted = [a.get("input", {}).get("url") for a in actions if a.get("name") == "navigate"]
    if not wanted:
        return []
    if is_error:
        # 批次在第一個失敗的動作停下：「actions[i] (get_page_text) failed: 原因」→ 那頁記錯誤原因；之後的頁 agent 會逐頁重做
        m = re.search(r"actions\[(\d+)\] \((\w+)\) failed: ([^\n(]+)", text)
        if not m:
            return []
        idx = int(m.group(1))
        nav_before = sum(1 for a in actions[:idx + 1] if a.get("name") == "navigate")
        if m.group(2) == "navigate":
            nav_before = max(nav_before, 1)
        url = wanted[nav_before - 1] if 0 < nav_before <= len(wanted) else None
        return [{"url": url, "text": m.group(3).strip(), "toolError": True}] if url else []
    heads = list(PAGE_HEAD.finditer(text))
    chunks = []
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        chunks.append((m.group(1), text[m.start():end].strip()))
    pages, used = [], set()
    for i, url in enumerate(wanted):
        pick = None
        if i < len(chunks) and _site(chunks[i][0]) == _site(url) and i not in used:
            pick = i
        else:
            pick = next((j for j, c in enumerate(chunks) if j not in used and _site(c[0]) == _site(url)), None)
        if pick is None:
            pages.append({"url": url, "text": "", "toolError": True})
        else:
            used.add(pick)
            pages.append({"url": url, "text": chunks[pick][1], "toolError": False})
    return pages


def strip_tab_context(text):
    """get_page_text 結果尾端的「Tab Context: …」是擴充功能附的分頁清單，不是頁面內容。"""
    return re.split(r"\n\s*Tab Context:\n", text, maxsplit=1)[0].rstrip()


def stop_reason(text):
    low = text[:6000].casefold()
    for marker in STOP_MARKERS:
        if marker in low:
            return marker
    if len(text.strip()) < 300:
        return "頁面文字不到 300 字"
    return None


def verdicts(result_text):
    out = {}
    for line in (result_text or "").splitlines():
        m = re.match(r"\s*`?(OK|BLOCKED)\s+(\S+)\s*(.*?)`?\s*$", line)
        if m:
            out[m.group(2)] = (m.group(1), m.group(3))
    return out


def save_pages(pages, result, rawdir, rawmap, update_rawmap):
    """原文存 raw 快取（文字原樣，引文才對得上），meta 另記 via browser。"""
    rawdir = Path(rawdir)
    agent_view = verdicts(result.get("result"))
    saved = []
    for page in pages:
        url = page["url"]
        reason = (f"工具錯誤：{page['text'][:100]}" if page["text"] else "工具錯誤") if page["toolError"] else stop_reason(page["text"])
        said = agent_view.get(url)
        if said and said[0] == "BLOCKED" and not reason:
            reason = f"agent 判定 blocked：{said[1]}"[:120]
        key = browser_key(url)
        entry = {"url": url, "sourceKey": key, "textChars": len(page["text"])}
        if reason:
            entry.update(status="blocked", reason=reason)
        else:
            (rawdir / f"{key}.txt").write_text(strip_tab_context(page["text"]), encoding="utf-8")
            (rawdir / f"{key}.meta.json").write_text(json.dumps({
                "url": url, "via": "browser (Claude in Chrome, get_page_text)", "model": "sonnet",
                "fetchedAt": datetime.now().astimezone().isoformat(timespec="seconds")}, ensure_ascii=False, indent=1),
                encoding="utf-8")
            update_rawmap(rawmap, key, f"{key}.txt")
            entry.update(status="fetched")
        saved.append(entry)
    return saved


def session_cost(result):
    usage = result.get("modelUsage") or {}
    return {"costUSD": round(float(result.get("total_cost_usd") or 0), 4),
            "models": sorted(usage), "numTurns": result.get("num_turns"),
            "tokens": {m: {k: v for k, v in u.items() if k.endswith("Tokens")} for m, u in usage.items()}}
