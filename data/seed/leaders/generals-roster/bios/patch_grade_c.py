#!/usr/bin/env python3
"""將領生平提示：英語國家官方來源（NARA／英國國家檔案館／各軍種官方戰史＝A；ODNB／ANB 公開內容＝B）與具名 C 級（可重跑）。

依據：
- World Line 主管 2026-11-12 06:32：英語國家 14 人也補跑；白名單加 NARA、英國國家檔案館、各軍種官方戰史（A），ODNB、ANB（B）。
- Tai 本人 2026-11-12 06:34（主管轉達）：「將領生平來源放寬到具名 C 級」。
改：PROMPT_research.md（插入一節＋改 Q9 句）、PROMPT_retry.md（出處等級句）、PROMPT_insuff_rerun.md（整份重寫）。
主迴圈每批重新讀取 PROMPT_*.md。不改 schema、不寫庫。verify.py 已同步接受將領檔的具名 C（gradePolicy）。
用法：python3 -I data/seed/leaders/generals-roster/bios/patch_grade_c.py
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
M0 = "<!-- GRADE_C_EN_2026-11-12 -->"
M1 = "<!-- /GRADE_C_EN_2026-11-12 -->"
ANCHOR = "依序嘗試，查到 A／B 就可停止往下（厚人物 2–4 個來源即可，不要逐頁瀏覽）："

SECTION = """## 英語國家官方來源與具名 C 級（主管 2026-11-12 06:32；Tai 本人 2026-11-12 06:34「將領生平來源放寬到具名 C 級」）
**本節優先於本檔其他「出處只能 A 或 B」「C／X 不收」「至少 1 個 A」的文字（只限將領生平）。**

**英語國家將領（美、英、加、澳、紐、南非、愛爾蘭）必查（可抓原文才可當出處）**
- **A**：美國國家檔案館 NARA（`www.archives.gov`、`catalog.archives.gov`，含各總統圖書館 NARA 頁）；英國國家檔案館（`www.nationalarchives.gov.uk`、`discovery.nationalarchives.gov.uk`）；各軍種官方戰史：美國陸軍軍史中心（`history.army.mil`）、美國海軍歷史與遺產司令部 NHHC（`www.history.navy.mil`）、美國空軍歷史研究署（`www.afhra.af.mil`）、美國陸戰隊大學史料處（`www.usmcu.edu`）、英國皇家空軍官方歷史頁（`www.raf.mod.uk`）；The London Gazette（`www.thegazette.co.uk`，任命公告）。
- **B**：Oxford Dictionary of National Biography（`www.oxforddnb.com`；現轉址 `academic.oup.com/oxford-dictionary-of-national-biography`）、American National Biography（`www.anb.org`；現轉址 `academic.oup.com/american-national-biography`）。兩站是訂閱制：**只用未登入即公開可見的內容（摘要／首段／條目標頭）**，不登入、不繞付費牆、不用他人帳號或代理；引文只能取自已抓到的公開文字。National Army Museum（`www.nam.ac.uk`，具名機構）可列 B。
- 403／逾時照實寫進 searchLog，不繞過（不 `curl -k`、不換 UA 冒充、不用快取鏡像規避防機器人頁）。

**具名 C 級（新）**
- **C＝有具名作者或具名出版機構的正當來源**：報紙與通訊社、大學（含系所／研究中心頁）、博物館與紀念館、具名作者或具名出版者的軍事史網站、一般出版社書籍等。C 依**每一頁**判斷（看該頁是否具名作者或具名出版機構），不靠網域白名單。`sources.gradeBasis` 必須寫出該頁的具名作者或具名出版機構，`authors` 或 `publisher` 至少一項非空。
- **一律不收（不論 A／B／C）**：Wikipedia 及任何維基類（含 Wikiwand、Fandom）、Wikidata、百度；無署名內容；AI 生成內容站；論壇、討論區、問答站（Reddit、Quora、知乎、PTT、軸心國歷史論壇等）；部落格（Blogspot、WordPress.com、Medium、Substack 等）；個人網站（除非由具名機構發布）。
- **每一筆 citation 都要寫 `grade`（A／B／C）**，且須與 `sources[sourceKey].grade` 一致。
- research.json 頂層加 `"gradePolicy": "ABC-2026-11-12"`（verify.py 依此接受 C）。
- **最低標準可以只靠 C 級來源達成**（≥3 段、≥300 字、每個職位有起迄日、有指揮職與主要戰役）。**不可因為缺 A／B 就標「來源不足」**；只有在 A／B／C 都查不到足夠內容時才標「來源不足：」。
- 仍優先 A，其次 B，再用 C 補足任期、戰役、指揮職；同一事實有 A／B 時不要只引 C。
- T14 角色門檻（R2–R4 的「1 筆 A 或 2 筆獨立 B」）不變：只有 C 支持的職位照寫 positions，必要時標 R6（roleGap=source），不升為 roleCandidates。
"""
BLOCK = f"{M0}\n{SECTION}{M1}\n"

OLD_Q9 = "出處 grade 只能 A 或 B（A＝國家級傳記辭典、政府／議會／國家圖書館官方頁、人名權威檔；B＝具名作者的機構百科、學術機構傳記、學術出版社專書或期刊論文等；C／X 不收）。"
NEW_Q9 = "出處 grade 只能 A、B 或具名 C（A＝國家級傳記辭典、政府／議會／國家圖書館官方頁、人名權威檔、官方戰史；B＝具名作者的機構百科、學術機構傳記、學術出版社專書或期刊論文等；C＝具名作者或具名出版機構的報紙、大學、博物館、軍事史網站等，見「英語國家官方來源與具名 C 級」節；X 與維基／無署名／AI／論壇／部落格不收）。"

OLD_RETRY = "可抓原文才可當出處（grade A／B）。維基只當索引，不是出處。"
NEW_RETRY = ("可抓原文才可當出處（grade A／B，或具名 C：有具名作者或具名出版機構的報紙、大學、博物館、軍事史網站；每筆 citation 寫 grade，頂層加 \"gradePolicy\": \"ABC-2026-11-12\"）。"
             "英語國家將領必查 NARA（archives.gov）、英國國家檔案館（nationalarchives.gov.uk）、各軍種官方戰史（history.army.mil、history.navy.mil、afhra.af.mil、usmcu.edu）＝A，ODNB／ANB 只用公開摘要＝B（不登入、不繞付費牆）。"
             "可只靠 C 達標，不可因缺 A／B 標來源不足（Tai 本人 2026-11-12 06:34；完整規則見 PROMPT_research.md「英語國家官方來源與具名 C 級」）。維基、無署名、AI 生成、論壇、部落格一律不收；維基只當索引，不是出處。")

RERUN = """# 將領生平：來源不足／未達標補跑（新規則，Sonnet，新 session，勿 --resume）

授權：World Line 主管 2026-11-12 03:03（日本／非英語來源）、06:32（英語國家也補跑；NARA／英國國家檔案館／官方戰史＝A，ODNB／ANB 公開內容＝B）；Tai 本人 2026-11-12 06:34（主管轉達）「將領生平來源放寬到具名 C 級」。每人只補跑這一次。不寫庫、不 push、不 commit。分支 feature/person-cards（不要切換分支）。

`{{OUTDIR}}/research.json` 已存在。本批只改下列人物（{{TIER}} 級 batch{{NN}}）：
{{PEOPLE}}

若某人在 research.json 裡**沒有條目**（名單上標「目前 None 段」者；例：S/batch004 的 heinzguderian，該批主 session 漏寫，只留下 sources），請依 PROMPT_research.md 為他**新增完整條目**（key 用名單上的 key），可沿用頂層 sources 裡已有的他的來源。

## 規則
- 完整規則見 `data/seed/leaders/generals-roster/bios/PROMPT_research.md`（以本批 {{NN}}、{{TIER}}、{{RAWDIR}}、{{OUTDIR}} 代入）以及它所引用的 B3 v3／T14／verify 規則，全部照舊適用；先讀它、現有 research.json 與 searchLog，尤其是「日本及其他非英語國家將領：補充搜尋範圍」與「英語國家官方來源與具名 C 級」兩節（後者優先於舊的「只收 A／B」文字）。
- **只改上列人物**在 research.json 的條目（paragraphs／positions／roleCandidates／gaps／searchLog／sources 新增）；其他人一律不動。raw 存到 `{{RAWDIR}}`。頂層加（或保留）`"gradePolicy": "ABC-2026-11-12"`。
- **本輪最低搜尋量（每人新增）**：至少 5 種來源類型、至少 15 次查詢（原文語言至少 4 次）、至少實際 curl 抓取 6 個新候選頁；searchLog 新增筆標 `"round": "insuff-rerun"`。
- **日本將領必查**：Web NDL Authorities（id.ndl.go.jp，A）、JACAR（jacar.go.jp、jacar.archives.go.jp，A）、防衛研究所（nids.mod.go.jp，A）、Kotobank『日本大百科全書』／『国史大辞典』／『世界大百科事典』具名條目（kotobank.jp，B）。
- **英語國家將領必查**：NARA（www.archives.gov、catalog.archives.gov，A）、英國國家檔案館（www.nationalarchives.gov.uk、discovery.nationalarchives.gov.uk，A）、各軍種官方戰史（history.army.mil、www.history.navy.mil、www.afhra.af.mil、www.usmcu.edu、www.raf.mod.uk，A）、London Gazette（A）；ODNB（oxforddnb.com）／ANB（anb.org）只用未登入可見的摘要或首段（B），不登入、不繞付費牆。
- **其他非英語國家**：該國國家圖書館權威檔或官方戰史（A）與具名機構百科（B），見 PROMPT_research.md；不要只查英語來源。
- **具名 C 級**：有具名作者或具名出版機構的報紙、大學、博物館、軍事史網站等（每頁判斷，gradeBasis 寫出具名者）。**可只靠 C 達標；不可因缺 A／B 就標來源不足。** 維基（含任何維基類）、Wikidata、百度、無署名、AI 生成、論壇、部落格、個人網站一律不收；維基只當索引。每筆 citation 都寫 grade（A／B／C），與 sources 一致。
- 最低標準不變：中文 ≥3 段、合計 ≥300 字；每個職位／角色都要有起迄日（缺迄日也算未達標，要盡量補齊）；須有指揮職與主要戰役。不可用無出處內容湊字數；每個事實子句都要有 citation。引文 NFC 正規化後不超過 80 字元，逐字出現在已抓原文。
- 補完後若已達標：移除或改寫先前「來源不足：」「篇幅不足：」gap（已補上的項目），並將 `sourceInsufficient` 設為 false（或刪除該欄）。
- 補完後仍未達標 → 更新 gap：target=`paragraph:length`、gapKind=not_found、note 以「來源不足：」開頭，寫目前段數／字數、缺的任期／戰役／指揮職，以及本輪已查的新網域（A／B／C）與結果。**不要硬湊。** 缺任期者照「待查證：缺迄日／缺起日」規則寫 gap。
- 不用 `curl -k`／`--insecure`；不登入；遇防機器人驗證不繞過。
- **預算**：本 session 上限 USD 6（到上限 session 會被中止、整批作廢）。本批最多 5 人，每人控制在約 USD 1 以內：先查最可能補上缺口的來源（缺迄日先查官方任免／公報，缺戰役先查官方戰史），補到達標就停，不要逐頁瀏覽。
- 完成後跑 `python3 -I data/seed/leaders/b3-trial/verify.py {{OUTDIR}}/research.json --report {{OUTDIR}}/verify-report.json`，須 exit 0。
- 結尾回覆：每人是否達標、新增段落／字數／任期、新增 searchLog 筆數、用到的新網域與等級（A／B／C）；最後單獨一行 `BATCH_RESULT=ok` 或 `BATCH_RESULT=fail`。不要 commit。
"""


def main() -> None:
    r = HERE / "PROMPT_research.md"
    t = r.read_text(encoding="utf-8")
    if M0 in t and M1 in t:
        pre, rest = t.split(M0, 1)
        _, post = rest.split(M1, 1)
        t = pre + BLOCK + (post[1:] if post.startswith("\n") else post)
    else:
        if ANCHOR not in t:
            raise SystemExit("PROMPT_research.md: anchor not found")
        t = t.replace(ANCHOR, BLOCK + "\n" + ANCHOR, 1)
    if OLD_Q9 in t:
        t = t.replace(OLD_Q9, NEW_Q9)
    elif NEW_Q9 not in t:
        raise SystemExit("PROMPT_research.md: Q9 sentence not found")
    r.write_text(t, encoding="utf-8")
    print("PROMPT_research.md: grade-C/English section upserted, Q9 updated")

    rt = HERE / "PROMPT_retry.md"
    tt = rt.read_text(encoding="utf-8")
    if OLD_RETRY in tt:
        tt = tt.replace(OLD_RETRY, NEW_RETRY)
        rt.write_text(tt, encoding="utf-8")
        print("PROMPT_retry.md: grade C / English sources added")
    elif NEW_RETRY in tt:
        print("PROMPT_retry.md: already patched")
    else:
        raise SystemExit("PROMPT_retry.md: expected sentence not found")

    (HERE / "PROMPT_insuff_rerun.md").write_text(RERUN, encoding="utf-8")
    print("PROMPT_insuff_rerun.md: rewritten")
    for f in ("PROMPT_research.md", "PROMPT_retry.md", "PROMPT_insuff_rerun.md"):
        import re
        bad = [m for m in re.findall(r"\{\{[^}]*\}\}", (HERE / f).read_text()) if m not in ("{{NN}}", "{{TIER}}", "{{PEOPLE}}", "{{TODAY}}", "{{RAWDIR}}", "{{OUTDIR}}")]
        if bad:
            raise SystemExit(f"{f}: unknown placeholders {bad}")


if __name__ == "__main__":
    main()
