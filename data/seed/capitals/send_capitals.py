#!/usr/bin/env python3
"""
歐洲首都 seed（1908–1945）。
涵蓋：德國（German Empire + Deutsches Reich）、奧匈→奧地利、
      法國→維琪、英國、義大利、俄羅斯帝國→蘇俄→蘇聯、
      鄂圖曼→土耳其、波蘭、捷克斯洛伐克、塞爾維亞→南斯拉夫。

只寫入開發庫（127.0.0.1:5052），拒絕送到 5051。

用法：
  python3 send_capitals.py [--dry-run]                           # 列出不送出（預設即為 dry-run）
  python3 send_capitals.py --send [--base URL] [--env FILE]      # 真的寫入
"""
import argparse, json, os, sys, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))

ap = argparse.ArgumentParser()
ap.add_argument("--send",    action="store_true", help="真的送出（預設 dry-run）")
ap.add_argument("--dry-run", action="store_true", help="明確指定 dry-run（不送出）")
ap.add_argument("--base",    default="http://127.0.0.1:5052")
ap.add_argument("--env",     default=os.path.join(HERE, "../../../.env"))
ap.add_argument("--ids",     default=os.path.join(HERE, "sent-capitals.json"),
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

# ─── 首都紀錄資料 ──────────────────────────────────────────────────────────────
# regimeId 由 GET /api/v1/sovereignty?date=<date> 查得（2026-11-02）。
# 查詢日期：1912-01-01（帝俄、奧匈、鄂圖曼、塞爾維亞）
#            1920-06-01（奧地利第一共和、蘇俄 SFSR）
#            1925-01-01（德、法、英、義、蘇聯、土、波蘭、捷克、KSCS）
#            1935-01-01（聯邦國家奧地利、南斯拉夫王國）
#            1942-01-01（Deutsches Reich、維琪法國）
RECORDS = [
    # ── 德意志帝國 German Empire（1871–1918）首都：柏林 ────────────────────────
    {
        "_id":        "CAP_BERLIN_GERMAN_EMPIRE",
        "regimeId":   "01a192dc-6440-7b84-ad59-f7836508ef72",  # slug: german-empire
        "cityName":   {"en": "Berlin", "zh": "柏林", "de": "Berlin"},
        "location":   {"type": "Point", "coordinates": [13.405, 52.520]},
        "validStart": "1908-01-01",
        "validEnd":   "1918-11-09",
        "sourceRef":  "Verfassung des Deutschen Reiches, 16. April 1871 — Berlin als Sitz von Kaiser, Reichsregierung und Reichstag",
        "note":       "1908 為本批起點，非帝國建國日（1871-01-18）。Kaiser Wilhelm II 於 1918-11-09 退位，帝國終止。",
    },
    # ── 威瑪共和／第三帝國 Deutsches Reich（1918–1945）首都：柏林 ──────────────
    {
        "_id":        "CAP_BERLIN_DEUTSCHES_REICH",
        "regimeId":   "01a18e71-c9ba-719c-bc51-3086edef89bc",  # slug: deutsches-reich
        "cityName":   {"en": "Berlin", "zh": "柏林", "de": "Berlin"},
        "location":   {"type": "Point", "coordinates": [13.405, 52.520]},
        "validStart": "1918-11-09",
        "validEnd":   "1945-05-08",
        "sourceRef":  (
            "Weimarer Verfassung (Verfassung des Deutschen Reichs), 11. August 1919 — "
            "Berlin als faktische Reichshauptstadt；"
            "Instrument of Surrender (German), 8 May 1945 — 德國無條件投降"
        ),
        "note":       "涵蓋威瑪共和（1918–1933）與第三帝國（1933–1945）；柏林全程為首都。",
    },
    # ── 奧匈帝國 Austria-Hungary（1867–1918）首都（西半）：維也納 ──────────────
    {
        "_id":        "CAP_VIENNA_AUSTRIA_HUNGARY",
        "regimeId":   "01a192dc-61e3-765f-926c-4aeca3305897",  # slug: austria-hungary
        "cityName":   {"en": "Vienna", "zh": "維也納", "de": "Wien"},
        "location":   {"type": "Point", "coordinates": [16.374, 48.208]},
        "validStart": "1908-01-01",
        "validEnd":   "1918-11-03",
        "sourceRef":  (
            "Österreichisch-Ungarischer Ausgleich (Compromise), 1867 — "
            "Wien als Hauptstadt Cisleithaniens und gemeinsamer Regierungssitz"
        ),
        "note":       "1908 為本批起點。停戰協定（Armistice of Villa Giusti）1918-11-03 為帝國事實解體日。",
    },
    # ── 奧地利共和國（第一共和 1918–1934）首都：維也納 ────────────────────────
    {
        "_id":        "CAP_VIENNA_REPUBLIC_AUSTRIA_1918",
        "regimeId":   "01a193a2-bdfd-7bca-9589-af51960e1bc2",  # slug: republic-of-austria-1918
        "cityName":   {"en": "Vienna", "zh": "維也納", "de": "Wien"},
        "location":   {"type": "Point", "coordinates": [16.374, 48.208]},
        "validStart": "1918-11-12",
        "validEnd":   "1934-05-01",
        "sourceRef":  (
            "Staatsgesetz über die Staats- und Regierungsform von Deutschösterreich, "
            "12. November 1918 (StGBl. Nr. 5/1918) — Wien als Staatshauptstadt"
        ),
        "note":       "至 1934-05-01 Maiverfassung 生效，政體轉為聯邦國家奧地利。",
    },
    # ── 聯邦國家奧地利（Dollfuß/Schuschnigg 1934–1938）首都：維也納 ──────────
    {
        "_id":        "CAP_VIENNA_FEDERAL_STATE_AUSTRIA",
        "regimeId":   "01a18e71-cbaf-730b-8d7c-6a4b920630c0",  # slug: federal-state-of-austria
        "cityName":   {"en": "Vienna", "zh": "維也納", "de": "Wien"},
        "location":   {"type": "Point", "coordinates": [16.374, 48.208]},
        "validStart": "1934-05-01",
        "validEnd":   "1938-03-13",
        "sourceRef":  "Verfassung des Bundesstaates Österreich (Maiverfassung), 1. Mai 1934 — Wien als Bundeshauptstadt",
        "note":       "至 1938-03-13 Anschluss（德奧合併），奧地利被併入 Deutsches Reich。",
    },
    # ── 法蘭西第三共和 French Third Republic（1870–1940）首都：巴黎 ────────────
    {
        "_id":        "CAP_PARIS_FRENCH_THIRD_REPUBLIC",
        "regimeId":   "01a18e71-cb8c-761f-83c5-944ad7c6a879",  # slug: french-third-republic
        "cityName":   {"en": "Paris", "zh": "巴黎", "fr": "Paris"},
        "location":   {"type": "Point", "coordinates": [2.352, 48.857]},
        "validStart": "1908-01-01",
        "validEnd":   "1940-07-10",
        "sourceRef":  (
            "Lois constitutionnelles de 1875 — Paris, siège du Gouvernement "
            "et de l'Assemblée nationale"
        ),
        "note":       "1908 為本批起點。1940-07-10 國民議會授予貝當全權，第三共和終止。",
    },
    # ── 法蘭西國（維琪 French State / État français 1940–1944）首都：維琪 ────
    {
        "_id":        "CAP_VICHY_FRENCH_STATE",
        "regimeId":   "01a18e71-cb9b-790b-8f4b-671d0e7359bc",  # slug: french-state-vichy
        "cityName":   {"en": "Vichy", "zh": "維琪", "fr": "Vichy"},
        "location":   {"type": "Point", "coordinates": [3.427, 46.123]},
        "validStart": "1940-07-10",
        "validEnd":   "1944-08-20",
        "sourceRef":  (
            "Loi constitutionnelle du 10 juillet 1940 (J.O. du 11 juillet 1940) — "
            "pleins pouvoirs à Pétain, siège gouvernemental à Vichy"
        ),
        "note":       "1944-08-20 貝當被德軍押往東部，維琪政府事實上瓦解。",
    },
    # ── 大不列顛及愛爾蘭聯合王國（–1922）首都：倫敦 ──────────────────────────
    {
        "_id":        "CAP_LONDON_UK_GBI",
        "regimeId":   "01a192dc-749e-708d-b866-b08c2971d624",  # slug: united-kingdom-of-great-britain-and-ireland
        "cityName":   {"en": "London", "zh": "倫敦"},
        "location":   {"type": "Point", "coordinates": [-0.128, 51.507]},
        "validStart": "1908-01-01",
        "validEnd":   "1922-12-06",
        "sourceRef":  "Acts of Union 1800 — London, seat of the United Parliament of Great Britain and Ireland",
        "note":       "1908 為本批起點。1922-12-06 愛爾蘭自由邦成立，英國更名。",
    },
    # ── 大不列顛及北愛爾蘭聯合王國（1922–）首都：倫敦 ────────────────────────
    {
        "_id":        "CAP_LONDON_UK",
        "regimeId":   "01a18e71-cba5-7726-90e3-9b90ab344afd",  # slug: united-kingdom
        "cityName":   {"en": "London", "zh": "倫敦"},
        "location":   {"type": "Point", "coordinates": [-0.128, 51.507]},
        "validStart": "1922-12-06",
        "validEnd":   None,
        "sourceRef":  "Royal and Parliamentary Titles Act 1927 — confirmed London as capital of the United Kingdom of Great Britain and Northern Ireland",
        "note":       "",
    },
    # ── 義大利王國 Kingdom of Italy（1861–1946）首都：羅馬 ────────────────────
    {
        "_id":        "CAP_ROME_KINGDOM_OF_ITALY",
        "regimeId":   "01a18e71-cc66-7f28-9763-3316d99f425d",  # slug: kingdom-of-italy
        "cityName":   {"en": "Rome", "zh": "羅馬", "it": "Roma"},
        "location":   {"type": "Point", "coordinates": [12.496, 41.903]},
        "validStart": "1908-01-01",
        "validEnd":   None,
        "sourceRef":  "Legge 3 febbraio 1871, n. 33 — Roma dichiarata capitale del Regno d'Italia",
        "note":       "1908 為本批起點；王國至 1946-06-02 廢除君主制。",
    },
    # ── 俄羅斯帝國 Russian Empire（–1917）首都：聖彼得堡／彼得格勒 ────────────
    {
        "_id":        "CAP_STPETERSBURG_RUSSIAN_EMPIRE",
        "regimeId":   "01a192dc-651a-7664-8858-ac617593d466",  # slug: russian-empire
        "cityName":   {
            "en": "Saint Petersburg (from Sep 1914: Petrograd)",
            "zh": "聖彼得堡（1914年9月起改稱彼得格勒）",
            "ru": "Санкт-Петербург (с сент. 1914: Петроград)",
        },
        "location":   {"type": "Point", "coordinates": [30.335, 59.934]},
        "validStart": "1908-01-01",
        "validEnd":   "1917-03-15",
        "sourceRef":  (
            "待查證（Peter the Great 1703 年建城敕令設為首都；"
            "1914-09-01 儒略曆／格雷高里曆 1914-09-14 沙皇敕令更名彼得格勒）"
        ),
        "note":       "1917-03-15（格雷高里曆）沙皇尼古拉二世退位，俄羅斯帝國終止。",
    },
    # ── 蘇維埃俄羅斯 RSFSR（1917–1922）首都：彼得格勒（至1918-03）────────────
    {
        "_id":        "CAP_PETROGRAD_RSFSR",
        "regimeId":   "01a19333-9b70-701d-a1e4-464af7aff56c",  # slug: russian-sfsr-1917
        "cityName":   {"en": "Petrograd", "zh": "彼得格勒", "ru": "Петроград"},
        "location":   {"type": "Point", "coordinates": [30.335, 59.934]},
        "validStart": "1917-11-07",
        "validEnd":   "1918-03-12",
        "sourceRef":  "待查證（布爾什維克革命 1917-11-07 格雷高里曆奪取彼得格勒；遷都決定由人民委員會議於 1918-03-16 正式頒布）",
        "note":       "格雷高里曆 1917-11-07（儒略曆 10-25）布爾什維克取得政權。",
    },
    # ── 蘇維埃俄羅斯 RSFSR（1917–1922）首都：莫斯科（1918-03 起）────────────
    {
        "_id":        "CAP_MOSCOW_RSFSR",
        "regimeId":   "01a19333-9b70-701d-a1e4-464af7aff56c",  # slug: russian-sfsr-1917
        "cityName":   {"en": "Moscow", "zh": "莫斯科", "ru": "Москва"},
        "location":   {"type": "Point", "coordinates": [37.617, 55.756]},
        "validStart": "1918-03-12",
        "validEnd":   "1922-12-30",
        "sourceRef":  (
            "Декрет Совета Народных Комиссаров о переезде правительства "
            "из Петрограда в Москву, 16 марта 1918 (Декрет СНК 1918-03-16)"
        ),
        "note":       "蘇俄政府於 1918-03-10 至 1918-03-12 實際遷移至莫斯科；正式令頒布於 1918-03-16。",
    },
    # ── 蘇聯 Soviet Union（1922–）首都：莫斯科 ────────────────────────────────
    {
        "_id":        "CAP_MOSCOW_SOVIET_UNION",
        "regimeId":   "01a18e71-cc2e-7f80-8d62-81879da43d7b",  # slug: soviet-union
        "cityName":   {"en": "Moscow", "zh": "莫斯科", "ru": "Москва"},
        "location":   {"type": "Point", "coordinates": [37.617, 55.756]},
        "validStart": "1922-12-30",
        "validEnd":   None,
        "sourceRef":  (
            "Договор об образовании Союза ССР (Treaty on the Creation of the USSR), "
            "30 декабря 1922；Конституция СССР 1924 年確認莫斯科為首都"
        ),
        "note":       "",
    },
    # ── 鄂圖曼帝國 Ottoman Empire（–1922）首都：君士坦丁堡 ──────────────────
    {
        "_id":        "CAP_CONSTANTINOPLE_OTTOMAN",
        "regimeId":   "01a192dc-65fb-7644-a296-6b5865e4b806",  # slug: ottoman-empire
        "cityName":   {
            "en": "Constantinople",
            "zh": "君士坦丁堡",
            "tr": "Kostantiniyye",
            "ota": "قسطنطينيه",
        },
        "location":   {"type": "Point", "coordinates": [28.978, 41.008]},
        "validStart": "1908-01-01",
        "validEnd":   "1922-11-01",
        "sourceRef":  "待查證（君士坦丁堡自 1453 年起為鄂圖曼帝國首都；大國民議會 1922-11-01 廢除蘇丹制度）",
        "note":       "1908 為本批起點。蘇丹制度廢除日 1922-11-01 為帝國首都紀錄終止日。",
    },
    # ── 土耳其共和國 Republic of Turkey（1923–）首都：安卡拉 ──────────────────
    {
        "_id":        "CAP_ANKARA_TURKEY",
        "regimeId":   "01a18e71-ccaa-7e5f-8e69-06921e5214cc",  # slug: republic-of-turkey
        "cityName":   {"en": "Ankara", "zh": "安卡拉", "tr": "Ankara"},
        "location":   {"type": "Point", "coordinates": [32.860, 39.933]},
        "validStart": "1923-10-13",
        "validEnd":   None,
        "sourceRef":  (
            "Ankara'nın Başşehir Olması Hakkında Kanun (Kanun No. 337), "
            "13 Ekim 1923 — «Ankara Türkiye devletinin makarrıdır»"
        ),
        "note":       "1923-10-13 大國民議會立法宣布安卡拉為首都，早於共和國宣告（1923-10-29）。",
    },
    # ── 波蘭第二共和 Polish Republic（1918–1939）首都：華沙 ──────────────────
    {
        "_id":        "CAP_WARSAW_POLISH_REPUBLIC",
        "regimeId":   "01a18e71-cbd6-7acf-83d7-f158c47d6c31",  # slug: polish-republic
        "cityName":   {"en": "Warsaw", "zh": "華沙", "pl": "Warszawa"},
        "location":   {"type": "Point", "coordinates": [21.012, 52.230]},
        "validStart": "1918-11-11",
        "validEnd":   "1939-09-28",
        "sourceRef":  (
            "Konstytucja Rzeczypospolitej Polskiej z 17 marca 1921 r., art. 5 — "
            "«Stolica Rzeczypospolitej jest Warszawa»"
        ),
        "note":       "1918-11-11 波蘭恢復獨立。1939-09-28 華沙守城投降（德軍佔領）。",
    },
    # ── 捷克斯洛伐克共和國（1918–1939）首都：布拉格 ──────────────────────────
    {
        "_id":        "CAP_PRAGUE_CZECHOSLOVAK_REPUBLIC",
        "regimeId":   "01a18e71-cbb8-79ec-af68-6ecc0a00e35a",  # slug: czechoslovak-republic
        "cityName":   {"en": "Prague", "zh": "布拉格", "cs": "Praha"},
        "location":   {"type": "Point", "coordinates": [14.438, 50.076]},
        "validStart": "1918-10-28",
        "validEnd":   "1939-03-15",
        "sourceRef":  (
            "Ústava Republiky Československé ze dne 29. února 1920, §1 — "
            "«Praha je sídelním městem republiky»"
        ),
        "note":       "1918-10-28 捷克斯洛伐克宣布獨立。1939-03-15 德軍佔領布拉格，設波希米亞—摩拉維亞保護國。",
    },
    # ── 塞爾維亞王國 Kingdom of Serbia（–1918）首都：貝爾格勒 ──────────────
    {
        "_id":        "CAP_BELGRADE_KINGDOM_SERBIA",
        "regimeId":   "01a192dc-6732-710b-a6ff-82d3cdf1455f",  # slug: kingdom-of-serbia
        "cityName":   {"en": "Belgrade", "zh": "貝爾格勒", "sr": "Beograd"},
        "location":   {"type": "Point", "coordinates": [20.465, 44.818]},
        "validStart": "1908-01-01",
        "validEnd":   "1918-12-01",
        "sourceRef":  (
            "Ustav Kraljevine Srbije od 5. juna 1903 — "
            "Beograd kao prestonica Kraljevine Srbije"
        ),
        "note":       "1908 為本批起點（含 1903 憲法後）。1918-12-01 塞—克—斯王國成立。",
    },
    # ── 塞爾維亞—克羅埃西亞—斯洛維尼亞王國（1918–1929）首都：貝爾格勒 ────────
    {
        "_id":        "CAP_BELGRADE_KSCS",
        "regimeId":   "01a193a2-be65-76de-9a37-06dfbeb0ae3d",  # slug: kingdom-of-serbs-croats-and-slovenes
        "cityName":   {"en": "Belgrade", "zh": "貝爾格勒", "sr": "Beograd"},
        "location":   {"type": "Point", "coordinates": [20.465, 44.818]},
        "validStart": "1918-12-01",
        "validEnd":   "1929-10-03",
        "sourceRef":  (
            "Vidovdanski ustav (Constitution of the Kingdom of Serbs, Croats and Slovenes), "
            "28. juni 1921 — Beograd kao prestonica Kraljevine"
        ),
        "note":       "1929-10-03 國王亞歷山大一世頒布王室公告，王國更名南斯拉夫王國。",
    },
    # ── 南斯拉夫王國 Kingdom of Yugoslavia（1929–1941）首都：貝爾格勒 ──────────
    {
        "_id":        "CAP_BELGRADE_YUGOSLAVIA",
        "regimeId":   "01a18e71-cc9a-75a4-b6d6-0045e85f83c3",  # slug: kingdom-of-yugoslavia
        "cityName":   {"en": "Belgrade", "zh": "貝爾格勒", "sr": "Beograd"},
        "location":   {"type": "Point", "coordinates": [20.465, 44.818]},
        "validStart": "1929-10-03",
        "validEnd":   "1941-04-17",
        "sourceRef":  (
            "Ustav Kraljevine Jugoslavije, 3. septembra 1931 — "
            "Beograd kao prestonica Kraljevine Jugoslavije"
        ),
        "note":       "1929-10-03 王國更名。1941-04-17 南斯拉夫向軸心國投降。",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # 第 2 批（2026-11-02）── 巴爾幹、北歐/波羅的海、伊比利、比荷盧瑞士、匈牙利、
    #                         日本、中華民國、滿洲國、泰國
    # regimeId 由 GET /api/v1/sovereignty?date=<date> 查得，或直接取自
    # sovereignty_records 資料表（2026-11-02 查詢）。
    # ═══════════════════════════════════════════════════════════════════════════

    # ── 保加利亞王國（Tsarstvo Balgariya，1908–1946）首都：索菲亞 ──────────────
    {
        "_id":        "CAP_SOFIA_TSARDOM_BULGARIA",
        "regimeId":   "01a18e71-cc4c-7dd5-930e-4d94f1c86ac3",  # slug: tsardom-of-bulgaria
        "cityName":   {"en": "Sofia", "zh": "索菲亞", "bg": "София"},
        "location":   {"type": "Point", "coordinates": [23.323, 42.698]},
        "validStart": "1908-10-05",
        "validEnd":   "1945-09-03",
        "sourceRef":  (
            "Търновска конституция (Tarnovo Constitution), 1879, чл. 2 — «Столицата на царството е София»；"
            "1908-10-05 保加利亞宣布脫離鄂圖曼帝國完全獨立（格里高曆），費迪南一世稱沙皇"
        ),
        "note":       "索菲亞自 1879 年起為保加利亞首都。1944-09-09 親蘇政變；1946-09-15 公投廢除君主制，改為保加利亞人民共和國。",
    },

    # ── 羅馬尼亞王國（Kingdom of Romania，1881–1947）首都：布加勒斯特 ─────────
    {
        "_id":        "CAP_BUCHAREST_ROMANIA_1908",
        "regimeId":   "01a18e71-cc3f-7004-8299-9781046c6937",  # slug: kingdom-of-romania
        "cityName":   {"en": "Bucharest", "zh": "布加勒斯特", "ro": "București"},
        "location":   {"type": "Point", "coordinates": [26.097, 44.440]},
        "validStart": "1908-01-01",
        "validEnd":   "1916-11-24",
        "sourceRef":  (
            "Constituțiunea Principatelor Unite ale Moldovei și Valahiei, 1866 "
            "(later Constituția Regatului României, 1879) — Bucureşti, capitala ţării"
        ),
        "note":       "1908 為本批起點，非王國建國日（1881-03-26）。1916-11-23 羅馬尼亞政府疏散，遷往雅西（Iași）；12-06 德軍佔領布加勒斯特。",
    },
    # ── 羅馬尼亞王國（暫遷首都：雅西，1916–1918）────────────────────────────────
    {
        "_id":        "CAP_IASI_ROMANIA_WWI",
        "regimeId":   "01a18e71-cc3f-7004-8299-9781046c6937",  # slug: kingdom-of-romania
        "cityName":   {"en": "Iași", "zh": "雅西", "ro": "Iași"},
        "location":   {"type": "Point", "coordinates": [27.587, 47.157]},
        "validStart": "1916-11-24",
        "validEnd":   "1918-11-10",
        "sourceRef":  (
            "待查證（政府疏散令，1916年11月；雅西為羅馬尼亞王室與政府戰時駐地）"
        ),
        "note":       "德軍占領布加勒斯特期間，王室與政府遷往雅西。1918-11-10 羅馬尼亞軍重返布加勒斯特。",
    },
    # ── 羅馬尼亞王國（首都回遷布加勒斯特，1918–）─────────────────────────────────
    {
        "_id":        "CAP_BUCHAREST_ROMANIA_1918",
        "regimeId":   "01a18e71-cc3f-7004-8299-9781046c6937",  # slug: kingdom-of-romania
        "cityName":   {"en": "Bucharest", "zh": "布加勒斯特", "ro": "București"},
        "location":   {"type": "Point", "coordinates": [26.097, 44.440]},
        "validStart": "1918-11-10",
        "validEnd":   "1945-09-03",
        "sourceRef":  (
            "待查證（羅馬尼亞軍 1918-11-10 重返布加勒斯特；"
            "Constituția Republicii Populare Române, 1947-12-30 廢除君主制）"
        ),
        "note":       "1918-11-10 首都回遷布加勒斯特。1947-12-30 廢除君主制，成立羅馬尼亞人民共和國。",
    },

    # ── 希臘王國（Kingdom of Greece，1832–1924，1935–1974）首都：雅典 ──────────
    {
        "_id":        "CAP_ATHENS_KINGDOM_GREECE_1908",
        "regimeId":   "01a18e71-cca2-7cbd-ab0f-146724b4b493",  # slug: kingdom-of-greece
        "cityName":   {"en": "Athens", "zh": "雅典", "el": "Αθήνα"},
        "location":   {"type": "Point", "coordinates": [23.728, 37.983]},
        "validStart": "1908-01-01",
        "validEnd":   "1924-03-25",
        "sourceRef":  (
            "Σύνταγμα Ελλάδος 1911, άρθρο 1 — «Πρωτεύουσα του Βασιλείου είναι αι Αθήναι»"
        ),
        "note":       "1908 為本批起點。1924-03-25 希臘宣布廢除君主制，成立第二希臘共和國。",
    },
    # ── 希臘王國（恢復君主，1935–1945+）────────────────────────────────────────
    {
        "_id":        "CAP_ATHENS_KINGDOM_GREECE_1935",
        "regimeId":   "01a18e71-cca2-7cbd-ab0f-146724b4b493",  # slug: kingdom-of-greece
        "cityName":   {"en": "Athens", "zh": "雅典", "el": "Αθήνα"},
        "location":   {"type": "Point", "coordinates": [23.728, 37.983]},
        "validStart": "1935-11-03",
        "validEnd":   None,
        "sourceRef":  (
            "Ψήφισμα της Βουλής Ελλάδος, 3 Νοεμβρίου 1935 — "
            "復辟君主制，喬治二世返國"
        ),
        "note":       "1935-11-03 公投恢復君主制，喬治二世復辟。雅典全程為首都。",
    },
    # ── 第二希臘共和國（Second Hellenic Republic，1924–1935）首都：雅典 ──────────
    {
        "_id":        "CAP_ATHENS_SECOND_HELLENIC_REPUBLIC",
        "regimeId":   "01a193e1-5a70-71aa-b09b-6c5c637fb3ef",  # slug: second-hellenic-republic
        "cityName":   {"en": "Athens", "zh": "雅典", "el": "Αθήνα"},
        "location":   {"type": "Point", "coordinates": [23.728, 37.983]},
        "validStart": "1924-03-25",
        "validEnd":   "1935-11-03",
        "sourceRef":  (
            "Ψήφισμα Δ' Εθνοσυνελεύσεως, 25 Μαρτίου 1924 — "
            "«Ανακηρύσσεται η Ελλάς ως Αβασίλευτος Δημοκρατία»"
        ),
        "note":       "1924-03-25 希臘宣布共和；1935-11-03 公投恢復君主制。雅典全程為首都。",
    },

    # ── 蒙特內哥羅親王國（Principality of Montenegro，1852–1910）首都：采蒂涅 ─────
    {
        "_id":        "CAP_CETINJE_PRINCIPALITY_MONTENEGRO",
        "regimeId":   "01a192dc-68ae-7cce-9335-607da931b3e1",  # slug: principality-of-montenegro
        "cityName":   {"en": "Cetinje", "zh": "采蒂涅", "sr": "Цетиње"},
        "location":   {"type": "Point", "coordinates": [18.916, 42.390]},
        "validStart": "1908-01-01",
        "validEnd":   "1910-08-28",
        "sourceRef":  (
            "待查證（采蒂涅自 1482 年起為蒙特內哥羅歷史首都；"
            "1878 年柏林條約正式承認蒙特內哥羅獨立）"
        ),
        "note":       "1908 為本批起點。1910-08-28 尼古拉一世宣布升格為王國。",
    },
    # ── 蒙特內哥羅王國（Kingdom of Montenegro，1910–1918）首都：采蒂涅 ─────────
    {
        "_id":        "CAP_CETINJE_KINGDOM_MONTENEGRO",
        "regimeId":   "01a192dc-6a27-7178-87f5-4f8643d8be55",  # slug: kingdom-of-montenegro
        "cityName":   {"en": "Cetinje", "zh": "采蒂涅", "sr": "Цетиње"},
        "location":   {"type": "Point", "coordinates": [18.916, 42.390]},
        "validStart": "1910-08-28",
        "validEnd":   "1918-11-26",
        "sourceRef":  (
            "待查證（1910-08-28 尼古拉一世宣布蒙特內哥羅為王國，采蒂涅繼續為首都）"
        ),
        "note":       "1918-11-26 波多里察議會宣布廢黜尼古拉一世，蒙特內哥羅加入塞—克—斯王國。",
    },

    # ── 阿爾巴尼亞臨時政府（Albania Provisional Government，1912–1914）首都：發羅拉 ─
    {
        "_id":        "CAP_VLORE_ALBANIA_PROVISIONAL_1912",
        "regimeId":   "01a192dc-6b59-7e6d-9fd2-e10db273111c",  # slug: albania-provisional-government-1912
        "cityName":   {"en": "Vlorë", "zh": "發羅拉", "sq": "Vlorë"},
        "location":   {"type": "Point", "coordinates": [19.488, 40.466]},
        "validStart": "1912-11-28",
        "validEnd":   "1914-02-21",
        "sourceRef":  (
            "Deklarata e Pavarësisë (Albanian Declaration of Independence), "
            "28 nëntor 1912 — Vlorë si qendër e Qeverisë Përkohshme"
        ),
        "note":       "1912-11-28 伊斯邁爾·卻馬里在發羅拉宣布阿爾巴尼亞獨立，臨時政府設於此地。",
    },
    # ── 阿爾巴尼亞親王國（Principality of Albania，1914–1925）首都：都拉斯→地拉那 ──
    {
        "_id":        "CAP_DURRES_PRINCIPALITY_ALBANIA",
        "regimeId":   "01a192dc-6d11-7054-9b73-d55ceefccf41",  # slug: principality-of-albania
        "cityName":   {"en": "Durrës", "zh": "都拉斯", "sq": "Durrës"},
        "location":   {"type": "Point", "coordinates": [19.456, 41.322]},
        "validStart": "1914-02-21",
        "validEnd":   "1920-01-31",
        "sourceRef":  (
            "待查證（威廉親王（Wilhelm zu Wied）1914-03-07 於都拉斯登陸；"
            "國際控制委員會（International Control Commission）駐都拉斯）"
        ),
        "note":       "1914-02-21 大國承認阿爾巴尼亞親王國；威廉親王駐都拉斯。1920-01-31 盧什涅大會（Kuvendi i Lushnjes）選定地拉那為首都。",
    },
    {
        "_id":        "CAP_TIRANA_PRINCIPALITY_ALBANIA",
        "regimeId":   "01a192dc-6d11-7054-9b73-d55ceefccf41",  # slug: principality-of-albania
        "cityName":   {"en": "Tirana", "zh": "地拉那", "sq": "Tiranë"},
        "location":   {"type": "Point", "coordinates": [19.819, 41.330]},
        "validStart": "1920-01-31",
        "validEnd":   "1925-01-21",
        "sourceRef":  (
            "Kuvendi i Lushnjes (Congress of Lushnjë), 21–31 janar 1920 — "
            "Tirana u zgjodh si kryeqyteti i Shqipërisë"
        ),
        "note":       "1920-01-31 盧什涅大會正式決議將首都遷往地拉那。1925-01-21 宣布共和。",
    },
    # ── 阿爾巴尼亞共和國（Albanian Republic，1925–1928）首都：地拉那 ──────────
    {
        "_id":        "CAP_TIRANA_ALBANIAN_REPUBLIC_1925",
        "regimeId":   "01a193e1-5a79-75bb-a8dc-a0b3a9702368",  # slug: albanian-republic-1925
        "cityName":   {"en": "Tirana", "zh": "地拉那", "sq": "Tiranë"},
        "location":   {"type": "Point", "coordinates": [19.819, 41.330]},
        "validStart": "1925-01-21",
        "validEnd":   "1928-09-01",
        "sourceRef":  (
            "Statuti Themelor i Republikës Shqiptare, 21 janar 1925 — "
            "Tirana si kryeqytet i Republikës"
        ),
        "note":       "1925-01-21 阿爾巴尼亞宣布共和，索古（Ahmet Zogu）為總統。1928-09-01 改制為王國。",
    },
    # ── 阿爾巴尼亞王國（Kingdom of Albania，1928–1939）首都：地拉那 ──────────────
    {
        "_id":        "CAP_TIRANA_ALBANIAN_KINGDOM",
        "regimeId":   "01a18e71-cc56-77ed-9ef5-cd8a617d57e7",  # slug: albanian-kingdom
        "cityName":   {"en": "Tirana", "zh": "地拉那", "sq": "Tiranë"},
        "location":   {"type": "Point", "coordinates": [19.819, 41.330]},
        "validStart": "1928-09-01",
        "validEnd":   "1939-04-12",
        "sourceRef":  (
            "Statuti Themelor i Mbretërisë Shqiptare, 1 shtator 1928 — "
            "Tirana si kryeqytet i Mbretërisë"
        ),
        "note":       "1928-09-01 索古一世（Zog I）宣布建立阿爾巴尼亞王國。1939-04-12 義大利兼併，王國終止。",
    },

    # ── 安卡拉大國民議會政府（Grand National Assembly，1920–1923）首都：安卡拉 ────
    {
        "_id":        "CAP_ANKARA_GRAND_NATIONAL_ASSEMBLY",
        "regimeId":   "01a193a2-bef1-7786-9b0f-2339f992c043",  # slug: government-of-the-grand-national-assembly
        "cityName":   {"en": "Ankara", "zh": "安卡拉", "tr": "Ankara"},
        "location":   {"type": "Point", "coordinates": [32.860, 39.933]},
        "validStart": "1920-04-23",
        "validEnd":   "1923-10-29",
        "sourceRef":  (
            "Türkiye Büyük Millet Meclisi'nin 1920-04-23 açılışı — "
            "Ankara, Millî Hükümetin merkezi；"
            "Ankara'nın başşehir olması hakkında kanun (Kanun No. 337), 13 Ekim 1923"
        ),
        "note":       "1920-04-23 大國民議會在安卡拉開幕，凱末爾主導的民族政府以安卡拉為中心。1923-10-29 宣布建立土耳其共和國。",
    },

    # ── 丹麥王國（Kingdom of Denmark）首都：哥本哈根 ──────────────────────────────
    {
        "_id":        "CAP_COPENHAGEN_KINGDOM_DENMARK",
        "regimeId":   "01a18e71-ccdd-79ff-a132-e08d28620a8c",  # slug: kingdom-of-denmark
        "cityName":   {"en": "Copenhagen", "zh": "哥本哈根", "da": "København"},
        "location":   {"type": "Point", "coordinates": [12.569, 55.677]},
        "validStart": "1908-01-01",
        "validEnd":   None,
        "sourceRef":  (
            "Danmarks Riges Grundlov (Danish Constitution), 5. juni 1849, §17 — "
            "«Kongens Residens er i København»"
        ),
        "note":       "1908 為本批起點。二戰期間（1940-04-09–1945-05-05）丹麥被德軍佔領，但政府留守哥本哈根，首都不變。",
    },

    # ── 挪威王國（Kingdom of Norway）首都：克里斯蒂安尼亞→奧斯陸 ──────────────
    {
        "_id":        "CAP_KRISTIANIA_KINGDOM_NORWAY",
        "regimeId":   "01a18e71-cce4-71c8-974d-3b6c9bd0c090",  # slug: kingdom-of-norway
        "cityName":   {"en": "Christiania / Kristiania", "zh": "克里斯蒂安尼亞", "no": "Kristiania"},
        "location":   {"type": "Point", "coordinates": [10.740, 59.913]},
        "validStart": "1908-01-01",
        "validEnd":   "1925-01-01",
        "sourceRef":  (
            "Lov om Norges Riges Grundlov (Norwegian Constitution), 1814, §1 — "
            "Christiania (Kristiania) som kongens residensby；"
            "城市正式更名 Kristiania 1877；"
            "Bystyret vedtak 1924 — rename to Oslo effective 1 Jan 1925"
        ),
        "note":       "城市名稱：Christiania（至1877）→ Kristiania（1877–1924）→ Oslo（1925起）。同一地點，分為兩段紀錄。",
    },
    {
        "_id":        "CAP_OSLO_KINGDOM_NORWAY",
        "regimeId":   "01a18e71-cce4-71c8-974d-3b6c9bd0c090",  # slug: kingdom-of-norway
        "cityName":   {"en": "Oslo", "zh": "奧斯陸", "no": "Oslo"},
        "location":   {"type": "Point", "coordinates": [10.740, 59.913]},
        "validStart": "1925-01-01",
        "validEnd":   None,
        "sourceRef":  (
            "Lov 11. juli 1924 om Kristianias navn — by 1 January 1925: Oslo；"
            "Grunnloven §§ 68, 74 — Stortinget samles i Riksstaden Oslo"
        ),
        "note":       "1925-01-01 城市更名為 Oslo。1940-06–1945-05 挪威被德軍佔領，政府流亡倫敦，奧斯陸仍為法定首都。",
    },

    # ── 瑞典王國（Kingdom of Sweden）首都：斯德哥爾摩 ───────────────────────────
    {
        "_id":        "CAP_STOCKHOLM_KINGDOM_SWEDEN",
        "regimeId":   "01a18e71-ccec-7db3-8170-716965effb83",  # slug: kingdom-of-sweden
        "cityName":   {"en": "Stockholm", "zh": "斯德哥爾摩", "sv": "Stockholm"},
        "location":   {"type": "Point", "coordinates": [18.068, 59.330]},
        "validStart": "1908-01-01",
        "validEnd":   None,
        "sourceRef":  (
            "Sveriges Riksdag — Stockholm, rikets huvudstad och konungens residens；"
            "待查證（斯德哥爾摩自 14 世紀末起為瑞典實際首都）"
        ),
        "note":       "1908 為本批起點。瑞典在二戰期間保持中立，首都未遷。",
    },

    # ── 芬蘭共和國（Republic of Finland，1917–）首都：赫爾辛基 ──────────────────
    {
        "_id":        "CAP_HELSINKI_REPUBLIC_FINLAND",
        "regimeId":   "01a18e71-cc37-7c3d-af5a-4c180d46e817",  # slug: republic-of-finland
        "cityName":   {"en": "Helsinki", "zh": "赫爾辛基", "fi": "Helsinki", "sv": "Helsingfors"},
        "location":   {"type": "Point", "coordinates": [24.938, 60.170]},
        "validStart": "1917-12-06",
        "validEnd":   None,
        "sourceRef":  (
            "Suomen itsenäisyysjulistus (Finnish Declaration of Independence), "
            "6 joulukuuta 1917 — Helsinki pääkaupunkina；"
            "Suomen Hallitusmuoto (Finnish Constitution), 17 heinäkuuta 1919, §2"
        ),
        "note":       "1917-12-06 芬蘭宣布獨立。赫爾辛基（瑞典語：Helsingfors）自 1812 年起為芬蘭大公國首府。",
    },

    # ── 愛沙尼亞共和國（Republic of Estonia，1918–1940）首都：塔林 ───────────────
    {
        "_id":        "CAP_TALLINN_REPUBLIC_ESTONIA",
        "regimeId":   "01a18e71-cc18-734e-aad0-ed7c48d0271e",  # slug: republic-of-estonia
        "cityName":   {"en": "Tallinn", "zh": "塔林", "et": "Tallinn"},
        "location":   {"type": "Point", "coordinates": [24.745, 59.437]},
        "validStart": "1918-02-24",
        "validEnd":   "1940-07-21",
        "sourceRef":  (
            "Eesti iseseisvusmanifest (Estonian Declaration of Independence), "
            "24. veebruar 1918 — Tallinn (endine Reval) pealinnaks；"
            "Eesti Vabariigi Põhiseadus, 1920, §1"
        ),
        "note":       "城市德語舊名：Reval（1918年前）；愛沙尼亞語改稱 Tallinn（1919年起通行）。1940-07-21 蘇聯佔領，愛沙尼亞蘇維埃社會主義共和國成立。",
    },

    # ── 拉脫維亞共和國（Republic of Latvia，1918–1940）首都：里加 ──────────────
    {
        "_id":        "CAP_RIGA_REPUBLIC_LATVIA",
        "regimeId":   "01a18e71-cc00-726a-b6fd-f06f10b734ee",  # slug: republic-of-latvia
        "cityName":   {"en": "Riga", "zh": "里加", "lv": "Rīga"},
        "location":   {"type": "Point", "coordinates": [24.106, 56.946]},
        "validStart": "1918-11-18",
        "validEnd":   "1940-07-21",
        "sourceRef":  (
            "Latvijas Neatkarības proklamēšana (Latvian Declaration of Independence), "
            "18. novembris 1918 — Rīga kā galvaspilsēta；"
            "Latvijas Satversme (Constitution), 1922, 2. pants"
        ),
        "note":       "1918-11-18 拉脫維亞宣布獨立。1940-07-21 蘇聯兼併，拉脫維亞蘇維埃社會主義共和國成立。",
    },

    # ── 立陶宛共和國（Republic of Lithuania，1918–1940）首都：考納斯→維爾紐斯 ────
    {
        "_id":        "CAP_KAUNAS_REPUBLIC_LITHUANIA",
        "regimeId":   "01a18e71-cbeb-7713-a547-b57e23a57220",  # slug: republic-of-lithuania
        "cityName":   {"en": "Kaunas", "zh": "考納斯", "lt": "Kaunas"},
        "location":   {"type": "Point", "coordinates": [23.900, 54.897]},
        "validStart": "1918-11-16",
        "validEnd":   "1939-10-28",
        "sourceRef":  (
            "待查證（1920-02-20 Seimas 決議以考納斯為臨時首都，因維爾紐斯遭波蘭佔領；"
            "Lietuvos Valstybės Konstitucija, 1922, 2 straipsnis — «Sostinė Vilnius»，但因佔領實際以考納斯為首都）"
        ),
        "note":       "歷史首都維爾紐斯（Vilnius）1920 年起被波蘭佔領，考納斯成為臨時首都直至 1939 年。",
    },
    {
        "_id":        "CAP_VILNIUS_REPUBLIC_LITHUANIA",
        "regimeId":   "01a18e71-cbeb-7713-a547-b57e23a57220",  # slug: republic-of-lithuania
        "cityName":   {"en": "Vilnius", "zh": "維爾紐斯", "lt": "Vilnius"},
        "location":   {"type": "Point", "coordinates": [25.279, 54.687]},
        "validStart": "1939-10-28",
        "validEnd":   "1940-07-21",
        "sourceRef":  (
            "Sovietų ir Lietuvos sutartis, 1939-10-10 — "
            "SSRS perduoda Vilnių Lietuvai；1939-10-28 Lietuva perima Vilnių"
        ),
        "note":       "1939-10-10 蘇聯—立陶宛條約，蘇聯將維爾紐斯歸還立陶宛；1939-10-28 立陶宛接管。1940-07-21 蘇聯兼併。",
    },

    # ── 冰島王國（Kingdom of Iceland，1918–1944）首都：雷克雅維克 ─────────────
    {
        "_id":        "CAP_REYKJAVIK_KINGDOM_ICELAND",
        "regimeId":   "01a193a2-be6d-7b59-8cab-83a0fb45bce6",  # slug: kingdom-of-iceland
        "cityName":   {"en": "Reykjavik", "zh": "雷克雅維克", "is": "Reykjavík"},
        "location":   {"type": "Point", "coordinates": [-21.933, 64.133]},
        "validStart": "1918-12-01",
        "validEnd":   "1944-06-17",
        "sourceRef":  (
            "Lög um ríkisstjórn Íslands (Act of Union between Denmark and Iceland), "
            "1. desember 1918 — Ísland sjálfstætt konungsríki í sambandi við Danmörku；"
            "Reykjavík sem höfuðborg"
        ),
        "note":       "1918-12-01 冰島成為與丹麥聯合的獨立王國。1944-06-17 宣布共和。",
    },
    # ── 冰島共和國（Republic of Iceland，1944–）首都：雷克雅維克 ──────────────
    {
        "_id":        "CAP_REYKJAVIK_REPUBLIC_ICELAND",
        "regimeId":   "01a1940e-f418-7b78-87a9-97862cd2c713",  # slug: republic-of-iceland
        "cityName":   {"en": "Reykjavik", "zh": "雷克雅維克", "is": "Reykjavík"},
        "location":   {"type": "Point", "coordinates": [-21.933, 64.133]},
        "validStart": "1944-06-17",
        "validEnd":   None,
        "sourceRef":  (
            "Stjórnarskrá lýðveldisins Íslands, 17. júní 1944 — "
            "Reykjavík sem höfuðborg lýðveldisins"
        ),
        "note":       "1944-06-17 冰島宣布廢除丹麥—冰島聯盟，成立共和國。",
    },

    # ── 葡萄牙王國（Kingdom of Portugal，1143–1910）首都：里斯本 ─────────────────
    {
        "_id":        "CAP_LISBON_KINGDOM_PORTUGAL",
        "regimeId":   "01a192dc-7631-793c-9e5b-4b55554afc51",  # slug: kingdom-of-portugal
        "cityName":   {"en": "Lisbon", "zh": "里斯本", "pt": "Lisboa"},
        "location":   {"type": "Point", "coordinates": [-9.139, 38.717]},
        "validStart": "1908-01-01",
        "validEnd":   "1910-10-05",
        "sourceRef":  (
            "待查證（里斯本自 1255 年起為葡萄牙首都）"
        ),
        "note":       "1908 為本批起點（含 1908-02-01 卡洛斯一世遇刺後曼努埃爾二世繼位）。1910-10-05 共和革命，王國終止。",
    },
    # ── 葡萄牙共和國（Portuguese Republic，1910–）首都：里斯本 ──────────────────
    {
        "_id":        "CAP_LISBON_PORTUGUESE_REPUBLIC",
        "regimeId":   "01a18e71-ccc4-76ef-a4ef-157823b5a1ca",  # slug: portuguese-republic
        "cityName":   {"en": "Lisbon", "zh": "里斯本", "pt": "Lisboa"},
        "location":   {"type": "Point", "coordinates": [-9.139, 38.717]},
        "validStart": "1910-10-05",
        "validEnd":   None,
        "sourceRef":  (
            "Constituição Política da República Portuguesa, 21 de agosto de 1911, art. 1 — "
            "Lisboa, capital da República"
        ),
        "note":       "1910-10-05 共和革命成功。薩拉查（Estado Novo）1933 年新憲法後政體轉型，但里斯本仍為首都。",
    },

    # ── 西班牙王國（Kingdom of Spain，1874–1931 波旁王朝復辟）首都：馬德里 ──────
    {
        "_id":        "CAP_MADRID_KINGDOM_SPAIN",
        "regimeId":   "01a192dc-754f-764a-bece-b9aeb270a008",  # slug: kingdom-of-spain
        "cityName":   {"en": "Madrid", "zh": "馬德里", "es": "Madrid"},
        "location":   {"type": "Point", "coordinates": [-3.702, 40.416]},
        "validStart": "1908-01-01",
        "validEnd":   "1931-04-14",
        "sourceRef":  (
            "Constitución de la Monarquía Española, 30 de junio de 1876, art. 39 — "
            "«Las Cortes se reunirán todos los años en la capital de la Monarquía»（Madrid）"
        ),
        "note":       "1908 為本批起點。1931-04-14 地方選舉後共和派勝利，阿方索十三世出走，宣布共和。",
    },
    # ── 西班牙第二共和國（Spanish Republic，1931–1939）首都：馬德里→瓦倫西亞→巴塞隆納
    {
        "_id":        "CAP_MADRID_SPANISH_REPUBLIC",
        "regimeId":   "01a18e71-ccb3-70ab-8663-74a509f73437",  # slug: spanish-republic
        "cityName":   {"en": "Madrid", "zh": "馬德里", "es": "Madrid"},
        "location":   {"type": "Point", "coordinates": [-3.702, 40.416]},
        "validStart": "1931-04-14",
        "validEnd":   "1936-11-06",
        "sourceRef":  (
            "Constitución de la República Española, 9 de diciembre de 1931, art. 5 — "
            "«La capital de la República se fija en Madrid»"
        ),
        "note":       "1936-11-06 因佛朗哥軍迫近馬德里，共和國政府遷往瓦倫西亞。",
    },
    {
        "_id":        "CAP_VALENCIA_SPANISH_REPUBLIC",
        "regimeId":   "01a18e71-ccb3-70ab-8663-74a509f73437",  # slug: spanish-republic
        "cityName":   {"en": "Valencia", "zh": "瓦倫西亞", "es": "Valencia"},
        "location":   {"type": "Point", "coordinates": [-0.377, 39.470]},
        "validStart": "1936-11-06",
        "validEnd":   "1937-11-01",
        "sourceRef":  (
            "待查證（共和國政府令 1936-11-06，遷都至瓦倫西亞；"
            "Decreto de traslado del Gobierno de la República, noviembre 1936）"
        ),
        "note":       "1937-10-31 政府再遷巴塞隆納；1937-11-01 生效。",
    },
    {
        "_id":        "CAP_BARCELONA_SPANISH_REPUBLIC",
        "regimeId":   "01a18e71-ccb3-70ab-8663-74a509f73437",  # slug: spanish-republic
        "cityName":   {"en": "Barcelona", "zh": "巴塞隆納", "es": "Barcelona", "ca": "Barcelona"},
        "location":   {"type": "Point", "coordinates": [2.177, 41.385]},
        "validStart": "1937-11-01",
        "validEnd":   "1939-04-01",
        "sourceRef":  (
            "待查證（共和國政府 1937-10-31 令遷往巴塞隆納；"
            "1939-01-26 佛朗哥軍攻陷巴塞隆納，政府出走法國；"
            "1939-04-01 佛朗哥宣布內戰結束）"
        ),
        "note":       "1939-01-26 巴塞隆納陷落後，政府短暫在赫羅納（Girona）與法國流亡，共和國實際覆滅。",
    },
    # ── 西班牙民族主義區（Spanish Nationalist Zone，1936–1939）首都：布爾戈斯 ────
    {
        "_id":        "CAP_BURGOS_SPANISH_NATIONALIST",
        "regimeId":   "01a193e2-129b-7b72-bc30-f6aa96f416ce",  # slug: spanish-nationalist-zone
        "cityName":   {"en": "Burgos", "zh": "布爾戈斯", "es": "Burgos"},
        "location":   {"type": "Point", "coordinates": [-3.700, 42.344]},
        "validStart": "1936-07-17",
        "validEnd":   "1939-04-01",
        "sourceRef":  (
            "Junta de Defensa Nacional de España, creada 24 de julio de 1936, sede en Burgos；"
            "Decreto no. 138 (1936-09-29) — Francisco Franco como Jefe del Gobierno del Estado, "
            "Burgos como sede del Gobierno"
        ),
        "note":       "1936-07-17 內戰爆發。民族主義政府以布爾戈斯為中心。1939-04-01 佛朗哥宣布勝利，內戰結束。",
    },
    # ── 西班牙（佛朗哥政權，Spanish State，1939–1975）首都：馬德里 ──────────────
    {
        "_id":        "CAP_MADRID_SPANISH_STATE",
        "regimeId":   "01a18e71-ccbd-7a45-84f8-b9b537d8b769",  # slug: spanish-state
        "cityName":   {"en": "Madrid", "zh": "馬德里", "es": "Madrid"},
        "location":   {"type": "Point", "coordinates": [-3.702, 40.416]},
        "validStart": "1939-04-01",
        "validEnd":   None,
        "sourceRef":  (
            "Ley de 8 de agosto de 1939 — España organizada como Estado Totalitario；"
            "佛朗哥政府 1939-04-01 起定都馬德里"
        ),
        "note":       "1939-04-01 佛朗哥宣布內戰結束，馬德里為西班牙國首都。政體為威權法西斯式體制（Estado Español）。",
    },

    # ── 比利時王國（Kingdom of Belgium，1831–）首都：布魯塞爾 ─────────────────────
    {
        "_id":        "CAP_BRUSSELS_KINGDOM_BELGIUM",
        "regimeId":   "01a18e71-cc81-7d72-82e7-ac0e3ca50fd1",  # slug: kingdom-of-belgium
        "cityName":   {"en": "Brussels", "zh": "布魯塞爾", "fr": "Bruxelles", "nl": "Brussel"},
        "location":   {"type": "Point", "coordinates": [4.352, 50.846]},
        "validStart": "1908-01-01",
        "validEnd":   None,
        "sourceRef":  (
            "Constitution belge, 7 février 1831, art. 35 — "
            "«Le siège du Gouvernement est établi à Bruxelles»"
        ),
        "note":       (
            "1908 為本批起點。"
            "一戰（1914-08-20–1918-11-22）比利時政府流亡法國聖阿德雷斯（Sainte-Adresse），布魯塞爾遭德軍佔領但仍為法定首都。"
            "二戰（1940-05-28–1944-09-04）德軍再次佔領；政府流亡倫敦。"
        ),
    },

    # ── 荷蘭王國（Kingdom of the Netherlands）首都（政府席位）：海牙 ───────────
    {
        "_id":        "CAP_THE_HAGUE_KINGDOM_NETHERLANDS",
        "regimeId":   "01a18e71-cc89-7c9d-a814-11a67de9f6c6",  # slug: kingdom-of-the-netherlands
        "cityName":   {"en": "The Hague", "zh": "海牙", "nl": "Den Haag"},
        "location":   {"type": "Point", "coordinates": [4.297, 52.076]},
        "validStart": "1908-01-01",
        "validEnd":   None,
        "sourceRef":  (
            "Grondwet voor het Koninkrijk der Nederlanden, 1840/1848 — "
            "'s-Gravenhage (Den Haag) als zetel van de Staten-Generaal en de Regering；"
            "Amsterdam is de formele hoofdstad (Grondwet, art. 32, kroning)"
        ),
        "note":       (
            "1908 為本批起點。阿姆斯特丹為憲法規定的形式首都（王室加冕地），但政府、議會、外交機關均設於海牙。"
            "1940-05-15–1945-05-05 德軍佔領，女王威廉明娜政府流亡倫敦；海牙仍為法定政府席位。"
        ),
    },

    # ── 盧森堡大公國（Grand Duchy of Luxembourg）首都：盧森堡市 ──────────────────
    {
        "_id":        "CAP_LUXEMBOURG_CITY_GRAND_DUCHY",
        "regimeId":   "01a18e71-cc91-7b22-aa9b-310fd6f30ea7",  # slug: grand-duchy-of-luxembourg
        "cityName":   {"en": "Luxembourg City", "zh": "盧森堡市", "fr": "Luxembourg", "lb": "Lëtzebuerg"},
        "location":   {"type": "Point", "coordinates": [6.131, 49.610]},
        "validStart": "1908-01-01",
        "validEnd":   None,
        "sourceRef":  (
            "Constitution du Grand-Duché de Luxembourg, 17 octobre 1868, art. 30 — "
            "«Le siège du gouvernement est à Luxembourg»"
        ),
        "note":       "1908 為本批起點。1940-05-10 德軍佔領，大公夏洛特流亡倫敦，1944-09-10 回國。首都全程為盧森堡市。",
    },

    # ── 瑞士聯邦（Swiss Confederation）聯邦城市：伯恩 ───────────────────────────
    {
        "_id":        "CAP_BERN_SWISS_CONFEDERATION",
        "regimeId":   "01a18e71-cccd-747f-8e6f-25d3dad7ca3b",  # slug: swiss-confederation
        "cityName":   {"en": "Bern", "zh": "伯恩", "de": "Bern", "fr": "Berne"},
        "location":   {"type": "Point", "coordinates": [7.449, 46.947]},
        "validStart": "1908-01-01",
        "validEnd":   None,
        "sourceRef":  (
            "Bundesgesetz betreffend die Bestimmung des eidgenössischen Hauptortes, "
            "28. November 1848 — Bern als Bundesstadt (Bundeshauptort)；"
            "瑞士憲法並無正式定「首都」，伯恩為聯邦政府城市（Bundesstadt）"
        ),
        "note":       "1908 為本批起點。瑞士維持中立，首都（聯邦城市）伯恩未曾遷移。",
    },

    # ── 匈牙利人民共和國（Hungarian People's Republic，1918–1919）首都：布達佩斯 ─
    {
        "_id":        "CAP_BUDAPEST_HUNGARIAN_PEOPLES_REPUBLIC_1918",
        "regimeId":   "01a193a2-be54-7f12-94a7-1f9f61cf5b38",  # slug: hungarian-peoples-republic-1918
        "cityName":   {"en": "Budapest", "zh": "布達佩斯", "hu": "Budapest"},
        "location":   {"type": "Point", "coordinates": [19.040, 47.497]},
        "validStart": "1918-11-16",
        "validEnd":   "1919-03-21",
        "sourceRef":  (
            "待查證（1918-11-16 卡洛伊伊（Károlyi Mihály）宣布匈牙利人民共和國，"
            "布達佩斯為首都）"
        ),
        "note":       "1918-11-16 奧匈帝國解體後匈牙利宣布共和。1919-03-21 匈牙利蘇維埃共和國接管政權。",
    },
    # ── 匈牙利蘇維埃共和國（Hungarian Soviet Republic，1919）首都：布達佩斯 ──────
    {
        "_id":        "CAP_BUDAPEST_HUNGARIAN_SOVIET_REPUBLIC",
        "regimeId":   "01a193a2-be5d-7a51-8445-38461caff1e0",  # slug: hungarian-soviet-republic
        "cityName":   {"en": "Budapest", "zh": "布達佩斯", "hu": "Budapest"},
        "location":   {"type": "Point", "coordinates": [19.040, 47.497]},
        "validStart": "1919-03-21",
        "validEnd":   "1919-08-01",
        "sourceRef":  (
            "待查證（匈牙利蘇維埃共和國（Magyar Tanácsköztársaság）1919-03-21 成立，"
            "布達佩斯為首都）"
        ),
        "note":       "1919-08-01 羅馬尼亞軍佔領布達佩斯，蘇維埃政權瓦解。",
    },
    # ── 匈牙利王國（Kingdom of Hungary，1920–1946）首都：布達佩斯 ────────────────
    {
        "_id":        "CAP_BUDAPEST_KINGDOM_HUNGARY",
        "regimeId":   "01a18e71-cbcc-78b3-88e2-758f1e3423ec",  # slug: kingdom-of-hungary
        "cityName":   {"en": "Budapest", "zh": "布達佩斯", "hu": "Budapest"},
        "location":   {"type": "Point", "coordinates": [19.040, 47.497]},
        "validStart": "1920-03-01",
        "validEnd":   "1945-02-01",
        "sourceRef":  (
            "待查證（1920-03-01 霍爾蒂（Horthy Miklós）就任攝政，匈牙利王國正式恢復，"
            "布達佩斯為首都；1945-02-01 布達佩斯被蘇軍攻陷）"
        ),
        "note":       "1920-06-04 特里亞農條約（Treaty of Trianon）後，匈牙利大幅縮小。1944-12 德軍支持「箭十字黨」政府遷往匈牙利西部；1946-02-01 匈牙利第二共和國成立。",
    },

    # ── 大日本帝國（Empire of Japan，1868–1945）首都：東京 ───────────────────────
    {
        "_id":        "CAP_TOKYO_EMPIRE_JAPAN",
        "regimeId":   "01a191c9-07d8-7a6d-969f-c702cc8df64c",  # slug: empire-of-japan
        "cityName":   {"en": "Tokyo", "zh": "東京", "ja": "東京"},
        "location":   {"type": "Point", "coordinates": [139.769, 35.682]},
        "validStart": "1908-01-01",
        "validEnd":   "1945-09-02",
        "sourceRef":  (
            "大日本帝國憲法（Dai-Nippon Teikoku Kenpō），明治22年（1889）2月11日頒布；"
            "東京自 1869 年（明治2年）起為天皇駐蹕地（遷自京都），實際首都"
        ),
        "note":       "1908 為本批起點。1945-09-02 日本在密蘇里號（USS Missouri）簽署投降書，帝國終止。",
    },

    # ── 中華民國（北洋政府，Republic of China – Beiyang，1912–1928）首都：北京 ───
    {
        "_id":        "CAP_BEIJING_ROC_BEIYANG",
        "regimeId":   "01a195a6-c6cb-7d13-9ee8-3e7582004d05",  # slug: republic-of-china-beiyang
        "cityName":   {"en": "Peking (Beijing)", "zh": "北京", "zh-Hant": "北京"},
        "location":   {"type": "Point", "coordinates": [116.390, 39.907]},
        "validStart": "1912-01-01",
        "validEnd":   "1928-06-08",
        "sourceRef":  (
            "中華民國臨時約法（Provisional Constitution of the ROC），1912-03-11，第二條：「中華民國建設完全之後，以南京為首都」—— "
            "但臨時政府 1912-04-01 遷北京；北洋政府以北京為首都全程。"
            "1928-06-08 國民革命軍佔領北京，北洋政府結束。"
        ),
        "note":       "北洋政府（袁世凱、段祺瑞、張作霖等）全程以北京為首都；1928年後國民政府改北京為「北平」。",
    },
    # ── 中華民國（國民政府，Republic of China – Nationalist，1928–1937 南京）────
    {
        "_id":        "CAP_NANJING_ROC_NATIONALIST",
        "regimeId":   "01a191c9-07f8-76a7-8497-ce49a6de97fa",  # slug: republic-of-china-nationalist
        "cityName":   {"en": "Nanjing", "zh": "南京", "zh-Hant": "南京"},
        "location":   {"type": "Point", "coordinates": [118.797, 32.061]},
        "validStart": "1928-06-08",
        "validEnd":   "1937-11-20",
        "sourceRef":  (
            "國民政府奠都南京令（1927-04-18）；中華民國訓政時期約法（1931），第一條：「中華民國領土……首都定於南京」。"
            "1937-11-20 國民政府正式發布遷都宣言，因日軍逼近南京。"
        ),
        "note":       "1928-06-08 北伐完成。1937-12-13 南京陷落（南京大屠殺）。日本在南京另立汪精衛偽政府（1940-03-30）。",
    },
    # ── 中華民國（戰時首都：武漢，1937–1938）────────────────────────────────────
    {
        "_id":        "CAP_WUHAN_ROC_NATIONALIST",
        "regimeId":   "01a191c9-07f8-76a7-8497-ce49a6de97fa",  # slug: republic-of-china-nationalist
        "cityName":   {"en": "Wuhan", "zh": "武漢", "zh-Hant": "武漢"},
        "location":   {"type": "Point", "coordinates": [114.299, 30.594]},
        "validStart": "1937-11-20",
        "validEnd":   "1938-10-25",
        "sourceRef":  (
            "待查證（1937-11-20 國民政府遷往武漢；"
            "1938-10-25 武漢失守（武漢會戰），政府繼續西遷重慶）"
        ),
        "note":       "武漢為南京陷落後短暫的國民政府所在地。1938-10-25 武漢三鎮淪陷，政府正式以重慶為陪都/首都。",
    },
    # ── 中華民國（戰時陪都：重慶，1938–1945）────────────────────────────────────
    {
        "_id":        "CAP_CHONGQING_ROC_NATIONALIST",
        "regimeId":   "01a191c9-07f8-76a7-8497-ce49a6de97fa",  # slug: republic-of-china-nationalist
        "cityName":   {"en": "Chongqing", "zh": "重慶", "zh-Hant": "重慶"},
        "location":   {"type": "Point", "coordinates": [106.553, 29.567]},
        "validStart": "1938-10-25",
        "validEnd":   "1945-09-02",
        "sourceRef":  (
            "國民政府 1937-11-20 遷都宣言指定重慶為陪都；"
            "1938-12-07 蔣介石正式在重慶設立國民政府。"
            "1945-09-02 日本投降；國民政府隨後遷回南京（1946-04-23）。"
        ),
        "note":       "重慶正式名義為「陪都」（temporary capital），事實上為抗戰期間的最高政治中心。1946-05-05 國民政府還都南京。",
    },

    # ── 滿洲國（Manchukuo，1932–1945）首都：新京（長春）──────────────────────────
    {
        "_id":        "CAP_XINJING_MANCHUKUO",
        "regimeId":   "01a191c9-07ff-7fd1-a279-449ef9d2591e",  # slug: manchukuo
        "cityName":   {"en": "Xinjing (Changchun)", "zh": "新京（長春）", "zh-Hant": "新京（長春）", "ja": "新京"},
        "location":   {"type": "Point", "coordinates": [125.325, 43.817]},
        "validStart": "1932-03-01",
        "validEnd":   "1945-08-17",
        "sourceRef":  (
            "滿洲國政府組織法（1932-03-01）；"
            "新京特別市設置（1932-03-10 命名新京 Xinjing，即現今長春）。"
            "1934-03-01 溥儀稱帝建立滿洲帝國；"
            "1945-08-17 溥儀宣布退位，蘇軍佔領。"
        ),
        "note":       "長春（原鄭家屯車站附近）改名新京（新的首都）。今中國吉林省長春市。",
    },

    # ── 泰國（Kingdom of Thailand / Siam，歷史至今）首都：曼谷 ─────────────────
    {
        "_id":        "CAP_BANGKOK_KINGDOM_THAILAND",
        "regimeId":   "01a191c9-0821-71a8-89a5-9a3f0b7aba3d",  # slug: kingdom-of-thailand
        "cityName":   {"en": "Bangkok", "zh": "曼谷", "th": "กรุงเทพมหานคร"},
        "location":   {"type": "Point", "coordinates": [100.501, 13.756]},
        "validStart": "1908-01-01",
        "validEnd":   None,
        "sourceRef":  (
            "待查證（曼谷（กรุงเทพฯ，Krung Thep）自 1782 年卻克里王朝起為暹羅/泰國首都；"
            "1939-06-24 暹羅正式改名泰國（Thailand））"
        ),
        "note":       "1908 為本批起點。1939-06-24 暹羅（Siam）更名為泰國（Thailand）。二戰期間泰國與日本合作（1941-12-21 簽訂同盟），首都曼谷未遷。",
    },
]

# ─── 送出邏輯 ──────────────────────────────────────────────────────────────────
# API 只接受 zh-Hant 與 en；腳本資料裡的 de/fr/it/ru/tr/ota/pl/cs/sr 僅供記錄。
_SUPPORTED = {"en", "zh-Hant"}

def normalize_city_name(cn: dict) -> dict:
    """保留 en；zh → zh-Hant；其餘語系略去。"""
    out = {}
    if "en" in cn:
        out["en"] = cn["en"]
    zh = cn.get("zh-Hant") or cn.get("zh")
    if zh:
        out["zh-Hant"] = zh
    return out or {k: v for k, v in cn.items() if k in _SUPPORTED}

sent = json.load(open(a.ids, encoding="utf-8")) if os.path.exists(a.ids) else {}
key  = api_key() if not dry else None

ok_count   = 0
skip_count = 0
fail_count = 0

for rec in RECORDS:
    rid = rec["_id"]
    if rid in sent:
        print(f"SKIP {rid}（已寫入：{sent[rid]}）")
        skip_count += 1
        continue

    body = {
        "regimeId":   rec["regimeId"],
        "cityName":   normalize_city_name(rec["cityName"]),
        "location":   rec["location"],
        "validStart": rec["validStart"],
        "validEnd":   rec.get("validEnd"),
        "sourceRef":  rec.get("sourceRef"),
        "note":       rec.get("note") or None,
    }
    # 移除 None 值的 validEnd（open-ended）
    if body["validEnd"] is None:
        del body["validEnd"]
    if not body["note"]:
        del body["note"]

    label = (
        f"{rec['cityName'].get('en','?')} / "
        f"{rec['validStart']} – {rec.get('validEnd') or '∞'}"
    )
    print(f"POST /api/v1/capital-records  ← {rid}  （{label}）")
    if dry:
        continue

    raw = json.dumps(body, ensure_ascii=False).encode()
    req = urllib.request.Request(
        a.base.rstrip("/") + "/api/v1/capital-records",
        data=raw, method="POST",
        headers={"Content-Type": "application/json", "X-API-Key": key},
    )
    try:
        resp = json.load(urllib.request.urlopen(req))
        new_id = resp["data"]["id"]
        sent[rid] = new_id
        json.dump(sent, open(a.ids, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print(f"   ✓ id = {new_id}")
        ok_count += 1
    except urllib.error.HTTPError as e:
        body_err = e.read().decode()[:400]
        if e.code == 409:
            print(f"   CONFLICT 409（已存在重疊紀錄）：{body_err}")
            fail_count += 1
        else:
            print(f"   FAIL {e.code}：{body_err}", file=sys.stderr)
            # 不中止，繼續下一筆
            fail_count += 1

if dry:
    print(f"\n（dry-run，未送出。共 {len(RECORDS)} 筆，跳過 {skip_count} 筆。）")
else:
    print(f"\n完成：寫入 {ok_count} 筆，跳過 {skip_count} 筆，失敗 {fail_count} 筆。")
