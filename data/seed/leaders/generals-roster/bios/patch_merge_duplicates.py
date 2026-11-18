#!/usr/bin/env python3
"""合併將領生平重複人物（可重跑；已合併就不動）。

依據：
- World Line 主管 2026-11-12 06:32「chesterwnimitz 和 chesternimitz 重複，請合併成一筆」（S/batch012）。
- World Line 主管 2026-11-12 10:20：A/batch021 小澤治三郎重複兩筆（key「小泽治三郎」與 jisaburoozawa）合併，保留 jisaburoozawa，
  與 Nimitz 合併一起、主迴圈（.dev/cc-generals-bios-loop.sh）跑完後執行。
執行時機：主迴圈結束後手動執行（來源不足補跑已於 09:16 取消，.dev/cc-generals-insuff-post.sh 不會再呼叫），避免和主迴圈搶同一檔／index。
規則：
- 保留哪筆（mode）：
  - "prefer"：擇優保留——先比 meetsMinimum，再比有起迄日的任期數、citation 數、中文字數；全同則保留 preferred（Nimitz：chesterwnimitz）。
  - "keep"：主管指定，一律保留 preferred（小澤：jisaburoozawa），不比分數。
- 被丟棄那筆的 citation 依「同 ord 且中文正文相同的段落」「同 key 的職位／角色」併入保留者（以 sourceKey＋quote 去重）；
  gaps、searchLog 以內容去重後併入；頂層 sources 本來就共用，不刪。
- 不新增欄位（不改 schema）：在保留者的 field:identity gap 記錄合併經過。
- 合併後跑 verify.py；不過就還原原檔並回報失敗。--dry-run 不動 repo：合併結果寫到暫存目錄（附 rawmap.json）跑 verify.py 並回報。
- 寫檔保留原檔 JSON 格式（縮排／ensure_ascii／結尾換行）。
用法（repo 根目錄）：python3 -I data/seed/leaders/generals-roster/bios/patch_merge_duplicates.py [--dry-run]；輸出一行 JSON 摘要。
"""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from check_min import check  # noqa: E402

VERIFY = HERE.parent.parent / "b3-trial" / "verify.py"
MERGES = [  # (tier, batch, key_a, key_b, preferred, mode, person, decision)
    ("S", "012", "chesterwnimitz", "chesternimitz", "chesterwnimitz", "prefer", "Chester W. Nimitz", "World Line 主管 2026-11-12 06:32"),
    ("A", "021", "jisaburoozawa", "小泽治三郎", "jisaburoozawa", "keep", "小澤治三郎（Jisaburō Ozawa）", "World Line 主管 2026-11-12 10:20"),
]
IDENTITY_NOTE = ("名單重複已合併：{kept}（保留）與 {dropped}（併入後刪除）為同一人 {person}；"
                 "依 {decision} 決定，由 patch_merge_duplicates.py 於主迴圈結束後合併（保留規則：{mode}），"
                 "citation／gaps／searchLog 取聯集（併入 citation {nc} 筆、gap {ng} 筆、searchLog {ns} 筆）。")


def fmt_of(raw):
    d = json.loads(raw)
    for ind in (1, 2, None):
        for ea in (False, True):
            if json.dumps(d, ensure_ascii=ea, indent=ind) == raw.rstrip("\n"):
                return (ind, ea, raw.endswith("\n"))
    return (1, False, raw.endswith("\n"))


def dump(d, fmt):
    ind, ea, nl = fmt
    return json.dumps(d, ensure_ascii=ea, indent=ind) + ("\n" if nl else "")


def run_verify(rj, report):
    return subprocess.run([sys.executable, "-I", str(VERIFY), str(rj), "--report", str(report)], capture_output=True, text=True)


def ncit(p):
    n = 0
    for sec in ("paragraphs", "positions", "roleCandidates"):
        for x in p.get(sec) or []:
            n += len(x.get("citations") or [])
    return n


def score(p):
    r = check(p)
    return (r["meetsMinimum"], r["termsFull"], ncit(p), r["zhChars"])


def ckey(c):
    return (c.get("sourceKey"), c.get("quote"))


def jkey(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True)


def merge_into(kept, dropped):
    nc = ng = ns = 0
    kp = {(g.get("ord"), (g.get("body") or {}).get("zh-Hant")): g for g in kept.get("paragraphs") or []}
    for g in dropped.get("paragraphs") or []:
        t = kp.get((g.get("ord"), (g.get("body") or {}).get("zh-Hant")))
        if t is None:
            continue
        have = {ckey(c) for c in t.get("citations") or []}
        for c in g.get("citations") or []:
            if ckey(c) not in have:
                t.setdefault("citations", []).append(c); have.add(ckey(c)); nc += 1
    for sec in ("positions", "roleCandidates"):
        km = {x.get("key"): x for x in kept.get(sec) or []}
        for x in dropped.get(sec) or []:
            t = km.get(x.get("key"))
            if t is None:
                continue
            have = {ckey(c) for c in t.get("citations") or []}
            for c in x.get("citations") or []:
                if ckey(c) not in have:
                    t.setdefault("citations", []).append(c); have.add(ckey(c)); nc += 1
    kg = {jkey(g) for g in kept.get("gaps") or []}
    for g in dropped.get("gaps") or []:
        if g.get("target") == "field:identity":
            continue
        if jkey(g) not in kg:
            kept.setdefault("gaps", []).append(g); kg.add(jkey(g)); ng += 1
    ks = {jkey(s) for s in kept.get("searchLog") or []}
    for s in dropped.get("searchLog") or []:
        if jkey(s) not in ks:
            kept.setdefault("searchLog", []).append(s); ks.add(jkey(s)); ns += 1
    return nc, ng, ns


def main():
    dry = "--dry-run" in sys.argv
    out = []
    for tier, nn, a, b, pref, mode, person, decision in MERGES:
        rj = HERE / tier / f"batch{nn}" / "research.json"
        raw = rj.read_text(encoding="utf-8"); fmt = fmt_of(raw)
        d = json.loads(raw)
        people = d.get("people") or []
        pa = next((p for p in people if p.get("key") == a), None)
        pb = next((p for p in people if p.get("key") == b), None)
        if pa is None or pb is None:
            out.append({"file": str(rj.relative_to(HERE)), "status": "already_merged_or_missing",
                        "present": [k for k, p in ((a, pa), (b, pb)) if p is not None]})
            continue
        sa, sb = score(pa), score(pb)
        if mode == "keep":
            kept, dropped = (pa, pb) if pref == a else (pb, pa)
        elif sa > sb or (sa == sb and pref == a):
            kept, dropped = pa, pb
        else:
            kept, dropped = pb, pa
        before = {"kept": kept["key"], "dropped": dropped["key"], "score_kept": list(score(kept)), "score_dropped": list(score(dropped))}
        nc, ng, ns = merge_into(kept, dropped)
        note = IDENTITY_NOTE.format(kept=kept["key"], dropped=dropped["key"], person=person, decision=decision, mode=mode, nc=nc, ng=ng, ns=ns)
        idg = [g for g in kept.get("gaps") or [] if g.get("target") == "field:identity"]
        if idg:
            idg[0]["note"] = note
        else:
            kept.setdefault("gaps", []).append({"target": "field:identity", "gapKind": "identity_uncertain", "note": note})
        d["people"] = [p for p in people if p is not dropped]
        rec = {"file": str(rj.relative_to(HERE)), "status": "merged" if not dry else "dry_run", "mode": mode, **before,
               "people_before": len(people), "people_after": len(d["people"]),
               "added_citations": nc, "added_gaps": ng, "added_searchLog": ns, "after": check(kept)}
        if dry:
            with tempfile.TemporaryDirectory(prefix="wl-merge-dry-") as td:
                tj = Path(td) / "research.json"
                tj.write_text(dump(d, fmt), encoding="utf-8")
                if d.get("rawMap"):
                    shutil.copy2(rj.parent / d["rawMap"], Path(td) / d["rawMap"])
                v = run_verify(tj, Path(td) / "verify-report.json")
                rec["dry_verify_rc"] = v.returncode
                rec["dry_verify_tail"] = (v.stdout + v.stderr)[-400:]
        else:
            bak = rj.with_suffix(".json.pre-merge")
            shutil.copy2(rj, bak)
            rj.write_text(dump(d, fmt), encoding="utf-8")
            v = run_verify(rj, rj.parent / "verify-report.json")
            if v.returncode != 0:
                shutil.copy2(bak, rj)
                rec["status"] = "verify_failed_reverted"
                rec["verify_tail"] = (v.stdout + v.stderr)[-600:]
            bak.unlink(missing_ok=True)
        out.append(rec)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
