#!/usr/bin/env python3
"""
滿洲國首都（新京）改版：撤回舊記錄 CAP_XINJING_MANCHUKUO，再新增考證組版本 CAP_XINJING_MANCHUKUO_V2。
依「改記錄＝撤回＋新增」規則；撤回用 POST /api/v1/capital-records/{id}/retraction，不硬刪。
舊：1932-03-01～1945-08-17（send_capitals.py）
新：1932-03-10～1945-08-11（capitals_batch3 v2，verified；出處《滿洲國政府公報》第 1 號）

只寫入開發庫（127.0.0.1:5052），拒絕送到 5051。

用法：
  python3 fix_manchukuo_xinjing.py [--dry-run]       # 預設 dry-run
  python3 fix_manchukuo_xinjing.py --send
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

# ─── 撤回對象與新紀錄 ─────────────────────────────────────────────────────────
OLD_ID_KEY = "CAP_XINJING_MANCHUKUO"
RETRACT_REASON = (
    "改版：依史料考證組 capitals_batch3 v2（verified），定都日改為 1932-03-10（國務院佈告第 1 號，"
    "載《滿洲國政府公報》第 1 號），訖日改為 1945-08-11（溥儀與政府撤離新京）；"
    "由 CAP_XINJING_MANCHUKUO_V2 取代。"
)
NEW = {
    "_id": "CAP_XINJING_MANCHUKUO_V2",
    "regimeId": "01a191c9-07ff-7fd1-a279-449ef9d2591e",
    "cityName": {
        "en": "Xinjing (Changchun)",
        "zh": "新京（長春）",
        "ja": "新京"
    },
    "location": {
        "type": "Point",
        "coordinates": [
            125.3235,
            43.8171
        ]
    },
    "validStart": "1932-03-10",
    "validEnd": "1945-08-11",
    "sourceRef": "大同元年 3 月 10 日國務院佈告第 1 號「滿洲國國都ヲ長春ニ奠ム」；3 月 14 日國務院佈告第 2 號「國都長春ヲ新京ト命名ス」（國務總理 鄭孝胥）；均載《滿洲國政府公報》第 1 號（大同元年 4 月 1 日）。據古屋哲夫〈滿州國人事法令年表〉",
    "note": "1932-03-01 建國宣言至 03-10 定都之間首都未定（03-09 執政就任式在長春）。1932-03-14 起名稱為新京，同一地點不分筆，名稱變更寫在 note。訖日：溥儀約 08-11 移往通化大栗子（臨江），日期待查證。 訖日 08-11＝溥儀與政府撤離新京往大栗子（待查證）；蘇軍 08-19/20 進城。"
}

def normalize_city_name(cn):
    out = {}
    if "en" in cn: out["en"] = cn["en"]
    zh = cn.get("zh-Hant") or cn.get("zh")
    if zh: out["zh-Hant"] = zh
    return out

def post(path, body, key):
    req = urllib.request.Request(a.base.rstrip("/") + path,
        data=json.dumps(body, ensure_ascii=False).encode(), method="POST",
        headers={"Content-Type": "application/json", "X-API-Key": key})
    return json.load(urllib.request.urlopen(req))

sent = json.load(open(a.ids, encoding="utf-8"))
old_id = sent.get(OLD_ID_KEY)
retracted_key = OLD_ID_KEY + "__RETRACTED"
print(f"撤回 POST /api/v1/capital-records/{old_id}/retraction  ← {OLD_ID_KEY}"
      + ("（已撤回，跳過）" if retracted_key in sent else ""))
print(f"新增 POST /api/v1/capital-records  ← {NEW['_id']}  （{NEW['validStart']} – {NEW['validEnd']}）"
      + ("（已寫入，跳過）" if NEW["_id"] in sent else ""))
if dry:
    print("\n（dry-run，未送出。）"); sys.exit(0)
if not old_id:
    sys.exit("找不到舊記錄 id，中止。")
key = api_key()
if retracted_key not in sent:
    try:
        r = post(f"/api/v1/capital-records/{old_id}/retraction", {"reason": RETRACT_REASON}, key)
        sent[retracted_key] = r["data"]["retractedAt"] if isinstance(r.get("data"), dict) and "retractedAt" in r["data"] else "retracted"
        json.dump(sent, open(a.ids, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print("   ✓ 撤回完成")
    except urllib.error.HTTPError as e:
        sys.exit(f"   FAIL 撤回 {e.code}：{e.read().decode()[:400]}")
if NEW["_id"] not in sent:
    body = {"regimeId": NEW["regimeId"], "cityName": normalize_city_name(NEW["cityName"]),
            "location": NEW["location"], "validStart": NEW["validStart"], "validEnd": NEW["validEnd"],
            "sourceRef": NEW["sourceRef"], "note": NEW["note"]}
    try:
        r = post("/api/v1/capital-records", body, key)
        sent[NEW["_id"]] = r["data"]["id"]
        json.dump(sent, open(a.ids, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print(f"   ✓ 新增 id = {r['data']['id']}")
    except urllib.error.HTTPError as e:
        sys.exit(f"   FAIL 新增 {e.code}：{e.read().decode()[:400]}（舊記錄已撤回，需補寫）")
print("\n完成。")
