#!/usr/bin/env python3
"""B3 full 主要領導人 18 人重跑（major-v2）：名單與加強版提示。

依據：Tai 2026-11-11 21:25 主要領導人優先；World Line 主管 2026-11-11 21:55（Tai 授權範圍內）同意三項規格變更，只適用這 18 人：
  ①提高最低搜尋量 ②英國人物指定 Historic Hansard 等 A 級來源，其他國家列對應官方／國家傳記來源 ③每個職位都要有任期日期，查不到標待查證。
其餘人物照 run100 規格（full/PROMPT_*.md）。舊產出 full/batch001–004 保留不覆蓋；本輪輸出 full/major-v2/batchNNN。
每批 3 人（6 批），以免單一 Sonnet session 超過 4 美元上限。
用法：python3 -I data/seed/leaders/b3-trial/full/major-v2/build_major.py（連跑兩次輸出逐位元相同）
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FULL = HERE.parent
BATCH_SIZE = 3
OUTDIR_OLD, OUTDIR_NEW = "data/seed/leaders/b3-trial/full/batch{{NN}}", "data/seed/leaders/b3-trial/full/major-v2/batch{{NN}}"
RAW_OLD, RAW_NEW = "/tmp/b3full/", "/tmp/b3full-major/"

SOURCES = {  # bioId → 指定優先查的來源（A 為主；B 已註明）
 "01a1c86e-c89b-70af-afe0-1ad0f4be2bf8": "英國：UK Parliament Historic Hansard 人物頁（api.parliament.uk/historic-hansard/people/…，A，歷任職位與起訖日）、GOV.UK Past Prime Ministers（A）、The London Gazette 任命公告（thegazette.co.uk，A）、Oxford DNB 公開摘要（A）、Churchill Archive Centre（Churchill College, Cambridge）機構傳記（B）、LoC／VIAF 權威檔",
 "01a19f15-33c3-7fff-a8d9-5521e842fb87": "英國：Historic Hansard 人物頁（A）、GOV.UK Past Prime Ministers（A）、London Gazette（A）、Oxford DNB 公開摘要（A）、National Library of Wales 威爾斯傳記辭典 Dictionary of Welsh Biography（biography.wales，A）",
 "01a19f15-3507-788a-9d61-83862bf96e28": "英國：Historic Hansard 人物頁（A）、GOV.UK Past Prime Ministers（A）、London Gazette（A）、Oxford DNB 公開摘要（A）、University of Birmingham Cadbury Research Library 的 Chamberlain Papers 說明（B）",
 "01a19f15-35f4-7d9a-847a-aeccc98305ec": "德國：Deutsche Biographie（NDB，A）、GND／lobid.org（A）、Bundesarchiv（A）、Reichstag-Abgeordnetendatenbank／Reichstagsprotokolle（BSB，A）、DHM LeMO（B）、Treccani（B）",
 "01a19f15-3574-776f-a3e9-348733e035e7": "德國：Deutsche Biographie（NDB，A）、GND／lobid.org（A）、Bundesarchiv（A）、DHM LeMO（B）、Reichsgesetzblatt（官方公報，A）",
 "01a1b492-3efd-7d05-8a70-3f38fdf9d599": "蘇聯：Президентская библиотека им. Ельцина（prlib.ru，A）、Большая российская энциклопедия（bigenc.ru，具名條目 B）、РГАСПИ 檔案說明（rgaspi.org，A）、DHM LeMO（B）、Treccani（B）、LoC 權威檔",
 "01a1b492-3ee1-75ee-8fc7-306c07a85a65": "蘇聯：Президентская библиотека（A）、Большая российская энциклопедия（具名 B）、РГАСПИ（A）、DHM LeMO（B）、Treccani（B）",
 "01a1b4b5-f9bc-7f2f-90ba-f2af428ba89c": "俄羅斯帝國：Президентская библиотека（A）、Большая российская энциклопедия（具名 B）、ГАРФ 檔案說明（A）、1914-1918-online（具名 B）",
 "01a1b48b-c87a-768a-b372-2918df397b6c": "美國：whitehouse.gov 歷任總統頁（A）、Biographical Directory of the U.S. Congress（bioguide.congress.gov，A）、FDR Presidential Library（NARA，fdrlibrary.org，A）、history.state.gov（A）、Miller Center（B）",
 "01a1b48b-c814-7f78-bba8-753c5a5ea41f": "美國：whitehouse.gov（A）、Woodrow Wilson Presidential Library（B）、history.state.gov（A）、Miller Center（B）、Princeton University 校長名錄（B）、New Jersey 州長名錄（A）",
 "0ff6f55e-8f9c-49aa-b9ba-5858a17c9dc3": "義大利：Treccani Dizionario Biografico degli Italiani（A）、Camera dei deputati Portale storico（storia.camera.it，A）、Senato della Repubblica、Gazzetta Ufficiale（A）",
 "01a1b4b2-2f65-7cca-9a4b-ff875f18c192": "日本：宮内庁（kunaicho.go.jp，A）、国立国会図書館（NDL 権威・近代日本人の肖像，A）、アジア歴史資料センター（jacar.go.jp，A）、防衛研究所（nids.mod.go.jp，A）",
 "62241525-b2f1-4931-bfb3-30ecf9dd3094": "日本：首相官邸 歴代内閣（kantei.go.jp，A）、国立国会図書館 近代日本人の肖像（A）、アジア歴史資料センター（A）、防衛研究所（A）、国立公文書館（A）",
 "01a1b490-dcc7-76dc-82d7-da76fb59d7d2": "中華民國：國史館（drnh.gov.tw，A）、總統府（president.gov.tw，A）、中央研究院近代史研究所（mh.sinica.edu.tw，A）、國家圖書館（A）、中正紀念堂（A）",
 "01a1b4b5-f9d8-7310-b964-ed7578856680": "奧匈：Österreichisches Biographisches Lexikon（biographien.ac.at，A）、Österreichische Nationalbibliothek（A）、Parlament Österreich（parlament.gv.at，A）、Deutsche Biographie（A）",
 "ef990cdf-5286-44c4-8e0a-1e8aaa1c629b": "法國：Assemblée nationale Sycomore（A）、Sénat 前參議員名錄（senat.fr，A）、BnF data（A）、Journal officiel（Gallica，A）",
 "01a1b48b-c890-7320-84f4-1442207f5f03": "西班牙：Real Academia de la Historia DB~e（dbe.rah.es，A）、Congreso de los Diputados／Cortes 歷史資料（A）、Boletín Oficial del Estado（boe.es，A）、Biblioteca Nacional de España 權威檔（A）",
 "01a1b492-3f04-7906-a59b-b9bfcc8f374d": "土耳其：TBMM（tbmm.gov.tr，A）、Cumhurbaşkanlığı（tccb.gov.tr，A）、Atatürk Araştırma Merkezi（atam.gov.tr，A）、TDV İslâm Ansiklopedisi（具名 B）",
}

BLOCK = """
## 主要領導人加強規格（World Line 主管 2026-11-11 21:55，Tai 授權範圍；只適用本批，優先於下方同名規則）
本批每人都是 1908–1945 主要領導人（Tai 2026-11-11 21:25），**不適用「厚人物 2–4 個來源即可」**。
1. **最低搜尋量（取代下方「最低嘗試」）**：每人至少 **5 種**來源類型、至少 **15 次**查詢（原文語言至少 4 次）、至少實際 curl 抓取 **6 個**候選頁；並至少取得 **3 個**可抓原文的 A／B 來源，其中至少 **1 個 A**（官方／議會／國家級傳記辭典／權威檔）。全部寫進 searchLog。
2. **指定來源（先查這些，查不到或被擋也要寫進 searchLog）**：
{SOURCES}
3. **職位任期**：positions 與 roleCandidates 的每一筆都要有 `period.start` 與 `period.end`，並有 quote 含該日期（或年／月）的 citation 支撐（可來自不同來源，各自是一筆 citation）。
   - 迄日查不到（含在職至死亡但來源沒寫）→ 該筆照寫 start，另加一筆 gap：target=`position:<key>`（角色用 `role:<key>`），gapKind=not_found，note 以「待查證：缺迄日；」開頭並寫已查過哪些來源。
   - 起日查不到 → 不寫入 positions／roleCandidates，改寫同樣格式的 gap（note 以「待查證：缺起日；」開頭）。
   - 1908–1945 窗內的主要職位（元首／首腦、四部閣員、黨職、國家級軍職）務必逐一查任期；窗外重要職位可只寫正文。
"""

REVIEW_BLOCK = """
6b. **主要領導人加強規格（本批全部適用，見 `{RESEARCH}` 的「主要領導人加強規格」）**：逐人檢查 searchLog 是否達 ≥5 種來源類型、≥15 次查詢（原文 ≥4）、≥6 個實抓頁、≥3 個 A／B 來源（≥1 個 A），並檢查指定來源是否有查（查過被擋也算）；未達 → verdict=returned 並寫缺什麼。逐筆檢查 positions／roleCandidates 是否都有起迄日與含日期的引文；缺迄日者須有「待查證：缺迄日」gap，缺起日者不得留在 positions／roleCandidates。
"""

def main():
    sel = json.loads((FULL / "selection-full.json").read_text(encoding="utf-8"))
    pri = sorted((p for p in sel["people"] if p.get("priority")), key=lambda p: p["priority"])
    if len(pri) != 18: sys.exit(f"priority 人數 {len(pri)} ≠ 18")
    if set(p["bioId"] for p in pri) != set(SOURCES): sys.exit("SOURCES 與 priority 名單不一致")
    people = []
    for i, p in enumerate(pri):
        q = dict(p); q["batch"] = f"{i // BATCH_SIZE + 1:03d}"; q["previousBatch"] = p["batch"]; q["majorSources"] = SOURCES[p["bioId"]]
        people.append(q)
    out = {"run": "b3-full-major-v2", "decision": "Tai 2026-11-11 21:25 主要領導人優先；主管 2026-11-11 21:55 三項加強規格（只適用這 18 人）",
           "previousOutput": "full/batch001–004（保留不覆蓋）", "batchSize": BATCH_SIZE, "batches": (len(people) + BATCH_SIZE - 1) // BATCH_SIZE, "people": people}
    (HERE / "selection-major.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    src_lines = "\n".join(f"   - {p['nameZh']}（{p['name']}）：{SOURCES[p['bioId']]}" for p in pri)
    t = (FULL / "PROMPT_research.md").read_text(encoding="utf-8")
    for old, new in ((OUTDIR_OLD, OUTDIR_NEW), (RAW_OLD, RAW_NEW), ("`data/seed/leaders/b3-trial/full/selection-full.json`", "`data/seed/leaders/b3-trial/full/major-v2/selection-major.json`"),
                     ("b3-full-batch{{NN}}", "b3-full-major-v2-batch{{NN}}"), ("# B3 full batch{{NN}}：研究", "# B3 full 主要領導人 v2 batch{{NN}}：研究"),
                     ("## 本批 5 人", "## 本批 3 人"), ("你只做本批 5 人的研究", "你只做本批 3 人的研究")):
        if old not in t: sys.exit(f"research 範本找不到 {old!r}")
        t = t.replace(old, new)
    anchor = "## 搜尋策略"
    if t.count(anchor) != 1: sys.exit("找不到搜尋策略標題")
    t = t.replace(anchor, BLOCK.replace("{SOURCES}", src_lines).lstrip("\n") + "\n" + anchor)
    (HERE / "PROMPT_research.md").write_text(t, encoding="utf-8")
    r = (FULL / "PROMPT_review.md").read_text(encoding="utf-8")
    for old, new in (("# B3 full batch{{NN}}：審查", "# B3 full 主要領導人 v2 batch{{NN}}：審查"),
                     ("data/seed/leaders/b3-trial/full/PROMPT_research.md", "data/seed/leaders/b3-trial/full/major-v2/PROMPT_research.md"),
                     ('"promptVersion": "full-v1（=run100-v1）"', '"promptVersion": "full-major-v2"')):
        if old not in r: sys.exit(f"review 範本找不到 {old!r}")
        r = r.replace(old, new)
    a2 = "7. 符合 Q1–Q10。"
    if r.count(a2) != 1: sys.exit("找不到審查第 7 項")
    r = r.replace(a2, REVIEW_BLOCK.replace("{RESEARCH}", "data/seed/leaders/b3-trial/full/major-v2/PROMPT_research.md").strip("\n") + "\n" + a2)
    (HERE / "PROMPT_review.md").write_text(r, encoding="utf-8")
    print("major people", len(people), "batches", out["batches"])

if __name__ == "__main__":
    main()
