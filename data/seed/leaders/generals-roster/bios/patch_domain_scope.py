#!/usr/bin/env python3
"""將日本及其他非英語國家將領的搜尋網域寫進生平提示（可重跑）。

依據：World Line 主管 2026-11-12 03:03（Tai 轉達；ARCHITECTURE §16 T1）。
- A：國立國會圖書館典據（Web NDL Authorities, id.ndl.go.jp）、JACAR（jacar.go.jp／jacar.archives.go.jp）
- B：日本大百科全書、國史大辭典、世界大百科事典（Kotobank 具名條目，kotobank.jp）
其他非英語國家用同等原則的國家圖書館權威檔／官方戰史，並在提示中列出分級。
用法：python3 -I data/seed/leaders/generals-roster/bios/patch_domain_scope.py
不改 schema、不寫庫。主迴圈每批會重新讀取 PROMPT_*.md。
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
MARKER_START = "<!-- DOMAIN_SCOPE_2026-11-12 -->"
MARKER_END = "<!-- /DOMAIN_SCOPE_2026-11-12 -->"

SECTION = """## 日本及其他非英語國家將領：補充搜尋範圍（World Line 主管 2026-11-12 03:03，依 ARCHITECTURE §16 T1）
日本將領、以及其他非英語國家將領，除本檔既有來源外，**必須**查下列網域（可抓原文才可當出處；維基只當索引，不是出處）。個人網站不收。

**日本（本輪新納入或改為必查）**
- **A**：國立國會圖書館典據 Web NDL Authorities（`id.ndl.go.jp`）；國立國會圖書館官方頁，含「近代日本人の肖像」（`ndl.go.jp`、`www.ndl.go.jp`）；JACAR アジア歴史資料センター（`jacar.go.jp`、`www.jacar.go.jp`、`jacar.archives.go.jp`）；防衛研究所戰史（`nids.mod.go.jp`、`www.nids.mod.go.jp`，已列）；必要時再查宮内庁（`kunaicho.go.jp`，皇族）、国立公文書館（`www.archives.go.jp`）、首相官邸歴代内閣（`kantei.go.jp`，兼任閣員時）。
- **B**：Kotobank（`kotobank.jp`、`www.kotobank.jp`）上**具名**條目的『日本大百科全書』（小学館）、『国史大辞典』（吉川弘文館）、『世界大百科事典』（平凡社）。只收有具名作者或具名詞典／條目責任者的條目；無署名彙編不收。

**其他非英語國家（同等原則：國家圖書館權威檔／官方戰史＝A；具名機構百科＝B）。下列多已見於上方策略，此處再標分級，以免只查英語來源：**
- 德國 **A**：Deutsche Biographie（`www.deutsche-biographie.de`）、GND／lobid.org、Bundesarchiv（`www.bundesarchiv.de`）、官方公報（Reichsgesetzblatt 數位版）。**B**：DHM LeMO（`www.dhm.de`）。
- 法國 **A**：BnF data（`data.bnf.fr`）、Assemblée nationale Sycomore、Sénat（`www.senat.fr`）、Journal officiel（Gallica `gallica.bnf.fr` 或 Légifrance `www.legifrance.gouv.fr`）、國防部記憶／戰史官方頁（`www.cheminsdememoire.gouv.fr`、`www.defense.gouv.fr` 官方戰史）。
- 義大利 **A**：Treccani DBI（`www.treccani.it`）、Camera Portale storico（`storia.camera.it`）、Senato、Gazzetta Ufficiale（`www.gazzettaufficiale.it`）。
- 俄國／蘇聯 **A**：總統圖書館（`www.prlib.ru`）、РГАСПИ（`rgaspi.org`）、ГАРФ 檔案說明。**B**：Большая российская энциклопедия 具名條目（`bigenc.ru`）。
- 中國／中華民國 **A**：國史館（`www.drnh.gov.tw`）、中央研究院近代史研究所（`mh.sinica.edu.tw`）、國家圖書館（`www.ncl.edu.tw`）、總統府（`www.president.gov.tw`）。
- 奧匈 **A**：Österreichisches Biographisches Lexikon（`www.biographien.ac.at`）、Österreichische Nationalbibliothek（`www.onb.ac.at`）、Parlament Österreich（`www.parlament.gv.at`）。
- 波蘭、羅馬尼亞、芬蘭、土耳其、南斯拉夫、泰國等：各國國家圖書館權威檔、議會／總統府官方履歷、官方戰史＝**A**；芬蘭 Kansallisbiografia；土耳其 TBMM（`www.tbmm.gov.tr`）、Atatürk Araştırma Merkezi（`www.atam.gov.tr`）；具名機構百科＝**B**。

未列入上表、首次用到的網域：依 §16 T1 暫分 A／B，寫進該筆 `sources.grade`／`gradeBasis` 與 searchLog，並在批次結尾列出來源網域；不把個人網站或無署名彙編當出處。
"""

BLOCK = f"{MARKER_START}\n{SECTION}{MARKER_END}\n"

OLD_EA = "日本 国立国会図書館「近代日本人の肖像」（ndl.go.jp/portrait）、国立公文書館アジア歴史資料センター（jacar.go.jp）。"
NEW_EA = "日本 国立国会図書館典據 Web NDL Authorities（id.ndl.go.jp）、国立国会図書館「近代日本人の肖像」（ndl.go.jp/portrait）、国立公文書館アジア歴史資料センター（jacar.go.jp／jacar.archives.go.jp）；Kotobank 具名條目之日本大百科全書／國史大辭典／世界大百科事典（kotobank.jp，B）。"

OLD_RETRY = "優先改查 A 級來源（國家級傳記辭典、政府／國防部／議會名錄、官方公報、人名權威檔；日本防衛研究所 nids.mod.go.jp、國史館、Deutsche Biographie、Treccani DBI、Oxford DNB 公開摘要、London Gazette 等）。"
NEW_RETRY = "優先改查 A 級來源（國家級傳記辭典、政府／國防部／議會名錄、官方公報、人名權威檔）。**日本將領必查**：Web NDL Authorities（id.ndl.go.jp）、JACAR（jacar.go.jp、jacar.archives.go.jp）、防衛研究所（nids.mod.go.jp），以及 Kotobank 具名百科條目（kotobank.jp，B）。其他非英語國家改查該國國家圖書館權威檔或官方戰史（完整分級見 `data/seed/leaders/generals-roster/bios/PROMPT_research.md`「日本及其他非英語國家將領：補充搜尋範圍」；德國 Deutsche Biographie／Bundesarchiv／lobid，法國 BnF／Journal officiel／國防部戰史，義大利 Treccani DBI／Gazzetta Ufficiale，俄國 prlib.ru／bigenc.ru，中國國史館／近史所等）。亦包括國史館、Oxford DNB 公開摘要、London Gazette 等既有來源。"

ANCHOR = "依序嘗試，查到 A／B 就可停止往下（厚人物 2–4 個來源即可，不要逐頁瀏覽）："


def upsert_section(text: str) -> str:
    if MARKER_START in text and MARKER_END in text:
        pre, rest = text.split(MARKER_START, 1)
        _, post = rest.split(MARKER_END, 1)
        if post.startswith("\n"):
            post = post[1:]
        return pre + BLOCK + post
    if ANCHOR not in text:
        raise SystemExit(f"anchor not found in PROMPT_research.md")
    return text.replace(ANCHOR, BLOCK + "\n" + ANCHOR, 1)


def main() -> None:
    research = HERE / "PROMPT_research.md"
    rt = research.read_text(encoding="utf-8")
    if OLD_EA in rt:
        rt = rt.replace(OLD_EA, NEW_EA)
    rt = upsert_section(rt)
    research.write_text(rt, encoding="utf-8")
    print("PROMPT_research.md: domain-scope section upserted")

    retry = HERE / "PROMPT_retry.md"
    tt = retry.read_text(encoding="utf-8")
    if OLD_RETRY in tt:
        tt = tt.replace(OLD_RETRY, NEW_RETRY)
        retry.write_text(tt, encoding="utf-8")
        print("PROMPT_retry.md: Japanese/non-English sources added")
    elif "日本將領必查" in tt:
        print("PROMPT_retry.md: already patched")
    else:
        raise SystemExit("PROMPT_retry.md: expected sentence not found")


if __name__ == "__main__":
    main()
