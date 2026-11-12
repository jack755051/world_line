#!/usr/bin/env python3
"""把網域歸類補進 run100/source-kind-overrides.json（寫庫腳本與 full/dryrun_full.py 共用）。可重跑：已存在且值相同就不動，值不同就中止。

依據：ARCHITECTURE §16 T1（A＝官方檔案、國家級傳記辭典、權威機構人名權威；B＝學術專書、具名作者／學術機構百科）。
歸類由 World Line 主管 2026-11-11 21:55 決定（Tai 授權範圍內）；之後新遇到的網域照同一原則加進 POLICY 並在報告列出；個人網站不收（值 null＝放棄）。
grade 不在 overrides（寫庫腳本取 seed citation 的 grade）；本腳本另輸出 domain-policy.json 供 dry-run 核對 seed grade 與政策是否一致。
用法：python3 -I data/seed/leaders/b3-trial/full/patch_source_kinds.py
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OVR = HERE.parent / "run100" / "source-kind-overrides.json"
POLICY = [  # (domain, source_kind, grade, 依據, 決定)
    ("lobid.org", "official_website", "A", "GND（德國國家圖書館人名權威檔）的官方鏡像；T1 權威機構人名權威", "主管 2026-11-11 21:55"),
    ("www.nids.mod.go.jp", "official_history", "A", "日本防衛省防衛研究所戰史研究中心（官方戰史）", "主管 2026-11-11 21:55"),
    ("www.dhm.de", "encyclopedia", "B", "Deutsches Historisches Museum LeMO 傳記（學術機構傳記）", "主管 2026-11-11 21:55"),
    ("millercenter.org", "encyclopedia", "B", "Miller Center, University of Virginia 總統傳記（學術機構傳記）", "主管 2026-11-11 21:55"),
    ("ebsco.com", "encyclopedia", "B", "EBSCO Research Starters（具名作者百科條目）", "主管 2026-11-11 21:55"),
    ("www.ebsco.com", "encyclopedia", "B", "EBSCO Research Starters（同上；batch003 來源用 www 主機名，寫庫腳本以完整主機名比對）", "主管 2026-11-11 21:55（同一網域補主機名）"),
    ("id.ndl.go.jp", "official_website", "A", "國立國會圖書館典據 Web NDL Authorities；T1 權威機構人名權威", "主管 2026-11-12 03:03"),
    ("ndl.go.jp", "official_website", "A", "日本國立國會圖書館官方頁（含近代日本人の肖像）", "主管 2026-11-12 03:03"),
    ("www.ndl.go.jp", "official_website", "A", "日本國立國會圖書館同上（www 主機名）", "主管 2026-11-12 03:03"),
    ("jacar.go.jp", "official_history", "A", "國立公文書館アジア歴史資料センター（JACAR）官方檔案", "主管 2026-11-12 03:03"),
    ("www.jacar.go.jp", "official_history", "A", "JACAR 同上（www 主機名）", "主管 2026-11-12 03:03"),
    ("jacar.archives.go.jp", "official_history", "A", "JACAR 官方檔案（archives.go.jp 主機）", "主管 2026-11-12 03:03"),
    ("nids.mod.go.jp", "official_history", "A", "日本防衛省防衛研究所戰史（無 www 主機名；www 已於 21:55 列入）", "主管 2026-11-11 21:55（同一網域補主機名）／主管 2026-11-12 03:03 確認"),
    ("kotobank.jp", "encyclopedia", "B", "Kotobank 具名條目：日本大百科全書、國史大辭典、世界大百科事典", "主管 2026-11-12 03:03"),
    ("www.kotobank.jp", "encyclopedia", "B", "Kotobank 同上（www 主機名）", "主管 2026-11-12 03:03"),
    # 英語國家將領（主管 2026-11-12 06:32）；主機名皆於 2026-11-12 06:3x 以一般 HTTPS（未用 -k）確認存在
    ("www.archives.gov", "archive", "A", "美國國家檔案館 NARA 官方頁（含總統圖書館 NARA 頁）", "主管 2026-11-12 06:32"),
    ("archives.gov", "archive", "A", "NARA 同上（無 www 主機名）", "主管 2026-11-12 06:32"),
    ("catalog.archives.gov", "archive", "A", "NARA 線上目錄（National Archives Catalog）", "主管 2026-11-12 06:32"),
    ("www.nationalarchives.gov.uk", "archive", "A", "英國國家檔案館（The National Archives）官方頁", "主管 2026-11-12 06:32"),
    ("nationalarchives.gov.uk", "archive", "A", "英國國家檔案館同上（無 www 主機名）", "主管 2026-11-12 06:32"),
    ("discovery.nationalarchives.gov.uk", "archive", "A", "英國國家檔案館 Discovery 目錄", "主管 2026-11-12 06:32"),
    ("history.army.mil", "official_history", "A", "美國陸軍軍史中心（U.S. Army Center of Military History）官方戰史", "主管 2026-11-12 06:32"),
    ("www.history.navy.mil", "official_history", "A", "美國海軍歷史與遺產司令部（NHHC）官方戰史", "主管 2026-11-12 06:32"),
    ("www.afhra.af.mil", "official_history", "A", "美國空軍歷史研究署（AFHRA）官方戰史", "主管 2026-11-12 06:32"),
    ("www.usmcu.edu", "official_history", "A", "美國陸戰隊大學（含 Marine Corps History Division）官方史料", "主管 2026-11-12 06:32"),
    ("www.raf.mod.uk", "official_history", "A", "英國皇家空軍官方網站（國防部，含官方歷史頁）", "主管 2026-11-12 06:32"),
    ("www.thegazette.co.uk", "official_website", "A", "The London Gazette 官方公報（任命公告）", "主管 2026-11-12 06:32"),
    ("www.oxforddnb.com", "encyclopedia", "B", "Oxford Dictionary of National Biography（訂閱制；只用公開摘要／首段，不登入）", "主管 2026-11-12 06:32"),
    ("oxforddnb.com", "encyclopedia", "B", "ODNB 同上（無 www 主機名）", "主管 2026-11-12 06:32"),
    ("www.anb.org", "encyclopedia", "B", "American National Biography（訂閱制；只用公開摘要／首段，不登入）", "主管 2026-11-12 06:32"),
    ("anb.org", "encyclopedia", "B", "ANB 同上（無 www 主機名）", "主管 2026-11-12 06:32"),
    ("academic.oup.com", "encyclopedia", "B", "OUP Academic：ODNB／ANB 現轉址主機（只限 /oxford-dictionary-of-national-biography、/american-national-biography 的公開內容）", "主管 2026-11-12 06:32"),
    ("www.nam.ac.uk", "encyclopedia", "B", "National Army Museum（英國國家陸軍博物館，具名機構）", "主管 2026-11-12 06:32"),
    # 禁用（source_kind None＝寫庫腳本 DROP；grade X）：主管 2026-11-12 22:08 套用 Tai 既有「個人網站不收」
    ("generals.dk", None, "X", "個人網站（Steen Ammentorp 個人經營的將領資料庫）；具名 C 須為具名作者或機構的正當出版物，個人網站不收", "主管 2026-11-12 22:08"),
    ("www.generals.dk", None, "X", "generals.dk 同上（www 主機名）", "主管 2026-11-12 22:08"),
]

# 具名 C 級（Tai 本人 2026-11-12 06:34「將領生平來源放寬到具名 C 級」）：依每一頁的具名作者／具名出版機構判定，
# 不用網域白名單，所以不進 POLICY；規則另輸出 grade-c-policy.json，verify.py 對將領生平檔同步檢查。
GRADE_C = {
    "decision": "Tai 本人 2026-11-12 06:34（World Line 主管轉達）：將領生平來源放寬到具名 C 級",
    "scope": "只限將領生平（data/seed/leaders/generals-roster/bios；research.json 頂層 gradePolicy=ABC-2026-11-12）；B3 其他檔仍只收 A／B",
    "rule": "C＝具名作者或具名機構的正當出版物（主管 2026-11-12 22:08 重申；個人網站不算）（報紙／通訊社、大學、博物館、具名作者或出版者的軍事史網站、一般出版社書籍）；逐頁判定，sources.authors 或 publisher 至少一項非空，gradeBasis 寫出具名者",
    "always_forbidden": ["Wikipedia 及任何維基類（Wikiwand、Fandom 等）", "Wikidata", "百度", "無署名內容", "AI 生成內容站", "論壇／討論區／問答站", "部落格", "個人網站（除非由具名機構發布）", "generals.dk（個人網站；主管 2026-11-12 22:08 明列禁用）"],
    "banned_domains": [{"domain": "generals.dk", "decision": "主管 2026-11-12 22:08", "basis": "個人網站；具名 C＝具名作者或機構的正當出版物", "effective": "verify.py／apply_refill.py：生效後新增的來源一律擋；既有已 commit 引用暫不改，REFILL_REPORT 列待替換"}],
    "source_kind_hint": {"報紙／通訊社": "news", "大學／博物館": "official_website 或 encyclopedia（依頁面性質）", "軍事史網站": "encyclopedia"},
    "minimum_standard": "可只靠 C 達成 v3 最低標準；不可因缺 A／B 標來源不足",
    "t14": "T14 R2–R4 門檻（1 筆 A 或 2 筆獨立 B）不變；只有 C 支持者留 positions（必要時 R6 roleGap=source）",
    "db_note": "write_b3_paragraphs.py 目前會丟棄 grade 非 A/B 的 citation；寫庫前須由 Tai 決定 C 級如何入庫（不在本次範圍，未改）",
}

def main():
    ovr = json.loads(OVR.read_text(encoding="utf-8"))
    added = []
    for dom, kind, grade, basis, dec in POLICY:
        if dom in ovr:
            if ovr[dom] != kind:
                sys.exit(f"{dom} 已存在且值不同：{ovr[dom]!r} ≠ {kind!r}")
            continue
        ovr[dom] = kind; added.append(dom)
    OVR.write_text(json.dumps(dict(sorted(ovr.items())), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (HERE / "domain-policy.json").write_text(json.dumps([{"domain": d, "source_kind": k, "grade": g, "basis": b, "decision": x} for d, k, g, b, x in POLICY],
                                                      ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (HERE / "grade-c-policy.json").write_text(json.dumps(GRADE_C, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("added:", added or "none", "total overrides:", len(ovr))

if __name__ == "__main__":
    main()
