#!/usr/bin/env python3
"""B3 v3 的確定性驅動。主 session 只看這裡的短摘要。

研究、補欄、審查都由 Claude Code workflow 依本程式印出的 args 啟動 agent。
本程式負責計畫、抽出單人檔、合併、verify、check_min、每人一份證據切片。
workflow 腳本不讀檔、不跑 python。

    python3 -I tools/b3v3/run_chunk.py dry-run --repo "$PWD" \\
        --prompt-dir .dev/b3v3/prompts \\
        --out-root data/seed/leaders/b3-trial/full/v3 \\
        --raw-root "$HOME/wl-source-cache/b3full-v3" \\
        --resume .dev/b3v3/partial/chunk4-remaining.json --concurrency 3

    python3 -I tools/b3v3/run_chunk.py next ...同上
    python3 -I tools/b3v3/run_chunk.py show-prompt --spec .dev/b3v3/run/next-spec.json --id retry:094:<bioId>

2026-11-18 節流改版：
- 審查一律先用 --review-model（預設 sonnet）。Sonnet 審查後該人 verify 仍有錯，才多一個
  escalate 階段，用 --escalate-model（預設 opus）只修那些錯。check_min「未達」不再直接升 Opus。
- --people 只跑指定 bioId（試跑用）。批次裡還沒研究的人會單獨排研究，不會因為批裡已有 research.json 就被略過。
- show-prompt 會把預查段落（研究）或證據切片（審查）接在提示詞後面，agent 不必另外讀檔。
- 實際啟動 agent（固定模型、輪數上限、工具、斷網快速失敗）用 tools/b3v3/run_loop.py。
"""
import argparse
import contextlib
import importlib.util
import io
import json
import subprocess
import sys
from collections import Counter
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
CHECK_MIN = REPO_ROOT / "data" / "seed" / "leaders" / "b3-trial" / "full" / "v3" / "check_min.py"
VERIFY = REPO_ROOT / "data" / "seed" / "leaders" / "b3-trial" / "verify.py"
WORKFLOW = ".dev/b3v3/workflow/b3-v3-chunk1-and-major-retry.js"


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


plan = load("plan_work")
specs = load("agent_specs")
merge = load("merge_people")
evidence = load("evidence_pack")


def resolve(repo, value):
    path = Path(value)
    if not path.is_absolute():
        path = Path(repo) / path
    return path


def dump(data):
    return json.dumps(data, ensure_ascii=False, indent=1) + "\n"


def chunked(items, size):
    size = max(1, size)
    return [items[index:index + size] for index in range(0, len(items), size)]


def filter_people(items, people):
    """--people：每批只留指定 bioId（試跑用）。沒有指定的人整批略過。"""
    if not people:
        return items
    want = set(people)
    out = []
    for batch in items:
        kept = [person for person in batch["people"] if person["bioId"] in want]
        if not kept:
            continue
        batch = dict(batch)
        batch["people"] = kept
        batch["details"] = [d for d in batch.get("details") or [] if d.get("bioId") in want]
        batch["shortfall"] = [d for d in batch.get("shortfall") or [] if d.get("bioId") in want]
        batch["retrySkipped"] = [d for d in batch.get("retrySkipped") or [] if d.get("bioId") in want]
        retry = dict(batch.get("retry") or {"mode": "none", "people": []})
        retry["people"] = [d for d in retry.get("people") or [] if d.get("bioId") in want]
        batch["retry"] = retry
        if batch.get("researchPeople") is not None:
            batch["researchPeople"] = [bio for bio in batch["researchPeople"] if bio in want]
        out.append(batch)
    return out


def make_plan(cfg):
    chunk = [part.strip() for part in (cfg.chunk or "").split(",") if part.strip()]
    if cfg.resume:
        items, skipped = plan.from_resume(
            cfg.repo, cfg.prompt_dir, cfg.out_root, cfg.raw_root,
            resolve(cfg.repo, cfg.resume), chunk, cfg.force_research,
        )
    else:
        if not chunk:
            raise SystemExit("沒有 --resume 時需要 --chunk")
        items = plan.from_chunk(
            cfg.repo, cfg.prompt_dir, cfg.out_root, cfg.raw_root, chunk, cfg.force_research,
        )
        skipped = []
    people = [part.strip() for part in (getattr(cfg, "people", None) or "").split(",") if part.strip()]
    items = filter_people(items, people)
    if cfg.limit is not None:
        if cfg.limit < 0:
            raise SystemExit("--limit 不可為負")
        items = items[:cfg.limit]
    return {"concurrency": cfg.concurrency, "batchCount": len(items), "skipped": skipped, "batches": items}


def agent_record(kind, phase, model, batch, person, prompt, schema):
    return {
        "id": f"{kind}:{batch['nn']}:{person['bioId']}",
        "kind": kind,
        "phase": phase,
        "model": model,
        "label": f"{kind}:{batch['nn']}:{person['bioId']}",
        "batch": batch["nn"],
        "bioId": person["bioId"],
        "name": person.get("name"),
        "outDir": batch["outDir"],
        "rawDir": batch["rawDir"],
        "batchId": batch["batchId"],
        "fields": [field["field"] for field in (person.get("missingFields") or [])],
        "reviewReason": person.get("reviewReason"),
        "line": person.get("line"),
        "specPath": batch.get("specPath"),
        "prompt": prompt,
        "schema": schema,
        "doneMarker": specs.done_path(batch, person),
    }


def marker_stage(path):
    path = Path(path)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if data.get("ok") is not True:
        return None
    return data.get("stage")


def all_agents(plan_doc, cfg):
    grouped = {"research": [], "retry": [], "review": [], "escalate": []}
    spec_ref = display_path(cfg.repo, spec_path_of(cfg))
    for batch in plan_doc["batches"]:
        batch = dict(batch, specPath=spec_ref)
        if batch.get("research"):
            only = batch.get("researchPeople")
            for person in batch["people"]:
                if only is not None and person["bioId"] not in only:
                    continue
                grouped["research"].append(agent_record(
                    "research", "Research", cfg.research_model, batch, person,
                    specs.research_prompt(batch, person, cfg.repo), specs.RETURN_SCHEMA,
                ))
        for person in batch["retry"]["people"]:
            grouped["retry"].append(agent_record(
                "retry", "Retry", cfg.retry_model, batch, person,
                specs.retry_prompt(batch, person, cfg.repo), specs.RETURN_SCHEMA,
            ))
        if not batch.get("review"):
            continue
        by_bio = {detail["bioId"]: detail for detail in batch.get("details") or []}
        for person in batch["people"]:
            detail = dict(person)
            extra = by_bio.get(person["bioId"]) or {}
            detail["shortfallFlag"] = bool(extra.get("shortfallFlag"))
            detail["reviewReason"] = extra.get("reviewReason") or "OK"
            # 審查一律先用便宜的模型。Sonnet 審查（含它做的欄位修正）之後 verify 仍有錯，才升階。
            grouped["review"].append(agent_record(
                "review", "Review", cfg.review_model, batch, detail,
                specs.review_prompt(batch, detail, cfg.repo), specs.REVIEW_SCHEMA,
            ))
            stage = marker_stage(specs.done_path(batch, person))
            if stage == "review" and extra.get("verifyErrorCount"):
                grouped["escalate"].append(agent_record(
                    "escalate", "Escalate", cfg.escalate_model, batch, detail,
                    specs.review_prompt(batch, detail, cfg.repo, escalate=True), specs.REVIEW_SCHEMA,
                ))
    return grouped


def load_state(path):
    if not path.exists():
        return {"doneIds": [], "outstanding": None}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"doneIds": [], "outstanding": None}
    data.setdefault("doneIds", [])
    data.setdefault("outstanding", None)
    return data


def save_state(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump(state), encoding="utf-8")


STAGE_ORDER = {"research": 0, "retry": 1, "review": 2, "escalate": 3}


def marker_done(agent):
    path = Path(agent["doneMarker"])
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    if data.get("ok") is not True or data.get("bioId") != agent["bioId"]:
        return False
    done_at = STAGE_ORDER.get(data.get("stage"))
    want = STAGE_ORDER.get(agent["kind"])
    if done_at is None or want is None:
        return False
    return done_at >= want


def is_done(agent, state):
    return agent["id"] in set(state.get("doneIds") or []) or marker_done(agent)


def pending_groups(grouped, state):
    return {phase: [agent for agent in agents if not is_done(agent, state)] for phase, agents in grouped.items()}


def active_phase(grouped):
    for phase in ("research", "retry", "review", "escalate"):
        if grouped[phase]:
            return phase
    return None


def public_agent(agent):
    return {
        "id": agent["id"], "label": agent["label"], "phase": agent["phase"],
        "model": agent["model"], "batch": agent["batch"], "bioId": agent["bioId"],
    }


def spec_path_of(cfg):
    if cfg.spec_out:
        return resolve(cfg.repo, cfg.spec_out)
    return Path(cfg.repo) / ".dev" / "b3v3" / "run" / "next-spec.json"


def state_path_of(cfg):
    if cfg.state:
        return resolve(cfg.repo, cfg.state)
    return Path(cfg.repo) / ".dev" / "b3v3" / "run" / "state.json"


def display_path(repo, path):
    path = Path(path)
    try:
        return str(path.relative_to(repo))
    except ValueError:
        return str(path)


def dry_run_payload(plan_doc, grouped, concurrency):
    waves = []
    for phase in ("research", "retry", "review", "escalate"):
        parts = chunked(grouped[phase], concurrency)
        for index, wave in enumerate(parts, 1):
            waves.append({
                "phase": phase,
                "index": index,
                "of": len(parts),
                "models": dict(Counter(agent["model"] for agent in wave)),
                "agents": [dict(public_agent(agent), name=agent.get("name")) for agent in wave],
            })
    review_models = dict(Counter(agent["model"] for agent in grouped["review"]))
    return {
        "concurrency": concurrency,
        "skipped": plan_doc.get("skipped") or [],
        "batchCount": plan_doc["batchCount"],
        "researchAgents": len(grouped["research"]),
        "retryAgents": len(grouped["retry"]),
        "reviewAgents": len(grouped["review"]),
        "escalateAgents": len(grouped["escalate"]),
        "reviewModels": review_models,
        "retryModels": dict(Counter(agent["model"] for agent in grouped["retry"])),
        "shortfallPeople": sum(len(batch.get("shortfall") or []) for batch in plan_doc["batches"]),
        "retryPeople": [
            {"batch": agent["batch"], "name": agent.get("name"), "bioId": agent["bioId"], "fields": agent["fields"]}
            for agent in grouped["retry"]
        ],
        "escalateCeiling": len(grouped["retry"]),
        "waves": waves,
    }


def format_dry_run(plan_doc, grouped, concurrency):
    payload = dry_run_payload(plan_doc, grouped, concurrency)
    review_models = payload["reviewModels"]
    model_bits = "、".join(f"{model} {count}" for model, count in sorted(review_models.items())) or "無"
    lines = [
        f"研究 {payload['researchAgents']}、重跑 {payload['retryAgents']}、"
        f"審查 {payload['reviewAgents']}（{model_bits}），同時 {concurrency}",
    ]
    if payload["skipped"]:
        lines.append("略過 " + "、".join(payload["skipped"]))
    labels = {"research": "研究", "retry": "重跑", "review": "審查", "escalate": "升階審查"}
    for phase, label in labels.items():
        agents = grouped[phase]
        parts = chunked(agents, concurrency)
        if phase == "research" and not agents:
            lines.append("研究 0")
            continue
        if not agents:
            lines.append(f"{label} 0")
            continue
        lines.append(f"{label} {len(agents)} 人，{len(parts)} 波")
        if phase == "retry":
            for agent in agents:
                fields = "、".join(agent["fields"]) or "（無欄位）"
                lines.append(f"  {agent['batch']} {agent.get('name')}：{fields}")
        for index, wave in enumerate(parts, 1):
            models = "、".join(
                f"{model}×{count}" for model, count in sorted(Counter(agent["model"] for agent in wave).items())
            )
            who = "、".join(f"{agent['batch']}:{agent.get('name')}({agent['model']})" for agent in wave)
            lines.append(f"  第{index}/{len(parts)}波 {models} {who}")
    shortfall = [
        f"{batch['nn']} {person['name']}"
        for batch in plan_doc["batches"] for person in (batch.get("shortfall") or [])
    ]
    lines.append(f"篇幅不足、不重跑、審查時帶旗標 {len(shortfall)} 人")
    for item in shortfall:
        lines.append(f"  {item}")
    skipped_retry = [
        f"{batch['nn']} {person['name']}"
        for batch in plan_doc["batches"] for person in (batch.get("retrySkipped") or [])
    ]
    if skipped_retry:
        lines.append("已做過重跑、不再補欄 " + "、".join(skipped_retry))
    auto = [batch["nn"] for batch in plan_doc["batches"] if batch["retry"]["mode"] == "auto"]
    if auto:
        lines.append("這些批要先研究，補欄人數等研究結束才知道：" + "、".join(auto))
    if payload["escalateCeiling"]:
        lines.append(
            f"補欄那 {payload['escalateCeiling']} 人的審查先照目前判定（已標註缺迄日用審查模型）。"
            "若重跑後 check_min 變成未達或 verify 報錯，該人改升階模型。"
        )
    lines.append("主 session 用 claude --model sonnet。不要把這份清單裡的提示詞讀進對話。")
    return "\n".join(lines)


def quiet_call(func, *args, **kwargs):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        result = func(*args, **kwargs)
    return result, buffer.getvalue()


def prepare_files(agents):
    packs = {}
    check_min = plan.load_check_min()
    for agent in agents:
        out = Path(agent["outDir"])
        people = out / "people"
        people.mkdir(parents=True, exist_ok=True)
        if agent["kind"] in ("research", "discover"):
            Path(agent["rawDir"]).mkdir(parents=True, exist_ok=True)
            continue
        research = out / "research.json"
        if not research.exists():
            raise SystemExit(f"batch{agent['batch']} 沒有 research.json，不能{agent['kind']}")
        person_file = people / f"{agent['bioId']}.json"
        quiet_call(merge.extract, research, agent["bioId"], person_file)
        if agent["kind"] not in ("review", "escalate"):
            continue
        if agent["outDir"] not in packs:
            packs[agent["outDir"]] = evidence.build(research)
        person = json.loads(person_file.read_text(encoding="utf-8"))["person"]
        sliced = evidence.slice_person(packs[agent["outDir"]], person.get("key"))
        raw_dir = Path(agent["rawDir"])
        raw_ok = raw_dir.is_dir() and any(raw_dir.glob("*.txt"))
        claims = sliced["claims"]
        if not raw_ok:
            for claim in claims:
                for cite in claim.get("citations") or []:
                    cite["verify"] = {"ok": None, "reason": "這台機器沒有原文快取，不要依這格改引文"}
        data = json.loads(research.read_text(encoding="utf-8"))
        row = next(item for item in check_min.report_for(data)["people"] if item["key"] == person.get("key"))
        errors = plan.errors_for_person(plan.load_verify_errors(out), person)
        doc = {
            "bioId": agent["bioId"],
            "key": person.get("key"),
            "name": person.get("name"),
            "rawLoaded": raw_ok,
            "checkMin": {
                "verdict": row.get("verdict"),
                "paragraphs": row.get("paragraphs"),
                "zhChars": row.get("zhChars"),
                "meetsMinimum": row.get("meetsMinimum"),
                "documentedShortfall": row.get("documentedShortfall"),
                "openTerms": row.get("openTerms") or [],
            },
            "verifyErrors": errors,
            "paths": evidence.unit_paths(person),
            "claims": claims,
        }
        (people / f"{agent['bioId']}.evidence.json").write_text(dump(doc), encoding="utf-8")


def run_tool(script, args, cwd):
    return subprocess.run(
        [sys.executable, "-I", str(script), *args],
        cwd=cwd, capture_output=True, text=True,
    )


def summarize_check(out_dir):
    report = json.loads((Path(out_dir) / "check_min-report.json").read_text(encoding="utf-8"))
    counts = Counter(row.get("verdict") or "?" for row in report["people"])
    bits = " ".join(f"{name}={count}" for name, count in sorted(counts.items()))
    return bits or "空"


def merge_agents(agents, cfg):
    if not agents:
        return
    sample = agents[0]
    out = Path(sample["outDir"])
    research = out / "research.json"
    bios = [agent["bioId"] for agent in agents]
    replace = research.exists()
    overwrite = False
    try:
        quiet_call(
            merge.merge, out, sample["rawDir"], sample["batchId"], bios, replace, overwrite,
        )
    except SystemExit as exc:
        raise SystemExit(f"batch{sample['batch']} merge 失敗：{exc}") from exc


def assemble_review(batch):
    notes = []
    people_dir = Path(batch["outDir"]) / "people"
    for person in batch["people"]:
        path = people_dir / f"{person['bioId']}.review.json"
        if not path.exists():
            return False
        try:
            notes.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            return False
    doc = {
        "batch": batch["nn"],
        "reviewedOn": date.today().isoformat(),
        "partial": False,
        "people": notes,
    }
    (Path(batch["outDir"]) / "review.json").write_text(dump(doc), encoding="utf-8")
    return True


def finish_spec(spec, cfg, plan_doc):
    by_batch = {}
    for agent in spec.get("agents") or []:
        by_batch.setdefault(agent["batch"], []).append(agent)
    batches = {batch["nn"]: batch for batch in plan_doc["batches"]}
    lines = []
    for nn, agents in by_batch.items():
        merge_agents(agents, cfg)
        out = Path(agents[0]["outDir"])
        research = out / "research.json"
        verified = run_tool(VERIFY, [str(research), "--report", str(out / "verify-report.json")], cfg.repo)
        checked = run_tool(CHECK_MIN, [str(research)], cfg.repo)
        if checked.returncode != 0:
            raise SystemExit(f"check_min batch{nn} 失敗 {(checked.stderr or checked.stdout).strip()[:200]}")
        review_done = ""
        if agents[0]["kind"] in ("review", "escalate") and nn in batches:
            if assemble_review(batches[nn]):
                review_done = " review.json"
        status = "ok" if verified.returncode == 0 else "fail"
        lines.append(f"batch{nn} {agents[0]['kind']} {len(agents)}人 verify={status} {summarize_check(out)}{review_done}")
    return lines


def write_spec(path, cfg, phase, wave, wave_index, wave_count):
    doc = {
        "wave": f"{phase}-{wave_index}",
        "phase": phase,
        "index": wave_index,
        "of": wave_count,
        "concurrency": cfg.concurrency,
        "repo": cfg.repo,
        "specPath": display_path(cfg.repo, path),
        "agents": wave,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump(doc), encoding="utf-8")
    return doc


def workflow_args(cfg, spec_file, agents):
    return {
        "repo": cfg.repo,
        "specPath": display_path(cfg.repo, spec_file),
        "concurrency": cfg.concurrency,
        "agents": [public_agent(agent) for agent in agents],
    }


def print_spawn(cfg, spec_file, phase, index, total, agents):
    sys.stdout.write(
        f"ACTION spawn\n{phase} 第{index}/{total}波 {len(agents)} 人 "
        + " ".join(f"{model}={count}" for model, count in sorted(Counter(a['model'] for a in agents).items()))
        + f"\nworkflow {WORKFLOW}\n---workflow-args---\n"
    )
    json.dump(workflow_args(cfg, spec_file, agents), sys.stdout, ensure_ascii=False, indent=1)
    sys.stdout.write("\n---end---\n")


def print_waiting(agents):
    missing = "、".join(agent["id"] for agent in agents)
    sys.stdout.write(f"ACTION waiting\n還沒看到 agent-done：{missing}\nworkflow 跑完再執行 next。確定跑完但沒寫標記就加 --accept。\n")


def cmd_dry_run(cfg):
    plan_doc = make_plan(cfg)
    state = load_state(state_path_of(cfg))
    grouped = pending_groups(all_agents(plan_doc, cfg), state)
    if cfg.json:
        json.dump(dry_run_payload(plan_doc, grouped, cfg.concurrency), sys.stdout, ensure_ascii=False, indent=1)
        sys.stdout.write("\n")
        return 0
    sys.stdout.write(format_dry_run(plan_doc, grouped, cfg.concurrency) + "\n")
    return 0


def outstanding_spec(cfg, state):
    pointer = state.get("outstanding")
    if not pointer:
        return None, spec_path_of(cfg)
    path = Path(pointer)
    if not path.exists():
        return None, path
    try:
        return json.loads(path.read_text(encoding="utf-8")), path
    except json.JSONDecodeError:
        return None, path


def unfinished(spec):
    return [agent for agent in (spec.get("agents") or []) if not marker_done(agent)]


def cmd_finish(cfg):
    state = load_state(state_path_of(cfg))
    spec, path = outstanding_spec(cfg, state)
    if spec is None:
        sys.stdout.write("ACTION done\n沒有待合併的波次。\n")
        return 0
    missing = unfinished(spec)
    if missing and not cfg.accept:
        print_waiting(missing)
        return 0
    plan_doc = make_plan(cfg)
    lines = finish_spec(spec, cfg, plan_doc)
    done = set(state.get("doneIds") or [])
    for agent in spec.get("agents") or []:
        done.add(agent["id"])
    state["doneIds"] = sorted(done)
    state["outstanding"] = None
    save_state(state_path_of(cfg), state)
    sys.stdout.write("ACTION finished\n" + "\n".join(lines) + "\n")
    return 0


def cmd_prepare(cfg, state=None):
    state_path = state_path_of(cfg)
    if state is None:
        state = load_state(state_path)
    spec, _path = outstanding_spec(cfg, state)
    if spec is not None and state.get("outstanding"):
        missing = unfinished(spec)
        if missing and not cfg.accept:
            print_waiting(missing)
            return 0
        sys.stdout.write("ACTION pending-finish\n上一波標記已齊。跑 next，它會先合併再準備下一波。\n")
        return 0
    plan_doc = make_plan(cfg)
    grouped = pending_groups(all_agents(plan_doc, cfg), state)
    phase = active_phase(grouped)
    if phase is None:
        state["outstanding"] = None
        save_state(state_path, state)
        sys.stdout.write("ACTION done\n這份清單沒有還沒做的 agent。\n")
        return 0
    waves = chunked(grouped[phase], cfg.concurrency)
    wave = waves[0]
    prepare_files(wave)
    path = spec_path_of(cfg)
    write_spec(path, cfg, phase, wave, 1, len(waves))
    state["outstanding"] = str(path)
    save_state(state_path, state)
    print_spawn(cfg, path, phase, 1, len(waves), wave)
    return 0


def cmd_next(cfg):
    state_path = state_path_of(cfg)
    state = load_state(state_path)
    spec, _path = outstanding_spec(cfg, state)
    if spec is not None and state.get("outstanding"):
        missing = unfinished(spec)
        if missing and not cfg.accept:
            print_waiting(missing)
            return 0
        plan_doc = make_plan(cfg)
        lines = finish_spec(spec, cfg, plan_doc)
        done = set(state.get("doneIds") or [])
        for agent in spec.get("agents") or []:
            done.add(agent["id"])
        state["doneIds"] = sorted(done)
        state["outstanding"] = None
        save_state(state_path, state)
        sys.stdout.write("ACTION finished\n" + "\n".join(lines) + "\n")
    return cmd_prepare(cfg, state)


ATTACH_LIMIT = 24000


def attachment(agent):
    """研究附預查段落，審查附證據切片。檔案不存在就不附（agent 依提示詞自己讀）。"""
    if not agent.get("outDir") or not agent.get("bioId"):
        return ""
    people = Path(agent["outDir"]) / "people"
    if agent.get("kind") == "research":
        path, label = people / f"{agent['bioId']}.snippets.md", "預查段落"
    elif agent.get("kind") in ("review", "escalate"):
        path, label = people / f"{agent['bioId']}.evidence.json", "證據切片"
    else:
        return ""
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    if agent.get("kind") != "research":
        try:
            text = json.dumps(json.loads(text), ensure_ascii=False, separators=(",", ":"))
        except json.JSONDecodeError:
            pass
    if len(text) > ATTACH_LIMIT:
        text = text[:ATTACH_LIMIT] + "\n…[截斷；其餘用 lookup]"
    return f"\n---{label}（{path.name}）---\n{text}\n---end---\n"


def cmd_show_prompt(spec_file, agent_id):
    data = json.loads(Path(spec_file).read_text(encoding="utf-8"))
    for agent in data.get("agents") or []:
        if agent.get("id") == agent_id:
            sys.stdout.write(agent.get("prompt") or "")
            if not (agent.get("prompt") or "").endswith("\n"):
                sys.stdout.write("\n")
            sys.stdout.write(attachment(agent))
            return 0
    sys.stderr.write(f"spec 裡沒有 {agent_id}\n")
    return 1


def build_parser():
    parser = argparse.ArgumentParser(description="B3 v3 便宜續跑驅動")
    sub = parser.add_subparsers(dest="cmd", required=True)
    show = sub.add_parser("show-prompt")
    show.add_argument("--spec", required=True)
    show.add_argument("--id", required=True)
    for name in ("dry-run", "prepare", "finish", "next"):
        command = sub.add_parser(name)
        command.add_argument("--repo", required=True)
        command.add_argument("--prompt-dir", required=True)
        command.add_argument("--out-root", required=True)
        command.add_argument("--raw-root", required=True)
        command.add_argument("--resume")
        command.add_argument("--chunk")
        command.add_argument("--people", help="只跑這些 bioId（逗號分隔，試跑用）")
        command.add_argument("--limit", type=int)
        command.add_argument("--force-research", action="store_true")
        command.add_argument("--concurrency", type=int, default=3)
        command.add_argument("--research-model", default="sonnet")
        command.add_argument("--retry-model", default="sonnet")
        command.add_argument("--review-model", default="sonnet")
        command.add_argument("--escalate-model", default="opus")
        command.add_argument("--spec-out")
        command.add_argument("--state")
        command.add_argument("--json", action="store_true")
        command.add_argument("--accept", action="store_true")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.cmd == "show-prompt":
        return cmd_show_prompt(args.spec, args.id)
    if args.cmd == "dry-run":
        return cmd_dry_run(args)
    if args.cmd == "prepare":
        return cmd_prepare(args)
    if args.cmd == "finish":
        return cmd_finish(args)
    if args.cmd == "next":
        return cmd_next(args)
    raise SystemExit(f"未知指令 {args.cmd}")


if __name__ == "__main__":
    raise SystemExit(main())
