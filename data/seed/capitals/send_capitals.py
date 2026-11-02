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
