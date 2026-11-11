"""段祺瑞、費薩爾一世補查產生器（Tai 2026-11-11 12:12 第 5 項；未寫庫、不連 DB、不連網）。

用法：python3 -I build.py
產物（同目錄）：research.json（b0b0e0f 對齊格式）、rawmap.json。之後另跑：
  python3 -I ../verify.py research.json --report verify-report.json
原文存 /tmp/b3supp2-raw/（不進版控；FRUS 頁面以 HTML 轉純文字，LoC 權威檔以 suggest2 JSON 解碼成純文字）。
5442 既有任期取自 ../selection.json（離線檔，不連 DB），逐筆比對結果寫進 research.json 的 recordComparison。
所有內容寫在本檔；不手改產物。輸出排序固定、無時間戳，連跑兩次逐位元相同。
"""
import json, sys, unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
ACC = "2026-11-11"
POL = "bio-2026-11-v0"
RAW_DIR = "/tmp/b3supp2-raw"
BEIYANG = "01a195a6-c6cb-7d13-9ee8-3e7582004d05"
TBD = "待查證"

FRUS_BASIS = "美國國務院歷史文獻辦公室出版的官方外交文件集（Foreign Relations of the United States），屬政府官方紀錄"
LOC_BASIS = "美國國會圖書館名稱權威檔（national library authority file）；引文為權威檔 670 欄所記來源摘錄"


def frus(vol, doc, title, raw):
    return {"title": title, "authors": [], "publisher": "Office of the Historian, U.S. Department of State",
            "published_text": f"Papers Relating to the Foreign Relations of the United States, {vol}",
            "url": f"https://history.state.gov/historicaldocuments/{doc}", "archive_url": None,
            "catalog_id": doc, "license_code": "US-Gov-PD", "grade": "A", "gradeBasis": FRUS_BASIS, "_raw": raw}


SOURCES = {
    "loc-duan": {"title": "Duan, Qirui, 1865-1936", "authors": [], "publisher": "Library of Congress",
                 "published_text": "LC Name Authority File nr94033282",
                 "url": "https://id.loc.gov/authorities/names/nr94033282.html", "archive_url": None,
                 "catalog_id": "nr94033282", "license_code": "US-Gov-PD", "grade": "A", "gradeBasis": LOC_BASIS,
                 "fetchUrl": "https://id.loc.gov/authorities/names/suggest2?q=Duan%2C%20Qirui", "_raw": "loc-duan.txt"},
    "loc-faisal": {"title": "Faysal I, King of Iraq, 1885-1933", "authors": [], "publisher": "Library of Congress",
                   "published_text": "LC Name Authority File n90649742",
                   "url": "https://id.loc.gov/authorities/names/n90649742.html", "archive_url": None,
                   "catalog_id": "n90649742", "license_code": "US-Gov-PD", "grade": "A", "gradeBasis": LOC_BASIS,
                   "fetchUrl": "https://id.loc.gov/authorities/names/suggest2?q=Fay%E1%B9%A3al%20I", "_raw": "loc-faisal.txt"},
    "frus1916-d82": frus("1916", "frus1916/d82", "Minister Reinsch to the Secretary of State, April 24, 1916", "frus1916-d82.txt"),
    "frus1916-d98": frus("1916", "frus1916/d98", "Minister Reinsch to the Secretary of State, June 30, 1916", "frus1916-d98.txt"),
    "frus1917-d111": frus("1917", "frus1917/d111", "Minister Reinsch to the Secretary of State, July 3, 1917", "frus1917-d111.txt"),
    "frus1917-d128": frus("1917", "frus1917/d128", "Minister Reinsch to the Secretary of State, August 9, 1917", "frus1917-d128.txt"),
    "frus1917-d145": frus("1917", "frus1917/d145", "Minister Reinsch to the Secretary of State, November 20, 1917", "frus1917-d145.txt"),
    "frus1924v01-d364": frus("1924, Volume I", "frus1924v01/d364", "The Chargé in China (Mayer) to the Secretary of State, November 21, 1924", "frus1924v01-d364.txt"),
    "frus1924v01-d366": frus("1924, Volume I", "frus1924v01/d366", "The Chargé in China (Mayer) to the Secretary of State, November 24, 1924", "frus1924v01-d366.txt"),
    "frus1926v01-d445": frus("1926, Volume I", "frus1926v01/d445", "The Minister in China (MacMurray) to the Secretary of State, April 10, 1926", "frus1926v01-d445.txt"),
    "frus1926v01-d451": frus("1926, Volume I", "frus1926v01/d451", "The Minister in China (MacMurray) to the Secretary of State, April 21, 1926", "frus1926v01-d451.txt"),
    "frus1926v01-d533": frus("1926, Volume I", "frus1926v01/d533", "The Minister in China (MacMurray) to the Secretary of State, June 16, 1926", "frus1926v01-d533.txt"),
    "frus1921v02-d100": frus("1921, Volume II", "frus1921v02/d100", "British memorandum on the mandate for Mesopotamia, December 30, 1921", "frus1921v02-d100.txt"),
    "frus1925v02-d188": frus("1925, Volume II", "frus1925v02/d188", "Telegram on the Iraq mandate, November 3, 1924", "frus1925v02-d188.txt"),
    "frus1927v02-d753": frus("1927, Volume II", "frus1927v02/d753", "Draft convention regarding Iraq, July 13, 1926", "frus1927v02-d753.txt"),
}


def c(sk, loc, quote, prec=None, note=None, lang="en"):
    return {"sourceKey": sk, "locator": loc, "quote": quote, "quoteLang": lang, "evidenceNote": note,
            "accessedOn": ACC, "grade": SOURCES[sk]["grade"], "datePrecision": prec, "claimSpan": None,
            "policyVersion": POL}


def per(s, sp, e, ep):
    return {"start": s, "end": e}, sp, ep


def para(ord_, s, sp, e, ep, hz, he, bz, be, cits, rel=()):
    return {"ord": ord_, "period": {"start": s, "end": e}, "periodStartPrecision": sp, "periodEndPrecision": ep,
            "heading": {"zh-Hant": hz, "en": he}, "body": {"zh-Hant": bz, "en": be},
            "relatedRecordIds": list(rel), "citations": cits}


def gap(target, kind, note, tried=(), cands=()):
    return {"target": target, "gapKind": kind, "note": note, "attempts": [{"url": u, "result": r} for u, r in tried],
            "candidateCitations": list(cands), "checkedOn": ACC}


def field(value, cits=(), prec=None, note=None):
    return {"value": value, "precision": prec, "note": note, "citations": list(cits)}


R = {  # 5442 recordId（取自 ../selection.json）
    "d1913": "01a1a20c-bbf4-783b-8f3c-411614c6ef1b", "d1916a": "01a1a20c-bc03-790b-b60b-9630f48560ed",
    "d1916b": "01a1a20c-bc06-7f95-9270-95cc91b158a6", "d1917": "01a1a20c-bc0b-70ad-9a46-aa31c184b8ae",
    "d1918": "01a1a20c-bc16-782e-953c-28a2b889f040", "f1932": "01a1aa4a-c325-7c74-9a1a-017548704f3b",
}

# 嘗試紀錄（含試跑已試過者）
T_BRIT_D = ("https://www.britannica.com/biography/Duan-Qirui", "HTTP 403，不繞過")
T_BRIT_F = ("https://www.britannica.com/biography/Faysal-I", "HTTP 403，不繞過")
T_ENC_D = ("https://www.encyclopedia.com/people/history/chinese-history-biographies/duan-qirui", "HTTP 404（另試兩種網址亦 404）")
T_ENC_F = ("https://www.encyclopedia.com/people/history/middle-eastern-history-biographies/faisal-i", "200，但僅 Encyclopedia of World Biography（無具名作者，Q9 未評等），不採")
T_VIAF = ("https://viaf.org/viaf/search?query=local.personalNames%20all%20%22Duan%20Qirui%22", "HTTP 403，不繞過")
T_OXREF = ("https://www.oxfordreference.com/search?q=Duan+Qirui", "HTTP 403，不繞過")
T_NDL = ("https://id.ndl.go.jp/auth/ndla?query=段祺瑞&format=json", "200，僅 82 位元組、無權威紀錄")
T_AVALON = ("https://avalon.law.yale.edu/20th_century/iraq001.asp", "HTTP 404；Avalon 中東主題目錄（subject_menus/mideast.asp）未列 1922／1930 英伊條約")
T_TRIAL_D = ("https://www.chinesetext.org 等（試跑 batch06）", "試跑時 Chinese Text Project 驗證挑戰頁、1914-1918-online Anubis 挑戰頁，皆不繞過；本次未重試")
T_FRUS_1918 = ("https://history.state.gov/search?q=Tuan+Premier+appointed&within=documents&start-date=1918-03-01&end-date=1918-04-30", "0 筆")
T_FRUS_F33 = ("https://history.state.gov/search?q=Feisal+Iraq&within=documents&start-date=1933-09-01&end-date=1933-12-31", "0 筆（另試 Iraq King Faisal death 亦 0 筆）")
T_FRUS_F20 = ("https://history.state.gov/search?q=Feisal+Syria+King&within=documents&start-date=1920-01-01&end-date=1920-12-31", "0 筆")
T_FRUS_F32 = ("https://history.state.gov/search?q=Iraq+League+membership&within=documents&start-date=1932-01-01&end-date=1932-12-31", "僅 frus1932v02/d487（入會條件談判），未載入會日期；未採")

DUAN = {
    "key": "cn-duan-qirui", "bioId": "01a1b51c-82f5-769f-b906-e1ae5f2acad8", "name": "Duan Qirui", "nameZh": "段祺瑞",
    "recordIds": [R["d1913"], R["d1916a"], R["d1916b"], R["d1917"], R["d1918"]], "thickness": "中",
    "fields": {
        "nameOrig": field("段祺瑞", [c("loc-duan", "nonlatinLabels", "段祺瑞, 1865-1936", lang="zh")]),
        "nameZh": field("段祺瑞", [c("loc-duan", "nonlatinLabels", "段祺瑞, 1865-1936", lang="zh")]),
        "nameRomanized": field("Duan, Qirui", [c("loc-duan", "標目", "Duan, Qirui, 1865-1936")],
                               note="舊式拼法 Tuan Chʻi-jui 見同檔 variantLabels；FRUS 作 Tuan Chi-jui"),
        "birthDate": field("1865-03-06", [c("loc-duan", "sources（670 欄，引 Chi, Y. 1992）", "b. 3/6/1865; d. 11/2/1936", "day")], "day",
                           note="LoC 670 欄以月/日/年記（美式），讀作 1865-03-06；與 5442 birth 一致。來源未註明是否為換算後公曆"),
        "deathDate": field("1936-11-02", [c("loc-duan", "sources（670 欄，引 Chi, Y. 1992）", "b. 3/6/1865; d. 11/2/1936", "day")], "day",
                           note="同上，讀作 1936-11-02；與 5442 death 一致"),
        "birthplace": field(TBD),
        "party": field(TBD, note="北洋軍人，FRUS 引文未記其黨籍；安福系等派系屬性未取得 A／B 原文，不填"),
        "summary": field("北洋政府軍人政治家。1916年4月受任國務總理兼陸軍總長，同年6月再任國務總理，1917年5月23日被免職；"
                         "1917年7月張勳復辟期間受命為國務總理兼總司令；1924年11月24日就任臨時執政，1926年4月下野。",
                         [c("frus1916-d82", "正文", "Tuan Chi-jui, Premier and Minister of War"),
                          c("frus1924v01-d366", "正文第 1 點", "Tuan Chi-jui assumed office this morning")],
                         note="簡介為段落 1–3 的濃縮，各句出處見各段"),
    },
    "paragraphs": [
        para(1, "1916-04-01", "month", "1917-05-23", "day", "出任國務總理", "Premier, 1916–1917",
             "1916年4月，袁世凱政府宣布改行責任內閣，任命段祺瑞為國務總理兼陸軍總長。同年6月29日夜，總統發布命令恢復國會、"
             "沿用南京臨時約法，段祺瑞再獲任命為國務總理。1917年5月23日段祺瑞被免去總理職務，其後北方多省宣布獨立。",
             "In April 1916 a mandate establishing a responsible cabinet appointed Tuan Chi-jui (Duan Qirui) Premier and Minister of War. "
             "On the night of 29 June 1916 the President issued mandates reconvening Parliament and Tuan was reappointed Premier. "
             "He was dismissed as Premier on 23 May 1917, after which several northern provinces seceded.",
             [c("frus1916-d82", "Peking, April 24, 1916, 6 p.m.，正文", "Tuan Chi-jui, Premier and Minister of War", "month",
                "電報日期 1916-04-24；命令發布日未明載，故起點記月精度"),
              c("frus1916-d98", "Peking, June 30, 1916, 6 p.m.，正文", "the President last night issued mandates", "day",
                "電報 6 月 30 日稱「昨夜」，據此記 1916-06-29（依電報日期換算）"),
              c("frus1916-d98", "同上，正文末", "Tuan reappointed Premier", "day"),
              c("frus1917-d111", "No. 1557, July 3, 1917，[Page 84]", "The dismissal of the Premier Tuan Chi-jui on May 23", "day")],
             [R["d1916a"], R["d1916b"]]),
        para(2, "1917-07-01", "month", None, None, "討伐復辟與再度組閣", "Against the Restoration, 1917",
             "1917年7月張勳擁清復辟，段祺瑞時為無兵權的平民，赴馬廠第八師號召反對復辟。總統黎元洪避入使館區前發布命令，"
             "任命段祺瑞為國務總理兼總司令。同年11月16日段祺瑞與全體閣員辭職，翌日經與總統會商後撤回辭呈。",
             "During Chang Hsun's monarchist restoration of July 1917, Tuan, then a private citizen without command, rallied the "
             "8th Division at Machang. Before taking refuge in the Legation Quarter on 2 July, President Li Yuan-hung issued a "
             "mandate appointing Tuan Premier and Commander-in-Chief. On 16 November 1917 Tuan and his whole cabinet resigned; "
             "the resignations were withdrawn the next day.",
             [c("frus1917-d128", "August 9, 1917，[Page 92]", "he was at that time actually only a private citizen without authority or command"),
              c("frus1917-d128", "同上，[Page 93]", "On July 2 he took refuge in the Legation Quarter, after having issued a mandate", "month",
                "主詞 he 為前句之 President Li；命令發布於 7 月 2 日或之前，日未能確定，記月精度"),
              c("frus1917-d128", "同上，[Page 93]", "appointing General Tuan Chi-jui Premier and Commander-in-Chief"),
              c("frus1917-d145", "No. 1749, November 20, 1917，正文", "General Tuan Chi-jui, the Prime Minister, and his whole Cabinet, resigned", "day"),
              c("frus1917-d145", "同上", "at the end of which the resignations were withdrawn", "day")],
             [R["d1917"]]),
        para(3, "1924-11-24", "day", "1926-04-01", "month", "臨時執政", "Provisional Chief Executive, 1924–1926",
             "1924年11月，張作霖、馮玉祥等通電擁段祺瑞為臨時執政；外交部告知內閣將把總理與總統職權交給段祺瑞。"
             "11月24日上午段祺瑞就任「中華民國執政」。1926年4月國民軍發動政變，段祺瑞一度遭軟禁、避入使館區，"
             "4月20日前後離京下野，其臨時政府為張作霖、吳佩孚聯軍所推翻。",
             "In November 1924 Chang Tso-lin, Feng Yu-hsiang and their followers called on the provinces to support Tuan as "
             "Provisional Chief Executive, and the cabinet was to hand over to him the powers of Premier and President. He assumed "
             "office as Chief Executive on the morning of 24 November 1924. In April 1926 a coup placed him under restraint; he "
             "left Peking around 20 April, and his Provisional Government was overthrown by the allied forces of Chang Tso-lin and Wu Pei-fu.",
             [c("frus1924v01-d364", "Peking, November 21, 1924，第 1 點", "Cabinet will hand over to Marshal Tuan the powers of Premier and President"),
              c("frus1924v01-d366", "Peking, November 24, 1924，第 1 點", "Tuan Chi-jui assumed office this morning", "day",
                "電報日期 1924-11-24，「this morning」即當日"),
              c("frus1926v01-d445", "Peking, April 10, 1926，第 1 點", "Marshal Tuan had been placed under restraint in his residence", "day"),
              c("frus1926v01-d451", "Peking, April 21, 1926，第 1 點", "Tuan, before leaving, issued mandates that appeared today", "month",
                "離京確切日未明載（電報引前一電 April 20），故迄點記月精度"),
              c("frus1926v01-d533", "註腳", "overthrew the Provisional Government of Tuan Chi-jui")]),
    ],
    "positions": [
        {"key": "duan-minister-of-war-1916", "regimeId": BEIYANG,
         "organization": {"zh-Hant": "中華民國北京政府", "en": "Peking Government, Republic of China"},
         "title": {"orig": TBD, "zh-Hant": "陸軍總長（兼）", "en": "Minister of War"}, "positionKind": "minister",
         "period": {"start": "1916-04-01", "end": None}, "startPrecision": "month", "endPrecision": None,
         "citations": [c("frus1916-d82", "Peking, April 24, 1916，正文", "Tuan Chi-jui, Premier and Minister of War", "month",
                         "電報日期 1916-04-24；任命日、卸任日未明載。原文職稱（中文）未取得")]},
        {"key": "duan-commander-in-chief-1917", "regimeId": BEIYANG,
         "organization": {"zh-Hant": "討伐復辟之共和軍", "en": "Republican troops against the 1917 restoration"},
         "title": {"orig": TBD, "zh-Hant": "總司令", "en": "Commander-in-Chief"}, "positionKind": "military_command",
         "period": {"start": "1917-07-01", "end": None}, "startPrecision": "month", "endPrecision": None,
         "citations": [c("frus1917-d128", "August 9, 1917，[Page 93]", "appointing General Tuan Chi-jui Premier and Commander-in-Chief", "month",
                         "命令發布於 1917-07-02 或之前；卸任日未明載")]},
    ],
    "roleCandidates": [
        {"key": "duan-premier-1916-apr", "regimeId": BEIYANG,
         "organization": {"zh-Hant": "中華民國北京政府", "en": "Peking Government, Republic of China"},
         "title": {"orig": TBD, "zh-Hant": "國務總理（FRUS 作 Premier）", "en": "Premier"}, "originalPositionKind": None,
         "period": {"start": "1916-04-01", "end": "1916-06-29"}, "startPrecision": "month", "endPrecision": "day",
         "citations": [c("frus1916-d82", "Peking, April 24, 1916，正文", "Tuan Chi-jui, Premier and Minister of War", "month"),
                       c("frus1916-d98", "Peking, June 30, 1916，正文", "Tuan reappointed Premier", "day",
                         "迄日取同一人再任命之日（6 月 29 日夜），屬推論；非下一任起日")],
         "role_kind": "head_of_government", "reason": "政府首腦（國務總理）任期，依 b0b0e0f 放 roleCandidates"},
        {"key": "duan-premier-1916-jun", "regimeId": BEIYANG,
         "organization": {"zh-Hant": "中華民國北京政府", "en": "Peking Government, Republic of China"},
         "title": {"orig": TBD, "zh-Hant": "國務總理", "en": "Premier"}, "originalPositionKind": None,
         "period": {"start": "1916-06-29", "end": "1917-05-23"}, "startPrecision": "day", "endPrecision": "day",
         "citations": [c("frus1916-d98", "Peking, June 30, 1916，正文", "the President last night issued mandates", "day",
                         "電報 6 月 30 日稱「昨夜」，記 1916-06-29"),
                       c("frus1916-d98", "同上，正文末", "Tuan reappointed Premier", "day"),
                       c("frus1917-d111", "July 3, 1917，[Page 84]", "The dismissal of the Premier Tuan Chi-jui on May 23", "day")],
         "role_kind": "head_of_government", "reason": "政府首腦（國務總理）任期，依 b0b0e0f 放 roleCandidates"},
        {"key": "duan-premier-1917-jul", "regimeId": BEIYANG,
         "organization": {"zh-Hant": "中華民國北京政府", "en": "Peking Government, Republic of China"},
         "title": {"orig": TBD, "zh-Hant": "國務總理", "en": "Premier"}, "originalPositionKind": None,
         "period": {"start": "1917-07-01", "end": None}, "startPrecision": "month", "endPrecision": None,
         "citations": [c("frus1917-d128", "August 9, 1917，[Page 93]", "appointing General Tuan Chi-jui Premier and Commander-in-Chief", "month",
                         "命令發布於 1917-07-02 或之前，日未能確定"),
                       c("frus1917-d145", "November 20, 1917，正文", "at the end of which the resignations were withdrawn", "day",
                         "1917-11-16 辭職、11-17 撤回；最終去職日未取得，迄日留空")],
         "role_kind": "head_of_government", "reason": "政府首腦（國務總理）任期，依 b0b0e0f 放 roleCandidates"},
        {"key": "duan-chief-executive-1924", "regimeId": BEIYANG,
         "organization": {"zh-Hant": "中華民國臨時執政府", "en": "Provisional Government of the Republic of China"},
         "title": {"orig": TBD, "zh-Hant": "臨時執政", "en": "Provisional Chief Executive"}, "originalPositionKind": None,
         "period": {"start": "1924-11-24", "end": "1926-04-01"}, "startPrecision": "day", "endPrecision": "month",
         "citations": [c("frus1924v01-d366", "Peking, November 24, 1924，第 1 點", "Tuan Chi-jui assumed office this morning", "day"),
                       c("frus1924v01-d364", "Peking, November 21, 1924，第 1 點", "Cabinet will hand over to Marshal Tuan the powers of Premier and President"),
                       c("frus1926v01-d451", "Peking, April 21, 1926，第 1 點", "Tuan, before leaving, issued mandates that appeared today", "month")],
         "role_kind": "head_of_state",
         "reason": "臨時執政承接總統與總理職權（FRUS 1924-11-21）；暫列元首候選，是否同時為政府首腦待角色層定案"},
    ],
    "gaps": [
        gap("field:birthplace", "not_found", "出生地未見於 LoC 權威檔與所取 FRUS 文件；待查證",
            [T_BRIT_D, T_ENC_D, T_VIAF, T_NDL, T_OXREF, T_TRIAL_D]),
        gap("field:party", "not_found", "黨派／派系（如安福系）未取得 A／B 原文；待查證", [T_BRIT_D, T_ENC_D]),
        gap("position:duan-premier-1913", "not_found",
            "5442 有 1913-05-01～1913-07-31 代理國務總理一筆，本次未取得任何 A／B 原文（FRUS 未見）；待查證", [T_BRIT_D, T_ENC_D]),
        gap("position:duan-premier-1918", "not_found",
            "5442 有 1918-03-23～1918-10-10 國務總理一筆，FRUS 1918 年 3–4 月搜尋 0 筆；待查證", [T_FRUS_1918]),
        gap("position:duan-premier-1917-jul", "not_found",
            "1917 年 7 月再任總理的最終去職日未取得：FRUS 僅記 11 月 16 日辭職、17 日撤回、並預期再度請辭；5442 記迄 1917-11-22，未能核對"),
        gap("position:duan-chief-executive-1924", "not_found",
            "臨時執政迄日：FRUS 4 月 10 日電稱已辭職並遭軟禁，但同電第 3 點稱政變未完全成功；4 月 21 日電稱其「離開前」發布命令（引 4 月 20 日電）。"
            "確切下野日未取得，迄日記 1926 年 4 月（月精度）"),
        gap("paragraph:early-life", "not_found", "出生地、天津武備學堂、留德等早年經歷未取得 A／B 原文；待查證",
            [T_BRIT_D, T_ENC_D, T_OXREF, T_TRIAL_D]),
    ],
}

FAISAL = {
    "key": "iq-faisal1", "bioId": "01a1b543-5a9c-79d2-93a9-e10877d61b78", "name": "Faisal I", "nameZh": "費薩爾一世",
    "recordIds": [R["f1932"]], "thickness": "中",
    "fields": {
        "nameOrig": field("فيصل", [c("loc-faisal", "nonlatinLabels", "فيصل، ملك العراق", lang="ar")],
                          note="LoC 阿拉伯文標目為「فيصل، ملك العراق」（費薩爾，伊拉克國王）；取人名部分"),
        "nameZh": field(TBD, note="本次未取得記載中文譯名的 A／B 來源（如臺灣國家圖書館權威檔）；5442 現用「費薩爾一世」未核對"),
        "nameRomanized": field("Faysal I, King of Iraq", [c("loc-faisal", "標目", "Faysal I, King of Iraq, 1885-1933")]),
        "birthDate": field(TBD, note="出生年互相矛盾（1885／1883），見 gaps field:birthDate；不選邊"),
        "deathDate": field("1933-09-08", [c("loc-faisal", "sources（670 欄，引 Encyc. Brit. 15th ed.）", "d. Sept. 8, 1933", "day")], "day",
                           note="與 5442 death 一致"),
        "birthplace": field(TBD),
        "party": field("不適用", note="君主，無黨籍"),
        "summary": field("麥加謝里夫侯賽因·本·阿里之子；1918–1920 年為敘利亞國王，1921–1933 年為伊拉克國王，1933年9月8日去世。"
                         "在位期間與英國締結 1922 年 10 月 10 日英伊同盟條約及 1926 年 1 月 13 日英伊條約。",
                         [c("loc-faisal", "sources（670 欄，引 Encyc. Brit. 15th ed.）", "was King of Syria from 1918-1920 and later King of Iraq from 1921-1933"),
                          c("frus1927v02-d753", "Schedule of Documents", "Anglo-Iraq Treaty of Alliance of October 10, 1922")],
                         note="簡介為段落 1–3 的濃縮，各句出處見各段"),
    },
    "paragraphs": [
        para(1, None, None, None, None, "出身", "Origins",
             "費薩爾為麥加埃米爾暨大謝里夫侯賽因·本·阿里之子，阿拉伯文名「فيصل」，西文文獻亦作 Faisal、Feisal、Fayṣal al-Awwal。",
             "Faysal (Faisal, Feisal) I was a son of Ḥusayn ibn ʻAlī, amīr and grand sharīf of Mecca.",
             [c("loc-faisal", "sources（670 欄，引 Encyc. Brit. 15th ed.）", "son of Ḥusayn ibn ʻAlī, amīr and grand sharīf of Mecca"),
              c("loc-faisal", "variantLabels", "Feisal I, King of Iraq, 1885-1933")]),
        para(2, "1918-01-01", "year", "1933-09-08", "day", "敘利亞與伊拉克國王", "King of Syria and of Iraq",
             "費薩爾於 1918–1920 年為敘利亞國王，其後於 1921–1933 年為伊拉克國王。英國政府 1921 年底致美方備忘錄提及"
             "「費薩爾國王加冕及阿拉伯內閣之任命」。1933年9月8日去世。",
             "He was King of Syria from 1918 to 1920 and later King of Iraq from 1921 to 1933. A British memorandum of December 1921 "
             "referred to the coronation of King Feisal and the appointment of the Arab cabinet in Mesopotamia. He died on 8 September 1933.",
             [c("loc-faisal", "sources（670 欄，引 Encyc. Brit. 15th ed.）", "was King of Syria from 1918-1920 and later King of Iraq from 1921-1933", "year"),
              c("frus1921v02-d100", "British memorandum, December 30, 1921", "the coronation of King Feisal and the appointment of the Arab cabinet"),
              c("loc-faisal", "sources（670 欄，引 Encyc. Brit. 15th ed.）", "d. Sept. 8, 1933", "day")],
             [R["f1932"]]),
        para(3, "1922-10-10", "day", None, None, "與英國的條約", "Treaties with Britain",
             "英國未將美索不達米亞委任統治書提交國際聯盟，而以與費薩爾國王締結的條約取代，條約載入委任統治的主要條款。"
             "相關文件包括 1922 年 10 月 10 日英伊同盟條約及 1926 年 1 月 13 日英伊條約；英國敕令書將後者題為「伊拉克：與費薩爾國王之條約」。",
             "Instead of submitting the mandate for Mesopotamia to the League of Nations, Britain concluded a treaty with King Feisal "
             "embodying the essential provisions of the mandate. The instruments include the Anglo-Iraq Treaty of Alliance of 10 October 1922 "
             "and the Anglo-Iraq Treaty of 13 January 1926, printed in Cmd. 2587 as 'Iraq, Treaty with King Feisal'.",
             [c("frus1925v02-d188", "London, November 3, 1924，正文", "in its place the treaty of King Feisal was concluded"),
              c("frus1927v02-d753", "Schedule of Documents", "Anglo-Iraq Treaty of Alliance of October 10, 1922", "day"),
              c("frus1927v02-d753", "Schedule of Documents", "Anglo-Iraq Treaty of January 13, 1926", "day"),
              c("frus1927v02-d753", "註腳", "Iraq, Treaty with King Feisal")]),
    ],
    "positions": [],
    "roleCandidates": [
        {"key": "faisal-king-syria", "regimeId": None,
         "organization": {"zh-Hant": "敘利亞（阿拉伯王國）", "en": "Syria"},
         "title": {"orig": TBD, "zh-Hant": "敘利亞國王", "en": "King of Syria"}, "originalPositionKind": None,
         "period": {"start": "1918-01-01", "end": "1920-01-01"}, "startPrecision": "year", "endPrecision": "year",
         "citations": [c("loc-faisal", "sources（670 欄，引 Encyc. Brit. 15th ed.）", "was King of Syria from 1918-1920 and later King of Iraq from 1921-1933", "year")],
         "role_kind": "head_of_state", "reason": "國家元首（國王）任期，依 b0b0e0f 放 roleCandidates；起年有矛盾，見 gaps"},
        {"key": "faisal-king-iraq", "regimeId": "01a193e1-5aab-753a-944f-26fdf8a22cc1",
         "organization": {"zh-Hant": "伊拉克王國", "en": "Kingdom of Iraq"},
         "title": {"orig": "ملك العراق", "zh-Hant": "伊拉克國王", "en": "King of Iraq"}, "originalPositionKind": None,
         "period": {"start": "1921-01-01", "end": "1933-09-08"}, "startPrecision": "year", "endPrecision": "day",
         "citations": [c("loc-faisal", "sources（670 欄，引 Encyc. Brit. 15th ed.）", "was King of Syria from 1918-1920 and later King of Iraq from 1921-1933", "year"),
                       c("loc-faisal", "nonlatinLabels", "فيصل، ملك العراق", lang="ar"),
                       c("loc-faisal", "sources（670 欄，引 Encyc. Brit. 15th ed.）", "d. Sept. 8, 1933", "day"),
                       c("frus1921v02-d100", "British memorandum, December 30, 1921", "the coronation of King Feisal and the appointment of the Arab cabinet")],
         "role_kind": "head_of_state", "reason": "國家元首（國王）任期，依 b0b0e0f 放 roleCandidates；加冕確切日待查證"},
    ],
    "gaps": [
        gap("field:birthDate", "conflict",
            "出生年矛盾：LoC 標目與其所引 Encyc. Brit. 15th ed. 作 1885 年 5 月 20 日；同檔所引 al-Aʻlām 作 1883 年（試跑未評等的 EWB 亦作 1883 年 5 月 20 日）。不選邊",
            [T_BRIT_F, T_ENC_F],
            [c("loc-faisal", "sources（670 欄，引 Encyc. Brit. 15th ed.）", "b. May 20, 1885", "day"),
             c("loc-faisal", "sources（670 欄，引 al-Aʻlām）", "Fayṣal al-Awwal; b. 1883; d. 1933", "year")]),
        gap("field:birthplace", "not_found", "出生地（試跑 EWB 作塔伊夫，未評等）未取得 A／B 原文；待查證", [T_BRIT_F, T_ENC_F]),
        gap("field:nameZh", "not_found", "中文譯名未取得 A／B 來源；待查證", [T_NDL]),
        gap("position:faisal-king-syria", "conflict",
            "敘利亞王位起年：LoC 所引 Encyc. Brit. 作 1918–1920；試跑未評等之 EWB 稱 1920 年宣布為敘利亞國王、同年 7 月遭法國逐出。不選邊；確切起訖日待查證",
            [T_BRIT_F, T_FRUS_F20]),
        gap("position:faisal-king-iraq", "not_found",
            "伊拉克王位起始確切日（加冕日）未取得：FRUS 1921-12-30 備忘錄僅提及已加冕；起點記 1921 年（年精度）", [T_BRIT_F, T_AVALON]),
        gap("paragraph:iraq-reign-details", "not_found",
            "1930 年英伊條約、1932 年加入國際聯盟、石油與軍隊等施政細節未取得 A／B 原文；Avalon 未收英伊條約", [T_AVALON, T_FRUS_F32, T_FRUS_F33]),
        gap("paragraph:early-life", "not_found", "早年（伊斯坦堡受教育、1913 年鄂圖曼議會議員）與阿拉伯起義未取得 A／B 原文；待查證",
            [T_BRIT_F, T_ENC_F]),
    ],
}


def compare(person, ours, mapping):
    """以 ../selection.json 的 5442 records 與本次候選角色逐筆比對（只報告）。mapping：recordId → roleCandidate key 或 None。"""
    sel = json.load(open(HERE.parent / "selection.json"))
    recs = []

    def walk(o):
        if isinstance(o, dict):
            if o.get("bioId") == person["bioId"] and "records" in o:
                recs.extend(o["records"])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(sel)
    by = {x["key"]: x for x in ours}
    out = []
    for r in sorted({r["recordId"]: r for r in recs}.values(), key=lambda r: r["validPeriod"]):
        s, e = r["validPeriod"].strip("[)").split(",")
        k = mapping.get(r["recordId"])
        rc = by.get(k)
        row = {"recordId": r["recordId"], "title5442": r["title"], "start5442": s, "end5442": e, "matchedCandidate": k}
        if not rc:
            row["result"] = "本次未取得 A／B 原文，無法核對（見 gaps）"
        else:
            p = rc["period"]
            row.update({"titleOurs": rc["title"]["zh-Hant"], "startOurs": p["start"], "startPrecisionOurs": rc["startPrecision"],
                        "endOurs": p["end"], "endPrecisionOurs": rc["endPrecision"]})
            diffs = []
            if rc["startPrecision"] == "day":
                diffs.append("起日相同" if p["start"] == s else f"起日不同（5442 {s}／本次 {p['start']}）")
            else:
                diffs.append(f"起點本次僅 {rc['startPrecision']} 精度（{p['start'][:7] if rc['startPrecision'] == 'month' else p['start'][:4]}），5442 {s}"
                             + ("，同月" if p["start"][:7] == s[:7] else "，不同月" if rc["startPrecision"] == "month" else ""))
            if p["end"] is None:
                diffs.append(f"迄日本次未取得（5442 {e}）")
            elif rc["endPrecision"] == "day":
                diffs.append("迄日相同" if p["end"] == e else f"迄日不同（5442 {e}／本次 {p['end']}）")
            else:
                diffs.append(f"迄點本次僅 {rc['endPrecision']} 精度（{p['end']}），5442 {e}")
            row["result"] = "；".join(diffs)
        out.append(row)
    for x in ours:
        if x["key"] not in mapping.values():
            out.append({"recordId": None, "matchedCandidate": x["key"], "titleOurs": x["title"]["zh-Hant"],
                        "startOurs": x["period"]["start"], "endOurs": x["period"]["end"],
                        "result": "5442 無對應 record（新發現任期，只報告，不改庫）"})
    return out


DUAN["recordComparison"] = compare(DUAN, DUAN["roleCandidates"], {
    R["d1913"]: None, R["d1916a"]: "duan-premier-1916-apr", R["d1916b"]: "duan-premier-1916-jun",
    R["d1917"]: "duan-premier-1917-jul", R["d1918"]: None})
DUAN["recordComparison"][1]["titleNote"] = "職稱差異：5442 作「國務卿」；FRUS 1916-04-24 電報英文作 Premier（中文原職稱未取得，不選邊）"
FAISAL["recordComparison"] = compare(FAISAL, FAISAL["roleCandidates"], {R["f1932"]: "faisal-king-iraq"})
FAISAL["recordComparison"][0]["titleNote"] = "職稱一致（King of Iraq）；5442 依選人說明只收 1932-10-03 獨立後，本次來源起於 1921 年"


def nfc(s):
    return unicodedata.normalize("NFC", s)


def check(doc):
    errs = []

    def walk(o, path):
        if isinstance(o, dict):
            if "quote" in o and "sourceKey" in o:
                q = o["quote"]
                if q != nfc(q):
                    errs.append(f"{path}：引文非 NFC")
                if not q or len(nfc(q)) > 80:
                    errs.append(f"{path}：引文長度 {len(nfc(q or ''))}")
                if o["sourceKey"] not in doc["sources"]:
                    errs.append(f"{path}：未知來源 {o['sourceKey']}")
                for k in ("locator", "accessedOn", "grade"):
                    if not o.get(k):
                        errs.append(f"{path}：缺 {k}")
            for k, v in o.items():
                walk(v, f"{path}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{path}[{i}]")
    walk(doc, "$")
    for p in doc["people"]:
        for x in p["positions"]:
            if x["positionKind"] in ("head_of_state", "head_of_government", "de_facto_leader", "party"):
                errs.append(f"{p['key']} {x['key']}：positionKind 不可為 {x['positionKind']}")
        for x in p["roleCandidates"]:
            if "roleKind" in x or "candidateRoleKind" in x:
                errs.append(f"{p['key']} {x['key']}：須用 role_kind")
        for k, f in p["fields"].items():
            if f["value"] not in (TBD, "不適用") and not f["citations"]:
                errs.append(f"{p['key']} field {k}：有值但無出處")
    raw = Path(RAW_DIR)
    if raw.exists():  # 有原文時另做逐字核對（verify.py 亦會做）
        import re
        texts = {k: re.sub(r"\s+", " ", nfc((raw / f).read_text(encoding="utf-8"))) for k, f in doc_rawmap.items() if (raw / f).exists()}

        def walk2(o):
            if isinstance(o, dict):
                if "quote" in o and "sourceKey" in o and o["sourceKey"] in texts:
                    if re.sub(r"\s+", " ", nfc(o["quote"])).strip() not in texts[o["sourceKey"]]:
                        errs.append(f"引文未逐字出現於 {o['sourceKey']}：{o['quote']}")
                for v in o.values():
                    walk2(v)
            elif isinstance(o, list):
                for v in o:
                    walk2(v)
        walk2(doc)
    return errs


doc_rawmap = {k: v["_raw"] for k, v in sorted(SOURCES.items())}
doc = {
    "batch": "b3-trial-supplement-duan-faisal", "researchedOn": ACC, "policyVersion": POL,
    "schemaNote": "結構依 ARCHITECTURE §16.2／§16.3／§16.4.1／§16.4.2，並對齊 b0b0e0f（positions.positionKind、roleCandidates.role_kind）。"
                  "fields 為本補查另加之生平欄位（姓名、生卒、出生地、黨派、簡介），每欄附出處或「待查證」；recordComparison 為與 5442 既有任期的逐筆比對（只報告）。",
    "rawDir": RAW_DIR, "rawMap": "rawmap.json",
    "sources": {k: {kk: vv for kk, vv in v.items() if kk != "_raw"} for k, v in sorted(SOURCES.items())},
    "people": [DUAN, FAISAL],
    "alignedTo": "b0b0e0f",
    "alignNote": "Tai 2026-11-11 12:12 第 5 項補查，直接以 b0b0e0f 對齊格式產生：經歷層用 positionKind；元首／首腦任期放 roleCandidates（role_kind）；"
                 "黨職一律 de_facto_leader 候選（本次兩人皆無取得出處之黨職）。由 build.py 產生，未寫庫。",
}

if __name__ == "__main__":
    errs = check(doc)
    if errs:
        print("\n".join(errs)); sys.exit(1)
    (HERE / "research.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (HERE / "rawmap.json").write_text(json.dumps(doc_rawmap, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for p in doc["people"]:
        print(p["key"], len(p["paragraphs"]), "段", len(p["positions"]), "職位", len(p["roleCandidates"]), "候選角色", len(p["gaps"]), "gaps")
    print("ok")
