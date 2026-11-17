#!/usr/bin/env python3
"""把研究／重跑／審查提示改成走 fetch_source.py，禁止把整頁原文讀進上下文。可重複執行。"""
import re
import sys
from pathlib import Path

MARKER = "<!-- b3v3-token-2026-11-17 -->"
TAIL = "上述檔首的 2026-11-17 token 節流優先於本文其餘句子，包含文末「優先於上文」的舊追加。"
REPO = Path(__file__).resolve().parents[2]

FETCH_RE = re.compile(
    r"## 抓取與原文（引文核對的依據）\n"
    r"(?:.*\n){1,8}?"
    r"- 原文不進版控（只在 /tmp）。quote 從 \.txt 複製，不要從 WebFetch 的摘要複製。\n"
)
SELF_CHECK_RE = re.compile(
    r"- 自檢：`python3 -I data/seed/leaders/b3-trial/verify.py [^`]+` 必須 ok（[^）]*）；"
    r"不 ok 就修到 ok（修不了的改成 gap 或刪掉，不可放寬規則、不可改 verify.py）。"
)
SELF_CHECK_NEW = (
    "- 自檢改由工作流執行（verify.py 必須 ok 且 rawChecked=true；check_min.py 固定寫同目錄 "
    "`check_min-report.json`）。你不要跑這兩支，也不要為了自檢 Read 原文。"
    "只有在沒有工作流、且你寫的是整份 research.json 時才自己跑；不 ok 就修到 ok"
    "（修不了的改成 gap 或刪掉，不可放寬規則、不可改 verify.py）。"
)


def fetch_section(rawdir, outdir):
    return (
        "## 抓取與原文（引文核對的依據）\n"
        "- 用 WebSearch／WebFetch **只做發現**（找候選 URL）。引文必須來自已存的 .txt。"
        "**禁止** Read／cat／head／sed 整份 raw 檔，**禁止**把整頁貼進上下文或工具參數。\n"
        f"- 先看已抓過的來源，已有的 sourceKey **不要重抓**："
        f"`python3 -I tools/b3v3/fetch_source.py status --rawdir {rawdir} --rawmap {outdir}/rawmap.json`\n"
        "- 抓新頁（工具內建 curl、不加 -k、UA 為 Mozilla/5.0；只印短摘要與關鍵字命中的段落）："
        f"`python3 -I tools/b3v3/fetch_source.py fetch --rawdir {rawdir} --rawmap {outdir}/rawmap.json "
        "--source-key <sourceKey> --url <url> --keywords '<姓名|原文姓名|生卒年|職稱>'`\n"
        "- 抄 quote 前只用 lookup，不要打開整檔："
        f"`python3 -I tools/b3v3/fetch_source.py lookup --rawdir {rawdir} --rawmap {outdir}/rawmap.json "
        "--source-key <sourceKey> --keywords '<想核對的原文片段>'`\n"
        "- 每個 sourceKey 對一個 .txt。rawmap.json 由 fetch 維護（單人檔也可帶 rawMap）。"
        f"research.json 頂層填 `\"rawDir\": \"{rawdir}\"`、`\"rawMap\": \"rawmap.json\"`。\n"
        "- 原文不進版控。quote 必須是 lookup 印出的那段裡的逐字片段，不要從 WebFetch 的摘要複製。"
        "Cloudflare／Anubis／403：工具會放棄，記入 searchLog 後換站；不要加 `-k`，不要用 Wayback 代替。\n"
    )


def insert_banner(text, banner):
    if MARKER not in text:
        lines = text.splitlines(keepends=True)
        block = "\n" + banner.strip() + "\n"
        if lines:
            lines.insert(1, block)
            text = "".join(lines)
        else:
            text = block + text
    if TAIL not in text:
        if not text.endswith("\n"):
            text += "\n"
        text += "\n" + TAIL + "\n"
    return text


def kind_of(name):
    if "retry" in name:
        return "retry"
    if "review" in name:
        return "review"
    if "research" in name:
        return "research"
    return None


def patch_text(name, text):
    kind = kind_of(name)
    if kind is None:
        return text, []
    notes = []
    if kind == "research":
        match = FETCH_RE.search(text)
        if match:
            raw = re.search(r"-o (\S+)/<sourceKey>\.html", match.group(0))
            out = re.search(r"寫 `(\S+)/rawmap\.json`", match.group(0))
            if not raw or not out:
                notes.append("fetch-section-unparsed")
            else:
                text = FETCH_RE.sub(fetch_section(raw.group(1), out.group(1)), text, count=1)
        elif "tools/b3v3/fetch_source.py fetch" not in text:
            notes.append("fetch-section-missing")
        text2, n = SELF_CHECK_RE.subn(SELF_CHECK_NEW, text, count=1)
        if n:
            text = text2
        elif "自檢改由工作流執行" not in text:
            notes.append("self-check-missing")
        text = text.replace("至少實際 curl 抓取", "至少用 tools/b3v3/fetch_source.py 抓取")
        text = text.replace("至少實際抓取（curl）", "至少用 tools/b3v3/fetch_source.py 抓取")
        text = text.replace("fetch_source.py 抓取**", "fetch_source.py 抓取 **")
        outdir = "{{OUTDIR}}"
        found = re.search(r"`((?:\{\{OUTDIR\}\}|data/seed/leaders/b3-trial/full/v3/batch\d+))/research\.json`", text)
        if found:
            outdir = found.group(1)
        text = insert_banner(text, f"""{MARKER}
若任務指定了 bioId：只研究那一人，只寫 `{outdir}/people/<bioId>.json`（`person`、`sources`、`rawMap`、`researchedOn`、`policyVersion`、`alignedTo`、`alignNote`、`schemaNote`），不要寫 research.json，不要跑 verify.py 或 check_min.py。抓取一律用下方「抓取與原文」的 fetch_source.py；已有的 sourceKey 不要重抓。禁止 Read／cat 整份 raw。WebFetch 只用於發現網址。""")
    elif kind == "retry":
        text = text.replace("至少實際 curl 抓取", "至少用 tools/b3v3/fetch_source.py 抓取")
        text = text.replace(
            "先讀它與現有 research.json、searchLog。",
            "先讀它。若任務給了單人檔，只讀那一份與其中的 searchLog，不要讀整份 research.json。",
        )
        text = text.replace(
            "在 research.json 的條目（paragraphs／positions／roleCandidates／gaps／searchLog／sources 新增）",
            "的條目（任務若指定單人檔，只改該檔的 person，不要重寫整份 research.json；否則才改 research.json。欄位仍是 paragraphs／positions／roleCandidates／gaps／searchLog／sources）",
        )
        text = re.sub(
            r"- 完成後跑 `python3 -I data/seed/leaders/b3-trial/verify.py [^`]+`，須 exit 0。",
            "- 不要自己跑 verify.py 或 check_min.py（單人檔尚未合併）。工作流合併後會跑這兩支。",
            text,
            count=1,
        )
        outdir = "{{OUTDIR}}"
        found = re.search(r"`((?:\{\{OUTDIR\}\}|data/seed/leaders/b3-trial/full/v3/batch\d+))", text)
        if found:
            outdir = found.group(1)
        text = insert_banner(text, f"""{MARKER}
只重跑任務點名的人。抓取與 quote 一律用 `tools/b3v3/fetch_source.py`（先 status，已有的 sourceKey 不要重抓；fetch 只印命中段落；lookup 查片段）。禁止 Read／cat 整份 raw，禁止把整頁貼進上下文。WebFetch 只用於發現網址。不要跑 check_min.py（工作流會寫 `check_min-report.json`）。若任務要你寫單人檔，覆寫 `{outdir}/people/<bioId>.json`，不要重寫整份 research.json。最低搜尋量、來源分級、原文語言查詢、不用 `-k`、不用 Wayback、403 就放棄，全部仍適用。""")
    else:
        text, n = re.subn(r"、原文 `[^`]+`。", "、以及同目錄的 `evidence-pack.json`（每筆 claim 含段落文字、quote、sourceKey、verify 結果）。不要 Read／cat 整份 raw 原文。", text, count=1)
        if n == 0 and "evidence-pack.json" not in text:
            notes.append("review-sources-line-missing")
        text = text.replace(
            "每人至少抽 1 個來源重抓比對",
            "全批最多 1 次抽查重抓，而且只能呼叫 tools/b3v3/fetch_source.py（只看它印出的短摘）",
        )
        text = text.replace(
            "不能只信 verify.py：再人工比對引文與它支撐的句子",
            "逐字是否在原文以 verify.py 與 evidence-pack 的 verify 為準，不要打開 raw 對子字串；仍須用證據包裡的段落文字判斷 quote 是否支撐該句",
        )
        text = insert_banner(text, f"""{MARKER}
逐字引文以 verify.py 為準。先讀同目錄 `evidence-pack.json`（工作流已產生：每筆 claim 的段落文字、quote、sourceKey、verify 結果），不要整批重讀 raw、不要重抓網頁。全批最多 1 次 spot refetch，且必須走 fetch_source.py。不要跑 check_min.py；最低標準看同目錄 `check_min-report.json`。來源分級、T14、Q1–Q10、最低嘗試仍然要查。""")
    return text, notes


def patch_file(path):
    original = path.read_text(encoding="utf-8")
    updated, notes = patch_text(path.name, original)
    if updated != original:
        path.write_text(updated, encoding="utf-8")
    return notes


def main(argv=None):
    roots = [REPO / ".dev" / "b3v3" / "prompts", REPO / "data" / "seed" / "leaders" / "b3-trial" / "full" / "v3"]
    problems = []
    changed = 0
    for root in roots:
        for path in sorted(root.glob("*.md")):
            if kind_of(path.name) is None:
                continue
            notes = patch_file(path)
            changed += 1
            for note in notes:
                problems.append(f"{path}: {note}")
    print(f"patched {changed} prompts")
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
