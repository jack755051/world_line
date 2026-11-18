"""產生來源搜尋 agent 的精簡上下文（唯讀戰役資料）→ staging/discovery-context.json。

主 session 不要把這份檔讀進對話；只把路徑交給來源搜尋子 agent。
"""
from pathlib import Path

from . import paths, plan as planmod


def discovery_prompt_path():
    here = Path(__file__).resolve()
    cands = [
        here.parents[3] / ".claude/skills/battle-run/prompts/discovery.md",
        Path.home() / "wl-battle-skill/.claude/skills/battle-run/prompts/discovery.md",
    ]
    for p in cands:
        if p.is_file():
            return p
    return None


def build(repo, battle, stage, *, gap_list=None, pilot_gaps=None, side_hint=""):
    cfg = paths.load_battle(repo, battle, "battle.config.json", {}) or {}
    fam = cfg.get("sourceFamilies") or {}
    src = []
    for k, v in (paths.load_battle(repo, battle, "sources.json", {}) or {}).items():
        src.append({
            "sourceKey": k, "title": v.get("title"), "url": v.get("url"), "grade": v.get("grade"),
            "family": (fam.get("map") or {}).get(k),
            "side": (fam.get("sides") or {}).get((fam.get("map") or {}).get(k)),
        })
    tried = []
    for g in (paths.load_battle(repo, battle, "gaps.json", {}) or {}).get("gaps") or []:
        if str(g.get("kind") or "").startswith("source") or g.get("kind") in ("blocked", "not_found"):
            tried.append({"kind": g.get("kind"), "target": g.get("target"), "note": (g.get("note") or "")[:220]})
    gl = gap_list or paths.load_json(Path(stage) / "gap-list.json", {}) or {}
    pg_gaps = pilot_gaps or (paths.load_json(Path(stage) / "pilot-gaps.json", {}) or {}).get("gaps") or []
    policy = {}
    if paths._SP is not None:
        policy = {
            "bannedHosts": list(paths._SP.BANNED_HOSTS),
            "bannedHostLabels": paths._SP.POLICY.get("bannedHostLabels"),
            "transcriptionRule": paths._SP.POLICY.get("transcriptionHostsNote"),
        }
    sc = paths.load_json(Path(stage) / "sources-candidates.json", {"sources": [], "rejected": []}) or {}
    st = paths.load_json(Path.home() / "wl-source-cache/battles" / battle / "fetch-status.json", {}) or {}
    ctx = {
        "battle": battle,
        "mainPhase": cfg.get("mainPhase"),
        "leadIn": cfg.get("leadIn"),
        "familiesRule": fam.get("rule"),
        "existingSources": src,
        "triedOrBlocked": tried,
        "gapCounts": gl.get("counts"),
        "pilotGaps": [
            {"id": g["id"], "need": g.get("need"), **{k: g[k] for k in ("names", "unitNames", "person", "date", "place") if g.get(k)}}
            for g in pg_gaps
        ],
        "gapsByType": {
            t: [g.get("names") or [g.get("person") or g.get("date") or g.get("place")][:2]
                for g in gl.get("gaps") or [] if g["type"] == t][:60]
            for t in ("R3", "R4", "R5", "R6", "R7")
        },
        "alreadyFoundThisWeek": [{"sourceKey": x.get("sourceKey"), "title": x.get("title"), "urls": x.get("urls"), "family": x.get("family")} for x in sc.get("sources") or []],
        "alreadyRejectedThisWeek": sc.get("rejected") or [],
        "fetchBlocked": [{"url": u, "why": r.get("why")} for u, r in st.items() if r.get("status") in ("blocked", "error", "banned")],
        "sideHint": side_hint,
        **policy,
    }
    paths.write_json(Path(stage) / "discovery-context.json", ctx)
    return ctx
