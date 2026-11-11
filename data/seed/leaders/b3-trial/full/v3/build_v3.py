#!/usr/bin/env python3
"""B3 full v3：最低標準（中文 ≥3 段、合計 ≥300 字、每個職位有任期）＋未達者自動加強重跑一次。

依據：Tai 2026-11-11 22:02 最低標準 3 段／300 字／職位任期、未達者加強重跑一次、仍不足記「篇幅不足」；
Tai 2026-11-11 22:08（皆由 World Line 主管轉達）：已寫入的 98 人不動、不重補；小樣本 1–2 批只從 824 人名單挑（含邱吉爾，厚中薄混合），跑完就停等 Tai 同意。
主要領導人 18 人另套 major-v2 加強規格（主管 2026-11-11 21:55）。
產出（本目錄）：PROMPT_research.md、PROMPT_retry.md、PROMPT_review.md、selection-sample.json（小樣本 2 批×3 人）。
用法：python3 -I data/seed/leaders/b3-trial/full/v3/build_v3.py（重跑結果逐位元相同）
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FULL = HERE.parent
TRIAL = FULL.parent
MAJOR = FULL / "major-v2"
SAMPLE = [  # 小樣本（皆在 selection-full.json 824 人內；厚薄為離線推定）
    # 邱吉爾（主要領導人★，厚）、Éamon de Valera（厚）、Jorge Ubico（中，美洲）
    ("001", ["01a1c86e-c89b-70af-afe0-1ad0f4be2bf8", "01a1b4b0-6fbb-7a56-8a6b-9a671ff693cc", "01a1b4af-e4cc-783b-b657-f81348ad4493"]),
    # Konstantin Päts（中）、Tribhuvan（薄，亞洲）、Heinrich Sahm（薄）
    ("002", ["01a1b4b2-2f2c-7cc8-a233-c26b6d7df1ea", "01a1b4af-e4ae-7ffe-b91b-13f90ca7ea6b", "01a1b4b2-2f1a-722b-93ed-d2ad6e6f6765"]),
]
BATCH_SIZE = 3

MIN_BLOCK = """
## 最低標準（Tai 2026-11-11 22:02；本批每人都適用，優先於下方「1 個 A／B 寫 1 段」「1–6 段」）
1. **篇幅**：每人中文（`body.zh-Hant`）**至少 3 段、合計至少 300 字**（NFC 後去空白的字元數）；英文段落一一對應。
2. **任期**：positions 與 roleCandidates 的每一筆都要有 `period.start` 與 `period.end`，並有 quote 含該日期（或年／月）的 citation。
   - 迄日查不到 → 該筆照寫 start，另加 gap：target=`position:<key>`（角色 `role:<key>`），gapKind=not_found，note 以「待查證：缺迄日；」開頭並寫已查來源。
   - 起日查不到 → 不寫入 positions／roleCandidates，改寫同格式 gap（note 以「待查證：缺起日；」開頭）。
3. **不足時先擴大搜尋**（官方／議會、國家級傳記辭典、權威檔、學術出版），不可用無出處的內容、重複句、空泛評語或常識補述湊字數；每個事實子句仍要對得到 citation（Q2）。
4. **盡力後仍不足**：照實寫，另加一筆 gap：target=`paragraph:length`，gapKind=not_found，note 以「篇幅不足：」開頭，寫目前段數／字數與已查過的來源類型。
5. flags 含 **major★** 者：另套下方「主要領導人加強規格」。
"""

RETRY = """# B3 full v3 batch{{NN}}：加強搜尋重跑（Sonnet，新 session，勿 --resume）

授權：Tai 2026-11-11 22:02（未達最低標準者自動加強搜尋重跑一次；不寫庫、不 push、不 commit）。分支 feature/person-cards（不要切換分支）。

`{{OUTDIR}}/research.json` 已由上一個 session 產出，但下列人物未達最低標準（中文 ≥3 段、合計 ≥300 字、每個職位有起迄日；見 `{{OUTDIR}}/min-check.round1.json`）：
{{PEOPLE}}

## 規則
- 完整規則見 `data/seed/leaders/b3-trial/full/v3/PROMPT_research.md`（以 `{{NN}}`、`{{RAWDIR}}`、`{{OUTDIR}}` 代入），全部照舊適用；先讀它與現有 research.json、searchLog。
- **只改上列人物**在 research.json 的條目（paragraphs／positions／roleCandidates／gaps／searchLog／sources 新增）；其他人一律不動。raw 存到 `{{RAWDIR}}`。
- **加強搜尋量（本 session 每人新增）**：至少 5 種來源類型、至少 15 次查詢（原文語言至少 4 次）、至少實際 curl 抓取 6 個新候選頁；searchLog 新增筆標 `"round": "retry"`。
- **優先改查 A 級來源**：英國人物查 UK Parliament Historic Hansard 人物頁（api.parliament.uk/historic-hansard/people/…）、London Gazette、GOV.UK；其他國家查國家級傳記辭典與議會／政府名錄，例如：Deutsche Biographie（NDB/ADB）、ÖBL、Treccani DBI、RAH DB~e、Nouvelle Biographie Nationale／Biographie nationale（Académie royale de Belgique）、Kansallisbiografia（Finland）、Svenskt biografiskt lexikon、Norsk biografisk leksikon、Dansk Biografisk Leksikon（lex.dk）、Alþingi 議員名錄（althingi.is）、Srpski biografski rečnik（Matica srpska）、Hrvatski biografski leksikon、Polski Słownik Biograficzny、Biografický slovník českých zemí、Magyar életrajzi lexikon／Országgyűlés 名錄、Dicționarul … ／Academia Română、Encyclopedia of Ukraine（CIUS，B）、各國總統府／國會歷任名錄、國家圖書館權威檔。可抓原文才可當出處（grade A／B），否則只能放 candidateCitations。
- 不可用無出處內容湊字數；每個事實子句都要有 citation。
- 補完後仍未達標 → 該人加（或更新）gap：target=`paragraph:length`、gapKind=not_found、note 以「篇幅不足：」開頭，寫目前段數／字數與本輪已查來源類型。缺任期者照「待查證：缺迄日／缺起日」規則寫 gap。
- 完成後跑 `python3 -I data/seed/leaders/b3-trial/verify.py {{OUTDIR}}/research.json --report {{OUTDIR}}/verify-report.json`，須 exit 0。
- 結尾回覆：每人新增段落／字數／任期補到幾筆、新增 searchLog 筆數、用到的新網域；最後單獨一行 `BATCH_RESULT=ok` 或 `BATCH_RESULT=fail`。不要 commit。
"""

REVIEW_ADD = """
6c. **最低標準（Tai 2026-11-11 22:02，本批每人適用；見 `data/seed/leaders/b3-trial/full/v3/PROMPT_research.md` 的「最低標準」）**：逐人核對中文段數 ≥3、合計 ≥300 字、每筆 positions／roleCandidates 有起迄日與含日期引文（缺迄日者須有「待查證：缺迄日」gap）。未達者必須有「篇幅不足：」gap 且 searchLog 顯示確實做過加強搜尋（`round: retry`），否則 verdict=returned。**為湊字數而寫的無出處句、重複句、空泛評語一律刪除並記入 changes**。flags 含 major★ 者另依 6b 檢查。
"""


def main():
    full = {p["bioId"]: p for p in json.loads((FULL / "selection-full.json").read_text(encoding="utf-8"))["people"]}
    majors = {p["bioId"]: p for p in json.loads((MAJOR / "selection-major.json").read_text(encoding="utf-8"))["people"]}
    sample = []
    for nn, bios in SAMPLE:
        for b in bios:
            if b not in full: sys.exit(f"{b} 不在 selection-full.json")
            q = dict(majors.get(b) or full[b])
            q["flags"] = (["major★"] if b in majors else []) + list(full[b].get("flags") or [])
            q["fullBatch"] = full[b]["batch"]; q["batch"] = nn
            sample.append(q)
    out = {"run": "b3-full-v3-sample", "decision": "Tai 2026-11-11 22:02／22:08（主管轉達）最低標準 3 段／300 字／職位任期；小樣本只從 824 人挑；主要領導人另套 major-v2（主管 21:55）",
           "batchSize": BATCH_SIZE, "batches": len(SAMPLE), "people": sample}
    (HERE / "selection-sample.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    # 研究提示：major-v2 研究提示（含主要領導人加強規格）＋最低標準；主要領導人規格只對 major★ 生效
    t = (MAJOR / "PROMPT_research.md").read_text(encoding="utf-8")
    for old, new in (("data/seed/leaders/b3-trial/full/major-v2/batch{{NN}}", "data/seed/leaders/b3-trial/full/v3/batch{{NN}}"),
                     ("/tmp/b3full-major/", "/tmp/b3full-v3/"),
                     ("`data/seed/leaders/b3-trial/full/major-v2/selection-major.json`", "`data/seed/leaders/b3-trial/full/v3/selection-sample.json`"),
                     ("b3-full-major-v2-batch{{NN}}", "b3-full-v3-batch{{NN}}"), ("# B3 full 主要領導人 v2 batch{{NN}}：研究", "# B3 full v3 batch{{NN}}：研究"),
                     ("只適用本批，優先於下方同名規則）\n本批每人都是 1908–1945 主要領導人（Tai 2026-11-11 21:25）",
                      "只適用 flags 含 major★ 者，優先於下方同名規則）\nmajor★ 者是 1908–1945 主要領導人（Tai 2026-11-11 21:25）")):
        if old not in t: sys.exit(f"research 範本找不到 {old!r}")
        t = t.replace(old, new)
    anchor = "## 主要領導人加強規格"
    if t.count(anchor) != 1: sys.exit("找不到主要領導人加強規格")
    t = t.replace(anchor, MIN_BLOCK.lstrip("\n") + "\n" + anchor)
    (HERE / "PROMPT_research.md").write_text(t, encoding="utf-8")
    (HERE / "PROMPT_retry.md").write_text(RETRY, encoding="utf-8")
    r = (MAJOR / "PROMPT_review.md").read_text(encoding="utf-8")
    for old, new in (("# B3 full 主要領導人 v2 batch{{NN}}：審查", "# B3 full v3 batch{{NN}}：審查"),
                     ("data/seed/leaders/b3-trial/full/major-v2/PROMPT_research.md", "data/seed/leaders/b3-trial/full/v3/PROMPT_research.md"),
                     ("（本批全部適用，見", "（只對 flags 含 major★ 者，見"),
                     ('"promptVersion": "full-major-v2"', '"promptVersion": "full-v3"')):
        if old not in r: sys.exit(f"review 範本找不到 {old!r}")
        r = r.replace(old, new)
    a2 = "7. 符合 Q1–Q10。"
    r = r.replace(a2, REVIEW_ADD.strip("\n") + "\n" + a2)
    (HERE / "PROMPT_review.md").write_text(r, encoding="utf-8")
    print("sample", len(sample))

if __name__ == "__main__":
    main()
