#!/usr/bin/env python3
"""
德國領導人紀錄 seed（1908–1945）。
涵蓋：German Empire（德意志帝國）與 Deutsches Reich（威瑪共和／第三帝國）
      的國家元首（head_of_state）與政府首腦（head_of_government）。

只寫入開發庫（127.0.0.1:5052），拒絕送到 5051。

用法：
  python3 send_leaders.py [--dry-run]                          # 列出不送出（預設即為 dry-run）
  python3 send_leaders.py --send [--base URL] [--env FILE]     # 真的寫入
"""
import argparse, json, os, sys, urllib.request, urllib.error
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))

ap = argparse.ArgumentParser()
ap.add_argument("--send",    action="store_true", help="真的送出（預設 dry-run）")
ap.add_argument("--dry-run", action="store_true", help="明確指定 dry-run（不送出）")
ap.add_argument("--base",    default="http://127.0.0.1:5052")
ap.add_argument("--env",     default=os.path.join(HERE, "../../../.env"))
ap.add_argument("--ids",     default=os.path.join(HERE, "sent-leaders.json"),
                help="已送出的 id 對照表（_id → UUID）")
a = ap.parse_args()

if a.send and a.base.rstrip("/").endswith(":5051"):
    sys.exit("拒絕：5051 是正式 appdb_ww2；這批只寫入開發庫。")

dry = a.dry_run or (not a.send)

def api_key():
    if not os.path.exists(a.env):
        sys.exit(f"找不到 env 檔：{a.env}")
    for line in open(a.env, encoding="utf-8"):
        if line.startswith("WORLDLINE_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit("找不到 WORLDLINE_API_KEY")

# ─── regimeId（由 GET /api/v1/sovereignty?date=<date> 查得，對照 send_capitals.py）
GERMAN_EMPIRE   = "01a192dc-6440-7b84-ad59-f7836508ef72"  # slug: german-empire
DEUTSCHES_REICH = "01a18e71-c9ba-719c-bc51-3086edef89bc"  # slug: deutsches-reich

# ─── 領導人紀錄資料 ────────────────────────────────────────────────────────────
# validFrom/validTo 採 API 的半開區間慣例 [start, end)：
#   - 同政權同職位日期不得重疊
#   - 前後任交接：前任 validTo = 後任 validFrom（無縫銜接）
#   - 無後繼者時 validTo = 政權/政府實際終止日（排他邊界）
# note 欄位僅本地存檔，不送至 API（CreateLeaderRecordRequest 無此欄位）。
RECORDS = [

    # ═══════════════════════════════════════════════════════════════════════════
    # 國家元首 head_of_state ── German Empire（德意志帝國）
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "_id":       "LS_HOS_GERMAN_EMPIRE_WILHELM_II",
        "regimeId":  GERMAN_EMPIRE,
        "name":      "Wilhelm II",
        "nameZh":    "威廉二世",
        "role":      "head_of_state",
        "title":     "Deutscher Kaiser und König von Preußen",
        "validFrom": "1908-01-01",
        "validTo":   "1918-11-09",
        "source":    "Verfassung des Deutschen Reiches, 16. April 1871, Art. 11 — Kaiser als Oberhaupt; Abdankungserklärung Wilhelms II., 9. November 1918 (veröffentlicht durch Reichskanzler Max von Baden). Vgl. Röhl, John C. G.: Wilhelm II. Der Weg in den Abgrund 1900–1941, München 2008.",
        "verified":  True,
        "note":      "1908-01-01 為本批起點，非即位日（1888-06-15）。空檔 1918-11-09～1919-02-11：Rat der Volksbeauftragten 集體執政，無單一正式 Reichspräsident；略去此段並於 Ebert 記錄中附注。",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # 國家元首 head_of_state ── Deutsches Reich（威瑪共和／第三帝國）
    # 空檔 1918-11-09～1919-02-11：Rat der Volksbeauftragten 為集體行政機構，
    # 無單一 Reichspräsident，略去此段（see note in Ebert record below）。
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "_id":       "LS_HOS_DEUTSCHES_REICH_EBERT",
        "regimeId":  DEUTSCHES_REICH,
        "name":      "Friedrich Ebert",
        "nameZh":    "弗里德里希·艾伯特",
        "role":      "head_of_state",
        "title":     "Reichspräsident",
        "validFrom": "1919-02-11",
        "validTo":   "1925-02-28",
        "source":    "Wahl durch die Weimarer Nationalversammlung, 11. Februar 1919 (Stenographische Berichte der Verfassunggebenden Deutschen Nationalversammlung, Band I, S. 55–56); Ebert starb am 28. Februar 1925 in Berlin.",
        "verified":  True,
        "note":      "空檔 1918-11-09～1919-02-11：Rat der Volksbeauftragten 集體執政（Ebert 為 SPD 側主席，另見 head_of_government 記錄），無單一 Reichspräsident，略去。",
    },
    # 空檔 1925-02～05：依 WRV Art. 51，Reichsgerichtspräsident 代理至新選出的
    # Reichspräsident 就職。Walter Simons 自 1925-02-28 代理至 1925-05-12。
    {
        "_id":       "LS_HOS_DEUTSCHES_REICH_SIMONS",
        "regimeId":  DEUTSCHES_REICH,
        "name":      "Walter Simons",
        "nameZh":    "瓦爾特·西蒙斯",
        "role":      "head_of_state",
        "title":     "Vertretender Reichspräsident (amtierend gem. Art. 51 WRV)",
        "validFrom": "1925-02-28",
        "validTo":   "1925-05-12",
        "source":    "Weimarer Reichsverfassung (WRV), Art. 51 — bei Verhinderung des Reichspräsidenten vertritt ihn der Präsident des Reichsgerichts; Simons als Reichsgerichtspräsident amtierend 28. Februar – 12. Mai 1925. Vgl. Huber, Ernst Rudolf: Deutsche Verfassungsgeschichte seit 1789, Bd. VI, Stuttgart 1981, S. 310.",
        "verified":  True,
        "note":      "代理，非正式選出。依威瑪憲法第 51 條規定。Hindenburg 1925-05-12 就職後卸任。",
    },
    {
        "_id":       "LS_HOS_DEUTSCHES_REICH_HINDENBURG",
        "regimeId":  DEUTSCHES_REICH,
        "name":      "Paul von Hindenburg",
        "nameZh":    "保羅·馮·興登堡",
        "role":      "head_of_state",
        "title":     "Reichspräsident",
        "validFrom": "1925-05-12",
        "validTo":   "1934-08-02",
        "source":    "Reichspräsidentenwahl 1925, 2. Wahlgang 26. April 1925, Amtsantritt 12. Mai 1925 (Berliner Tageblatt, 12. Mai 1925, S. 1); Tod 2. August 1934, Gut Neudeck. Vgl. Pyta, Wolfram: Hindenburg, München 2007.",
        "verified":  True,
        "note":      "Hindenburg 於 1934-08-02 逝世。同日依 1934-08-01 頒布之《國家元首法》（Gesetz über das Staatsoberhaupt des Deutschen Reichs, RGBl. I 1934, S. 747）兩職合併，Hitler 繼任。",
    },
    {
        "_id":       "LS_HOS_DEUTSCHES_REICH_HITLER",
        "regimeId":  DEUTSCHES_REICH,
        "name":      "Adolf Hitler",
        "nameZh":    "阿道夫·希特勒",
        "role":      "head_of_state",
        "title":     "Führer und Reichskanzler",
        "validFrom": "1934-08-02",
        "validTo":   "1945-04-30",
        "source":    "Gesetz über das Staatsoberhaupt des Deutschen Reichs, 1. August 1934 (RGBl. I 1934, S. 747), wirksam ab 2. August 1934; Tod (Selbstmord) 30. April 1945, Führerbunker Berlin. Vgl. Kershaw, Ian: Hitler 1936–1945: Nemesis, Stuttgart 2000.",
        "verified":  True,
        "note":      "1934-08-01 法律於 Hindenburg 逝世（1934-08-02）同日生效，合併 Reichspräsident 與 Reichskanzler 為 Führer und Reichskanzler。",
    },
    {
        "_id":       "LS_HOS_DEUTSCHES_REICH_DOENITZ",
        "regimeId":  DEUTSCHES_REICH,
        "name":      "Karl Dönitz",
        "nameZh":    "卡爾·鄧尼茨",
        "role":      "head_of_state",
        "title":     "Reichspräsident",
        "validFrom": "1945-04-30",
        "validTo":   "1945-05-23",
        "source":    "Hitlers Politisches Testament, 29. April 1945 (abgedruckt in: Das Deutsche Reich und der Zweite Weltkrieg, MGFA, Bd. 10/2, München 2008, S. 1968); Verhaftung Dönitz' und Auflösung der Flensburger Regierung durch brit. Streitkräfte, 23. Mai 1945.",
        "verified":  True,
        "note":      "依希特勒政治遺囑任命為 Reichspräsident。1945-05-08 德國無條件投降後殘餘政府續存至 1945-05-23 被盟軍在 Flensburg 逮捕解散。",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # 政府首腦 head_of_government ── German Empire（德意志帝國）
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "_id":       "LS_HOG_GERMAN_EMPIRE_BUELOW",
        "regimeId":  GERMAN_EMPIRE,
        "name":      "Bernhard von Bülow",
        "nameZh":    "伯恩哈德·馮·比洛",
        "role":      "head_of_government",
        "title":     "Reichskanzler",
        "validFrom": "1908-01-01",
        "validTo":   "1909-07-14",
        "source":    "Kaiserliche Entlassungsurkunde, 14. Juli 1909; Ernennung 17. Oktober 1900 (RGBl. 1900, S. 643). Vgl. Röhl, John C. G.: Wilhelm II. Der Weg in den Abgrund, München 2008.",
        "verified":  True,
        "note":      "1908-01-01 為本批起點，非就任日（1900-10-17）。1909-07-14 獲 Kaiser 批准辭職，Bethmann Hollweg 同日就任。",
    },
    {
        "_id":       "LS_HOG_GERMAN_EMPIRE_BETHMANN",
        "regimeId":  GERMAN_EMPIRE,
        "name":      "Theobald von Bethmann Hollweg",
        "nameZh":    "泰奧巴爾德·馮·貝特曼·霍爾韋格",
        "role":      "head_of_government",
        "title":     "Reichskanzler",
        "validFrom": "1909-07-14",
        "validTo":   "1917-07-14",
        "source":    "Kaiserliche Ernennung 14. Juli 1909; Rücktritt 13. Juli 1917. Vgl. Erdmann, Karl Dietrich: Die Zeit der Weltkriege (Gebhardt, Handbuch der deutschen Geschichte, Bd. 18), Stuttgart 1976, S. 74.",
        "verified":  True,
        "note":      "1917-07-13 在 OHL 壓力下辭職，Kaiser 批准；Michaelis 翌日（1917-07-14）就任。",
    },
    {
        "_id":       "LS_HOG_GERMAN_EMPIRE_MICHAELIS",
        "regimeId":  GERMAN_EMPIRE,
        "name":      "Georg Michaelis",
        "nameZh":    "格奧爾格·米夏埃利斯",
        "role":      "head_of_government",
        "title":     "Reichskanzler",
        "validFrom": "1917-07-14",
        "validTo":   "1917-10-26",
        "source":    "Kaiserliche Ernennung 14. Juli 1917; Entlassung 24. Oktober 1917; Hertling ernannt 26. Oktober 1917. Vgl. Huber, Ernst Rudolf: Deutsche Verfassungsgeschichte seit 1789, Bd. V, Stuttgart 1978, S. 352.",
        "verified":  True,
        "note":      "任期約 3 個月，為帝國史上最短任 Reichskanzler。1917-10-24 被解職；Hertling 1917-10-26 就任，中間 2 日看守期。",
    },
    {
        "_id":       "LS_HOG_GERMAN_EMPIRE_HERTLING",
        "regimeId":  GERMAN_EMPIRE,
        "name":      "Georg von Hertling",
        "nameZh":    "格奧爾格·馮·赫特林",
        "role":      "head_of_government",
        "title":     "Reichskanzler",
        "validFrom": "1917-10-26",
        "validTo":   "1918-10-03",
        "source":    "Kaiserliche Ernennung 26. Oktober 1917; Rücktritt 29. September 1918; Max von Baden ernannt 3. Oktober 1918. Vgl. Huber, Deutsche Verfassungsgeschichte, Bd. V, S. 353–360.",
        "verified":  True,
        "note":      "1918-09-29 Hertling 以高齡及健康為由請辭；Max von Baden 1918-10-03 就任，中間 4 日交接。",
    },
    {
        "_id":       "LS_HOG_GERMAN_EMPIRE_MAX_VON_BADEN",
        "regimeId":  GERMAN_EMPIRE,
        "name":      "Max von Baden",
        "nameZh":    "巴登的馬克斯親王",
        "role":      "head_of_government",
        "title":     "Reichskanzler",
        "validFrom": "1918-10-03",
        "validTo":   "1918-11-09",
        "source":    "Kaiserliche Ernennung 3. Oktober 1918; Übergabe des Reichskanzleramts an Friedrich Ebert 9. November 1918. Vgl. Max von Baden: Erinnerungen und Dokumente, Berlin/Leipzig 1927, S. 596–609.",
        "verified":  True,
        "note":      "1918-11-09 Max von Baden 宣布 Kaiser 退位（未獲 Wilhelm II 本人授權）並自行將職務交予 Ebert；德意志帝國政府即日終止，Deutsches Reich 接管。",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # 政府首腦 head_of_government ── Deutsches Reich（威瑪共和／第三帝國）
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "_id":       "LS_HOG_DEUTSCHES_REICH_EBERT",
        "regimeId":  DEUTSCHES_REICH,
        "name":      "Friedrich Ebert",
        "nameZh":    "弗里德里希·艾伯特",
        "role":      "head_of_government",
        "title":     "Vorsitzender des Rats der Volksbeauftragten",
        "validFrom": "1918-11-09",
        "validTo":   "1919-02-13",
        "source":    "Konstituierung des Rats der Volksbeauftragten, 9. November 1918; Ebert als SPD-Vorsitzender. Vgl. Kolb, Eberhard: Die Weimarer Republik, 7. Aufl., München 2009, S. 13–20.",
        "verified":  True,
        "note":      "人民代表委員會（Rat der Volksbeauftragten）為集體最高行政機構；Ebert 為 SPD 側主席。1919-02-13 Scheidemann 就任首屆 Reichsministerpräsident。",
    },
    {
        "_id":       "LS_HOG_DEUTSCHES_REICH_SCHEIDEMANN",
        "regimeId":  DEUTSCHES_REICH,
        "name":      "Philipp Scheidemann",
        "nameZh":    "菲利普·沙伊德曼",
        "role":      "head_of_government",
        "title":     "Reichsministerpräsident",
        "validFrom": "1919-02-13",
        "validTo":   "1919-06-21",
        "source":    "Ernennung durch die Nationalversammlung, 13. Februar 1919; Rücktritt 20. Juni 1919 (Protest gegen den Versailler Vertrag); Bauer ernannt 21. Juni 1919. Vgl. Kolb, Die Weimarer Republik, S. 25.",
        "verified":  True,
        "note":      "Scheidemann 為拒簽凡爾賽和約提前辭職（1919-06-28 簽署）；Bauer 翌日（1919-06-21）就任。",
    },
    {
        "_id":       "LS_HOG_DEUTSCHES_REICH_BAUER",
        "regimeId":  DEUTSCHES_REICH,
        "name":      "Gustav Bauer",
        "nameZh":    "古斯塔夫·鮑爾",
        "role":      "head_of_government",
        "title":     "Reichsministerpräsident",
        "validFrom": "1919-06-21",
        "validTo":   "1920-03-27",
        "source":    "Ernennung 21. Juni 1919; Rücktritt 27. März 1920 infolge des Kapp-Putsches (13.–17. März 1920). Vgl. Winkler, Heinrich August: Weimar 1918–1933, München 1993, S. 118.",
        "verified":  True,
        "note":      "1920-03-27 因 Kapp 叛變後政治危機辭職；Müller（第一次）同日就任。",
    },
    {
        "_id":       "LS_HOG_DEUTSCHES_REICH_MUELLER_I",
        "regimeId":  DEUTSCHES_REICH,
        "name":      "Hermann Müller",
        "nameZh":    "赫爾曼·米勒",
        "role":      "head_of_government",
        "title":     "Reichskanzler",
        "validFrom": "1920-03-27",
        "validTo":   "1920-06-25",
        "source":    "Ernennung 27. März 1920; Rücktritt nach der Reichstagswahl 6. Juni 1920; Fehrenbach ernannt 25. Juni 1920. Vgl. Winkler, Weimar 1918–1933, S. 126.",
        "verified":  True,
        "note":      "第一次擔任 Reichskanzler。1920-06-06 大選後聯合政府談判失敗，Müller 下台；Fehrenbach 1920-06-25 就任。",
    },
    {
        "_id":       "LS_HOG_DEUTSCHES_REICH_FEHRENBACH",
        "regimeId":  DEUTSCHES_REICH,
        "name":      "Konstantin Fehrenbach",
        "nameZh":    "康斯坦丁·費倫巴赫",
        "role":      "head_of_government",
        "title":     "Reichskanzler",
        "validFrom": "1920-06-25",
        "validTo":   "1921-05-10",
        "source":    "Ernennung 25. Juni 1920; Rücktritt 4. Mai 1921 nach alliiertem Ultimatum (Londoner Ultimatum) in der Reparationsfrage; Wirth ernannt 10. Mai 1921. Vgl. Winkler, Weimar 1918–1933, S. 149.",
        "verified":  True,
        "note":      "1921-05-04 辭職；Wirth 1921-05-10 就任，中間 6 日看守期。",
    },
    {
        "_id":       "LS_HOG_DEUTSCHES_REICH_WIRTH",
        "regimeId":  DEUTSCHES_REICH,
        "name":      "Joseph Wirth",
        "nameZh":    "約瑟夫·維爾特",
        "role":      "head_of_government",
        "title":     "Reichskanzler",
        "validFrom": "1921-05-10",
        "validTo":   "1922-11-22",
        "source":    "Ernennung 10. Mai 1921; Rücktritt 14. November 1922; Cuno ernannt 22. November 1922. Vgl. Winkler, Weimar 1918–1933, S. 190.",
        "verified":  True,
        "note":      "1922-11-14 辭職（政府聯合崩潰）；Cuno 1922-11-22 就任，中間 8 日看守期。validTo 設至 Cuno 就任日以涵蓋看守期。",
    },
    {
        "_id":       "LS_HOG_DEUTSCHES_REICH_CUNO",
        "regimeId":  DEUTSCHES_REICH,
        "name":      "Wilhelm Cuno",
        "nameZh":    "威廉·庫諾",
        "role":      "head_of_government",
        "title":     "Reichskanzler",
        "validFrom": "1922-11-22",
        "validTo":   "1923-08-13",
        "source":    "Ernennung 22. November 1922; Rücktritt 12. August 1923 infolge des Generalstreiks; Stresemann ernannt 13. August 1923. Vgl. Winkler, Weimar 1918–1933, S. 232.",
        "verified":  True,
        "note":      "任內爆發魯爾危機（1923-01-11 法比佔領魯爾）及惡性通貨膨脹。1923-08-12 辭職；Stresemann 翌日就任。",
    },
    {
        "_id":       "LS_HOG_DEUTSCHES_REICH_STRESEMANN",
        "regimeId":  DEUTSCHES_REICH,
        "name":      "Gustav Stresemann",
        "nameZh":    "古斯塔夫·施特雷澤曼",
        "role":      "head_of_government",
        "title":     "Reichskanzler",
        "validFrom": "1923-08-13",
        "validTo":   "1923-11-30",
        "source":    "Ernennung 13. August 1923; Misstrauensvotum im Reichstag 23. November 1923; Marx ernannt 30. November 1923. Vgl. Winkler, Weimar 1918–1933, S. 248–266.",
        "verified":  True,
        "note":      "1923-11-23 議會不信任投票失敗，辭任 Reichskanzler（繼續擔任 Außenminister 至 1929-10-03 逝世）。Marx 1923-11-30 就任，中間 7 日看守期；validTo 設至 Marx 就任日。",
    },
    {
        "_id":       "LS_HOG_DEUTSCHES_REICH_MARX_I",
        "regimeId":  DEUTSCHES_REICH,
        "name":      "Wilhelm Marx",
        "nameZh":    "威廉·馬克思",
        "role":      "head_of_government",
        "title":     "Reichskanzler",
        "validFrom": "1923-11-30",
        "validTo":   "1925-01-15",
        "source":    "Ernennung (1. Kabinett) 30. November 1923; 2. Kabinett ab 3. Juni 1924; Rücktritt/Ablösung 15. Januar 1925 (Luther ernannt). Vgl. Winkler, Weimar 1918–1933, S. 275.",
        "verified":  True,
        "note":      "第一、二任連任（1923-11-30～1924-06-03、1924-06-03～1925-01-15），合併為一筆；Luther 1925-01-15 就任。",
    },
    {
        "_id":       "LS_HOG_DEUTSCHES_REICH_LUTHER",
        "regimeId":  DEUTSCHES_REICH,
        "name":      "Hans Luther",
        "nameZh":    "漢斯·盧瑟",
        "role":      "head_of_government",
        "title":     "Reichskanzler",
        "validFrom": "1925-01-15",
        "validTo":   "1926-05-17",
        "source":    "Ernennung (1. Kabinett) 15. Januar 1925; 2. Kabinett ab 20. Januar 1926; Misstrauensvotum 12. Mai 1926; Marx ernannt 17. Mai 1926. Vgl. Winkler, Weimar 1918–1933, S. 303.",
        "verified":  True,
        "note":      "第一任（1925-01-15～1925-12-20）、第二任（1926-01-20～1926-05-17），中間約 1 個月為組閣談判期，合併為一筆。",
    },
    {
        "_id":       "LS_HOG_DEUTSCHES_REICH_MARX_II",
        "regimeId":  DEUTSCHES_REICH,
        "name":      "Wilhelm Marx",
        "nameZh":    "威廉·馬克思",
        "role":      "head_of_government",
        "title":     "Reichskanzler",
        "validFrom": "1926-05-17",
        "validTo":   "1928-06-28",
        "source":    "Ernennung (3. Kabinett) 17. Mai 1926; 4. Kabinett ab 29. Juni 1927; Rücktritt nach Reichstagswahl 20. Mai 1928; Müller ernannt 28. Juni 1928. Vgl. Winkler, Weimar 1918–1933, S. 324.",
        "verified":  True,
        "note":      "第三任（1926-05-17～1927-06-29）、第四任（1927-06-29～1928-06-28），合併為一筆；Müller（第二次）1928-06-28 就任。",
    },
    {
        "_id":       "LS_HOG_DEUTSCHES_REICH_MUELLER_II",
        "regimeId":  DEUTSCHES_REICH,
        "name":      "Hermann Müller",
        "nameZh":    "赫爾曼·米勒",
        "role":      "head_of_government",
        "title":     "Reichskanzler",
        "validFrom": "1928-06-28",
        "validTo":   "1930-03-30",
        "source":    "Ernennung 28. Juni 1928; Rücktritt 27. März 1930 (Koalitionsstreit über Arbeitslosenversicherungsbeiträge); Brüning ernannt 30. März 1930. Vgl. Winkler, Weimar 1918–1933, S. 385.",
        "verified":  True,
        "note":      "第二次擔任 Reichskanzler（大聯合政府）。1930-03-27 辭職；Brüning 1930-03-30 就任。",
    },
    {
        "_id":       "LS_HOG_DEUTSCHES_REICH_BRUENING",
        "regimeId":  DEUTSCHES_REICH,
        "name":      "Heinrich Brüning",
        "nameZh":    "海因里希·布呂寧",
        "role":      "head_of_government",
        "title":     "Reichskanzler",
        "validFrom": "1930-03-30",
        "validTo":   "1932-06-01",
        "source":    "Ernennung 30. März 1930; Entlassung durch Hindenburg 30. Mai 1932; Papen ernannt 1. Juni 1932. Vgl. Brüning, Heinrich: Memoiren 1918–1934, Stuttgart 1970.",
        "verified":  True,
        "note":      "以緊急命令（Notverordnungen per Art. 48 WRV）治國。1932-05-30 被 Hindenburg 解職；Papen 1932-06-01 就任。",
    },
    {
        "_id":       "LS_HOG_DEUTSCHES_REICH_PAPEN",
        "regimeId":  DEUTSCHES_REICH,
        "name":      "Franz von Papen",
        "nameZh":    "弗朗茨·馮·帕彭",
        "role":      "head_of_government",
        "title":     "Reichskanzler",
        "validFrom": "1932-06-01",
        "validTo":   "1932-12-03",
        "source":    "Ernennung 1. Juni 1932; Rücktritt 3. Dezember 1932; Schleicher ernannt 3. Dezember 1932. Vgl. Winkler, Heinrich August: Der Weg in die Katastrophe 1930–1933, Berlin 1987, S. 556.",
        "verified":  True,
        "note":      "「男爵內閣」（Kabinett der Barone）。1932-11-17 辭職後組閣談判失敗，Schleicher 1932-12-03 就任；validTo 設至 Schleicher 就任日。",
    },
    {
        "_id":       "LS_HOG_DEUTSCHES_REICH_SCHLEICHER",
        "regimeId":  DEUTSCHES_REICH,
        "name":      "Kurt von Schleicher",
        "nameZh":    "庫爾特·馮·施萊謝爾",
        "role":      "head_of_government",
        "title":     "Reichskanzler",
        "validFrom": "1932-12-03",
        "validTo":   "1933-01-30",
        "source":    "Ernennung 3. Dezember 1932; Rücktritt 28. Januar 1933; Hitler ernannt 30. Januar 1933. Vgl. Winkler, Der Weg in die Katastrophe, S. 856.",
        "verified":  True,
        "note":      "1933-01-28 辭職；Hitler 1933-01-30 由 Hindenburg 任命，中間 2 日看守期；validTo 設至 Hitler 就任日。",
    },
    {
        "_id":       "LS_HOG_DEUTSCHES_REICH_HITLER",
        "regimeId":  DEUTSCHES_REICH,
        "name":      "Adolf Hitler",
        "nameZh":    "阿道夫·希特勒",
        "role":      "head_of_government",
        "title":     "Reichskanzler",
        "validFrom": "1933-01-30",
        "validTo":   "1945-04-30",
        "source":    "Ernennung durch Reichspräsident Hindenburg, 30. Januar 1933 (Berliner Tageblatt, 31. Januar 1933, Morgenausgabe, S. 1); Tod (Selbstmord) 30. April 1945. Vgl. Kershaw, Ian: Hitler 1936–1945: Nemesis, Stuttgart 2000.",
        "verified":  True,
        "note":      "1934-08-02 起兼任 Staatsoberhaupt，稱號改為 Führer und Reichskanzler。Goebbels 依遺囑同日就任 Reichskanzler。",
    },
    {
        "_id":       "LS_HOG_DEUTSCHES_REICH_GOEBBELS",
        "regimeId":  DEUTSCHES_REICH,
        "name":      "Joseph Goebbels",
        "nameZh":    "約瑟夫·戈培爾",
        "role":      "head_of_government",
        "title":     "Reichskanzler",
        "validFrom": "1945-04-30",
        "validTo":   "1945-05-02",
        "source":    "Hitlers Politisches Testament, 29. April 1945 (ernennt Goebbels zum Reichskanzler; in: Das Deutsche Reich und der Zweite Weltkrieg, MGFA, Bd. 10/2, S. 1968); Goebbels Selbstmord 1. Mai 1945, Berlin; Schwerin von Krosigk als Leitender Minister ab 2. Mai 1945.",
        "verified":  True,
        "note":      "依希特勒政治遺囑任命；自殺身亡（1945-05-01）前未實際執行職務。validTo 設至 Schwerin von Krosigk 就任日（1945-05-02）。",
    },
    {
        "_id":       "LS_HOG_DEUTSCHES_REICH_SCHWERIN",
        "regimeId":  DEUTSCHES_REICH,
        "name":      "Lutz Graf Schwerin von Krosigk",
        "nameZh":    "盧茨·施韋林·馮·克羅西克",
        "role":      "head_of_government",
        "title":     "Leitender Minister",
        "validFrom": "1945-05-02",
        "validTo":   "1945-05-23",
        "source":    "Ernennung durch Dönitz als 'Leitender Minister' ab 2. Mai 1945; Verhaftung der Flensburger Regierung durch britische Streitkräfte, 23. Mai 1945. Vgl. Steinert, Marlis: 23 Tage — die Regierung Dönitz, Hamburg 1967.",
        "verified":  True,
        "note":      "Dönitz 拒絕另任 Reichskanzler，以「首席部長」（Leitender Minister）名義領導殘餘政府，至 1945-05-23 在 Flensburg 被盟軍逮捕解散。",
    },
]

# ─── 重疊檢查（dry-run 主要輸出） ─────────────────────────────────────────────
def parse_date(s):
    """YYYY-MM-DD → date；None → date.max（無上界）。"""
    if s is None:
        return date.max
    return date.fromisoformat(s)

def check_overlaps(records):
    """回傳 list of (rec_a, rec_b, 說明) overlap 錯誤。"""
    from collections import defaultdict
    groups = defaultdict(list)
    for r in records:
        key = (r["regimeId"], r["role"])
        groups[key].append(r)
    errors = []
    for key, recs in groups.items():
        sorted_recs = sorted(recs, key=lambda x: x["validFrom"])
        for i in range(len(sorted_recs) - 1):
            a, b = sorted_recs[i], sorted_recs[i + 1]
            a_end = parse_date(a.get("validTo"))
            b_start = parse_date(b["validFrom"])
            if b_start < a_end:   # half-open: [a_start, a_end) ∩ [b_start, ...) 非空
                errors.append((a, b, f"{a['_id']} validTo={a.get('validTo')} > {b['_id']} validFrom={b['validFrom']}"))
    return errors

# ─── 送出邏輯 ──────────────────────────────────────────────────────────────────
sent = json.load(open(a.ids, encoding="utf-8")) if os.path.exists(a.ids) else {}
key  = api_key() if not dry else None

# dry-run 前置：印出統計與重疊檢查
verified_false = [r for r in RECORDS if not r.get("verified", True)]
print(f"\n{'─'*60}")
print(f"  德國領導人 seed  共 {len(RECORDS)} 筆  (verified=False: {len(verified_false)} 筆)")
print(f"{'─'*60}")

overlap_errors = check_overlaps(RECORDS)
if overlap_errors:
    print(f"\n[ERROR] 發現 {len(overlap_errors)} 筆重疊：")
    for a_, b_, msg in overlap_errors:
        print(f"  ✗ 重疊：{msg}")
    if not dry:
        sys.exit("中止：有重疊，請先修正資料再 --send。")
else:
    print("  重疊檢查：✓ 無重疊")

print()

ok_count   = 0
skip_count = 0
fail_count = 0

for rec in RECORDS:
    rid = rec["_id"]
    if rid in sent:
        print(f"  SKIP  {rid}（已寫入：{sent[rid]}）")
        skip_count += 1
        continue

    # 送出欄位（對應 CreateLeaderRecordRequest）
    body = {
        "regimeId":  rec["regimeId"],
        "name":      rec["name"],
        "nameZh":    rec.get("nameZh"),
        "role":      rec["role"],
        "title":     rec.get("title"),
        "validFrom": rec["validFrom"],
        "source":    rec["source"],
        "verified":  rec.get("verified", True),
    }
    if rec.get("validTo") is not None:
        body["validTo"] = rec["validTo"]
    if rec.get("sourceUrl"):
        body["sourceUrl"] = rec["sourceUrl"]

    label = f"{rec['name']}  {rec['validFrom']} – {rec.get('validTo') or '∞'}  [{rec['role']}]"
    print(f"  POST /api/v1/leader-records  ← {rid}")
    print(f"       {label}")
    if dry:
        continue

    raw = json.dumps(body, ensure_ascii=False).encode()
    req = urllib.request.Request(
        a.base.rstrip("/") + "/api/v1/leader-records",
        data=raw, method="POST",
        headers={"Content-Type": "application/json", "X-API-Key": key},
    )
    try:
        resp = json.load(urllib.request.urlopen(req))
        new_id = resp["data"]["id"]
        sent[rid] = new_id
        json.dump(sent, open(a.ids, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print(f"       ✓ id = {new_id}")
        ok_count += 1
    except urllib.error.HTTPError as e:
        body_err = e.read().decode()[:400]
        if e.code == 409:
            print(f"       CONFLICT 409（已存在重疊紀錄）：{body_err}")
        else:
            print(f"       FAIL {e.code}：{body_err}", file=sys.stderr)
        fail_count += 1

if dry:
    print(f"\n（dry-run，未送出。共 {len(RECORDS)} 筆，跳過 {skip_count} 筆。）\n")
else:
    print(f"\n完成：寫入 {ok_count} 筆，跳過 {skip_count} 筆，失敗 {fail_count} 筆。\n")
