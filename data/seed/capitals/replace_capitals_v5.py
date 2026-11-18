#!/usr/bin/env python3
"""
首都記錄改版（改記錄＝撤回＋新增，不硬刪）。2026-11-03。
  - 匈牙利 3 筆、瓦倫西亞、巴塞隆納：撤回舊「待查證」記錄，新增 capitals_batch4 v1 的正式出處版本（*_V2）。
  - 布拉格（波希米亞—摩拉維亞保護國）：訖日 1945-05-09 → 1945-05-08（政權訖日），新版 *_CLIP。
撤回用 POST /api/v1/capital-records/{id}/retraction；每筆先撤回再新增，進度記在 sent-capitals.json
（<舊_id>__RETRACTED、<新_id>），可重跑。

只寫入開發庫（127.0.0.1:5052），拒絕送到 5051。

用法：
  python3 replace_capitals_v5.py [--dry-run]
  python3 replace_capitals_v5.py --send
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
REPLACEMENTS = [{'old': 'CAP_BUDAPEST_HUNGARIAN_PEOPLES_REPUBLIC_1918', 'reason': '改版：待查證記錄換成史料考證組 capitals_batch4 v1 的正式出處版本（verified），由 CAP_BUDAPEST_HUNGARIAN_PEOPLES_REPUBLIC_V2 取代。', 'new': {'_id': 'CAP_BUDAPEST_HUNGARIAN_PEOPLES_REPUBLIC_V2', 'regimeId': '01a193a2-be54-7f12-94a7-1f9f61cf5b38', 'cityName': {'en': 'Budapest', 'zh': '布達佩斯'}, 'location': {'type': 'Point', 'coordinates': [19.04, 47.497]}, 'validStart': '1918-11-16', 'validEnd': '1919-03-21', 'sourceRef': '1872. évi XXXVI. törvénycikk Buda-Pest fővárosi törvényhatóság alakításáról és rendezéséről, 1. §（Buda-Pest főváros；1872-12-23 公布）', 'note': '1918-11-16 奧匈帝國解體後匈牙利宣布共和。1919-03-21 匈牙利蘇維埃共和國接管政權。 首都法源為 1872:XXXVI 統一法，已核對 net.jogtar.hu《Ezer év törvényei》全文；此法在 1918–19 年仍然有效（廢止與否待核）。人民共和國宣布日期另見 1918-11-16 Néphatározat。'}}, {'old': 'CAP_BUDAPEST_HUNGARIAN_SOVIET_REPUBLIC', 'reason': '改版：待查證記錄換成史料考證組 capitals_batch4 v1 的正式出處版本（verified），由 CAP_BUDAPEST_HUNGARIAN_SOVIET_REPUBLIC_V2 取代。', 'new': {'_id': 'CAP_BUDAPEST_HUNGARIAN_SOVIET_REPUBLIC_V2', 'regimeId': '01a193a2-be5d-7a51-8445-38461caff1e0', 'cityName': {'en': 'Budapest', 'zh': '布達佩斯'}, 'location': {'type': 'Point', 'coordinates': [19.04, 47.497]}, 'validStart': '1919-03-21', 'validEnd': '1919-08-01', 'sourceRef': '1872. évi XXXVI. törvénycikk, 1. §（同上）', 'note': '1919-08-01 羅馬尼亞軍佔領布達佩斯，蘇維埃政權瓦解。 首都法源同上。蘇維埃政府 1919-08-01 解散，羅馬尼亞軍是 08-04 才進入布達佩斯。原 note 寫「08-01 羅馬尼亞軍佔領」，日期不對，請修正。'}}, {'old': 'CAP_BUDAPEST_KINGDOM_HUNGARY', 'reason': '改版：待查證記錄換成史料考證組 capitals_batch4 v1 的正式出處版本（verified），由 CAP_BUDAPEST_KINGDOM_HUNGARY_V2 取代。', 'new': {'_id': 'CAP_BUDAPEST_KINGDOM_HUNGARY_V2', 'regimeId': '01a18e71-cbcc-78b3-88e2-758f1e3423ec', 'cityName': {'en': 'Budapest', 'zh': '布達佩斯'}, 'location': {'type': 'Point', 'coordinates': [19.04, 47.497]}, 'validStart': '1920-03-01', 'validEnd': '1945-02-01', 'sourceRef': '1872. évi XXXVI. törvénycikk, 1. §（同上）', 'note': '1920-06-04 特里亞農條約（Treaty of Trianon）後，匈牙利大幅縮小。1944-12 德軍支持「箭十字黨」政府遷往匈牙利西部；1946-02-01 匈牙利第二共和國成立。 首都法源同上。訖日要注意：依「訖日＝政府撤離日」的原則，薩拉希政府在 1944-12 撤離布達佩斯前往西部（Sopron、Kőszeg 一帶），日期待查，應分筆；布達佩斯被圍、1945-02-13 才完全陷落，原 note 寫 02-01「被蘇軍攻陷」不準確，訖日待查。'}}, {'old': 'CAP_VALENCIA_SPANISH_REPUBLIC', 'reason': '改版：待查證記錄換成史料考證組 capitals_batch4 v1 的正式出處版本（verified），由 CAP_VALENCIA_SPANISH_REPUBLIC_V2 取代。', 'new': {'_id': 'CAP_VALENCIA_SPANISH_REPUBLIC_V2', 'regimeId': '01a18e71-ccb3-70ab-8663-74a509f73437', 'cityName': {'en': 'Valencia', 'zh': '瓦倫西亞'}, 'location': {'type': 'Point', 'coordinates': [-0.377, 39.47]}, 'validStart': '1936-11-06', 'validEnd': '1937-11-01', 'sourceRef': 'Decreto de 7 de noviembre de 1936（Presidencia del Consejo de Ministros）：«Habiendo trasladado el Gobierno su residencia oficial a Valencia ...»，Gaceta de Madrid núm. 313, 8-XI-1936, p. 669', 'note': '1937-10-31 政府再遷巴塞隆納；1937-11-01 生效。 條文已核對 BOE 的 Gazeta 歷史庫 PDF。政府 11-06 夜間撤離馬德里。訖日：巴塞隆納法令在 1937-10-31 公布生效，建議訖日由 11-01 改為 10-31。'}}, {'old': 'CAP_BARCELONA_SPANISH_REPUBLIC', 'reason': '改版：待查證記錄換成史料考證組 capitals_batch4 v1 的正式出處版本（verified），由 CAP_BARCELONA_SPANISH_REPUBLIC_V2 取代。', 'new': {'_id': 'CAP_BARCELONA_SPANISH_REPUBLIC_V2', 'regimeId': '01a18e71-ccb3-70ab-8663-74a509f73437', 'cityName': {'en': 'Barcelona', 'zh': '巴塞隆納'}, 'location': {'type': 'Point', 'coordinates': [2.177, 41.385]}, 'validStart': '1937-11-01', 'validEnd': '1939-04-01', 'sourceRef': 'Decreto（Presidencia del Consejo de Ministros）Art. 1.°«Se fija temporalmente en Barcelona la residencia oficial del Gobierno de la República, a partir de la publicación de este Decreto en la Gaceta»，Gaceta de la República núm. 304, 31-X-1937, p. 392', 'note': '1939-01-26 巴塞隆納陷落後，政府短暫在赫羅納（Girona）與法國流亡，共和國實際覆滅。 條文已核對 BOE 的 Gazeta 歷史庫 PDF。起日建議由 11-01 改為 1937-10-31。依撤離原則，訖日應改為政府撤離巴塞隆納的日子（約 1939-01-25/26，之後暫駐菲格雷斯，再流亡法國）；原訖日 1939-04-01 是內戰結束日，日期待查證。'}}, {'old': 'CAP_PRAGUE_PROTECTORATE_BOHEMIA_MORAVIA', 'reason': '依 dev DB 政權存在期間截斷：原訖日 1945-05-09 超出 protectorate-bohemia-moravia 的訖日 1945-05-08，由 CAP_PRAGUE_PROTECTORATE_BOHEMIA_MORAVIA_CLIP 取代。', 'new': {'_id': 'CAP_PRAGUE_PROTECTORATE_BOHEMIA_MORAVIA_CLIP', 'regimeId': '01a1920c-f61e-7766-aafd-8df5f800bd89', 'cityName': {'en': 'Prague', 'zh': '布拉格', 'de': 'Praha / Prag'}, 'location': {'type': 'Point', 'coordinates': [14.4214, 50.0875]}, 'validStart': '1939-03-16', 'validEnd': '1945-05-08', 'sourceRef': 'Erlaß des Führers und Reichskanzlers über das Protektorat Böhmen und Mähren vom 16. März 1939 (RGBl. I S. 485), Art. 5 Abs. 1「Sein [des Reichsprotektors] Amtssitz ist Prag.」', 'note': '依 dev DB 政權存在期間（protectorate-bohemia-moravia：1939-03-15～1945-05-08）截斷：原期間 1939-03-16～1945-05-09，本筆為 1939-03-16～1945-05-08。 首都依據＝帝國保護長官駐在地條文；保護國政府（哈查）亦駐布拉格。條文已核對捷克外交部公布全文 PDF。訖日 1945-05-09＝國務部長 K. H. Frank 撤出布拉格，保護國統治瓦解（待查證）。布拉格起義 05-05，德軍 05-08 投降，紅軍 05-09 入城，哈查 05-13 被捕。；訖日待查。'}}]

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
key = None if dry else api_key()
def save():
    json.dump(sent, open(a.ids, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
fail = 0
for rp in REPLACEMENTS:
    old_key, new = rp["old"], rp["new"]
    old_id = sent.get(old_key)
    rk = old_key + "__RETRACTED"
    print(f"撤回 {old_key}（{old_id}）" + ("（已撤回，跳過）" if rk in sent else ""))
    print(f"新增 {new['_id']}  {new['cityName'].get('zh')}  {new['validStart']} – {new.get('validEnd') or '∞'}" + ("（已寫入，跳過）" if new["_id"] in sent else ""))
    if dry:
        continue
    if not old_id:
        print("   FAIL 找不到舊記錄 id"); fail += 1; continue
    if rk not in sent:
        try:
            post(f"/api/v1/capital-records/{old_id}/retraction", {"reason": rp["reason"]}, key)
            sent[rk] = "retracted"; save(); print("   ✓ 撤回")
        except urllib.error.HTTPError as e:
            print(f"   FAIL 撤回 {e.code}：{e.read().decode()[:300]}"); fail += 1; continue
    if new["_id"] not in sent:
        body = {"regimeId": new["regimeId"], "cityName": normalize_city_name(new["cityName"]), "location": new["location"],
                "validStart": new["validStart"], "validEnd": new.get("validEnd"), "sourceRef": new.get("sourceRef"), "note": new.get("note")}
        if body["validEnd"] is None: del body["validEnd"]
        try:
            r = post("/api/v1/capital-records", body, key)
            sent[new["_id"]] = r["data"]["id"]; save(); print(f"   ✓ 新增 id = {r['data']['id']}")
        except urllib.error.HTTPError as e:
            print(f"   FAIL 新增 {e.code}：{e.read().decode()[:300]}（舊記錄已撤回，需補寫）"); fail += 1
print("\n（dry-run，未送出。）" if dry else f"\n完成：{len(REPLACEMENTS)} 組，失敗 {fail}。")
