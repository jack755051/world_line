#!/usr/bin/env python3
"""battle-run 命令列。主 session 只跑這個，不要自己讀原文。

用法（在 repo 根目錄，或加 --repo）：
  python3 -I tools/battles/battle_run/cli.py dry-run --battle dunkirk_1940 --pilot ellis-ch10-calais
  python3 -I tools/battles/battle_run/cli.py plan --battle <b>
  python3 -I tools/battles/battle_run/cli.py snippets --battle <b> --gaps <gap-list.json>
  python3 -I tools/battles/battle_run/cli.py prep --battle <b> --batch b01
  python3 -I tools/battles/battle_run/cli.py verify --battle <b>
  python3 -I tools/battles/battle_run/cli.py tokens --since 2026-11-18T08:00:00+08:00
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 避免在 repo 的 tools/ 留下 __pycache__
sys.dont_write_bytecode = True

# 讓「直接跑這個檔」也找得到套件
_HERE = Path(__file__).resolve().parent
if str(_HERE.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent))

from battle_run import context, fetch, paths, plan, prep, run, snippets, tokens, verify  # noqa: E402


def add_common(p):
    p.add_argument("--repo", default=None, help="world_line-battle-demo 路徑")
    p.add_argument("--stage", default=None, help="staging 目錄（預設 ~/wl-battle-staging/<battle>）")
    p.add_argument("--battle", required=False, help="戰役 slug，如 dunkirk_1940")
    return p


def resolve(args, battle=None):
    battle = battle or getattr(args, "battle", None) or (getattr(args, "pilot", None) and plan.PILOTS.get(args.pilot, {}).get("battle"))
    if not battle:
        raise SystemExit("請加 --battle 或 --pilot")
    repo = paths.bind_repo(paths.detect_repo(args.repo))
    stage = Path(args.stage).expanduser() if args.stage else paths.default_stage_root() / battle
    stage.mkdir(parents=True, exist_ok=True)
    return repo, battle, stage


def cmd_plan(args):
    kw = plan.apply_pilot(getattr(args, "pilot", None), {
        "battle": args.battle,
        "date_from": args.date_from,
        "date_to": args.date_to,
        "places": args.place or None,
        "include_leadin": not args.no_leadin,
    })
    repo, battle, stage = resolve(args, kw.get("battle"))
    files = plan.load_battle_files(repo, battle, paths)
    report_path = args.import_report
    if not report_path:
        # 常見位置：demos/battle-v2.5/battles/<id>/IMPORT-REPORT.md
        slug = battle.replace("_", "-")
        cand = repo / "demos/battle-v2.5/battles" / slug / "IMPORT-REPORT.md"
        report_path = str(cand) if cand.is_file() else None
    notes = plan.parse_import_report(Path(report_path).read_text(encoding="utf-8")) if report_path else []
    out = plan.build_gaps(
        files,
        include_leadin=kw.get("include_leadin", True),
        date_from=kw.get("date_from"),
        date_to=kw.get("date_to"),
        places=kw.get("places"),
        import_notes=notes,
    )
    if kw.get("pilot"):
        out["pilot"] = {k: v for k, v in kw["pilot"].items() if k != "label"}
        out["pilotLabel"] = kw["pilot"].get("label")
    paths.write_json(stage / "gap-list.json", out)
    batches = plan.split_batches(out["gaps"], max_per_batch=args.batch_size)
    paths.write_json(stage / "batches.json", {"battle": battle, "batches": [{"batch": b["batch"], "gapIds": b["gapIds"]} for b in batches]})
    print(json.dumps({"battle": battle, "stage": str(stage), "counts": out["counts"], "gaps": len(out["gaps"]), "batches": len(batches)}, ensure_ascii=False))
    return out, batches, repo, battle, stage


def cmd_snippets(args):
    repo, battle, stage = resolve(args)
    gp = Path(args.gaps) if args.gaps else stage / "gap-list.json"
    gaps = (paths.load_json(gp) or {}).get("gaps") or []
    if args.gap_id:
        gaps = [g for g in gaps if g["id"] in set(args.gap_id)]
    corp = snippets.corpus_from_cache(
        repo, battle, stage, paths,
        url_substr=args.url_substr, source_key=args.source_key, urls=args.url,
    )
    items = snippets.extract(gaps, corp, win=args.win, mx=args.max)
    outp = Path(args.out) if args.out else stage / "snip" / "all.json"
    paths.write_json(outp, {"battle": battle, "items": items, "stats": snippets.stats(items, corp)})
    st = snippets.stats(items, corp)
    st["out"] = str(outp)
    st["corpusDocs"] = len(corp)
    print(json.dumps(st, ensure_ascii=False))
    return items, corp, st


def cmd_prep(args):
    repo, battle, stage = resolve(args)
    gp = Path(args.gaps) if args.gaps else stage / "gap-list.json"
    data = paths.load_json(gp) or {}
    gaps = data.get("gaps") or []
    if args.gap_id:
        gaps = [g for g in gaps if g["id"] in set(args.gap_id)]
    # 若有 batches.json 且指定 batch，只取該批
    if args.batch and (stage / "batches.json").exists() and not args.gap_id:
        bmap = {b["batch"]: b["gapIds"] for b in (paths.load_json(stage / "batches.json") or {}).get("batches") or []}
        if args.batch in bmap:
            want = set(bmap[args.batch])
            gaps = [g for g in gaps if g["id"] in want]
    pilot = data.get("pilot") or {}
    st = prep.prepare(
        repo, battle, stage, gaps, args.batch or "b01",
        win=args.win, mx=args.max,
        url_substr=args.url_substr or pilot.get("url_substr"),
        source_key=args.source_key or pilot.get("source_key"),
        urls=args.url,
        existing_keys=set((paths.load_battle(repo, battle, "sources.json") or {})),
        loc=not args.no_loc_filter,
    )
    print(json.dumps(st, ensure_ascii=False))
    return st


def cmd_run(args):
    repo, battle, stage = resolve(args)
    bs = [b for x in args.batch for b in x.split(",") if b]
    if not bs:
        raise SystemExit("請加 --batch b03,b04")
    u = run.run(repo, battle, stage, bs, model=args.model, name=args.name, dry=args.dry)
    print(json.dumps(u, ensure_ascii=False))
    return u


def cmd_verify(args):
    repo, battle, stage = resolve(args)
    _rep, summary = verify.run(repo, battle, stage)
    print(summary)
    return summary


def cmd_context(args):
    repo, battle, stage = resolve(args)
    gl = paths.load_json(stage / "gap-list.json")
    ctx = context.build(repo, battle, stage, gap_list=gl, side_hint=args.side_hint or "")
    print(json.dumps({"battle": battle, "bytes": len(json.dumps(ctx, ensure_ascii=False)), "path": str(stage / "discovery-context.json")}, ensure_ascii=False))


def cmd_fetch(args):
    repo, battle, stage = resolve(args)
    rows = fetch.run(repo, battle, stage)
    from collections import Counter
    print(json.dumps({"battle": battle, "byStatus": dict(Counter(r["status"] for r in rows)), "n": len(rows)}, ensure_ascii=False))


def cmd_tokens(args):
    since = tokens.parse_since(args.since)
    extra = []
    try:
        extra.append(paths.detect_repo(args.repo))
    except SystemExit:
        pass
    extra += args.project_dir or []
    rep = tokens.report(since, stop_tokens=args.stop_tokens, globs=tokens.default_globs(extra))
    print("\n".join(rep["lines"]))
    if rep["stop"]:
        sys.exit(2)


def cmd_dry_run(args):
    """只跑計畫＋預篩，不啟動 agent、不連網。輸出寫進 --stage。"""
    out, batches, repo, battle, stage = cmd_plan(args)
    pilot = out.get("pilot") or {}
    url_substr = args.url_substr or pilot.get("url_substr")
    source_key = args.source_key or pilot.get("source_key")
    corp = snippets.corpus_from_cache(
        repo, battle, stage, paths,
        url_substr=url_substr, source_key=source_key, urls=args.url,
    )
    items = snippets.extract(out["gaps"], corp, win=args.win, mx=args.max)
    dropped = {}
    if not args.no_loc_filter:
        items, dropped = snippets.loc_filter(items, snippets.known_places(paths.load_battle(repo, battle, "osm-places.json", {})))
    st = snippets.stats(items, corp)
    st["locDropped"] = sum(dropped.values())
    paths.write_json(stage / "dry-run-snippets.json", {
        "battle": battle, "pilot": out.get("pilotLabel") or args.pilot,
        "urlSubstr": url_substr, "sourceKey": source_key,
        "stats": st,
        "corpus": [{"sourceKey": c["sourceKey"], "url": c["url"], "chars": c["chars"]} for c in corp],
        "items": [
            {
                "id": it["gap"]["id"],
                "type": it["gap"]["type"],
                "subtype": it["gap"].get("subtype"),
                "need": it["gap"].get("need"),
                "keywords": it["keywords"],
                "nSnippets": len(it["snippets"]),
                "snippetChars": sum(len(s["text"]) for s in it["snippets"]),
            }
            for it in items
        ],
    })
    # 也寫一份給人工看的摘要
    lines = [
        f"battle {battle}  pilot {out.get('pilotLabel') or args.pilot or '-'}",
        f"gaps {st['gaps']}  with-snippets {st['gapsWithSnippets']}  without {st['gapsWithoutSnippets']}  loc-dropped-snippets {st['locDropped']}",
        f"snippets {st['snippets']}  snippet-chars {st['snippetChars']}  corpus-chars {st['corpusChars']}  ratio {st['ratio']}",
        f"corpus docs {len(corp)}  batches {len(batches)}  stage {stage}",
        f"counts {json.dumps(out['counts'], ensure_ascii=False)}",
    ]
    (stage / "dry-run-summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return st


def build_parser():
    p = argparse.ArgumentParser(prog="battle_run")
    sub = p.add_subparsers(dest="cmd", required=True)

    def S(name, fn, **extra):
        sp = sub.add_parser(name)
        add_common(sp)
        sp.add_argument("--pilot", default=None, choices=list(plan.PILOTS) + [None] if False else list(plan.PILOTS), nargs="?")
        # argparse choices with optional is messy; just a string
        sp.set_defaults(func=fn, **extra)
        return sp

    # re-do more cleanly
    p = argparse.ArgumentParser(prog="battle_run")
    sub = p.add_subparsers(dest="cmd", required=True)

    def base(name, help=None):
        sp = sub.add_parser(name, help=help)
        add_common(sp)
        return sp

    sp = base("plan", "算出缺口清單")
    sp.add_argument("--pilot", default=None)
    sp.add_argument("--date-from", dest="date_from", default=None)
    sp.add_argument("--date-to", dest="date_to", default=None)
    sp.add_argument("--place", action="append", default=[])
    sp.add_argument("--no-leadin", action="store_true")
    sp.add_argument("--batch-size", type=int, default=8)
    sp.add_argument("--import-report", dest="import_report", default=None)
    sp.set_defaults(func=cmd_plan)

    def add_snip_opts(sp):
        sp.add_argument("--gaps", default=None)
        sp.add_argument("--gap-id", action="append", default=[])
        sp.add_argument("--win", type=int, default=280)
        sp.add_argument("--max", type=int, default=6)
        sp.add_argument("--url-substr", dest="url_substr", default=None)
        sp.add_argument("--source-key", dest="source_key", default=None)
        sp.add_argument("--url", action="append", default=[])
        sp.add_argument("--out", default=None)
        sp.add_argument("--no-loc-filter", dest="no_loc_filter", action="store_true", help="不做 R3 地名鄰近篩選")

    sp = base("snippets", "從快取原文切片段")
    add_snip_opts(sp)
    sp.set_defaults(func=cmd_snippets)

    sp = base("prep", "準備一批的片段檔與提示詞")
    add_snip_opts(sp)
    sp.add_argument("--batch", default="b01")
    sp.set_defaults(func=cmd_prep)

    sp = base("run", "一次 claude -p 處理一批或多批（片段放進提示詞、不給工具），寫 out/<name>.json")
    sp.add_argument("--batch", action="append", default=[], help="可重複或用逗號：--batch b03,b04")
    sp.add_argument("--model", default="sonnet", help="sonnet｜haiku｜opus")
    sp.add_argument("--name", default=None, help="輸出檔名（預設 b03 或 b03-b06）")
    sp.add_argument("--dry", action="store_true", help="只寫提示詞、印字數，不呼叫模型")
    sp.set_defaults(func=cmd_run)

    sp = base("verify", "驗收 staging/out 候選，印一行摘要")
    sp.set_defaults(func=cmd_verify)

    sp = base("context", "寫 discovery-context.json")
    sp.add_argument("--side-hint", dest="side_hint", default="")
    sp.set_defaults(func=cmd_context)

    sp = base("fetch", "抓 sources-candidates.json 的新網址（不繞過、不重抓）")
    sp.set_defaults(func=cmd_fetch)

    sp = base("tokens", "統計用量，超過門檻以結束碼 2 退出")
    sp.add_argument("--since", required=True)
    sp.add_argument("--stop-tokens", dest="stop_tokens", type=int, default=tokens.DEFAULT_STOP)
    sp.add_argument("--project-dir", dest="project_dir", action="append", default=[], help="另外要統計的工作目錄")
    sp.set_defaults(func=cmd_tokens)

    sp = base("dry-run", "只跑計畫＋預篩，不啟動 agent")
    sp.add_argument("--pilot", default=None)
    sp.add_argument("--date-from", dest="date_from", default=None)
    sp.add_argument("--date-to", dest="date_to", default=None)
    sp.add_argument("--place", action="append", default=[])
    sp.add_argument("--no-leadin", action="store_true")
    sp.add_argument("--batch-size", type=int, default=8)
    sp.add_argument("--import-report", dest="import_report", default=None)
    add_snip_opts(sp)
    sp.set_defaults(func=cmd_dry_run)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    # --pilot 在某些子命令可能不存在
    if getattr(args, "pilot", None) is None and not getattr(args, "battle", None) and args.cmd != "tokens":
        pass
    return args.func(args)


if __name__ == "__main__":
    main()
