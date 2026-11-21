#!/usr/bin/env python3
"""組 B3 v3 研究／補欄／審查 agent 的提示詞與啟動設定。提示詞由 run_chunk.py 寫進 spec，不進主 session。

2026-11-18 節流改版：
- 提示詞自足、只有幾 KB。agent 不再讀 research-NN.md／review-NN.md 規則檔（約 30KB）。
- 研究前由 prefilter.py 做查詢、抓取與段落篩選；agent 主要只寫草稿 JSON，Python 組單人檔並自檢。
- 審查只讀證據切片，改檔用 person_patch.py 局部修改，不讀單人檔全文。
- launch_profile() 固定每一種 agent 的模型、輪數上限、工具與允許的指令。
"""
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

SYSTEM_PROMPT = (
    "你是 World Line B3 v3 人物生平資料的工作者。工作目錄是 repo 根目錄。"
    "只用任務列出的指令與檔案；指令照原樣執行，不要加 cd、管線、heredoc 或其他程式。"
    "不要讀任務沒有指定的檔。不要 git、不要寫資料庫、不要呼叫 5052 API、不要繞過 Cloudflare／Anubis／403、不要用 Wayback。"
    "回覆極短，不要貼引文或頁面。"
)

SOURCE_RULE = (
    "來源：段落／職位／角色的出處只能 A 或 B。A＝國家級傳記辭典、政府／議會／國家圖書館官方頁、人名權威檔；"
    "B＝具名作者的機構百科、學術機構傳記、學術出版品。無具名作者的百科條目、無作者館藏圖說是未評等，"
    "私人彙編（rulers.org、archontology.org 類）是 X：都只能當 C 放 gap 的 candidateCitations。"
    "第三方轉錄官方文件記 B。預查的「建議等級」只依網域，要看頁面確認（Treccani 百科條目 B、DBI A；"
    "Britannica、コトバンク要具名執筆者）。不用、也不寫任何 Wikipedia／Wikidata／百度網址。"
)

QUOTE_RULE = (
    "quote：從預查段落或 lookup 輸出逐字複製（空白可不同），NFC ≤80 字，一句完整語意片段，"
    "不跨「@」段、不含省略號、不轉述、不翻譯。同一來源可多筆。datePrecision 只在 quote 本身含日期時填 day／month／year，否則 null。"
)

WRITE_RULE = (
    "段落：zh-Hant 至少 3 段、合計至少 300 字（來源夠時）；每段 zh ≤400 字、en ≤800 字元，en 與 zh 對應。"
    "每個事實子句（日期、地點、人名、職稱、評語）都要對得到該段某筆 quote；對不到就拆段或刪句，不可編造、不可用常識或空話湊字。"
    "段落 citation 加 claimSpan：它支撐 zh-Hant 正文第幾句（依「。！？；」切句，從 1 起算，例 [1,2]）；每一句都要有 citation 對到。"
    "精度：day 寫原日期；month／year 起點寫該單位第一天，終點寫下一單位第一天（到 1911 年 → 1912-01-01、year）；"
    "日期 null 時精度也 null。段落 period 迄點依段內最後一件事。"
    "盡力後仍不夠 3 段／300 字：照實寫，加 gap target=paragraph:length、gapKind=not_found，note 以「篇幅不足：」開頭，寫段數／字數與查過的來源類型。"
)

TERM_RULE = (
    "任期：positions／roleCandidates 每筆都要 period.start、period.end 與含該日期的 quote。"
    "迄日查不到：照寫 start，加 gap target=position:<key>（角色 role:<key>）、gapKind=not_found，note 以「待查證：缺迄日；」開頭並寫查過的來源。"
    "起日查不到：不建該筆，寫同格式 gap（「待查證：缺起日；」）。以名簿下一任起日推得的迄日，evidenceNote 要寫「依名簿下一任起日推得（推論）」。"
    "名單裡 5442 已有的元首／首腦任期不要重建（可寫 gap note「不重建：…」）；1908–1945 以外的元首／首腦任期只寫正文。"
    "regimeId 一律 null，organization 寫中英。conflict 只用於兩份已抓來源互相矛盾。"
)

T14_RULE = (
    "T14（兩層互斥，依序第一條命中就停）：R0 元首／首腦／攝政／代理 → roleCandidates head_of_state|head_of_government（代理加 acting:true）。"
    "R1 所有黨職，以及職稱或引文明寫以某黨身分取得的席位 → roleCandidates de_facto_leader，reason 寫「Tai 2026-11-11 12:12：黨職一律算 de_facto_leader」"
    "（席位另加 originalPositionKind，例 legislator）；不明確是否黨職 → 留 positions 加 partyPostAmbiguous:true 與 partyPostAmbiguousReason。"
    "R2 佔領／殖民轄區最高行政長官且可證明 ≥30 天 → occupation_administrator|colonial_governor。"
    "R3 外交、國防／陸軍／戰爭、財政、內政四部的正職閣員且可證明 ≥90 天 → cabinet_minister。"
    "R4 國家級最高軍職（職位等級要引文明寫），或戰區／方面軍司令且有日期＋地點＋出處的戰役連結 → military_commander。"
    "R5 其他（副職、次官、非四部閣員、議員、地方長官、軍校、警察、時間窗外）→ positions，t14Rule:\"R5\"、t14Reason。"
    "R6 類別符合 R2–R4 但門檻證明不了（端點缺、精度不夠、來源不足 1A 或 2 獨立 B、缺戰役連結、等級沒明寫）→ positions，"
    "t14Rule:\"R6\"、roleEligible:true、roleEligibleKind、roleGap（dates|source|regime|battle_link|rank）、t14Reason。"
    "閣員／將領／佔領殖民長官留在 positions 時加 t14Overlap（cabinet|general|occupation_colonial）。roleCandidates 要有 reason 與 t14Rule（R0–R4）。"
    "時間窗＝與 1908–1945 有交集。positionKind 只能是 minister、legislator、military_command、diplomat、judicial、other、police、military_education。"
)

DRAFT_SHAPE = (
    '{"thickness":"厚|中|薄",'
    '"sources":{"<sourceKey>":{"grade":"A|B|C","gradeBasis":"為何是此等級","authors":["具名作者"],"title":"…","publisher":"…"}},'
    '"paragraphs":[{"ord":1,"period":{"start":"1875-01-01","end":"1900-01-01"},"periodStartPrecision":"year","periodEndPrecision":"year",'
    '"heading":{"zh-Hant":"…","en":"…"},"body":{"zh-Hant":"…","en":"…"},'
    '"citations":[{"sourceKey":"…","quote":"逐字片段","quoteLang":"de","datePrecision":null,"claimSpan":[1,2]}]}],'
    '"positions":[{"key":"…","regimeId":null,"organization":{"zh-Hant":"…","en":"…"},"title":{"orig":"…","zh-Hant":"…","en":"…"},'
    '"positionKind":"minister","period":{"start":"…","end":"…"},"startPrecision":"day","endPrecision":"day",'
    '"t14Overlap":"cabinet","t14Rule":"R5","t14Reason":"…","citations":[]}],'
    '"roleCandidates":[{"key":"…","role_kind":"cabinet_minister","t14Rule":"R3","reason":"…","organization":{},"title":{},'
    '"period":{},"startPrecision":"day","endPrecision":"day","citations":[]}],'
    '"gaps":[{"target":"position:<key>|role:<key>|paragraph:length|identity","gapKind":"not_found|conflict|identity_uncertain","note":"…","candidateCitations":[]}],'
    '"searchLog":[]}'
)


def rules(repo):
    return (
        f"工作目錄：{repo}。只寫任務指定的檔。"
        "不要 git add／commit／push，不要寫任何資料庫，不要呼叫 5052 API，"
        "不要繞過 Cloudflare／Anubis／403，不要用 Wayback 代替被擋的頁。"
        "不要 Read、cat、head 整份 raw 原文，不要把整頁貼進上下文。"
        "已在 raw 目錄（快取於 ~/wl-source-cache/b3full-v3）的 sourceKey 不要重抓。"
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


def draft_path(batch, person):
    return f"{batch['outDir']}/people/{person['bioId']}.draft.json"


def snippets_path(batch, person):
    return f"{batch['outDir']}/people/{person['bioId']}.snippets.md"


def spec_ref(batch):
    return batch.get("specPath") or "<SPEC>"


def agent_id(kind, batch, person):
    return f"{kind}:{batch['nn']}:{person['bioId']}"


def fetch_cmd(batch, sub="fetch"):
    base = f"python3 -I tools/b3v3/fetch_source.py {sub} --rawdir {batch['rawDir']} --rawmap {batch['outDir']}/rawmap.json"
    if sub == "fetch":
        return base + " --source-key <新key> --url <url> --keywords '<姓名|年份>'"
    return base + " --source-key <key> --keywords '<原文片段>'"


def done_line(batch, person, stage):
    return (
        "做完後寫 "
        f"{done_path(batch, person)} ，內容是 "
        f'{{"stage":"{stage}","bioId":"{person["bioId"]}","ok":true}}。'
        "不要寫別的批次。"
    )


def research_prompt(batch, person, repo):
    aid = agent_id("research", batch, person)
    check = f"python3 -I tools/b3v3/person_draft.py check --spec {spec_ref(batch)} --id {aid}"
    return "\n".join([
        "你只研究一個人，寫一份草稿 JSON。不要研究其他人。",
        f"人物：{person['line']}",
        f"bioId：{person['bioId']}",
        f"預查段落：{snippets_path(batch, person)}。內容附在本訊息最後；沒附才 Read 這個檔一次。",
        f"只寫這個檔：{draft_path(batch, person)}（用 Write；之後用 Edit 修）。"
        "不要讀 research.json、規則檔、其他批或 raw 全文。單人檔與 rawMap 由 Python 組。",
        "步驟（工具呼叫合計最多 10 次）：",
        "1. 依預查段落寫草稿。",
        f"2. 跑 {check}",
        "3. 有錯就 Edit 草稿再 check，最多 2 次。",
        f"4. 最後跑 {check} --done（還有錯也要跑，審查會接手）。",
        "預查段落裡沒有任何 A／B 來源談到此人、或不夠寫最低篇幅（3 段／300 字）時，必須先補查再寫草稿，"
        "不能直接標篇幅不足；夠寫就不要補查。補查上限："
        "WebSearch 最多 2 次、fetch 最多 3 頁，每次都寫進 draft.searchLog"
        "（{\"sourceType\":\"…\",\"query\":\"…\",\"url\":\"…或null\",\"result\":\"found_A|found_B|unrated|not_relevant|blocked_403|challenge_page|no_result\",\"note\":\"…\"}）：",
        fetch_cmd(batch),
        "抓到的新來源在 draft.sources.<key> 寫 url、title、authors、publisher、grade、gradeBasis。"
        "403／挑戰頁就放棄、記 searchLog。查原文片段：" + fetch_cmd(batch, "lookup"),
        "草稿格式（accessedOn、grade、policyVersion、locator、rawMap、頂層欄位與預查 searchLog 由 Python 補；"
        "sources 只寫要改的欄位，至少確認 grade 與 gradeBasis）：",
        DRAFT_SHAPE,
        SOURCE_RULE,
        QUOTE_RULE,
        WRITE_RULE,
        TERM_RULE,
        T14_RULE,
        "回覆一行：段數／字數／來源數／未解問題（60 字內）。",
        rules(repo),
    ])


def retry_prompt(batch, person, repo):
    fields = person.get("missingFields") or []
    listed = "\n".join(f"- {field['field']}：{field['detail']}" for field in fields) or "- （沒有列出欄位就不要改）"
    aid = agent_id("retry", batch, person)
    patch = f"python3 -I tools/b3v3/person_patch.py <get|set|del|append> --file {person_path(batch, person)} --path <路徑> [--json '<JSON>']"
    return "\n".join([
        "只補這個人缺的欄位。不要重做整份研究，不要改本批其他人，不要為了湊字數加段。",
        f"人物：{person['line']}",
        f"bioId：{person['bioId']}",
        "這次只補這些欄位：",
        listed,
        "缺起日或缺迄日：只找這個日期。找到就填上並附帶日期的引文；找不到就保留或寫上"
        "「待查證：缺起日」或「待查證：缺迄日」gap。",
        "缺引文或引文空白：只補該筆 quote，quote 必須來自 lookup。",
        DATE_RULE,
        "不要追求 15 次查詢或 6 個新頁：WebSearch 最多 1 次、新頁最多 2 頁。searchLog 只記這次實際查的步驟，標 \"round\": \"field-retry\"。",
        f"讀改單人檔只用局部指令（路徑例：person.positions[0].period.end）：{patch}",
        f"查原文：{fetch_cmd(batch, 'lookup')}",
        f"抓新頁：{fetch_cmd(batch)}（已有的 sourceKey 不要重抓；建議關鍵字：{keyword_hint(person)}）",
        RAWMAP_RULE,
        QUOTE_RULE,
        f"最後跑 python3 -I tools/b3v3/person_draft.py check --spec {spec_ref(batch)} --id {aid} --done（它會寫 agent-done）。",
        "工具呼叫合計最多 8 次。",
        rules(repo),
    ])


def review_prompt(batch, person, repo, escalate=False):
    kind = "escalate" if escalate else "review"
    aid = agent_id(kind, batch, person)
    patch = f"python3 -I tools/b3v3/person_patch.py <get|set|del|append> --file {person_path(batch, person)} --path <路徑> [--json '<JSON>']"
    lines = [
        "你是審查者，只審一個人。",
        f"人物：{person.get('line') or person.get('name')}",
        f"bioId：{person['bioId']}",
        "上次審查被中斷，請重查這個人。" if batch.get("recheck") else f"審查 batch{batch['nn']} 的這個人。",
    ]
    if escalate:
        lines.append("前一輪 Sonnet 審查後 verify 仍有錯（見 verifyErrors）。只修這些錯，其他維持。")
    if person.get("shortfallFlag"):
        lines.append("這個人標記為篇幅不足。不要為了湊字數重寫或加段。審查既有內容，verdict 寫「篇幅不足」。")
    lines.extend([
        f"證據切片：{evidence_path(batch, person)}。內容附在本訊息最後；沒附才 Read 這個檔一次。"
        "不要讀單人檔全文、research.json、evidence-pack.json、raw 或規則檔。",
        "證據切片的 claims 以段、職位、候選角色、gap 為單位（where 如「段1」「職位 <key>」）："
        "每個單位的 text 只寫一次，citations 逐筆含 index、quote、sourceKey、grade、verify"
        "（ok、normOffset 或 reason）。同檔還有 checkMin、verifyErrors，以及 paths（每個單位在單人檔裡的路徑）。",
        "審查重點：1. verifyErrors 與 verify.ok=false 的引文：改成原文裡逐字的短片段（用 lookup 找），找不到就刪掉那筆引文和它支撐的子句。"
        "2. 每個事實子句都要對得到該單位的 quote，對不到就刪子句。3. 段落／職位／角色只收 A／B。"
        "4. T14 歸類與必填欄位（t14Rule／t14Reason、R6 的 roleEligible／roleGap、黨職在 roleCandidates）。"
        "不要新增來源沒寫的事實。searchLog 前段是 Python 預查（索引、權威檔、候選頁），不要因查詢次數退件。",
        DATE_RULE,
        f"看或改一小塊：{patch}",
        f"查原文：{fetch_cmd(batch, 'lookup')}（已有的 sourceKey 不要重抓）",
        f"結束（一定要跑，沒有要改也直接跑）：python3 -I tools/b3v3/person_draft.py review-done --spec {spec_ref(batch)} --id {aid} "
        "--verdict <pass|pass_with_changes|returned|篇幅不足> --note '<60 字內；改了起迄日要寫理由>' --changes '[\"改了什麼\"]'",
        "它會寫 review 記錄與 agent-done，並印出改完後的 verify 錯誤數。不要寫整份 review.json（驅動程式會合併）。",
        "工具呼叫合計最多 5 次。",
        rules(repo),
    ])
    return "\n".join(lines)


def _rel(repo, path):
    path = str(path)
    repo = str(repo).rstrip("/")
    if path.startswith(repo + "/"):
        return path[len(repo) + 1:]
    return "/" + path if not path.startswith("/") else "/" + path


def launch_profile(agent, repo):
    """每種 agent 的固定啟動設定：模型、輪數上限、工具、允許的指令（dontAsk：清單外一律拒絕）。"""
    kind = agent["kind"]
    people = _rel(repo, f"{agent['outDir']}/people")
    bio = agent["bioId"]
    fetch_all = "Bash(python3 -I tools/b3v3/fetch_source.py:*)"
    lookup = "Bash(python3 -I tools/b3v3/fetch_source.py lookup:*)"
    patch = "Bash(python3 -I tools/b3v3/person_patch.py:*)"
    if kind == "research":
        draft = f"{people}/{bio}.draft.json"
        return {
            "model": agent.get("model") or "sonnet",
            "maxTurns": 11,
            "tools": "Bash,Read,Write,Edit,WebSearch",
            "allowed": [
                "Bash(python3 -I tools/b3v3/person_draft.py check:*)", fetch_all,
                f"Write({draft})", f"Edit({draft})", f"Read({people}/{bio}.*)", "WebSearch",
            ],
            "timeoutSeconds": 25 * 60,
        }
    if kind == "retry":
        return {
            "model": agent.get("model") or "sonnet",
            "maxTurns": 9,
            "tools": "Bash,Read,WebSearch",
            "allowed": [
                "Bash(python3 -I tools/b3v3/person_draft.py check:*)", fetch_all, patch,
                f"Read({people}/{bio}.evidence.json)", "WebSearch",
            ],
            "timeoutSeconds": 15 * 60,
        }
    if kind in ("review", "escalate"):
        return {
            "model": agent.get("model") or ("opus" if kind == "escalate" else "sonnet"),
            "maxTurns": 6,
            "tools": "Bash,Read",
            "allowed": [
                "Bash(python3 -I tools/b3v3/person_draft.py review-done:*)", lookup, patch,
                f"Read({people}/{bio}.evidence.json)",
            ],
            "timeoutSeconds": 12 * 60,
        }
    if kind == "deep" and agent.get("browserOnly"):     # 瀏覽器補抓 pilot：只擷取，不搜尋、不抓新頁
        own = f"{people}/{bio}.stage2.json"
        return {
            "model": "sonnet", "maxTurns": 10, "tools": "Bash,Read,Write,Edit",
            "allowed": ["Bash(python3 -I tools/b3v3/tiers.py check:*)", lookup,
                        f"Write({own})", f"Edit({own})", f"Read({people}/{bio}.*)"],
            "timeoutSeconds": 15 * 60,
        }
    if kind == "deep":
        own = f"{people}/{bio}.stage2.json"
        return {
            "model": "sonnet",
            "maxTurns": 20,   # 2026-11-19：harvest＋fetch 多 2–4 次工具呼叫
            "tools": "Bash,Read,Write,Edit,WebSearch",
            "allowed": [
                "Bash(python3 -I tools/b3v3/tiers.py check:*)", "Bash(python3 -I tools/b3v3/tiers.py harvest:*)", fetch_all,
                f"Write({own})", f"Edit({own})", f"Read({people}/{bio}.*)", "WebSearch",
            ],
            "timeoutSeconds": 25 * 60,
        }
    if kind == "csupp":
        own = f"{people}/{bio}.supplementC.json"
        return {
            "model": "sonnet",
            "maxTurns": 8,
            "tools": "Bash,Read,Write,Edit",
            "allowed": [
                "Bash(python3 -I tools/b3v3/tiers.py check:*)", lookup,
                f"Write({own})", f"Edit({own})", f"Read({people}/{bio}.*)",
            ],
            "timeoutSeconds": 12 * 60,
        }
    if kind == "citefix":
        return {
            "model": "sonnet",
            "maxTurns": 3,
            "tools": "Bash",
            "allowed": ["Bash(python3 -I tools/b3v3/uncited.py map:*)", lookup],
            "timeoutSeconds": 8 * 60,
        }
    if kind == "discover":
        return {
            "model": agent.get("model") or "haiku",
            "maxTurns": 4,
            "tools": "WebSearch",
            "allowed": ["WebSearch"],
            "timeoutSeconds": 6 * 60,
        }
    raise ValueError(f"未知 agent 種類 {kind}")


def discover_prompt(agent):
    return "\n".join([
        "只找網址，不要寫檔。人物：" + (agent.get("line") or agent.get("name") or ""),
        "用 WebSearch 最多 3 次，找這個人的合格生平來源頁：國家級傳記辭典、政府／議會／國家圖書館官方頁、人名權威檔、"
        "具名作者的機構百科或學術傳記。原文語言姓名至少查 1 次。",
        "不要 Wikipedia、Wikidata、百度、任何 wiki、部落格、論壇、私人彙編（rulers.org、archontology 等）。",
        "最後只回一行 JSON：{\"urls\":[\"https://…\"]}，最多 6 個，最可能有生平與任期日期的排前面。",
    ])


# ---- 分層補查（tools/b3v3/tiers.py；Tai 2026-11-18）----
# 第二階段：更大的 A／B 補查（原文姓名、日本人試 JACAR／NDL／コトバンク／首相官邸，WebSearch 3–5 次）。
# 第三階段：第二階段仍不足才用 C（Wikipedia 等），只寫進 person.supplementC，只補最低篇幅與起迄日（日期一律待查證）。
# 審查後：Python 找主段落沒有出處的句子；有才給 Sonnet 1–2 輪補 claimSpan 或刪句。

STAGE2_SHAPE = (
    '{"sources":{"<新key>":{"url":"…","title":"…","authors":["…"],"publisher":"…","grade":"A|B","gradeBasis":"…"}},'
    '"paragraphsAppend":[{"ord":5,"period":{},"periodStartPrecision":null,"periodEndPrecision":null,"heading":{"zh-Hant":"…","en":"…"},'
    '"body":{"zh-Hant":"…","en":"…"},"citations":[{"sourceKey":"…","quote":"…","quoteLang":"ja","datePrecision":null,"claimSpan":[1]}]}],'
    '"paragraphsReplace":{"<ord>":{…整段…}},'
    '"positionsUpdate":{"<key>":{"period":{"start":"…","end":"…"},"startPrecision":"day","endPrecision":"day","addCitations":[{…}]}},'
    '"positionsAdd":[{…}],"roleCandidatesUpdate":{},"roleCandidatesAdd":[],'
    '"gapsRemove":["position:<key>"],"gapsAdd":[{…}],"searchLog":[{…}]}'
)

CSUPP_SHAPE = (
    '{"clauses":[{"target":"paragraph:length","text":{"zh-Hant":"…","en":"…"},"cKey":"<C來源key>","quote":"逐字片段"}],'
    '"dates":[{"target":"position:<key>.end","value":"1931-12-13","precision":"day","cKey":"…","quote":"含日期的逐字片段"}]}'
)


def tier_check_cmd(agent):
    return f"python3 -I tools/b3v3/tiers.py check --spec {agent['specPath']} --id {agent['id']}"


def stage2_prompt(agent, ctx, repo):
    batch = {"rawDir": agent["rawDir"], "outDir": agent["outDir"]}
    natives = "、".join(f"{k}={v}" for k, v in (ctx.get("nativeNames") or {}).items()) or "（索引沒有）"
    lines = [
        "第二階段補查（只收 A／B）：只補這個人缺的篇幅與起迄日。不要重寫已有、已有出處的內容。",
        f"人物：{agent.get('line') or agent.get('name')}",
        f"bioId：{agent['bioId']}",
        f"原文姓名（索引，只用來搜尋；只用本人語言＋英文搜）：{natives}",
        "現況（主內容，段落句子已編號）：",
        ctx["state"],
        f"要補：{ctx['needs']}",
        f"預查（原文姓名比對過的段落）：{agent['outDir']}/people/{agent['bioId']}.deep.md，內容附在最後；沒附才 Read 一次。",
        "步驟：1. 先用附的預查段落。2. 不夠就 WebSearch（3–5 次，至少 2 次用原文姓名）並 fetch 新頁（最多 5 頁）。",
    ]
    if ctx.get("japanese"):
        lines.append("日本人：依序試 JACAR（jacar.go.jp／jacar.archives.go.jp，搜「原文姓名 任免」）、NDL（ndl.go.jp、dl.ndl.go.jp、"
                     "近代日本人の肖像）、コトバンク（只用具名執筆者的辭典條目，記 B）、首相官邸歴代内閣頁（A）。")
    if ".end" in ctx.get("needs", ""):
        lines.append(
            "缺迄日的找法（依序，算在 WebSearch 次數內）：a. 後任：預查最後的「索引提示」有後任名字時，搜「後任姓名＋職稱＋就任／任命」"
            "（原文，例：「鈴木喜三郎 政友会総裁 就任」「successor appointed Minister of War 1917」），A／B 來源寫出後任就任日，"
            "前任的迄日就填那天，evidenceNote 寫「推論：下一任 <姓名> 於 <日期> 就任」，endPrecision 照引文。"
            "b. 官方名單：政府、議會、內閣的歷任名單頁（例：首相官邸歴代内閣、議會議員名簿、官報任免欄），抓一頁、lookup 找這個人。"
            "c. 死亡在任：A／B 寫明在任中去世時，迄日填死亡日，evidenceNote 寫「推論：在任中去世」。"
            "Wikidata 的日期只是線索，不能當出處；quote 要含你填的那個年份。")
        lines.append(
            f"缺迄日：搜完一定跑 python3 -I tools/b3v3/tiers.py harvest --spec {agent['specPath']} --id {agent['id']}"
            "（從你的搜尋結果挑 A／B 網域、自動抓前 3 頁，只回姓名＋年份片段與 sourceKey）。quote 從片段或 lookup 逐字複製，"
            "來源照它的 url 寫進 sources、等級看頁面確認。結束前至少 2 個非 wiki 候選網址已抓或寫明略過原因"
            "（harvest 自動記；不夠就自己 fetch，searchLog 每筆加 url 與 result＝fetched／skipped:原因）。")
    lines += [
        f"抓新頁：{fetch_cmd(batch)}",
        f"查原文：{fetch_cmd(batch, 'lookup')}",
        f"只寫這個檔：{agent['outDir']}/people/{agent['bioId']}.stage2.json（Write；之後 Edit）。Python 會把它套到單人檔上。格式：",
        STAGE2_SHAPE,
        "新段落 ord 接在現有最大 ord 之後；新來源要先 fetch 成功。迄日找到就 positionsUpdate 填上並 addCitations（quote 含日期），"
        "同時 gapsRemove 那個 target。找不到就不要動，維持「待查證：缺迄日」。",
        SOURCE_RULE,
        QUOTE_RULE,
        WRITE_RULE,
        TERM_RULE,
        DATE_RULE,
        f"檢查：{tier_check_cmd(agent)}（有錯就 Edit 再跑，最多 2 次）。最後一定跑 {tier_check_cmd(agent)} --done。",
        "工具呼叫合計最多 18 次。回覆一行：補了什麼／還缺什麼（60 字內）。",
        rules(repo),
    ]
    return "\n".join(lines)


def csupp_prompt(agent, ctx, repo):
    batch = {"rawDir": agent["rawDir"], "outDir": agent["outDir"]}
    lines = [
        "第三階段：A／B 已查過仍不足。只用 C 級來源（下面附的 Wikipedia 段落）寫「C 級補充」，不碰主內容。",
        f"人物：{agent.get('line') or agent.get('name')}",
        f"bioId：{agent['bioId']}",
        f"要補：{ctx['needs']}",
        "主內容（只供對照，不要改、不要重複寫已有的事）：",
        ctx["state"],
        f"C 段落：{agent['outDir']}/people/{agent['bioId']}.c.md，內容附在最後；沒附才 Read 一次。來源 key 用 [c-…] 標的那個。",
        f"只寫這個檔：{agent['outDir']}/people/{agent['bioId']}.supplementC.json（Write；之後 Edit）。格式：",
        CSUPP_SHAPE,
        "clauses：target=paragraph:length，每條一兩句 zh-Hant（en 對應），合計讓主內容＋C 達到約 300 字即可，不要多寫；"
        "每條都要一筆逐字 quote（NFC ≤80 字，從 C 段落或 lookup 複製）。",
        "dates：只補主內容缺的起迄日，target 寫 position:<key>.start|end 或 role:<key>.start|end；value 寫 YYYY-MM-DD"
        "（月／年精度用該單位第一天），quote 要含那個日期。C 單獨不能確認日期，Python 會標 待查證。",
        "A／B 為準：C 和主內容的日期、任期、年份衝突時不要寫（同名職位的另一任期、迄日早於起日都算），Python 會自動移到衝突註記。",
        "每句 zh／en 裡的年份、月日、數字、外文專名、「」裡的詞都必須出現在那條的 quote；quote 沒有的不要寫，Python 會刪掉沒支撐的句子。",
        f"查原文：{fetch_cmd(batch, 'lookup')}",
        f"檢查：{tier_check_cmd(agent)}；最後跑 {tier_check_cmd(agent)} --done。",
        "工具呼叫合計最多 7 次。不要 WebSearch，不要抓新頁。回覆一行（40 字內）。",
        rules(repo),
    ]
    return "\n".join(lines)


def citefix_prompt(agent, ctx, repo):
    batch = {"rawDir": agent["rawDir"], "outDir": agent["outDir"]}
    person_file = f"{agent['outDir']}/people/{agent['bioId']}.json"
    return "\n".join([
        "審查後的 Python 檢查找到主段落裡沒有出處的句子。只處理這些句子，不改別的。",
        f"bioId：{agent['bioId']}",
        "沒有出處的句子與該段現有引文（c<索引>）：",
        ctx["state"],
        "對每一句：該段某筆引文確實支撐它 → 把句號加進那筆的 claimSpan；沒有任何引文支撐 → 放進 drop。不要新增來源或事實。",
        f"一次寫完：python3 -I tools/b3v3/uncited.py map --file {person_file} --json "
        "'{\"<段ord>\":{\"<引文索引>\":[句號,…]},\"drop\":{\"<段ord>\":[句號,…]}}'",
        f"不確定引文內容時可查原文一次：{fetch_cmd(batch, 'lookup')}",
        "工具呼叫最多 2 次。回覆一行（30 字內）。",
        rules(repo),
    ])
