"""shanghai_1937 R3 部隊位置（文字）／R5 交戰／R6 地點控制的建置腳本（引文經 tools/battles/citelib.py 逐字定位；JM-179 引文照掃描 OCR 原樣）。
用法：python3 -I tools/battles/builders/shanghai_1937_r356.py shanghai_1937（可重跑；重跑後須再跑 verify_quotes／crosscheck／mark_fields --apply）
地點只給出處地名＋OSM 編號（優先 admin_centre／label 之 place 節點，依 georef.config.json lonlatRule），不含座標；
三張已配準的圖（jm179-map1、mnd2017-fig4、fig5）全未過 2 km 門檻，R3 全部為文字出處。
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from citelib import Cites, REPO
if len(sys.argv) < 2 or sys.argv[1] != "shanghai_1937":
    raise SystemExit("用法：python3 -I tools/battles/builders/shanghai_1937_r356.py shanghai_1937（本 builder 內含 shanghai_1937 的研究資料，只接受此戰役代碼）")
BATTLE = sys.argv[1]
_C = Cites(BATTLE)
J, JA, JB, SU, MN = (_C.short(k) for k in ("jm179", "jacar-c13071346000", "jacar-c11112056100", "su2015", "mnd2017"))
OUT = REPO / "data/seed/battles" / BATTLE
_OP = json.loads((OUT / "osm-places.json").read_text())
OSM, AC = _OP["results"], _OP.get("adminCentre", {})
def place(k):
    if k is None: return {"nameOsm": None, "osm": None}
    if AC.get(k):
        n = AC[k]["node"]; return {"nameOsm": n["name"], "osm": {"type": "node", "id": n["id"]}, "osmVia": {"type": "relation", "id": AC[k]["relation"], "role": AC[k]["role"]}}
    x = OSM[k][0]
    return {"nameOsm": x["name"].split(",")[0], "osm": {"type": x["type"], "id": x["id"]}}
hdr = lambda s: {"schema": f"battle-data/0.1 {s}", "researchedOn": "2026-11-13"}
# ---------- R3 ----------
pos = []
def R3(unit, date, asin, pk, rel, cites, also=(), attr=None, dp="day", dnote=None):
    d = {"unitKey": unit, "date": date, "datePrecision": dp, "placeAsInSource": asin, "place": place(pk), "basis": "text", "relation": rel,
         "alsoPlaces": [dict(placeAsInSource=a, **place(b)) for a, b in also], "citations": cites}
    if attr: d["attributionNote"] = attr
    if dnote: d["dateNote"] = dnote
    pos.append(d)
R3("cn-ind-20-bde", "1937-08-12", "南翔鎮", "南翔镇", "deployed", [MN("4.獨立第20旅於12日晚進駐南翔鎮。")], dnote="主期前一日（開戰前部署）；OSM 只查得火車站，無 place 節點")
R3("cn-9-ag", "1937-08-12", "大場、彭浦及蘇州河北岸", "大场镇", "deployed", [MN("1.第9集團軍(淞滬警備隊改編)各以一"), MN("部進駐大場、彭浦及蘇州河北岸。")], also=[("彭浦", "彭浦")], dp="approx",
   dnote="mnd2017「中、日雙方遂調整部署如下」段，開戰前（8/12 前後）")
R3("cn-87-div", "1937-08-12", "吳淞鎮、劉家宅及舊市政府", "吴淞街道", "deployed", [MN("3.第88師向東推進，第87師一部進駐吳"), MN("淞鎮、劉家宅及舊市政府。")], dp="approx", attr="87 師一部", dnote="同上部署段，開戰前")
R3("cn-56-div", "1937-08-12", "瀏河至江陰地區江防", "浏河镇", "deployed", [MN("2.第39軍之第56師及江蘇保安團奉命擔"), MN("任瀏河至江陰地區江防。")], also=[("江陰", "江阴")], dp="approx",
   dnote="同上部署段，開戰前；為瀏河—江陰沿江帶狀防區，place 只標兩端")
R3("cn-87-div", "1937-08-14", "八字橋、持志大學及滬江大學", None, "captured", [MN("14日入夜後，第87、88師先後奪"), MN("取八字橋、持志大學及滬江大學要點，並持")], dnote="八字橋 OSM 查無；地點留出處地名")
R3("cn-88-div", "1937-08-14", "八字橋、持志大學及滬江大學", None, "captured", [MN("14日入夜後，第87、88師先後奪"), MN("取八字橋、持志大學及滬江大學要點，並持")])
R3("jp-sea", "1937-08-23", "川沙鎮及呉淞桟橋附近", "吴淞街道", "landed", [JA("上海派遣軍ハ八月二十三日川沙鎮"), JA("呉淞桟橋附近ニ上陸シテ"), J("On . 23 August, the Shanghai Expeditionary Army landed at the"), J("mouth of the Huangpu River and in the area northwest thereof,")],
   attr="JACAR「川沙鎮」與今浦東川沙同名而位置不同（mnd2017 圖四標於長江岸），不給 OSM；place 只取呉淞")
R3("jp-3-div", "1937-08-23", "吳淞、寶山、川沙口附近", "吴淞街道", "landed", [MN("23日晨日軍第3、11師團各以一部分別"), MN("於吳淞、寶山、川沙口附近地區登陸，擊破")], also=[("寶山", "宝山城")], attr="原文 3、11 師團各以一部分別登陸，未分配地點")
R3("jp-11-div", "1937-08-23", "吳淞、寶山、川沙口附近", "吴淞街道", "landed", [MN("23日晨日軍第3、11師團各以一部分別"), MN("於吳淞、寶山、川沙口附近地區登陸，擊破")], also=[("寶山", "宝山城")], attr="同上")
R3("cn-15-ag", "1937-08-23", "吳淞、寶山、川沙口、羅店、瀏河等方面", "罗店镇", "attacking", [MN("15集團軍自8月23日至9月11日間，分向吳淞"), MN("、寶山、川沙口、羅店、瀏河等方面日軍發")], dp="approx",
   also=[("吳淞", "吴淞街道"), ("寶山", "宝山城"), ("瀏河", "浏河镇")], dnote="8/23–9/11 期間（取起日）")
R3("jp-sea", "1937-10-05", "大場鎮附近", "大场镇", "attacking", [JA("十月上旬ヨリ重点ヲ大場鎮附近ニ指向シ攻撃セシガ")], dp="approx", dnote="原文「十月上旬」，日期取旬中，推估", attr="主語「軍」＝上海派遣軍（上文）")
R3("jp-10-army", "1937-11-05", "金山衛（金出衛城南方）", "金山卫", "landed", [MN("11月5日拂曉，日軍以其第10軍在金山"), MN("衛附近行登陸，擊破國軍薄弱守備部隊(63"), JB("五日午前三時三十分金出衛城南方予定泊地ニ投錨ヲ完了セリ"), J("As soon as the lOth Army landed in the vicinity of Hangchou")],
   attr="JACAR 翻刻「金出衛」照錄（金山衛）")
R3("cn-63-div", "1937-11-05", "金山衛附近", "金山卫", "defending", [MN("衛附近行登陸，擊破國軍薄弱守備部隊(63"), MN("師之兩個步兵連)後，繼向黃浦江方向進攻")], attr="63 師之兩個步兵連")
R3("cn-107-div", "1937-11-08", "得勝口", None, "defending", [MN("江北岸。8日，日軍擊退107師，由得勝口渡")], dnote="得勝口 OSM 查無（黃浦江渡口）", attr="日軍擊退 107 師後由得勝口渡江向松江")
R3("cn-15-ag", "1937-11-12", "瀏河鎮至嘉定一線", "浏河镇", "covering_withdrawal", [MN("21集團軍固守瀏河鎮至嘉定一線，掩護戰區"), MN("主力撤退。該兩集團軍於12日夜達成任務後")], also=[("嘉定", "嘉定城")], attr="上一行「所幸第15、」接本行「21集團軍」（同一欄）")
R3("cn-21-ag", "1937-11-12", "瀏河鎮至嘉定一線", "浏河镇", "covering_withdrawal", [MN("21集團軍固守瀏河鎮至嘉定一線，掩護戰區"), MN("主力撤退。該兩集團軍於12日夜達成任務後")], also=[("嘉定", "嘉定城")])
R3("jp-16-div", "1937-11-13", "白茆口、滸浦口（Paimaokou）", "白茆", "landed", [MN("同時以新增之第16師配屬重藤旅團於白茆"), MN("口、滸浦口登陸，企圖切斷國軍主力退路。"), J("(the 16th Division and an element of the Shigeto"), J("kou on 16 November, landed on the ]Jth.")],
   dnote="JM-179 OCR「]Jth」讀作 13th（原定 16 日）；mnd2017 未載日期，判讀待審")
R3("jp-shigeto-det", "1937-11-13", "白茆口、滸浦口（Paimaokou）", "白茆", "landed", [MN("同時以新增之第16師配屬重藤旅團於白茆"), J("(the 16th Division and an element of the Shigeto"), J("kou on 16 November, landed on the ]Jth.")], attr="JM：an element of the Shigeto Detachment")
R3("jp-16-div", "1937-11-13", "ten kilometers east of Changshu", "常熟", "reached", [J("opposition and advanced to within ten kilometers east of Changshu")], attr="常熟以東 10 km，place 只取常熟", dnote="JM 同日（same day）")
R3("cn-40-div", "1937-11-13", "江防（地點未載）", None, "defending", [MN("13日日軍擊破任江防之第40師，並以空軍猛")], dnote="地點出處未載")
# ---------- R5 ----------
eng = []
def E(key, orig, zh, start, end, asin, pk, att, dfn, cites, status="sourced", note=None, conflict=None, gap=None, prec="day", zhb="出處原文（mnd2017 節名）"):
    d = {"key": key, "nameOrig": orig, "nameZh": zh, "nameZhBasis": zhb, "period": {"start": start, "end": end, "precision": prec},
         "place": dict(asInSource=asin, **place(pk)), "attackers": att, "defenders": dfn, "status": status, "citations": cites}
    if note: d["note"] = note
    if conflict: d["conflict"] = conflict
    if gap: d["gapReason"] = gap
    eng.append(d)
E("siege-hongkou", "國軍圍攻時期", "國軍圍攻時期（虹口、楊樹浦）", "1937-08-13", "1937-08-20", "虹口之敵；楊樹浦市街", None, ["cn-9-ag", "cn-87-div", "cn-88-div", "cn-36-div"], ["jp-shanghai-snlf"],
  [MN("(一)國軍圍攻時期(8月13日至8月20日)"), MN("民國26年8月13日夜，軍事委員會令第9"), MN("集團軍於次日拂曉開始攻擊虹口之敵"), MN("列87、88、36三個師向敵陣地中央薄弱處發"), JA("十三日同方面交戦状態ニ入リ")],
  note="守方 mnd2017 稱「日海軍陸隊隊據守營房」；R1 jp-shanghai-snlf。虹口 OSM 未查")
E("wusong-liuhe", "吳淞至瀏河鎮間反登陸作戰", "吳淞至瀏河鎮間反登陸作戰", "1937-08-23", "1937-09-10", "吳淞至瀏河鎮間", "吴淞街道", ["jp-sea", "jp-3-div", "jp-11-div", "jp-9-div", "jp-shigeto-det"], ["cn-15-ag"],
  [MN("(二)吳淞至瀏河鎮間反登陸作戰(8月23"), MN("23日晨日軍第3、11師團各以一部分別"), MN("15集團軍自8月23日至9月11日間，分向吳淞"), JA("上海派遣軍ハ八月二十三日川沙鎮"), J("On . 23 August, the Shanghai Expeditionary Army landed at the")],
  conflict="止日：mnd2017 節名 9/10；同文正文 15 集團軍攻擊至 9/11。取節名 9/10", note="日方攻方含「第3、9、11師團及重籐旅團」（mnd2017 正文）")
E("defensive-phase", "國軍守勢時期", "國軍守勢時期（蘊藻濱、大場鎮）", "1937-09-06", "1937-11-05", "蘊藻濱；大場鎮附近", "大场镇", ["jp-sea", "jp-9-div", "jp-13-div", "jp-101-div"], ["cn-central", "cn-left-wing"],
  [MN("(三)國軍守勢時期(9月6日至11月5日)"), MN("至10月1日，國軍左翼方面被迫退守楊涇"), MN("師團、第101師團及戰車聯隊、重砲兵聯隊"), JA("十月上旬ヨリ重点ヲ大場鎮附近ニ指向シ攻撃セシガ"), J("Toward the end of the month, however, it started to break")],
  note="涵蓋大場鎮失守；大場失守日出處只到「同月下旬」（JACAR），見 R6")
E("suzhou-creek", "蘇州河", "蘇州河之戰", None, "1937-11-09", "蘇州河（同河畔ノ既設特火点陣地）", None, ["jp-sea"], ["cn-central"],
  [JA("同月下旬戦況漸ク進展ス軍ハ直チニ蘇州河ニ向ヒ追撃シ"), JA("九日遂ニ敵ヲ撃退シ十一日上海南市ヲ掃蕩セリ"), J("through enemy positions and pursued the enemy toward the Suchou Ho.")], prec="approx", zhb="執行者譯名",
  note="起日只到「10 月下旬」（JACAR「同月下旬」、JM「Toward the end of the month」），留空；止日 11/9 只有 JACAR；守方為中央軍屬執行者依 mnd2017 11/5 對峙線「蘇州河左岸至南站」推定，待查證", status="partial")
E("zhabei-800", "八百壯士（死守閘北）", "閘北八百壯士", "1937-10-26", None, "閘北", "闸北", ["jp-sea"], ["一團（su2015 未載番號，未列 R1）"],
  [SU("26 日，蔣考慮「滬戰不利之影響」"), SU("同日夜間，淞滬前線國軍移轉陣"), SU("地，並在閘北留一團死守，以「感動中外」")], status="partial", zhb="出處原文（su2015）",
  note="起日由 su2015「26 日……同日夜間」推得（上下文為 10 月）；止日出處未載；攻方為上海派遣軍屬推定")
E("hangzhou-bay", "杭州灣北岸反登陸作戰", "杭州灣北岸反登陸作戰", "1937-11-05", "1937-11-08", "金山衛附近", "金山卫", ["jp-10-army", "jp-6-div", "jp-18-div", "jp-kunisaki-det"], ["cn-right-wing", "cn-63-div", "cn-107-div"],
  [MN("(四)杭州灣北岸反登陸作戰(11月5日至"), MN("11月5日拂曉，日軍以其第10軍在金山"), MN("江北岸。8日，日軍擊退107師，由得勝口渡"), JB("五日午前三時三十分金出衛城南方予定泊地ニ投錨ヲ完了セリ"), J("As soon as the lOth Army landed in the vicinity of Hangchou")],
  note="第 6、18 師團與國崎支隊隨第十軍航渡（JACAR c111 上文），各自登陸點出處未分")
E("baimao-landing", "白茆口登陸", "白茆口、滸浦口登陸", "1937-11-13", "1937-11-13", "白茆口、滸浦口（Paimaokou）", "白茆", ["jp-16-div", "jp-shigeto-det"], [],
  [MN("同時以新增之第16師配屬重藤旅團於白茆"), MN("口、滸浦口登陸，企圖切斷國軍主力退路。"), J("kou on 16 November, landed on the ]Jth."), J("It enoountered. very little")], zhb="出處原文（mnd2017）",
  note="JM-179：幾無抵抗；守方出處未載。日期依 JM OCR「]Jth」讀作 13 日，待審", status="partial")
E("retreat-pursuit", "轉進作戰", "轉進作戰（日軍追擊至常熟—蘇州—嘉興線）", "1937-11-08", "1937-11-26", "京滬兩側地區；吳福線；錫澄線", None, ["jp-ccaa", "jp-sea", "jp-10-army", "jp-16-div"], ["cn-3rd-war-zone", "cn-9-ag", "cn-15-ag", "cn-19-ag", "cn-21-ag"],
  [MN("(五)轉進作戰(11月8日至12月7日)"), J("the Chinese began a general retreat on 12 Novem.ber"), J("12 November, the Expeditionary Army began a full-scale pursuit and"), MN("擊，掩護友軍通過。19日追擊部隊已進抵至"), MN("常熟、吳興、嘉興之線(達日軍大本營原定"), MN("興激戰，迄26日吳興失陷，第7軍向孝豐轉")],
  conflict="起日：mnd2017 11/8（轉進令）、JM 11/12（全面撤退／追擊開始）；止日 mnd2017 12/7，本表截至主期止日 11/26（吳興失陷）")
E("wuxing", "吳興", "吳興之戰", "1937-11-20", "1937-11-26", "吳興", "湖州", ["日軍（出處未載番號）"], ["第7軍（未列 R1）"],
  [MN("部隊向錫、澄線轉進，20日國軍與日軍於吳"), MN("興激戰，迄26日吳興失陷，第7軍向孝豐轉")], zhb="執行者譯名", note="只有 mnd2017 一族")
# ---------- R6 ----------
sites = []
REG = {"axis": "empire-of-japan", "allied": "republic-of-china-nationalist", None: None}
def S(asin, pk, date, ctrl, ev, cites, status="sourced", note=None, conflict=None, dp="day", dnote=None):
    d = {"placeAsInSource": asin, "place": place(pk), "date": date, "datePrecision": dp, "controllerAfter": ctrl, "controllerRegimeSlug": REG[ctrl],
         "sovereignRegimeSlug": "republic-of-china-nationalist", "event": ev, "status": status, "citations": cites}
    if dnote: d["dateNote"] = dnote
    if note: d["note"] = note
    if conflict: d["conflict"] = conflict
    sites.append(d)
S("呉淞（呉淞桟橋附近）／吳淞", "吴淞街道", "1937-08-23", "axis", "landed", [JA("呉淞桟橋附近ニ上陸シテ"), MN("於吳淞、寶山、川沙口附近地區登陸，擊破")], status="partial", note="登陸點，非全鎮控制；吳淞鎮全面易手日出處未載")
S("閘北", "闸北", "1937-10-26", None, "main_force_withdrew_garrison_left", [SU("同日夜間，淞滬前線國軍移轉陣"), SU("地，並在閘北留一團死守，以「感動中外」")], status="partial",
  dnote="su2015「26 日……同日夜間」，上下文為 10 月", note="國軍主力移轉、留一團死守；日軍占領日出處未載，controllerAfter 留空")
S("大場鎮", "大场镇", None, "axis", "captured", [JA("十月上旬ヨリ重点ヲ大場鎮附近ニ指向シ攻撃セシガ"), JA("同月下旬戦況漸ク進展ス軍ハ直チニ蘇州河ニ向ヒ追撃シ")], status="partial", dp="month-part",
  dnote="出處只到「十月下旬」（JACAR），常見之 10/26 本輪 A/B 出處未見，日期留空", note="控制方為日軍屬推定（下旬戰況進展、轉向蘇州河追擊）")
S("金山衛（金出衛城南方）", "金山卫", "1937-11-05", "axis", "landed", [MN("11月5日拂曉，日軍以其第10軍在金山"), MN("衛附近行登陸，擊破國軍薄弱守備部隊(63"), JB("五日午前三時三十分金出衛城南方予定泊地ニ投錨ヲ完了セリ")])
S("上海南市／Shanghai", "上海南市", "1937-11-11", "axis", "cleared", [JA("九日遂ニ敵ヲ撃退シ十一日上海南市ヲ掃蕩セリ"), J("12 November, the Expeditionary Army began a full-scale pursuit and"), J("cleared Shanghai and its vicinity of Chinese troops.")],
  conflict="JACAR：11/11 掃蕩南市；JM-179：11/12 起追擊並肅清上海及附近。取 JACAR 11/11（南市）", note="上海公共租界與法租界不在此列（主權／控制另見 R8）")
S("白茆口", "白茆", "1937-11-13", "axis", "landed", [MN("同時以新增之第16師配屬重藤旅團於白茆"), J("kou on 16 November, landed on the ]Jth.")], status="partial", dnote="JM OCR「]Jth」讀作 13 日，待審")
for asin, pk in [("常熟（Changshu）", "常熟"), ("蘇州／吳縣（Suchou）", "苏州"), ("嘉興（Chiahsing）", "嘉兴")]:
    S(asin, pk, "1937-11-19", "axis", "line_reached", [J("advanced to the line connecting Cba~ahu, Suchou and ClUAhai!lg"), J("on 19 ~ovEmber"), MN("擊，掩護友軍通過。19日追擊部隊已進抵至"), MN("常熟、吳興、嘉興之線(達日軍大本營原定"), MN("追擊，先頭已進抵至常熟-吳縣-嘉興之線，")],
      conflict="mnd2017 同文兩處：「常熟、吳興、嘉興之線」與「常熟-吳縣-嘉興之線」；JM 作 Changshu–Suchou–Chiahsing。採吳縣（蘇州）", note="抵達線，非城市攻占日；JM OCR 地名照錄（Cba~ahu＝Changshu、ClUAhai!lg＝Chiahsing）")
S("吳興", "湖州", "1937-11-26", "axis", "captured", [MN("興激戰，迄26日吳興失陷，第7軍向孝豐轉")], note="只有 mnd2017 一族")
for f, d in [("r3-unit-positions.json", hdr("r3") | {"note": "主期 1937-08-13～11-26；地點只給出處地名＋OSM 編號（優先 admin_centre／label place 節點），不含座標；relation 為執行者歸類標籤；三張配準圖全未過 2 km，R3 全部為文字出處", "positions": pos}),
             ("r5-engagements.json", hdr("r5") | {"note": "舊 data/campaigns/shanghai_1937.json 只作線索；交戰分段依 mnd2017 節名（轉引國防部《抗日戰史》）並以 JACAR／JM-179 對照；conflict 欄記來源差異", "engagements": eng}),
             ("r6-site-control.json", hdr("r6") | {"note": "controllerAfter：axis＝日軍、allied＝國軍；null 表示出處未載控制方；sovereignRegimeSlug 皆為中華民國（租界另見 R8）", "sites": sites})]:
    (OUT / f).write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n")
print(len(pos), "R3;", len(eng), "R5;", len(sites), "R6")
