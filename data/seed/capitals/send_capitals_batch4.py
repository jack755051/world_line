#!/usr/bin/env python3
"""
首都 seed 第四批（capitals_batch4 v1 中 verified 的 9 筆）。
本檔寫入：華盛頓、瓦都茲、但澤、坎培拉（4 筆；期間都在政權存在期間內，不需截斷）。
未寫入（DEFERRED，5 筆）：匈牙利 3 筆、瓦倫西亞、巴塞隆納。開發庫已有同政權、同期間的「待查證」記錄，
直接新增會觸發 excl_capital_records_no_overlap；要更新須先撤回舊記錄再新增，待主管核准。
來源：史料考證組 /workspace/wl-seed/capitals_batch4.json；格式比照 send_capitals.py，共用 sent-capitals.json。

只寫入開發庫（127.0.0.1:5052），拒絕送到 5051。

用法：
  python3 send_capitals_batch4.py [--dry-run]
  python3 send_capitals_batch4.py --send
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
# regimeId 由考證組提供並對照 dev DB regimes 驗證（2026-11-03）。validEnd 為排他邊界。
RECORDS = [
    {
        "_id": 'CAP_WASHINGTON_USA',
        "regimeId": '01a191b4-36ac-792e-9113-9a46cc51fc9b',  # slug: united-states-of-america
        "cityName": {'en': 'Washington, D.C.', 'zh': '華盛頓'},
        "location": {'type': 'Point', 'coordinates': [-77.0091, 38.8899]},
        "validStart": '1914-07-29',
        "validEnd": '1945-09-02',
        "sourceRef": 'An Act for establishing the temporary and permanent seat of the Government of the United States (Residence Act), July 16, 1790, ch. 28, 1 Stat. 130, §§ 1, 6（§6：自 1800 年 12 月第一個星期一起，政府所在地移至該特區）',
        "note": '條文已核對 govinfo／LegisLink 的 Statutes at Large 影本。圓點用國會大廈附近。政府依法在 1800 年遷入。起日 1914-07-29 照清單上這個政權的存續起點（為何從 1914 起算請主管確認）。',
    },
    {
        "_id": 'CAP_VADUZ_LIECHTENSTEIN',
        "regimeId": '01a18e71-cd07-754d-8612-0f651dfb6860',  # slug: principality-of-liechtenstein
        "cityName": {'en': 'Vaduz', 'zh': '瓦都茲'},
        "location": {'type': 'Point', 'coordinates': [9.5209, 47.141]},
        "validStart": '1908-01-01',
        "validEnd": '1945-12-31',
        "sourceRef": 'Verfassung des Fürstentums Liechtenstein vom 5. Oktober 1921 (LGBl. 1921 Nr. 15)，及所附約翰二世親王 1921-10-02 手諭「in Vaduz, dem Hauptorte Meines Landes」；現行 Art. 1 Abs. 2「Vaduz ist der Hauptort ...」',
        "note": '條文已核對 gesetze.li 上的 LGBl. 1921 Nr. 15 全文（含附件手諭）。據 verfassungen.eu，1921 年原文 Art. 1 Abs. 2 為「Vaduz ist der Hauptort und der Sitz der Landesbehörden」，原始影本待核。1908～1921 期間的依據沿用 1862 年憲法（未核）。 政權在 1945 年後仍存續，訖日依本專案範圍截斷為 1945-12-31。',
    },
    {
        "_id": 'CAP_DANZIG_FREE_CITY',
        "regimeId": '01a18e71-cbe1-7782-9cb7-e0b8e8711eb9',  # slug: free-city-of-danzig
        "cityName": {'en': 'Danzig (Gdańsk)', 'zh': '但澤'},
        "location": {'type': 'Point', 'coordinates': [18.6466, 54.352]},
        "validStart": '1920-11-15',
        "validEnd": '1939-09-01',
        "sourceRef": "Treaty of Versailles, 28 June 1919, Part III, Art. 100–102（Art. 102：'establish the town of Danzig ... as a Free City'）",
        "note": '條文已核對 en.wikisource 全文。自由市即以但澤城為中心。訖日 1939-09-01＝德國吞併（照清單）。',
    },
    {
        "_id": 'CAP_CANBERRA_AUSTRALIA',
        "regimeId": '01a1948c-dc4d-7dac-8794-60a129dfc347',  # slug: commonwealth-of-australia
        "cityName": {'en': 'Canberra', 'zh': '坎培拉'},
        "location": {'type': 'Point', 'coordinates': [149.13, -35.2809]},
        "validStart": '1937-07-07',
        "validEnd": '1945-09-02',
        "sourceRef": 'Seat of Government Act 1908 (Cth), No. 24 of 1908, s. 3「the Seat of Government of the Commonwealth shall be in the district of Yass-Canberra」',
        "note": '條文已核對 legislation.gov.au 與 foundingdocs.gov.au 的原文。國會自 1927-05-09 起在坎培拉開議（清單起日為 1937 年，所以全段都是坎培拉）。部分部會（例如國防部）仍留在墨爾本。',
    },
]

# 與開發庫既有「待查證」記錄重疊、本次不送出（需撤回＋新增，待核准）。
# 各筆對應的既有記錄：CAP_BUDAPEST_HUNGARIAN_PEOPLES_REPUBLIC_V2 ↔ 01a19cc8-3d6f-777c-849c-64d9ab52a696; CAP_BUDAPEST_HUNGARIAN_SOVIET_REPUBLIC_V2 ↔ 01a19cc8-3d74-7ab6-936b-389aeceaac8a; CAP_BUDAPEST_KINGDOM_HUNGARY_V2 ↔ 01a19cc8-3d79-7462-995c-8c42d344613c; CAP_VALENCIA_SPANISH_REPUBLIC_V2 ↔ 01a19cc8-3d50-7251-b868-33ef7bdecc48; CAP_BARCELONA_SPANISH_REPUBLIC_V2 ↔ 01a19cc8-3d55-7de6-9992-4e1395b08d6f
DEFERRED = [
    {
        "_id": 'CAP_BUDAPEST_HUNGARIAN_PEOPLES_REPUBLIC_V2',
        "regimeId": '01a193a2-be54-7f12-94a7-1f9f61cf5b38',  # slug: hungarian-peoples-republic-1918
        "cityName": {'en': 'Budapest', 'zh': '布達佩斯'},
        "location": {'type': 'Point', 'coordinates': [19.04, 47.497]},
        "validStart": '1918-11-16',
        "validEnd": '1919-03-21',
        "sourceRef": '1872. évi XXXVI. törvénycikk Buda-Pest fővárosi törvényhatóság alakításáról és rendezéséről, 1. §（Buda-Pest főváros；1872-12-23 公布）',
        "note": '1918-11-16 奧匈帝國解體後匈牙利宣布共和。1919-03-21 匈牙利蘇維埃共和國接管政權。 首都法源為 1872:XXXVI 統一法，已核對 net.jogtar.hu《Ezer év törvényei》全文；此法在 1918–19 年仍然有效（廢止與否待核）。人民共和國宣布日期另見 1918-11-16 Néphatározat。',
    },
    {
        "_id": 'CAP_BUDAPEST_HUNGARIAN_SOVIET_REPUBLIC_V2',
        "regimeId": '01a193a2-be5d-7a51-8445-38461caff1e0',  # slug: hungarian-soviet-republic
        "cityName": {'en': 'Budapest', 'zh': '布達佩斯'},
        "location": {'type': 'Point', 'coordinates': [19.04, 47.497]},
        "validStart": '1919-03-21',
        "validEnd": '1919-08-01',
        "sourceRef": '1872. évi XXXVI. törvénycikk, 1. §（同上）',
        "note": '1919-08-01 羅馬尼亞軍佔領布達佩斯，蘇維埃政權瓦解。 首都法源同上。蘇維埃政府 1919-08-01 解散，羅馬尼亞軍是 08-04 才進入布達佩斯。原 note 寫「08-01 羅馬尼亞軍佔領」，日期不對，請修正。',
    },
    {
        "_id": 'CAP_BUDAPEST_KINGDOM_HUNGARY_V2',
        "regimeId": '01a18e71-cbcc-78b3-88e2-758f1e3423ec',  # slug: kingdom-of-hungary
        "cityName": {'en': 'Budapest', 'zh': '布達佩斯'},
        "location": {'type': 'Point', 'coordinates': [19.04, 47.497]},
        "validStart": '1920-03-01',
        "validEnd": '1945-02-01',
        "sourceRef": '1872. évi XXXVI. törvénycikk, 1. §（同上）',
        "note": '1920-06-04 特里亞農條約（Treaty of Trianon）後，匈牙利大幅縮小。1944-12 德軍支持「箭十字黨」政府遷往匈牙利西部；1946-02-01 匈牙利第二共和國成立。 首都法源同上。訖日要注意：依「訖日＝政府撤離日」的原則，薩拉希政府在 1944-12 撤離布達佩斯前往西部（Sopron、Kőszeg 一帶），日期待查，應分筆；布達佩斯被圍、1945-02-13 才完全陷落，原 note 寫 02-01「被蘇軍攻陷」不準確，訖日待查。',
    },
    {
        "_id": 'CAP_VALENCIA_SPANISH_REPUBLIC_V2',
        "regimeId": '01a18e71-ccb3-70ab-8663-74a509f73437',  # slug: spanish-republic
        "cityName": {'en': 'Valencia', 'zh': '瓦倫西亞'},
        "location": {'type': 'Point', 'coordinates': [-0.377, 39.47]},
        "validStart": '1936-11-06',
        "validEnd": '1937-11-01',
        "sourceRef": 'Decreto de 7 de noviembre de 1936（Presidencia del Consejo de Ministros）：«Habiendo trasladado el Gobierno su residencia oficial a Valencia ...»，Gaceta de Madrid núm. 313, 8-XI-1936, p. 669',
        "note": '1937-10-31 政府再遷巴塞隆納；1937-11-01 生效。 條文已核對 BOE 的 Gazeta 歷史庫 PDF。政府 11-06 夜間撤離馬德里。訖日：巴塞隆納法令在 1937-10-31 公布生效，建議訖日由 11-01 改為 10-31。',
    },
    {
        "_id": 'CAP_BARCELONA_SPANISH_REPUBLIC_V2',
        "regimeId": '01a18e71-ccb3-70ab-8663-74a509f73437',  # slug: spanish-republic
        "cityName": {'en': 'Barcelona', 'zh': '巴塞隆納'},
        "location": {'type': 'Point', 'coordinates': [2.177, 41.385]},
        "validStart": '1937-11-01',
        "validEnd": '1939-04-01',
        "sourceRef": 'Decreto（Presidencia del Consejo de Ministros）Art. 1.°«Se fija temporalmente en Barcelona la residencia oficial del Gobierno de la República, a partir de la publicación de este Decreto en la Gaceta»，Gaceta de la República núm. 304, 31-X-1937, p. 392',
        "note": '1939-01-26 巴塞隆納陷落後，政府短暫在赫羅納（Girona）與法國流亡，共和國實際覆滅。 條文已核對 BOE 的 Gazeta 歷史庫 PDF。起日建議由 11-01 改為 1937-10-31。依撤離原則，訖日應改為政府撤離巴塞隆納的日子（約 1939-01-25/26，之後暫駐菲格雷斯，再流亡法國）；原訖日 1939-04-01 是內戰結束日，日期待查證。',
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
