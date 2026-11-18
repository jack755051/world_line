#!/usr/bin/env python3
"""
首都 seed 第三批（capitals_batch3 v2 中 verified 的記錄）。
涵蓋：斯洛伐克國、波希米亞－摩拉維亞保護國、波蘭總督府、汪精衛政權。
來源：史料考證組 /workspace/wl-seed/capitals_batch3.json；待查證 29 筆本批不寫入。
滿洲國（新京）verified 記錄未寫入：dev DB 已有 CAP_XINJING_MANCHUKUO（1932-03-01～1945-08-17），
期間重疊會觸發 excl_capital_records_no_overlap；如要改用新起訖日需走撤回＋新增。
格式比照 send_capitals.py，共用 sent-capitals.json 對照表。

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
# regimeId 由 dev DB regimes／regime_names 對照（2026-11-03）。validEnd 為排他邊界。
RECORDS = [
    {
        "_id": 'CAP_BRATISLAVA_SLOVAK_STATE',
        "regimeId": '01a18e71-cbc3-7ad9-9564-f1d11a322e86',  # slug: slovak-state-1939
        "cityName": {'en': 'Bratislava', 'zh': '布拉提斯拉發', 'sk': 'Bratislava'},
        "location": {'type': 'Point', 'coordinates': [17.1077, 48.1486]},
        "validStart": '1939-03-14',
        "validEnd": '1945-03-31',
        "sourceRef": 'Zákon č. 1/1939 Sl. z. zo dňa 14. marca 1939 o samostatnom Slovenskom štáte (Slovenský zákonník 1939, čiastka 1, s. 1); Ústavný zákon č. 185/1939 Sl. z. zo dňa 21. júla 1939 o ústave Slovenskej republiky, § 4 ods. 3「Hlavným mestom republiky je Bratislava.」(Slovenský zákonník 1939, čiastka 41, vydaná 31. júla 1939)',
        "note": '起日＝斯洛伐克邦議會於布拉提斯拉發通過 1/1939 獨立法（當日生效）；1/1939 本身未明文規定首都，首都法定化見 185/1939 § 4(3)（1939-07-31 公布）。訖日＝政府與總統撤離布拉提斯拉發（1945-03-31 16:00，據總理 Štefan Tiso 日記，經 sk.wikisource《Kapitulačný akt vlády Štefana Tisa》註釋轉引；學術頁碼待補）。紅軍 1945-04-04 攻占該市。條文已核對 ÚPN 公布之公報影本 upn.gov.sk/data/pdf/ustava1939.pdf。',
    },
    {
        "_id": 'CAP_PRAGUE_PROTECTORATE_BOHEMIA_MORAVIA',
        "regimeId": '01a1920c-f61e-7766-aafd-8df5f800bd89',  # slug: protectorate-bohemia-moravia
        "cityName": {'en': 'Prague', 'zh': '布拉格', 'de': 'Praha / Prag'},
        "location": {'type': 'Point', 'coordinates': [14.4214, 50.0875]},
        "validStart": '1939-03-16',
        "validEnd": '1945-05-09',
        "sourceRef": 'Erlaß des Führers und Reichskanzlers über das Protektorat Böhmen und Mähren vom 16. März 1939 (RGBl. I S. 485), Art. 5 Abs. 1「Sein [des Reichsprotektors] Amtssitz ist Prag.」',
        "note": '首都依據＝帝國保護長官駐在地條文；保護國政府（哈查）亦駐布拉格。條文已核對捷克外交部公布全文 PDF。訖日 1945-05-09＝國務部長 K. H. Frank 撤出布拉格，保護國統治瓦解（待查證）。布拉格起義 05-05，德軍 05-08 投降，紅軍 05-09 入城，哈查 05-13 被捕。；訖日待查。',
    },
    {
        "_id": 'CAP_KRAKOW_GENERALGOUVERNEMENT',
        "regimeId": '01a1920c-f731-779a-8ca6-5ae4d3ecb566',  # slug: generalgouvernement
        "cityName": {'en': 'Kraków', 'zh': '克拉科夫', 'de': 'Krakau / Kraków'},
        "location": {'type': 'Point', 'coordinates': [19.9372, 50.0614]},
        "validStart": '1939-11-07',
        "validEnd": '1945-01-17',
        "sourceRef": 'Erste Verordnung über den Aufbau der Verwaltung der besetzten polnischen Gebiete vom 26. Oktober 1939, § 2「Sitz des Generalgouverneurs ist Krakau」(VOBl. GGP 1939 Nr. 1)；轉引自 Kraków 雅蓋隆大學學術論文 (ruj.uj.edu.pl)，引用 Okupacja i ruch oporu w Dzienniku Hansa Franka, t. 1 (Warszawa 1970), s. 116–117',
        "note": '起日採 Diensttagebuch 導論的 11-07（另說 11-13，見上一筆）。訖日 1945-01-17＝弗蘭克撤離克拉科夫（常見說法，待查證）；紅軍 01-19 攻占克拉科夫。；訖日待查。',
    },
    {
        "_id": 'CAP_NANJING_REORGANIZED_NATIONAL_GOVERNMENT',
        "regimeId": '01a191c9-084e-78df-a189-19a82ce1d80f',  # slug: reorganized-national-government-nanjing
        "cityName": {'en': 'Nanjing', 'zh': '南京'},
        "location": {'type': 'Point', 'coordinates': [118.7969, 32.0603]},
        "validStart": '1940-03-30',
        "validEnd": '1945-08-16',
        "sourceRef": '《國民政府還都宣言》（1940-03-30），載汪政權《國民政府公報》1940-04-01；東京審判 Court Exhibit No. 2605',
        "note": '訖日＝陳公博宣布解散（08-16）；起日已核對宣言日期，訖日依據待查證。 訖日＝政府宣布解散。；訖日待查。',
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
