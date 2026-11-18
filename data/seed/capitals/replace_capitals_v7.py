#!/usr/bin/env python3
"""
首都改版 v7（2026-11-03；capitals_batch4 v3、capitals_batch5 v2）。改記錄＝撤回＋新增，不硬刪。依序執行：
  - 匈牙利王國布達佩斯、西班牙瓦倫西亞／巴塞隆納：撤回 _V2，新增 v3 verified 版（_V3）。待查證暫駐段不寫。
  - 蒙特內哥羅采蒂涅（待查證）：撤回，新增截至 1916-01-13 的待查證版（_CLIP）。
  - 立陶宛：撤回維爾紐斯段（無替代）；考納斯段（待查證）延至 1940-07-21（_EXT）。
  - 新增：奧地利聯邦國維也納 1922-10-01～1934-05-01；立陶宛蘇維埃考納斯、AMGOT 巴勒莫（batch5 v2）。
old 為 None 表示純新增；new 為 None 表示純撤回。進度記在 sent-capitals.json，可重跑。

只寫入開發庫（127.0.0.1:5052），拒絕送到 5051。

用法：
  python3 replace_capitals_v7.py [--dry-run]
  python3 replace_capitals_v7.py --send
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
REPLACEMENTS = [{'old': 'CAP_BUDAPEST_KINGDOM_HUNGARY_V2', 'reason': '改版：依史料考證組 capitals_batch4 v3（verified）更新期間，由 CAP_BUDAPEST_KINGDOM_HUNGARY_V3 取代。', 'new': {'_id': 'CAP_BUDAPEST_KINGDOM_HUNGARY_V3', 'regimeId': '01a18e71-cbcc-78b3-88e2-758f1e3423ec', 'cityName': {'en': 'Budapest', 'zh': '布達佩斯'}, 'location': {'type': 'Point', 'coordinates': [19.04, 47.497]}, 'validStart': '1920-03-01', 'validEnd': '1944-12-11', 'sourceRef': '1872. évi XXXVI. törvénycikk, 1. §（同上）', 'note': 'v3 訖日 1944-12-11（原 _V2 為 1945-02-01）；之後克塞格暫駐段為待查證，本次不寫，留空。 1920-06-04 簽訂特里亞農條約。訖日 1944-12-11＝薩拉希政府撤離布達佩斯（hu.wikipedia《Szálasi-kormány》、The Orange Files；學術頁碼待補）。布達佩斯 1944-12-26 被合圍，1945-02-13 完全陷落。原檔 valid_to 為 1945-02-01。'}}, {'old': 'CAP_VALENCIA_SPANISH_REPUBLIC_V2', 'reason': '改版：依史料考證組 capitals_batch4 v3（verified）更新期間，由 CAP_VALENCIA_SPANISH_REPUBLIC_V3 取代。', 'new': {'_id': 'CAP_VALENCIA_SPANISH_REPUBLIC_V3', 'regimeId': '01a18e71-ccb3-70ab-8663-74a509f73437', 'cityName': {'en': 'Valencia', 'zh': '瓦倫西亞'}, 'location': {'type': 'Point', 'coordinates': [-0.377, 39.47]}, 'validStart': '1936-11-06', 'validEnd': '1937-10-31', 'sourceRef': 'Decreto de 7 de noviembre de 1936（Presidencia del Consejo de Ministros）：«Habiendo trasladado el Gobierno su residencia oficial a Valencia ...»，Gaceta de Madrid núm. 313, 8-XI-1936, p. 669', 'note': 'v3 訖日 1937-10-31（原 _V2 為 1937-11-01）。  條文已核對 BOE 的 Gazeta 歷史庫 PDF。政府 11-06 夜間撤離馬德里。訖日改為 1937-10-31，也就是巴塞隆納法令在 Gaceta 公布生效的日子（原檔為 11-01）。'}}, {'old': 'CAP_BARCELONA_SPANISH_REPUBLIC_V2', 'reason': '改版：依史料考證組 capitals_batch4 v3（verified）更新期間，由 CAP_BARCELONA_SPANISH_REPUBLIC_V3 取代。', 'new': {'_id': 'CAP_BARCELONA_SPANISH_REPUBLIC_V3', 'regimeId': '01a18e71-ccb3-70ab-8663-74a509f73437', 'cityName': {'en': 'Barcelona', 'zh': '巴塞隆納'}, 'location': {'type': 'Point', 'coordinates': [2.177, 41.385]}, 'validStart': '1937-10-31', 'validEnd': '1939-01-23', 'sourceRef': 'Decreto（Presidencia del Consejo de Ministros）Art. 1.°«Se fija temporalmente en Barcelona la residencia oficial del Gobierno de la República, a partir de la publicación de este Decreto en la Gaceta»，Gaceta de la República núm. 304, 31-X-1937, p. 392；訖日：Real Academia de la Historia, Historia Hispánica, 〈1939 23/i〉「El Gobierno republicano se traslada de Barcelona a Figueras」', 'note': 'v3 期間 1937-10-31～1939-01-23（原 _V2 為 1937-11-01～1939-04-01）；之後菲格雷斯、埃爾達、馬德里、瓦倫西亞暫駐段為待查證，本次不寫，留空。 起日 1937-10-31＝法令公布生效日（原檔為 11-01）。訖日 1939-01-23＝政府由巴塞隆納遷往菲格雷斯（出處：西班牙皇家歷史學院 Historia Hispánica）。佛朗哥軍 01-26 入城。庫內原 valid_to 為 1939-04-01，那是政權結束日，不是政府離開巴塞隆納的日子，應改為 01-23。'}}, {'old': 'CAP_CETINJE_KINGDOM_MONTENEGRO', 'reason': '依 capitals_batch4 v3：采蒂涅段訖日為 1916-01-13（奧匈攻占、政府撤離），不再覆蓋到 1918；仍為待查證，由 CAP_CETINJE_KINGDOM_MONTENEGRO_CLIP 取代。', 'new': {'_id': 'CAP_CETINJE_KINGDOM_MONTENEGRO_CLIP', 'regimeId': '01a192dc-6a27-7178-87f5-4f8643d8be55', 'cityName': {'en': 'Cetinje', 'zh-Hant': '采蒂涅'}, 'location': {'type': 'Point', 'coordinates': [18.916, 42.39]}, 'validStart': '1910-08-28', 'validEnd': '1916-01-13', 'sourceRef': '待查證（1910-08-28 尼古拉一世宣布蒙特內哥羅為王國，采蒂涅繼續為首都）', 'note': '仍為待查證。原期間 1910-08-28～1918-11-26，依 capitals_batch4 v3 截至 1916-01-13；之後斯庫台、波爾多、塞納河畔訥伊流亡駐地均為待查證，本次不寫，留空。 1918-11-26 波多里察議會宣布廢黜尼古拉一世，蒙特內哥羅加入塞—克—斯王國。'}}, {'old': 'CAP_VILNIUS_REPUBLIC_LITHUANIA', 'reason': '依 capitals_batch4 v3 撤回：1939-10-28 立陶宛只是接管維爾紐斯，政府並沒有遷入：總統府、部長會議、各部到 1940-06-15 蘇聯佔領時都還在考納斯（Stravinskienė 2017, Istorija 107(3)；Antanavičiūtė 2012）。依「圓點＝當天政府實際所在地」，這一段應標考納斯。', 'new': None}, {'old': 'CAP_KAUNAS_REPUBLIC_LITHUANIA', 'reason': '依 capitals_batch4 v3：1939-10-28 後政府仍在考納斯，考納斯段延至 1940-07-21；由 CAP_KAUNAS_REPUBLIC_LITHUANIA_EXT 取代。', 'new': {'_id': 'CAP_KAUNAS_REPUBLIC_LITHUANIA_EXT', 'regimeId': '01a18e71-cbeb-7713-a547-b57e23a57220', 'cityName': {'en': 'Kaunas', 'zh-Hant': '考納斯'}, 'location': {'type': 'Point', 'coordinates': [23.9, 54.897]}, 'validStart': '1918-11-16', 'validEnd': '1940-07-21', 'sourceRef': '待查證（1920-02-20 Seimas 決議以考納斯為臨時首都，因維爾紐斯遭波蘭佔領；Lietuvos Valstybės Konstitucija, 1922, 2 straipsnis — «Sostinė Vilnius»，但因佔領實際以考納斯為首都）', 'note': '仍為待查證。原期間 1918-11-16～1939-10-28，依 capitals_batch4 v3 延至 1940-07-21（維爾紐斯段已撤回；政府到 1940-06-15 蘇聯佔領時仍在考納斯，見 Stravinskienė 2017、Antanavičiūtė 2012）。 歷史首都維爾紐斯（Vilnius）1920 年起被波蘭佔領，考納斯成為臨時首都直至 1939 年。'}}, {'old': None, 'reason': None, 'new': {'_id': 'CAP_VIENNA_FEDERAL_STATE_AUSTRIA_1922', 'regimeId': '01a18e71-cbaf-730b-8d7c-6a4b920630c0', 'cityName': {'en': 'Vienna', 'zh': '維也納'}, 'location': {'type': 'Point', 'coordinates': [16.3738, 48.2082]}, 'validStart': '1922-10-01', 'validEnd': '1934-05-01', 'sourceRef': 'Bundes-Verfassungsgesetz, BGBl. Nr. 1/1920, Art. 5：「Bundeshauptstadt und Sitz der obersten Organe des Bundes ist Wien.」（RIS Bundesrecht konsolidiert，Gesetzesnummer 10000041，Dokumentnummer NOR12000710，ELI https://www.ris.bka.gv.at/eli/bgbl/1920/1/A5/NOR12000710，有效期 1920-11-10～1925-09-30，之後由 BGBl. Nr. 367/1925 再公告；條文已和 ÖAW/ACDH 數位版 b-vg.acdh.oeaw.ac.at bv_doc_id__62 核對。1929 年 BVG 第 1 條增訂第 2 項：非常時期可遷移最高機關駐地。）', 'note': '補 1922-10-01～1934-05-01 空檔（dev DB 中此期間屬 federal-state-of-austria）。 這一筆是為了補庫內空檔而設：政權存續期從 1922-10-01 起，但庫內 CAP_VIENNA_FEDERAL_STATE_AUSTRIA 從 1934-05-01（五月憲法）才開始。起訖日照主管給的日期。注意：這段期間在法律上是第一共和（Republik Österreich，B-VG 1920）。清單把 1922-10-01 以後歸到 federal-state-of-austria，政權的分界請主管確認。'}}, {'old': None, 'reason': None, 'new': {'_id': 'CAP_KAUNAS_LITHUANIAN_SSR', 'regimeId': '01a18e71-cbf6-7eeb-b518-f8241e1a04f1', 'cityName': {'en': 'Kaunas', 'zh': '考納斯'}, 'location': {'type': 'Point', 'coordinates': [23.9036, 54.8985]}, 'validStart': '1940-07-21', 'validEnd': '1940-08-04', 'sourceRef': "學術：R. Antanavičiūtė, 'Urban Development in Vilnius during the Second World War' (2012)：「Since Kaunas was still the actual capital, the Supreme Council of the Lithuanian SSR passed a resolution on 25 August 1940 to transfer the capital to Vilnius」", 'note': 'capitals_batch5 v2。 政府實際所在地是考納斯；法理首都是維爾紐斯。1940-08-25 最高蘇維埃決議遷都維爾紐斯，目標在 1941-09-01 前完成，日期在本政權範圍之後。'}}, {'old': None, 'reason': None, 'new': {'_id': 'CAP_PALERMO_AMGOT_ITALY', 'regimeId': '01a191a0-4580-7331-bfe8-e485b4024014', 'cityName': {'en': 'Palermo', 'zh': '巴勒莫'}, 'location': {'type': 'Point', 'coordinates': [13.3615, 38.1157]}, 'validStart': '1943-09-17', 'validEnd': '1944-03-01', 'sourceRef': '官方史：H. L. Coles & A. K. Weinberg, Civil Affairs: Soldiers Become Governors (U.S. Army Center of Military History, 1964), ch. VIII（AMGOT 總部先設在敘拉古，約兩週後遷往巴勒莫）與 ch. X（1943-10-21 起「Headquarters AMG, located in Palermo」管理後方靜態地區）', 'note': 'capitals_batch5 v2。 主點標巴勒莫（AMG 行政總部）。1943-10-21 起分出 AMG 15th Army Group，駐巴里，負責前線地區；同盟國管制委員會在布林迪西。這兩處只寫在 note。'}}]

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
    if old_key:
        old_id = sent.get(old_key)
        rk = old_key + "__RETRACTED"
        print(f"撤回 {old_key}（{old_id}）" + ("（已撤回，跳過）" if rk in sent else ""))
    if new:
        print(f"新增 {new['_id']}  {new['cityName'].get('zh') or new['cityName'].get('zh-Hant')}  {new['validStart']} – {new.get('validEnd') or '∞'}" + ("（已寫入，跳過）" if new["_id"] in sent else ""))
    if dry:
        continue
    if old_key:
        if not old_id:
            print("   FAIL 找不到舊記錄 id"); fail += 1; continue
        if rk not in sent:
            try:
                post(f"/api/v1/capital-records/{old_id}/retraction", {"reason": rp["reason"]}, key)
                sent[rk] = "retracted"; save(); print("   ✓ 撤回")
            except urllib.error.HTTPError as e:
                print(f"   FAIL 撤回 {e.code}：{e.read().decode()[:300]}"); fail += 1; continue
    if new and new["_id"] not in sent:
        body = {"regimeId": new["regimeId"], "cityName": normalize_city_name(new["cityName"]), "location": new["location"],
                "validStart": new["validStart"], "validEnd": new.get("validEnd"), "sourceRef": new.get("sourceRef"), "note": new.get("note")}
        if body["validEnd"] is None: del body["validEnd"]
        try:
            r = post("/api/v1/capital-records", body, key)
            sent[new["_id"]] = r["data"]["id"]; save(); print(f"   ✓ 新增 id = {r['data']['id']}")
        except urllib.error.HTTPError as e:
            print(f"   FAIL 新增 {e.code}：{e.read().decode()[:300]}"); fail += 1
print("\n（dry-run，未送出。）" if dry else f"\n完成：{len(REPLACEMENTS)} 組，失敗 {fail}。")
