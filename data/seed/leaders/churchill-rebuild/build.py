#!/usr/bin/env python3
"""邱吉爾補建（Tai 2026-11-11 09:30 決定；只產出待寫資料，不寫庫）。

讀當天抓下的原始頁面文字（/tmp/churchill-raw/*.txt，不進版控），逐筆檢查引文後產生：
  research.json      gap-830 P 格式＋B3 頂層 sources／sourceKey（§16.3.2 第 4、5 點）
  pending-write.json 寫入 API／SQL 的待寫內容（未送出）
  verify-report.json 檢查結果與原始頁面 sha256

檢查（不連 DB、不連網）：
  - 每筆引文 NFC 後 ≤ 80 字元，且逐字出現在原始頁面（空白連續者視為一個空格）；
  - 來源網域不在硬性排除清單（wikipedia／wikidata／baidu／enciclopediadelecuador）；
  - 每個有值欄位（nameZh 除外）至少一筆 A／B citation；任期至少 1 筆 A；
  - 日期格式、卒日晚於生日、任期迄日晚於起日、迄日不晚於地圖範圍終點 1945-10-01。
任何一項不過就不輸出、以非 0 結束。

用法：python3 -I build.py [--raw /tmp/churchill-raw]
"""
import argparse, hashlib, json, os, re, sys, unicodedata
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
ACCESSED = "2026-11-11"
POLICY = "bio-2026-11-v0"
BANNED = ("wikipedia.org", "wikidata.org", "baidu.com", "enciclopediadelecuador.com")
MAP_END = "1945-10-01"           # 地圖範圍半開終點（範圍 1908-01-01～1945-09-30）
UK_REGIME = "01a18e71-cba5-7726-90e3-9b90ab344afd"   # 5442 regimes.slug = united-kingdom（唯讀查得）

SOURCES = {
    "govuk-churchill": {
        "raw": "govuk.txt", "grade": "A", "gradeWhy": "政府官方傳記頁",
        "title": "Sir Winston Churchill — History of Sir Winston Churchill (Past Prime Ministers)",
        "publisher": "GOV.UK (Prime Minister's Office, 10 Downing Street)",
        "url": "https://www.gov.uk/government/history/past-prime-ministers/winston-churchill",
        "sourceKind": "official_history", "licenseCode": None,
    },
    "hansard-churchill": {
        "raw": "hansard.txt", "html": "hansard.html", "grade": "A", "gradeWhy": "議會官方紀錄",
        "title": "Mr Winston Churchill (Hansard 1803–2005, People)",
        "publisher": "UK Parliament (Historic Hansard)",
        "url": "https://api.parliament.uk/historic-hansard/people/mr-winston-churchill/index.html",
        "sourceKind": "official_record", "licenseCode": None,
    },
    "nobel-churchill": {
        "raw": "nobel.txt", "grade": "B", "gradeWhy": "機構傳記、無具名作者，保守評 B（同 b3-sample）",
        "title": "Winston Churchill – Biographical (Nobel Prize in Literature 1953)",
        "publisher": "Nobel Foundation (NobelPrize.org)",
        "url": "https://www.nobelprize.org/prizes/literature/1953/churchill/biographical/",
        "sourceKind": "official_history", "licenseCode": None,
    },
}


def c(key, locator, quote, note=None, prec=None):
    return {"sourceKey": key, "locator": locator, "quote": quote, "quoteLang": "en",
            "evidenceNote": note, "accessedOn": ACCESSED, "grade": SOURCES[key]["grade"],
            "datePrecision": prec, "policyVersion": POLICY}


PERSON = {
    "key": "gb-winston-churchill",
    "bioId": None,  # 庫中無有效生平；寫入後由 API 回傳新 id
    "groupKeys": ["winston churchill"],
    "recordIds": [],  # 庫中無有效任期可連；新任期見 newRecords
    "recordNameVariants": ["Winston Churchill"],
    "wikidataQid": None,
    "name": {"value": "Winston Churchill", "sources": [
        # 引文＝頁面 <h1> 逐字文字（不是 <title>「Mr Winston Churchill (Hansard)」）；main() 另核對 <h1>
        c("hansard-churchill", "Page heading", "Mr Winston Churchill")]},
    "nameZh": {"value": "溫斯頓·邱吉爾", "sources": [],
               "note": "沿用 5442 已撤回任期 01a19efa-769a-… 與 b3-sample 的中文名；無來源（前端顯示待補來源）；"
                       "Tai 2026-11-11 10:13 決定無出處保留"},
    "birthDate": {"value": "1874-11-30", "precision": "day", "sources": [
        c("govuk-churchill", "Fact box: Born", "30 November 1874, Blenheim Palace, Oxfordshire", prec="day")]},
    "deathDate": {"value": "1965-01-24", "precision": "day", "sources": [
        c("govuk-churchill", "Fact box: Died", "24 January 1965, London", prec="day"),
        c("hansard-churchill", "Life dates under name", "1874 - January 24, 1965", prec="day"),
        c("nobel-churchill", "Closing line of biography", "Winston Churchill died on January 24, 1965.", prec="day")]},
    "birthPlace": {"value": {"zh-Hant": "牛津郡布倫亨宮", "en": "Blenheim Palace, Oxfordshire"}, "sources": [
        c("govuk-churchill", "Fact box: Born", "30 November 1874, Blenheim Palace, Oxfordshire")]},
    "party": {"value": {"zh-Hant": "保守黨", "en": "Conservative Party"}, "sources": [
        c("govuk-churchill", "Subtitle under page heading", "Conservative 1940 to 1945, 1951 to 1955",
          note="來源把保守黨限定在兩次首相任期（1940–45、1951–55）；同頁傳記另述 1904 年轉入自由黨、戰間期再回保守黨，"
               "故此值只代表首相任內黨籍，不代表一生（Tai 2026-11-11 10:13 決定）"),
        c("govuk-churchill", "Fact box: Political party", "Conservative",
          note="Fact box 只寫 Conservative；此值只代表首相任內黨籍（1940–45、1951–55），不代表一生"
               "（1904 轉自由黨、戰間期回保守黨；Tai 2026-11-11 10:13 決定）")]},
    "summary": {"value": {
        "zh-Hant": "英國保守黨政治人物，1940年至1945年及1951年至1955年兩度出任首相；1965年逝世並獲國葬。",
        "en": "British Conservative politician who served twice as Prime Minister, 1940–1945 and 1951–1955; "
              "he died in 1965 and was given a state funeral."}, "sources": [
        c("govuk-churchill", "Subtitle under page heading", "Conservative 1940 to 1945, 1951 to 1955"),
        c("govuk-churchill", "Fact box: Dates in office", "1940 to 1945, 1951 to 1955"),
        c("govuk-churchill", "Biography, last paragraph", "Churchill died in 1965, and was honoured with a state funeral.")]},
    "portrait": None,
    "conflicts": [],
    "unverified": [
        {"field": "wikidataQid", "clue": "本次未查 Wikidata",
         "why": "只當線索、非必要；留 null，不憑記憶填（Tai 2026-11-11 10:13 決定 null）"},
        {"field": "portrait", "clue": "Commons 檔案頁",
         "why": "本次未查授權模板，依規則留 null（Tai 2026-11-11 10:13 決定 null）"},
        {"field": "deathPlace", "clue": "GOV.UK Fact box: Died「24 January 1965, London」",
         "why": "CreateLeaderBioRequest 沒有 deathPlace 欄（DB 有 death_place）；Tai 2026-11-11 10:13 決定這次不寫、"
                "不另寫 death_place SQL（超出計畫），待 API 支援再補"},
        {"field": "record:gb-churchill-pm-1940 split 1945-05-23",
         "clue": "1945-05-23 聯合內閣結束、組看守內閣；既有資料把麥克唐納 1929–31／1931–35 依內閣拆筆",
         "why": "手上 A 級來源（Hansard、GOV.UK）只給一段連續任期，無來源支撐拆點；Tai 2026-11-11 10:13 決定只建一筆 "
                "[1940-05-10,1945-07-26)，拆點待查證（需 Commons Library 名錄等來源，目前被防機器人擋）"},
    ],
    "newRecords": [{
        "key": "gb-churchill-pm-1940",
        "regimeId": UK_REGIME, "regimeSlug": "united-kingdom",
        "role": "head_of_government", "title": "Prime Minister",
        "name": "Winston Churchill", "nameZh": "溫斯頓·邱吉爾",
        "validFrom": "1940-05-10", "validTo": "1945-07-26",   # 半開：最後在任日 1945-07-25
        "startPrecision": "day", "endPrecision": "day",
        "originalEndDate": "1945-07-26",
        "originalEndNote": "原始卸任日 1945-07-26（Hansard 閉區間最後在任日 July 25, 1945 → 半開終點 1945-07-26）；"
                           "早於地圖範圍終點 1945-10-01，不需截斷",
        "verified": True,
        "source": "UK Parliament, Historic Hansard, «Mr Winston Churchill», Offices: Prime Minister, "
                  "May 10, 1940 - July 25, 1945（另見 GOV.UK Past Prime Ministers：1940 to 1945）",
        "sourceUrl": "https://api.parliament.uk/historic-hansard/people/mr-winston-churchill/index.html",
        "citations": [
            c("hansard-churchill", "Offices: Prime Minister (first entry)", "May 10, 1940 - July 25, 1945",
              note="Hansard 寫閉區間（含 7 月 25 日）；依半開區間存為 [1940-05-10,1945-07-26)", prec="day"),
            c("govuk-churchill", "Fact box: Dates in office", "1940 to 1945, 1951 to 1955",
              note="只支撐到年；1951–55 屬範圍外任期，依 Q4 不建紀錄", prec="year"),
        ],
    }],
}


DECIDED = "Tai 2026-11-11 10:13（Asia/Taipei，經 World Line 主管轉達）：6 項全照史料考證建議"
DECISIONS = [
    {"no": 1, "item": "任期拆筆", "decision": "只建一筆 [1940-05-10,1945-07-26)，不拆 1945-05-23 看守內閣；拆點記待查證"},
    {"no": 2, "item": "職銜", "decision": "Prime Minister（照 Hansard）"},
    {"no": 3, "item": "黨派", "decision": "Conservative；evidenceNote 註明只代表首相任內黨籍"},
    {"no": 4, "item": "卒地", "decision": "這次不寫，記在 research.json unverified；不寫任何 death_place SQL（超出計畫）"},
    {"no": 5, "item": "b3-sample 連結", "decision": "寫庫後另開 commit 補 b3-sample 邱吉爾 bioId／relatedRecordIds；"
                                                   "寫入第一、二階段都不改 b3-sample"},
    {"no": 6, "item": "nameZh／wikidataQid／照片", "decision": "nameZh 無出處保留；wikidataQid 與照片 null"},
]


def norm(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s)).strip()


def h1_text(html):
    """頁面第一個 <h1> 的純文字（去標籤、空白合併）。"""
    m = re.search(r"<h1\b[^>]*>(.*?)</h1>", html, re.S | re.I)
    return norm(re.sub(r"<[^>]+>", "", m.group(1))) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="/tmp/churchill-raw")
    a = ap.parse_args()
    errs, raw, sha, quotes, h1 = [], {}, {}, [], {}
    for k, s in SOURCES.items():
        host = urlparse(s["url"]).hostname or ""
        if any(host == b or host.endswith("." + b) for b in BANNED):
            errs.append(f"{k}: 硬性排除網域 {host}")
        path = os.path.join(a.raw, s["raw"])
        data = open(path, "rb").read()
        sha[k] = hashlib.sha256(data).hexdigest()
        raw[k] = norm(data.decode("utf-8"))
        if s.get("html"):
            hdata = open(os.path.join(a.raw, s["html"]), "rb").read()
            sha[k + ":html"] = hashlib.sha256(hdata).hexdigest()
            h1[k] = h1_text(hdata.decode("utf-8"))

    def check_cits(where, cits, need_a=False):
        if not cits:
            errs.append(f"{where}: 沒有 citation")
        if need_a and not any(x["grade"] == "A" for x in cits):
            errs.append(f"{where}: 沒有 A 級來源")
        if not need_a and cits and not (any(x["grade"] == "A" for x in cits)
                                        or len({x["sourceKey"] for x in cits if x["grade"] == "B"}) >= 2):
            errs.append(f"{where}: 未達 1 A 或 2 獨立 B")
        for x in cits:
            q = unicodedata.normalize("NFC", x["quote"])
            quotes.append({"where": where, "sourceKey": x["sourceKey"], "len": len(q), "quote": q})
            if len(q) > 80:
                errs.append(f"{where}: 引文超過 80 字元（{len(q)}）")
            if norm(q) not in raw[x["sourceKey"]]:
                errs.append(f"{where}: 引文未逐字出現在 {x['sourceKey']}：{q}")
            if x["locator"] == "Page heading":
                # locator 指頁面標題時，引文必須逐字等於該頁 <h1>（不可拿 <title> 充當）
                if x["sourceKey"] not in h1:
                    errs.append(f"{where}: locator=Page heading 但 {x['sourceKey']} 沒有 html 可核對 <h1>")
                elif norm(q) != h1[x["sourceKey"]]:
                    errs.append(f"{where}: 引文與 <h1>「{h1[x['sourceKey']]}」不符：{q}")
                else:
                    quotes[-1]["h1Match"] = True

    p = PERSON
    for f in ("name", "birthDate", "deathDate", "birthPlace", "party", "summary"):
        if p[f] and p[f].get("value"):
            check_cits(f"field:{f}", p[f]["sources"])
    for f in ("birthDate", "deathDate"):
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", p[f]["value"]):
            errs.append(f"{f}: 日期格式")
    if p["deathDate"]["value"] <= p["birthDate"]["value"]:
        errs.append("卒日不晚於生日")
    for r in p["newRecords"]:
        check_cits(f"record:{r['key']}", r["citations"], need_a=True)
        if not (r["validFrom"] < r["validTo"] <= MAP_END):
            errs.append(f"record:{r['key']}: 起訖不合（需起<迄≤{MAP_END}）")
    zh = p["summary"]["value"]["zh-Hant"]
    if len(unicodedata.normalize("NFC", zh)) > 400:
        errs.append("summary 中文超過 400 字")

    if p.get("deathPlace"):
        errs.append("不得寫 death_place（Tai 決定 ④）")
    if p["wikidataQid"] is not None or p["portrait"] is not None:
        errs.append("wikidataQid／portrait 必須為 null（Tai 決定 ⑥）")
    if len(p["newRecords"]) != 1 or p["newRecords"][0]["title"] != "Prime Minister":
        errs.append("任期只建一筆、title=Prime Minister（Tai 決定 ①②）")

    report = {"ok": not errs, "errors": errs, "quoteCount": len(quotes),
              "maxQuoteLen": max(q["len"] for q in quotes), "rawSha256": sha, "h1": h1, "quotes": quotes}
    with open(os.path.join(HERE, "verify-report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1); fh.write("\n")
    if errs:
        print("✗", *errs, sep="\n  "); sys.exit(1)

    sources_out = {k: {x: v for x, v in s.items() if x not in ("raw", "html")} | {"accessedOn": ACCESSED}
                   for k, s in SOURCES.items()}
    research = {"batch": "churchill-rebuild", "researchedOn": ACCESSED,
                "decidedBy": "Tai 2026-11-11 09:30（Asia/Taipei）：照 gap-830 流程補建，寫庫前回報 Tai",
                "decisions": {"decidedBy": DECIDED, "items": DECISIONS},
                "sources": sources_out, "people": [p], "staging": []}
    with open(os.path.join(HERE, "research.json"), "w", encoding="utf-8") as fh:
        json.dump(research, fh, ensure_ascii=False, indent=1); fh.write("\n")

    # 待寫內容：步驟 1–3 走 5052 API（同 send_batch.py），步驟 4 走 SQL（API 不收 quote／grade／leader_record_citations）
    bio_cits = [{"field": f, "sourceKey": x["sourceKey"], "locator": x["locator"],
                 "evidenceNote": x["evidenceNote"] or x["quote"], "accessedOn": x["accessedOn"],
                 "quote": x["quote"], "quoteLang": x["quoteLang"], "grade": x["grade"],
                 "datePrecision": x["datePrecision"], "policyVersion": x["policyVersion"]}
                for f in ("name", "birthDate", "deathDate", "birthPlace", "party", "summary")
                for x in p[f]["sources"]]
    rec = p["newRecords"][0]
    pending = {
        "status": "pending — 未寫庫；Tai 2026-11-11 10:13 已核准內容與寫入本機開發庫 5052（試跑、備份後才寫，不 push）",
        "decisions": {"decidedBy": DECIDED, "items": DECISIONS},
        "target": {"api": "http://127.0.0.1:5052/api/v1", "db": "worldline_borders_dev（5442）"},
        "step1_sources": [{"sourceKey": k, "request": {"sourceKind": s["sourceKind"], "title": s["title"],
                                                        "publisher": s["publisher"], "url": s["url"],
                                                        "licenseCode": s["licenseCode"]}}
                          for k, s in SOURCES.items()],
        "step2_leaderBio": {"request": {
            "name": p["name"]["value"], "nameZh": p["nameZh"]["value"], "isTest": False,
            "birthDate": p["birthDate"]["value"], "birthDatePrecision": "day",
            "deathDate": p["deathDate"]["value"], "deathDatePrecision": "day",
            "birthPlace": p["birthPlace"]["value"], "party": p["party"]["value"], "summary": p["summary"]["value"],
            "citations": [{"field": x["field"], "sourceId": "<step1:" + x["sourceKey"] + ">", "locator": x["locator"],
                           "evidenceNote": x["evidenceNote"], "accessedOn": x["accessedOn"]} for x in bio_cits]}},
        "step3_leaderRecord": {"request": {
            "regimeId": rec["regimeId"], "name": rec["name"], "nameZh": rec["nameZh"], "role": rec["role"],
            "title": rec["title"], "validFrom": rec["validFrom"], "validTo": rec["validTo"],
            "source": rec["source"], "sourceUrl": rec["sourceUrl"], "verified": True,
            "personId": "<step2:bioId>"}, "originalEndDate": rec["originalEndDate"],
            "originalEndNote": rec["originalEndNote"]},
        "step4_sql": {
            "leader_bio_field_citations_update": [
                {"match": {"bio_id": "<step2:bioId>", "field": x["field"], "source_id": "<step1:" + x["sourceKey"] + ">",
                           "locator": x["locator"], "evidence_note": x["evidenceNote"]},
                 "set": {"quote": x["quote"], "quote_lang": x["quoteLang"], "grade": x["grade"],
                         "date_precision": x["datePrecision"], "policy_version": x["policyVersion"]}}
                for x in bio_cits],
            "leader_record_citations_insert": [
                {"record_id": "<step3:recordId>", "source_id": "<step1:" + x["sourceKey"] + ">", "locator": x["locator"],
                 "quote": x["quote"], "quote_lang": x["quoteLang"], "evidence_note": x["evidenceNote"],
                 "accessed_on": x["accessedOn"], "grade": x["grade"], "date_precision": x["datePrecision"],
                 "policy_version": x["policyVersion"]} for x in rec["citations"]]},
        "doNotTouch": {"retractedTestBios": ["01a19efa-758c-718a-b1ec-27916469f239",
                                             "01a19ef6-b466-7e2e-94e1-8ec3c0e5ac10",
                                             "01a19ef9-1c0b-781a-911b-adc230abbeaf"],
                       "retractedRecord": "01a19efa-769a-7615-9705-89c66d803905"},
    }
    with open(os.path.join(HERE, "pending-write.json"), "w", encoding="utf-8") as fh:
        json.dump(pending, fh, ensure_ascii=False, indent=1); fh.write("\n")
    print(f"✓ ok：{len(quotes)} 筆引文（最長 {report['maxQuoteLen']} 字元）；"
          f"sources {len(SOURCES)}、bio 1、bio citations {len(bio_cits)}、record 1、record citations {len(rec['citations'])}")


if __name__ == "__main__":
    main()
