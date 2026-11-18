"""準備一個抽取批次：片段檔（附來源表）＋ agent 提示詞。

寫入 staging/<battle>/snip/<batch>.json 與 prompts/<batch>.md。
沒有命中片段的缺口直接寫入 out/<batch>-auto.json 的 noFind，不送 agent。
"""
from __future__ import annotations

from pathlib import Path

from . import paths, snippets


def prompt_template_path():
    here = Path(__file__).resolve()
    # skill 目錄：~/wl-battle-skill/.claude/skills/battle-run/prompts/extract.md
    # 安裝後：repo/.claude/skills/battle-run/prompts/extract.md
    cands = [
        here.parents[3] / ".claude/skills/battle-run/prompts/extract.md",  # repo or skill root
        Path.home() / "wl-battle-skill/.claude/skills/battle-run/prompts/extract.md",
    ]
    for p in cands:
        if p.is_file():
            return p
    raise SystemExit("找不到 extract.md 提示詞，請確認 skill 已放到 .claude/skills/battle-run/prompts/")


def prepare(repo, battle, stage, gaps, batch, *, win=240, mx=5, url_substr=None, source_key=None, urls=None, existing_keys=None, loc=True):
    stage = Path(stage)
    corp = snippets.corpus_from_cache(repo, battle, stage, paths, url_substr=url_substr, source_key=source_key, urls=urls)
    items = snippets.extract(gaps, corp, win=win, mx=mx, existing_keys=existing_keys)
    auto = [{"gapId": it["gap"]["id"], "why": "關鍵字在所有已快取原文中都沒有命中（Python 自動判定，未送 agent）"}
            for it in items if not it["snippets"]]
    dropped = {}
    if loc:
        places = snippets.known_places(paths.load_battle(repo, battle, "osm-places.json", {}))
        items, dropped = snippets.loc_filter(items, places)
        auto += [{"gapId": gid, "why": f"命中的 {n} 段片段裡，部隊名前後 {snippets.LOC_NEAR} 字元內都沒有地名（Python 自動判定，未送模型）"}
                 for gid, n in dropped.items()
                 if not next(it for it in items if it["gap"]["id"] == gid)["snippets"]]
    items_ok = [it for it in items if it["snippets"]]
    paths.write_json(stage / "out" / f"{batch}-auto.json", {
        "battle": battle, "batch": batch + "-auto", "candidates": [], "noFind": auto,
    })
    cfg = paths.load_battle(repo, battle, "battle.config.json", {}) or {}
    mp = cfg.get("mainPhase") or {}
    cand = paths.load_json(stage / "sources-candidates.json", {"sources": []})
    src = paths.source_table(repo, battle, cand)
    cite = (cfg.get("texts") or {}).get("cite") or {}
    used = {s["sourceKey"] for it in items_ok for s in it["snippets"] if s.get("sourceKey")}
    table = {}
    for k, v in src.items():
        if k not in used:
            continue
        table[k] = {
            "grade": v.get("grade"),
            "family": v.get("family"),
            "side": v.get("side"),
            "lang": (cite.get(k) or {}).get("lang") or v.get("lang"),
            "locatorBase": (cite.get(k) or {}).get("locator") or (cite.get(k) or {}).get("unpagedLocator") or v.get("title"),
        }
    slim = []
    for it in items_ok:
        rec = dict(it)
        rec["gap"] = {k: v for k, v in it["gap"].items() if k not in ("triedNote",)}
        slim.append(rec)
    snip_path = stage / "snip" / f"{batch}.json"
    out_path = stage / "out" / f"{batch}.json"
    paths.write_json(snip_path, {"battle": battle, "batch": batch, "sources": table, "items": slim})
    tmpl = prompt_template_path().read_text(encoding="utf-8")
    lead = cfg.get("leadIn") or {}
    period = f"{mp.get('start') or lead.get('start')}～{mp.get('end') or lead.get('end')}"
    for k, v in {
        "{BATTLE}": battle,
        "{START}": str(mp.get("start") or lead.get("start") or ""),
        "{END}": str(mp.get("end") or lead.get("end") or ""),
        "{PERIOD}": period,
        "{BATCH}": batch,
        "{SNIP}": str(snip_path),
        "{OUT}": str(out_path),
    }.items():
        tmpl = tmpl.replace(k, v)
    prompt_path = stage / "prompts" / f"{batch}.md"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(tmpl, encoding="utf-8")
    st = snippets.stats(items, corp)
    st.update({"batch": batch, "autoNoFind": len(auto), "locDropped": sum(dropped.values()), "prompt": str(prompt_path), "snip": str(snip_path), "out": str(out_path)})
    return st
