#!/usr/bin/env python3
"""組 B3 v3 研究／補欄／審查 agent 的提示詞。提示詞由 run_chunk.py 寫進 spec，不進主 session。"""
import re

RETURN_SCHEMA = {
    "type": "object",
    "properties": {
        "bioId": {"type": "string"},
        "name": {"type": "string"},
        "stage": {"type": "string"},
        "ok": {"type": "boolean"},
        "rawMapIsObject": {
            "type": "boolean",
            "description": "單人檔的 rawMap 是物件（sourceKey → 檔名），不是字串",
        },
        "note": {"type": "string", "description": "60 字以內，不要貼引文或頁面"},
    },
    "required": ["bioId", "name", "stage", "ok", "note"],
}

REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "bioId": {"type": "string"},
        "name": {"type": "string"},
        "verdict": {"type": "string", "description": "pass、pass_with_changes、returned 或 篇幅不足"},
        "ok": {"type": "boolean"},
        "note": {"type": "string", "description": "60 字以內。若改了起迄日，寫明理由"},
    },
    "required": ["bioId", "name", "verdict", "ok", "note"],
}

DATE_RULE = (
    "不要把已有出處、或 evidenceNote／gap 寫明為推論的起迄日改成 null。"
    "batch093 的佩納曾被審查拿掉推論迄日，check_min 就從達標變成未達標。"
    "沒有新的來源衝突就維持原日期。若來源確實無法支撐，保留原日期，"
    "或改成 null 時必須同時寫 gap，note 以「待查證：缺迄日」或「待查證：缺起日」開頭，並在回覆 note 寫原因。"
)

RAWMAP_RULE = (
    "單人檔的 rawMap 必須是 JSON 物件：鍵是 sourceKey，值是檔名（通常是 \"<sourceKey>.txt\"）。"
    "不可以寫成字串 \"rawmap.json\"。那一行只屬於 research.json 頂層。"
)


def rules(repo):
    return (
        f"工作目錄：{repo}。只寫任務指定的單人檔、agent-done 與 RAWDIR。"
        "不要 git add／commit／push，不要寫任何資料庫，不要呼叫 5052 API，"
        "不要繞過 Cloudflare／Anubis／403，不要用 Wayback 代替被擋的頁。"
        "不要 Read、cat、head 整份 raw 原文，不要把整頁貼進上下文。"
        "已在 raw 目錄（快取於 ~/wl-source-cache/b3full-v3）的 sourceKey 不要重抓；先 status，再用 lookup。"
    )


def keyword_hint(person):
    line = person.get("line") or ""
    bio = person.get("bioId") or ""
    if bio:
        line = line.replace(bio, " ")
    years = []
    for year in re.findall(r"(?<!\d)\d{4}(?!\d)", line):
        if year not in years:
            years.append(year)
        if len(years) == 4:
            break
    parts = [person.get("name"), person.get("nameZh"), *years]
    return "|".join(part for part in parts if part)


def person_path(batch, person):
    return f"{batch['outDir']}/people/{person['bioId']}.json"


def done_path(batch, person):
    return f"{batch['outDir']}/people/{person['bioId']}.agent-done.json"


def evidence_path(batch, person):
    return f"{batch['outDir']}/people/{person['bioId']}.evidence.json"


def review_note_path(batch, person):
    return f"{batch['outDir']}/people/{person['bioId']}.review.json"


def done_line(batch, person, stage):
    return (
        "做完後寫 "
        f"{done_path(batch, person)} ，內容是 "
        f'{{"stage":"{stage}","bioId":"{person["bioId"]}","ok":true}}。'
        "不要寫別的批次。"
    )


def research_prompt(batch, person, repo):
    return "\n".join([
        "你只研究一個人，開一個全新的研究。不要研究提示詞裡的其他人。",
        f"人物：{person['line']}",
        f"bioId：{person['bioId']}",
        f"只寫這個檔：{person_path(batch, person)}",
        "內容是一個 JSON 物件：person、sources、rawMap、researchedOn、"
        "policyVersion（bio-2026-11-v0）、alignedTo（b0b0e0f）、alignNote、schemaNote。"
        f"不要寫 {batch['outDir']}/research.json。",
        RAWMAP_RULE,
        f"規則檔（格式、來源分級、Q1–Q10、T14、最低 8 次查詢／4 種來源類型／原文語言檢索都要做）：{batch['researchPrompt']}",
        "抓取與引文不要照規則檔裡舊的 curl／整檔 Read。一律：",
        f"python3 -I tools/b3v3/fetch_source.py status --rawdir {batch['rawDir']} --rawmap {batch['outDir']}/rawmap.json",
        "已有的 sourceKey 不要重抓。新頁：",
        "python3 -I tools/b3v3/fetch_source.py fetch "
        f"--rawdir {batch['rawDir']} --rawmap {batch['outDir']}/rawmap.json "
        f"--source-key <sourceKey> --url <url> --keywords '{keyword_hint(person)}'",
        "抄 quote 只用 lookup，關鍵字改成你要的原文片段。WebFetch 只用於發現網址。",
        "不要跑 verify.py 或 check_min.py。回覆不要貼引文或頁面。",
        done_line(batch, person, "research"),
        rules(repo),
    ])


def retry_prompt(batch, person, repo):
    fields = person.get("missingFields") or []
    listed = "\n".join(f"- {field['field']}：{field['detail']}" for field in fields) or "- （沒有列出欄位就不要改）"
    return "\n".join([
        "只補這個人缺的欄位。不要重做整份研究，不要改本批其他人，不要為了湊字數加段。",
        f"人物：{person['line']}",
        f"bioId：{person['bioId']}",
        f"規則檔（來源分級、Q1–Q10 仍適用；本任務的範圍優先於規則檔裡的整份重跑）：{batch['retryPrompt']}",
        f"只讀這一份：{person_path(batch, person)}。不要讀整份 research.json，不要讀 raw 原文。",
        "改完覆寫同一個單人檔。",
        "這次只補這些欄位：",
        listed,
        "缺起日或缺迄日：只找這個日期。找到就填上並附帶日期的引文；找不到就保留或寫上"
        "「待查證：缺起日」或「待查證：缺迄日」gap。",
        "缺引文或引文空白：只補該筆 quote，quote 必須來自 lookup。",
        DATE_RULE,
        "不要追求 15 次查詢或 6 個新頁。searchLog 只記這次實際查的步驟，標 \"round\": \"field-retry\"。",
        f"抓取：python3 -I tools/b3v3/fetch_source.py status --rawdir {batch['rawDir']} --rawmap {batch['outDir']}/rawmap.json",
        f"已有的 sourceKey 不要重抓。新頁與 lookup 都用 fetch_source.py。建議關鍵字：{keyword_hint(person)}",
        RAWMAP_RULE,
        "不要跑 verify.py 或 check_min.py。回覆不要貼頁面。",
        done_line(batch, person, "retry"),
        rules(repo),
    ])


def review_prompt(batch, person, repo):
    lines = [
        "你是審查者，只審一個人。",
        f"人物：{person.get('line') or person.get('name')}",
        f"bioId：{person['bioId']}",
        f"規則檔 {batch['reviewPrompt']} 的來源分級、T14、最低標準、Q1–Q10 仍適用；本任務的範圍優先。",
        "上次審查被中斷，請重查這個人。" if batch.get("recheck") else f"審查 batch{batch['nn']} 的這個人。",
    ]
    if person.get("shortfallFlag"):
        lines.append("這個人標記為篇幅不足。不要為了湊字數重寫或加段。審查既有內容，verdict 寫「篇幅不足」。")
    lines.extend([
        DATE_RULE,
        f"只讀這兩個檔：{person_path(batch, person)} 與 {evidence_path(batch, person)}。",
        "證據切片裡有這個人的 claim、check_min 判定、verify 錯誤。不要讀整份 research.json，不要讀整份 evidence-pack.json，不要讀 raw。",
        "逐字引文以證據切片的 verify 為準。全人最多 1 次抽查重抓，而且只能：",
        "python3 -I tools/b3v3/fetch_source.py fetch "
        f"--rawdir {batch['rawDir']} --rawmap {batch['outDir']}/rawmap.json "
        "--source-key <sourceKey> --url <url> --keywords '<詞>'",
        "已有的 sourceKey 不要重抓。",
        f"要改內容就覆寫 {person_path(batch, person)}。",
        f"另寫 {review_note_path(batch, person)} ，內容是 "
        '{"bioId":"...","verdict":"pass|pass_with_changes|returned|篇幅不足","changes":[],"note":"..."}。',
        "不要跑 verify.py 或 check_min.py。不要寫整份 review.json（驅動程式會合併）。回覆不要貼頁面。",
        done_line(batch, person, "review"),
        rules(repo),
    ])
    return "\n".join(lines)
