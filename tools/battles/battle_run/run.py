"""一次 `claude -p` 呼叫處理一批或多批（取代開完整子 agent）。

片段直接放進提示詞，模型不給任何工具、不載 MCP、不讀 CLAUDE.md，只輸出 JSON；Python 寫 out/<name>.json。
2026-11-18 試跑：開完整子 agent 一批約 5 萬 token，其中九成是固定成本；這個做法固定成本約 600 token。
工作目錄設在 staging，所以用量記在 ~/.claude/projects/*wl-battle-staging*，`tokens` 指令算得到。
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from . import paths

SYSTEM = "你是資料抄錄程式。只根據使用者給的片段輸出一個 JSON 物件，不輸出其他文字。"
GAP_KEEP = ("id", "type", "subtype", "phase", "unitKey", "names", "echelon", "side", "missingDates", "need", "period", "personKey", "key", "date")
SNIP_KEEP = ("sid", "sourceKey", "url", "pdfPage", "dateHeadingBefore", "text")


def template_path():
    here = Path(__file__).resolve()
    for p in (here.parents[3] / ".claude/skills/battle-run/prompts/extract-inline.md",
              Path.home() / "wl-battle-skill/.claude/skills/battle-run/prompts/extract-inline.md"):
        if p.is_file():
            return p
    raise SystemExit("找不到 extract-inline.md")


def build_prompt(battle, name, snip_docs, start, end, accessed):
    sources, items = {}, []
    for d in snip_docs:
        sources.update(d.get("sources") or {})
        for it in d.get("items") or []:
            items.append({
                "gap": {k: v for k, v in it["gap"].items() if k in GAP_KEEP and v not in (None, [], "")},
                "snippets": [{k: s[k] for k in SNIP_KEEP if s.get(k) is not None} for s in it["snippets"]],
            })
    data = json.dumps({"sources": sources, "items": items}, ensure_ascii=False, separators=(",", ":"))
    t = template_path().read_text(encoding="utf-8")
    for k, v in {"{BATTLE}": battle, "{START}": start, "{END}": end, "{BATCH}": name,
                 "{DATA}": data, '"accessedOn": "2026-11-18"': f'"accessedOn": "{accessed}"'}.items():
        t = t.replace(k, v)
    return t, [it["gap"]["id"] for it in items]


def parse_json(text):
    a, b = text.find("{"), text.rfind("}")
    if a < 0 or b <= a:
        raise ValueError("回覆裡沒有 JSON 物件")
    return json.loads(text[a:b + 1])


def call(prompt, model, cwd):
    cmd = ["claude", "-p", "--model", model, "--tools", "", "--strict-mcp-config",
           "--mcp-config", '{"mcpServers":{}}', "--disable-slash-commands", "--setting-sources", "",
           "--system-prompt", SYSTEM, "--output-format", "json"]
    r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, cwd=str(cwd))
    if r.returncode != 0:
        raise SystemExit(f"claude -p 失敗（{r.returncode}）：{(r.stderr or r.stdout)[:300]}")
    return json.loads(r.stdout)


def run(repo, battle, stage, batches, model="sonnet", name=None, accessed=None, dry=False):
    import datetime
    stage = Path(stage)
    name = name or (batches[0] if len(batches) == 1 else f"{batches[0]}-{batches[-1]}")
    docs = []
    for b in batches:
        p = stage / "snip" / f"{b}.json"
        if not p.is_file():
            raise SystemExit(f"沒有 {p}，先跑 prep --batch {b}")
        docs.append(paths.load_json(p))
    cfg = paths.load_battle(repo, battle, "battle.config.json", {}) or {}
    mp, lead = cfg.get("mainPhase") or {}, cfg.get("leadIn") or {}
    start, end = str(mp.get("start") or lead.get("start") or ""), str(mp.get("end") or lead.get("end") or "")
    accessed = accessed or datetime.date.today().isoformat()
    prompt, gap_ids = build_prompt(battle, name, docs, start, end, accessed)
    (stage / "prompts").mkdir(parents=True, exist_ok=True)
    (stage / "prompts" / f"{name}.inline.md").write_text(prompt, encoding="utf-8")
    if not gap_ids:
        return {"name": name, "gaps": 0, "note": "這幾批沒有要送模型的缺口（都已自動記查無）"}
    if dry:
        return {"name": name, "gaps": len(gap_ids), "promptChars": len(prompt), "dry": True}
    res = call(prompt, model, stage)
    try:
        out = parse_json(res.get("result") or "")
    except (ValueError, json.JSONDecodeError) as e:
        (stage / "out-raw").mkdir(exist_ok=True)
        (stage / "out-raw" / f"{name}.txt").write_text(res.get("result") or "", encoding="utf-8")
        raise SystemExit(f"{name}：回覆不是 JSON（{e}），原樣存在 out-raw/{name}.txt")
    out["battle"], out["batch"] = battle, name
    out.setdefault("candidates", [])
    out.setdefault("noFind", [])
    seen = {c.get("gapId") for c in out["candidates"]} | {n.get("gapId") for n in out["noFind"]}
    for gid in gap_ids:
        if gid not in seen:
            out["noFind"].append({"gapId": gid, "why": "模型回覆沒有提到這個缺口（程式補記）"})
    out["model"] = model
    paths.write_json(stage / "out" / f"{name}.json", out)
    u = res.get("usage") or {}
    usage = {"name": name, "model": model, "gaps": len(gap_ids), "promptChars": len(prompt),
             "input": u.get("input_tokens", 0), "cacheCreate": u.get("cache_creation_input_tokens", 0),
             "cacheRead": u.get("cache_read_input_tokens", 0), "output": u.get("output_tokens", 0),
             "costUsd": res.get("total_cost_usd"), "candidates": len(out["candidates"]), "noFind": len(out["noFind"])}
    usage["tokens"] = usage["input"] + usage["cacheCreate"] + usage["cacheRead"] + usage["output"]
    log = stage / "usage.jsonl"
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(usage, ensure_ascii=False) + "\n")
    return usage
