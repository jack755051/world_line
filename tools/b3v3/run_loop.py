#!/usr/bin/env python3
"""B3 v3 生平的便宜驅動：一次一個 Claude，模型與輪數寫死在啟動指令裡。

每一波：
  1. run_chunk.py next（Python：合併、verify、check_min、證據切片、下一波）。
  2. 研究前先跑 prefilter.py（Python 查詢、抓取、篩段落）。命中來源少於 2 個時，
     才跑一個只回網址的 haiku 發現步驟（WebSearch 最多 3 次），網址交回 Python 抓。
  3. 用 agent_specs.launch_profile() 啟動 agent：--model、--max-turns、--tools、
     --allowedTools（dontAsk：清單外一律拒絕）、自訂短 system prompt、--strict-mcp-config。
     提示詞是 show-prompt 的輸出（已附預查段落或證據切片）。
  4. 斷網快速失敗：輸出出現 ENOTFOUND／連線錯誤，或 DNS 連續 3 分鐘查不到 api.anthropic.com，
     就停掉 agent，等網路恢復再重跑同一個，不會乾等 75 分鐘。
  5. 撞到用量上限：等 20 分鐘再試，不探測。

    cd <repo>; python3 -u tools/b3v3/run_loop.py --chunk 123 --people <bioId>,<bioId> \\
        --state .dev/b3v3/run/pilot-state.json --spec-out .dev/b3v3/run/pilot-spec.json \\
        --log-dir ~/wl-b3v3-runs/pilot

不 git、不寫庫、不呼叫 5052。紀錄寫在 --log-dir（repo 外）。
"""
import argparse
import importlib.util
import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
API_HOST = "api.anthropic.com"
NET_RE = re.compile(
    r"(ENOTFOUND|EAI_AGAIN|ECONNREFUSED|ECONNRESET|ETIMEDOUT|ENETUNREACH|getaddrinfo|"
    r"Connection error|Unable to connect|fetch failed|socket hang up|\"subtype\":\s*\"api_retry\")",
    re.I,
)
LIMIT_RE = re.compile(
    r"(usage limit|rate limit|hit your limit|reached your limit|limit reached|try again at|resets? at|"
    r"out of extra usage|too many requests|\bHTTP\s*429\b|status(?: code)? 429|quota exceeded)",
    re.I,
)
NET_HITS_TO_KILL = 3
NET_GRACE_SECONDS = 180
DNS_FAILS_TO_KILL = 3
POLL_SECONDS = 5
DNS_EVERY_SECONDS = 60
STALL_SECONDS = 10 * 60
NET_RETRIES = 6
NET_WAIT_SECONDS = 120
LIMIT_WAIT_SECONDS = 20 * 60
FAIL_RETRIES = 1


def _load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


specs = _load("agent_specs")
run_chunk = _load("run_chunk")


def now():
    return datetime.now().isoformat(timespec="seconds")


class Journal:
    def __init__(self, log_dir):
        self.dir = Path(log_dir).expanduser()
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "journal.jsonl"

    def log(self, event, **payload):
        rec = {"ts": now(), "event": event, **payload}
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        bits = " ".join(f"{k}={v}" for k, v in payload.items() if not isinstance(v, (dict, list)))
        print(f"[{rec['ts']}] {event} {bits}", flush=True)


def dns_ok(host=API_HOST):
    try:
        socket.getaddrinfo(host, 443)
        return True
    except OSError:
        return False


def chunk_args(args):
    out = [
        "--repo", str(REPO),
        "--prompt-dir", args.prompt_dir,
        "--out-root", args.out_root,
        "--raw-root", args.raw_root,
        "--concurrency", "1",
        "--state", args.state,
        "--spec-out", args.spec_out,
        "--research-model", args.research_model,
        "--retry-model", args.retry_model,
        "--review-model", args.review_model,
        "--escalate-model", args.escalate_model,
    ]
    for flag, value in (("--chunk", args.chunk), ("--resume", args.resume), ("--people", args.people)):
        if value:
            out += [flag, value]
    return out


def py(script, *argv):
    return subprocess.run([sys.executable, "-I", str(HERE / script), *argv], cwd=REPO, capture_output=True, text=True)


def run_next(args, journal):
    proc = py("run_chunk.py", "next", *chunk_args(args))
    (journal.dir / "last-next.txt").write_text(proc.stdout + "\n" + proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        journal.log("next_failed", code=proc.returncode, stderr=proc.stderr[-800:])
        raise SystemExit(f"run_chunk next 失敗：{proc.returncode}")
    actions = [line.split(" ", 1)[1].strip() for line in proc.stdout.splitlines() if line.startswith("ACTION ")]
    finished = [line for line in proc.stdout.splitlines() if line.startswith("batch")]
    return actions, finished


def spec_agents(args):
    path = REPO / args.spec_out
    if not path.exists():
        return []
    return list(json.loads(path.read_text(encoding="utf-8")).get("agents") or [])


def build_command(agent, prompt, session_id, profile, name):
    cmd = [
        "claude",
        "--model", profile["model"],
        "--max-turns", str(profile["maxTurns"]),
        "--tools", profile["tools"],
        "--allowedTools", ",".join(profile["allowed"]),
        "--permission-mode", "dontAsk",
        "--strict-mcp-config",
        "--disable-slash-commands",
        "--system-prompt", specs.SYSTEM_PROMPT,
        "--output-format", "stream-json", "--verbose",
        "--session-id", session_id,
        "-n", name,
        "-p", prompt,
    ]
    return cmd


def kill_group(proc):
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        return
    for _ in range(30):
        if proc.poll() is not None:
            return
        time.sleep(1)
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def net_hits_in(text):
    """斷網訊號只看 CLI 自己的輸出（stderr、system 事件如 api_retry），不看 assistant／user 事件：
    agent 寫的內容或工具結果裡出現「fetch failed」不算斷網（tiers-pilot5 Reza 被誤殺）。"""
    hits = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("{"):
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError:
                obj = None
            if isinstance(obj, dict) and obj.get("type") in ("assistant", "user", "result"):
                continue
        hits += len(NET_RE.findall(line))
    return hits


def watch(proc, log_path, timeout, journal, agent_id, dns_probe=dns_ok):
    """回傳 (結果, rc)。結果：exit、network、timeout、stall。"""
    started = time.time()
    last_size = 0
    last_growth = started
    net_hits = 0
    first_net = None
    dns_fails = 0
    last_dns = started
    offset = 0
    pending = ""
    while True:
        rc = proc.poll()
        if rc is not None:
            return "exit", rc
        now_ts = time.time()
        size = log_path.stat().st_size if log_path.exists() else 0
        if size > last_size:
            with log_path.open("rb") as fh:
                fh.seek(offset)
                chunk = fh.read().decode("utf-8", errors="replace")
            offset = size
            chunk = pending + chunk
            complete, _, pending = chunk.rpartition("\n")   # 最後半行留到下次（JSON 可能還沒寫完）
            hits = net_hits_in(complete)
            if hits:
                net_hits += hits
                first_net = first_net or now_ts
            last_size = size
            last_growth = now_ts
        if now_ts - last_dns >= DNS_EVERY_SECONDS:
            last_dns = now_ts
            dns_fails = 0 if dns_probe() else dns_fails + 1
        network_bad = dns_fails >= DNS_FAILS_TO_KILL or net_hits >= NET_HITS_TO_KILL or (
            first_net is not None and now_ts - first_net >= NET_GRACE_SECONDS and dns_fails > 0)
        if network_bad:
            journal.log("network_kill", id=agent_id, netHits=net_hits, dnsFails=dns_fails, seconds=int(now_ts - started))
            kill_group(proc)
            return "network", 75
        if now_ts - started > timeout:
            journal.log("agent_timeout", id=agent_id, seconds=int(now_ts - started))
            kill_group(proc)
            return "timeout", 124
        if now_ts - last_growth > STALL_SECONDS:
            journal.log("agent_stall", id=agent_id, seconds=int(now_ts - last_growth))
            kill_group(proc)
            return "stall", 125
        time.sleep(POLL_SECONDS)


def stream_result(log_path):
    """stream-json 的最後一筆 result：輪數、用量、是否錯誤。"""
    result = None
    if not log_path.exists():
        return None
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") == "result":
            result = obj
    return result


def wait_network(journal, agent_id):
    waited = 0
    while not dns_ok():
        if waited == 0:
            journal.log("network_down_wait", id=agent_id)
        time.sleep(NET_WAIT_SECONDS)
        waited += NET_WAIT_SECONDS
        if waited > 6 * 3600:
            raise SystemExit("網路 6 小時沒有恢復，停止")
    if waited:
        journal.log("network_back", id=agent_id, waited=waited)


# 中途被砍的 attempt 沒有 result 事件：用串流裡各訊息最後一筆 usage 估算（Sonnet 費率，
# 對 tiers-pilot4／5 的 89 筆實際 costUSD 校準，誤差約 +0～20%，偏高）。WebSearch 用的 Haiku 子呼叫不在串流裡，沒算。
EST_RATES = {"input_tokens": 2.0, "cache_creation_input_tokens": 4.0, "cache_read_input_tokens": 0.2, "output_tokens": 10.0}


def partial_usage(log_path):
    """被砍的 attempt：串流 assistant 訊息的 usage（同一訊息取最後一筆）加總與估計費用。沒有就回 None。"""
    last = {}
    try:
        lines = Path(log_path).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    for line in lines:
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = obj.get("message") if isinstance(obj.get("message"), dict) else {}
        if obj.get("type") == "assistant" and isinstance(msg.get("usage"), dict):
            last[msg.get("id") or len(last)] = msg["usage"]
    if not last:
        return None
    total = {k: sum(int(u.get(k) or 0) for u in last.values()) for k in EST_RATES}
    total["messages"] = len(last)
    total["estCostUSD"] = round(sum(total[k] * rate for k, rate in EST_RATES.items()) / 1e6, 4)
    return total


def launch(agent, prompt, journal, tag="", before_attempt=None):
    """跑一個 agent 到結束。斷網就等網路恢復後重跑同一個。回傳紀錄 dict。
    before_attempt(attempt)：每次啟動前呼叫（呼叫端用來在重試前還原上一輪寫了一半的檔案）。"""
    profile = specs.launch_profile(agent, REPO)
    safe = (agent["id"] + tag).replace(":", "-")
    attempts = []
    for attempt in range(1, NET_RETRIES + 2):
        wait_network(journal, agent["id"])
        if before_attempt:
            before_attempt(attempt)
        session_id = str(uuid.uuid4())
        log_path = journal.dir / f"{safe}.{attempt}.jsonl"
        cmd = build_command(agent, prompt, session_id, profile, f"b3v3-{safe[:60]}")
        journal.log("launch", id=agent["id"] + tag, model=profile["model"], maxTurns=profile["maxTurns"],
                    session=session_id, attempt=attempt, promptChars=len(prompt))
        env = dict(os.environ, CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS="0")
        with log_path.open("ab") as fh:
            proc = subprocess.Popen(cmd, cwd=REPO, env=env, stdout=fh, stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL, start_new_session=True)
            outcome, rc = watch(proc, log_path, profile["timeoutSeconds"], journal, agent["id"])
        result = stream_result(log_path) or {}
        record = {
            "id": agent["id"] + tag, "session": session_id, "model": profile["model"], "outcome": outcome, "rc": rc,
            "subtype": result.get("subtype"), "numTurns": result.get("num_turns"),
            "usage": result.get("usage"), "modelUsage": result.get("modelUsage"),
            "durationMs": result.get("duration_ms"), "log": str(log_path),
            "result": (result.get("result") or "")[:300] if isinstance(result.get("result"), str) else None,
            "attempt": attempt,
        }
        if not record["modelUsage"]:
            record["partialUsage"] = partial_usage(log_path)
        attempts.append(record)
        journal.log("agent_end", **{k: v for k, v in record.items() if k not in ("usage", "modelUsage")},
                    usage=record["usage"])
        tail = log_path.read_text(encoding="utf-8", errors="replace")[-6000:] if log_path.exists() else ""
        if outcome == "network":
            continue
        if outcome == "exit" and LIMIT_RE.search(tail) and result.get("is_error"):
            journal.log("usage_limit_wait", id=agent["id"], seconds=LIMIT_WAIT_SECONDS)
            time.sleep(LIMIT_WAIT_SECONDS)
            continue
        break
    return attempts


def marker_ok(agent):
    """標記要存在、ok、bioId 相符，而且 stage 不早於這個 agent 的種類（研究的標記不算審查完成）。"""
    return run_chunk.marker_done(agent)


def show_prompt(args, agent):
    proc = py("run_chunk.py", "show-prompt", "--spec", str(REPO / args.spec_out), "--id", agent["id"])
    if proc.returncode != 0:
        raise SystemExit(proc.stderr)
    return proc.stdout


def parse_urls(text):
    urls = []
    for match in re.finditer(r"\{[^{}]*\"urls\"[^{}]*\}", text or ""):
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            continue
        for url in data.get("urls") or []:
            if isinstance(url, str) and url.startswith(("http://", "https://")) and url not in urls:
                urls.append(url)
    return urls[:6]


DISCOVER_MIN_NARRATIVE = 2
DISCOVER_MIN_CHARS = 2500


def needs_discover(summary):
    """有傳記敘述的命中來源少於 2 個，或預查段落太短，才花一次 haiku 找網址。"""
    narrative = summary.get("narrative", summary.get("relevant", 0))
    return narrative < DISCOVER_MIN_NARRATIVE or summary.get("snippetChars", 0) < DISCOVER_MIN_CHARS


def prefilter(args, agent, journal):
    spec = str(REPO / args.spec_out)
    proc = py("prefilter.py", "run", "--spec", spec, "--id", agent["id"])
    summary = {}
    for line in proc.stdout.splitlines():
        if line.startswith("PREFILTER "):
            summary = json.loads(line[len("PREFILTER "):])
    journal.log("prefilter", id=agent["id"], code=proc.returncode, **summary)
    if proc.returncode != 0:
        journal.log("prefilter_error", id=agent["id"], stderr=proc.stderr[-600:])
        return []
    records = []
    if args.discover and needs_discover(summary):
        disc = dict(agent, kind="discover", model=args.discover_model)
        records = launch(disc, specs.discover_prompt(agent), journal, tag=":discover")
        urls = parse_urls(" ".join((rec.get("result") or "") for rec in records))
        if not urls:
            last = Path(records[-1]["log"]) if records else None
            urls = parse_urls(stream_result(last).get("result") if last and stream_result(last) else "")
        journal.log("discover_urls", id=agent["id"], urls=urls)
        if urls:
            extra = journal.dir / f"{agent['bioId']}.urls.json"
            extra.write_text(json.dumps({"urls": urls}, ensure_ascii=False), encoding="utf-8")
            proc = py("prefilter.py", "run", "--spec", spec, "--id", agent["id"], "--extra-urls", str(extra))
            for line in proc.stdout.splitlines():
                if line.startswith("PREFILTER "):
                    journal.log("prefilter_after_discover", id=agent["id"], **json.loads(line[len("PREFILTER "):]))
    return records


def finish_without_marker(args, agent, journal):
    spec = str(REPO / args.spec_out)
    if agent["kind"] in ("research", "retry"):
        draft = Path(agent["outDir"]) / "people" / f"{agent['bioId']}.draft.json"
        if agent["kind"] == "retry" or draft.exists():
            proc = py("person_draft.py", "check", "--spec", spec, "--id", agent["id"], "--done")
            journal.log("driver_marked_done", id=agent["id"], out=proc.stdout[-400:])
            return marker_ok(agent)
        return False
    if agent["kind"] in ("review", "escalate"):
        proc = py("person_draft.py", "review-done", "--spec", spec, "--id", agent["id"], "--verdict", "returned",
                  "--note", "審查 agent 沒跑 review-done（輪數或逾時），驅動程式補記錄；需人工確認")
        journal.log("driver_marked_review", id=agent["id"], out=proc.stdout[-400:])
        return marker_ok(agent)
    return False


def main(argv=None):
    parser = argparse.ArgumentParser(description="B3 v3 便宜驅動")
    parser.add_argument("--chunk")
    parser.add_argument("--resume")
    parser.add_argument("--people")
    parser.add_argument("--prompt-dir", default=".dev/b3v3/prompts")
    parser.add_argument("--out-root", default="data/seed/leaders/b3-trial/full/v3")
    parser.add_argument("--raw-root", default=str(Path.home() / "wl-source-cache" / "b3full-v3"))
    parser.add_argument("--state", default=".dev/b3v3/run/loop-state.json")
    parser.add_argument("--spec-out", default=".dev/b3v3/run/loop-spec.json")
    parser.add_argument("--log-dir", default=str(Path.home() / "wl-b3v3-runs" / "loop"))
    parser.add_argument("--research-model", default="sonnet")
    parser.add_argument("--retry-model", default="sonnet")
    parser.add_argument("--review-model", default="sonnet")
    parser.add_argument("--escalate-model", default="opus")
    parser.add_argument("--discover-model", default="haiku")
    parser.add_argument("--no-discover", dest="discover", action="store_false")
    parser.add_argument("--max-agents", type=int, default=0, help="啟動這麼多個 agent 後停（0＝不限）")
    args = parser.parse_args(argv)
    if not args.chunk and not args.resume:
        raise SystemExit("需要 --chunk 或 --resume")
    journal = Journal(args.log_dir)
    stop_flag = journal.dir / "STOP"
    journal.log("start", chunk=args.chunk, people=args.people, pid=os.getpid())
    launched = 0
    idle = 0
    while True:
        if stop_flag.exists():
            journal.log("stop", reason="stop_flag")
            break
        actions, finished = run_next(args, journal)
        for line in finished:
            journal.log("finished", line=line)
        if not actions or actions[-1] == "done":
            journal.log("all_done")
            break
        if actions[-1] not in ("spawn", "waiting"):
            journal.log("stop", reason=f"unexpected_action={actions[-1]}")
            break
        agents = spec_agents(args)
        pending = [agent for agent in agents if not marker_ok(agent)]
        if actions[-1] == "waiting" and not pending:
            idle += 1
            if idle >= 3:
                journal.log("stop", reason="waiting_but_all_markers_done")
                return 1
            time.sleep(2)
            continue
        idle = 0
        for agent in agents:
            if marker_ok(agent):
                continue
            if args.max_agents and launched >= args.max_agents:
                journal.log("stop", reason="max_agents")
                return 0
            if agent["kind"] == "research":
                prefilter(args, agent, journal)
            prompt = show_prompt(args, agent)
            for _ in range(FAIL_RETRIES + 1):
                launch(agent, prompt, journal)
                launched += 1
                if marker_ok(agent) or finish_without_marker(args, agent, journal):
                    break
                journal.log("agent_failed", id=agent["id"])
            if not marker_ok(agent):
                journal.log("stop", reason=f"agent_failed:{agent['id']}")
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
