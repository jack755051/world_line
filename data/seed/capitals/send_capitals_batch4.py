#!/usr/bin/env python3
"""
首都 seed 第四批（capitals_batch4 v2，verified 15 筆）。
本檔 RECORDS：v1 已寫入的華盛頓、瓦都茲、但澤、坎培拉（重跑會 SKIP），加上 v2 新增的匈牙利臨時國民政府
德布勒森、布達佩斯 2 筆。
匈牙利人民共和國與 v1 已寫入的 _V2 相同（見 replace_capitals_v5.py），不重複。
HELD（8 筆，不送出）：與 dev DB 既有記錄期間不同或重疊，待主管決定——
  匈牙利蘇維埃訖日 1919-08-04（庫裡 _V2 為 1919-08-01）、匈牙利王國布達佩斯訖日 1944-12-11 與克塞格暫駐、
  西班牙瓦倫西亞／巴塞隆納起訖日差一天與菲格雷斯暫駐、蒙特內哥羅波爾多／訥伊流亡駐地（與待查證采蒂涅重疊）。
來源：史料考證組 /workspace/wl-seed/capitals_batch4.json v2；格式比照 send_capitals.py，共用 sent-capitals.json。

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
        "regimeId": '01a191b4-36ac-792e-9113-9a46cc51fc9b',
        "cityName": {'en': 'Washington, D.C.', 'zh': '華盛頓'},
        "location": {'type': 'Point', 'coordinates': [-77.0091, 38.8899]},
        "validStart": '1914-07-29',
        "validEnd": '1945-09-02',
        "sourceRef": 'An Act for establishing the temporary and permanent seat of the Government of the United States (Residence Act), July 16, 1790, ch. 28, 1 Stat. 130, §§ 1, 6（§6：自 1800 年 12 月第一個星期一起，政府所在地移至該特區）',
        "note": '條文已核對 govinfo／LegisLink 的 Statutes at Large 影本。圓點用國會大廈附近。政府依法在 1800 年遷入。起日 1914-07-29 照清單上這個政權的存續起點（為何從 1914 起算請主管確認）。',
    },
    {
        "_id": 'CAP_VADUZ_LIECHTENSTEIN',
        "regimeId": '01a18e71-cd07-754d-8612-0f651dfb6860',
        "cityName": {'en': 'Vaduz', 'zh': '瓦都茲'},
        "location": {'type': 'Point', 'coordinates': [9.5209, 47.141]},
        "validStart": '1908-01-01',
        "validEnd": '1945-12-31',
        "sourceRef": 'Verfassung des Fürstentums Liechtenstein vom 5. Oktober 1921 (LGBl. 1921 Nr. 15)，及所附約翰二世親王 1921-10-02 手諭「in Vaduz, dem Hauptorte Meines Landes」；現行 Art. 1 Abs. 2「Vaduz ist der Hauptort ...」',
        "note": '條文已核對 gesetze.li 上的 LGBl. 1921 Nr. 15 全文（含附件手諭）。據 verfassungen.eu，1921 年原文 Art. 1 Abs. 2 為「Vaduz ist der Hauptort und der Sitz der Landesbehörden」，原始影本待核。1908～1921 期間的依據沿用 1862 年憲法（未核）。 政權在 1945 年後仍存續，訖日依本專案範圍截斷為 1945-12-31。',
    },
    {
        "_id": 'CAP_DANZIG_FREE_CITY',
        "regimeId": '01a18e71-cbe1-7782-9cb7-e0b8e8711eb9',
        "cityName": {'en': 'Danzig (Gdańsk)', 'zh': '但澤'},
        "location": {'type': 'Point', 'coordinates': [18.6466, 54.352]},
        "validStart": '1920-11-15',
        "validEnd": '1939-09-01',
        "sourceRef": "Treaty of Versailles, 28 June 1919, Part III, Art. 100–102（Art. 102：'establish the town of Danzig ... as a Free City'）",
        "note": '條文已核對 en.wikisource 全文。自由市即以但澤城為中心。訖日 1939-09-01＝德國吞併（照清單）。',
    },
    {
        "_id": 'CAP_CANBERRA_AUSTRALIA',
        "regimeId": '01a1948c-dc4d-7dac-8794-60a129dfc347',
        "cityName": {'en': 'Canberra', 'zh': '坎培拉'},
        "location": {'type': 'Point', 'coordinates': [149.13, -35.2809]},
        "validStart": '1937-07-07',
        "validEnd": '1945-09-02',
        "sourceRef": 'Seat of Government Act 1908 (Cth), No. 24 of 1908, s. 3「the Seat of Government of the Commonwealth shall be in the district of Yass-Canberra」',
        "note": '條文已核對 legislation.gov.au 與 foundingdocs.gov.au 的原文。國會自 1927-05-09 起在坎培拉開議（清單起日為 1937 年，所以全段都是坎培拉）。部分部會（例如國防部）仍留在墨爾本。',
    },
    {
        "_id": 'CAP_DEBRECEN_HUNGARIAN_PROVISIONAL_NATIONAL_GOVERNMENT',
        "regimeId": '01a191a0-45b6-75be-b8c1-1f224451729f',  # slug: hungarian-provisional-national-government
        "cityName": {'en': 'Debrecen', 'zh': '德布勒森', 'hu': 'Debrecen'},
        "location": {'type': 'Point', 'coordinates': [21.6273, 47.5316]},
        "validStart": '1945-02-01',
        "validEnd": '1945-04-11',
        "sourceRef": '學術：〈Az Ideiglenes Nemzetgyűlés és a kormány Debrecenben〉，Debreceni Szemle（ojs.lib.unideb.hu）：總理府和各部 1944-12-22 至 1945-04 初設在德布勒森 Kossuth u. 12–14 的財政署大樓',
        "note": '【暫駐】臨時國民政府在德布勒森。訖日 1945-04-11＝遷往布達佩斯（1956 年研究所年表 rev.hu）。',
    },
    {
        "_id": 'CAP_BUDAPEST_HUNGARIAN_PROVISIONAL_NATIONAL_GOVERNMENT',
        "regimeId": '01a191a0-45b6-75be-b8c1-1f224451729f',  # slug: hungarian-provisional-national-government
        "cityName": {'en': 'Budapest', 'zh': '布達佩斯', 'hu': 'Budapest'},
        "location": {'type': 'Point', 'coordinates': [19.0402, 47.4979]},
        "validStart": '1945-04-11',
        "validEnd": '1945-09-03',
        "sourceRef": '1872. évi XXXVI. törvénycikk, 1. §（首都法源）；遷移日：《Magyarország története 1944–1953, kronológia》（1956-os Intézet, rev.hu）「1945.04.11: Az Ideiglenes Nemzeti Kormány Debrecenből átteszi székhelyét Budapestre」',
        "note": '訖日照清單 1945-09-03。',
    },
]

# HELD：與 dev DB 既有記錄期間不同或重疊，本次不送出（列在回報與 /workspace/wl-seed/conv/cap4v2_held.json）。
HELD = [{'regime': '匈牙利蘇維埃共和國', 'slug': 'hungarian-soviet-republic', 'capital_zh': '布達佩斯', 'start_date': '1919-03-21', 'end_date': '1919-08-04', 'existing': [{'id': '01a19ebd-aae4-72b7-8edc-7df1d1c0c50b', 'city': '布達佩斯', 's': '1919-03-21', 'e': '1919-08-01', 'pending': False}]}, {'regime': '匈牙利王國', 'slug': 'kingdom-of-hungary', 'capital_zh': '布達佩斯', 'start_date': '1920-03-01', 'end_date': '1944-12-11', 'existing': [{'id': '01a19ebd-ab2d-7bb8-887d-0eacae4e3f48', 'city': '布達佩斯', 's': '1920-03-01', 'e': '1945-02-01', 'pending': False}]}, {'regime': '匈牙利王國', 'slug': 'kingdom-of-hungary', 'capital_zh': '克塞格（暫駐）', 'start_date': '1944-12-11', 'end_date': '1945-02-01', 'existing': [{'id': '01a19ebd-ab2d-7bb8-887d-0eacae4e3f48', 'city': '布達佩斯', 's': '1920-03-01', 'e': '1945-02-01', 'pending': False}]}, {'regime': '蒙特內哥羅王國', 'slug': 'kingdom-of-montenegro', 'capital_zh': '波爾多（流亡，暫駐）', 'start_date': '1916-01-19', 'end_date': '1916-05-01', 'existing': [{'id': '01a19cc8-3ce9-7c78-9cf3-67fd06d93bc5', 'city': '采蒂涅', 's': '1910-08-28', 'e': '1918-11-26', 'pending': True}]}, {'regime': '蒙特內哥羅王國', 'slug': 'kingdom-of-montenegro', 'capital_zh': '塞納河畔訥伊（流亡，暫駐）', 'start_date': '1916-05-01', 'end_date': '1918-11-26', 'existing': [{'id': '01a19cc8-3ce9-7c78-9cf3-67fd06d93bc5', 'city': '采蒂涅', 's': '1910-08-28', 'e': '1918-11-26', 'pending': True}]}, {'regime': '西班牙共和國', 'slug': 'spanish-republic', 'capital_zh': '瓦倫西亞', 'start_date': '1936-11-06', 'end_date': '1937-10-31', 'existing': [{'id': '01a19ebd-abc1-7614-b5ee-385a2de04e6c', 'city': '瓦倫西亞', 's': '1936-11-06', 'e': '1937-11-01', 'pending': False}]}, {'regime': '西班牙共和國', 'slug': 'spanish-republic', 'capital_zh': '巴塞隆納', 'start_date': '1937-10-31', 'end_date': '1939-01-23', 'existing': [{'id': '01a19ebd-abc1-7614-b5ee-385a2de04e6c', 'city': '瓦倫西亞', 's': '1936-11-06', 'e': '1937-11-01', 'pending': False}, {'id': '01a19ebd-ac17-74c3-b656-8a815d4e937b', 'city': '巴塞隆納', 's': '1937-11-01', 'e': '1939-04-01', 'pending': False}]}, {'regime': '西班牙共和國', 'slug': 'spanish-republic', 'capital_zh': '菲格雷斯（暫駐）', 'start_date': '1939-01-23', 'end_date': '1939-02-08', 'existing': [{'id': '01a19ebd-ac17-74c3-b656-8a815d4e937b', 'city': '巴塞隆納', 's': '1937-11-01', 'e': '1939-04-01', 'pending': False}]}]

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
