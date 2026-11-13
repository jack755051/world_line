"""shanghai_1937 R1 部隊名冊與 R7 指揮官／待補人物的建置腳本（引文經 tools/battles/citelib.py 逐字定位；JM-179 引文照掃描 OCR 原樣）。
用法：python3 -I tools/battles/builders/shanghai_1937_r1r7.py shanghai_1937（可重跑；重跑後須再跑 verify_quotes／crosscheck／mark_fields --apply）
中文名：每筆 field_sources.nameZh 記出處——source-text＝取自所引中文 A/B 出處原文用字（nameZhStatus=from-source，未經人工審訂）；
executor-translation＝執行者譯名（不給 nameZhStatus，由 mark_fields 標 unreviewed）。一律繁體。
"""
import sys, json, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from citelib import Cites, REPO
if len(sys.argv) < 2 or sys.argv[1] != "shanghai_1937":
    raise SystemExit("用法：python3 -I tools/battles/builders/shanghai_1937_r1r7.py shanghai_1937（本 builder 內含 shanghai_1937 的研究資料，只接受此戰役代碼）")
BATTLE = sys.argv[1]
_C = Cites(BATTLE)
J, J70, JA, JB, SU, CH, MN = (_C.short(k) for k in ("jm179", "jm70", "jacar-c13071346000", "jacar-c11112056100", "su2015", "chang2016", "mnd2017"))
JD = _C.short("jacar-c11111935000")  # 主管 2026-11-13 20:56
OUT = REPO / "data/seed/battles" / BATTLE
MS = "1937-08-13"
NOTE = "起訖為本戰役主期（1937-08-13～11-26）內有出處的在場範圍，非單位編成／解編日；起日沒有出處者取主期起日（欄位內另標）或留空，止日未見出處者填 null"
RG = {"jp": "empire-of-japan", "cn": "republic-of-china-nationalist"}
SIDE = {"jp": "axis", "cn": "allied"}
units = []
def ZS(src, asin):  # 中文名取自出處原文
    return {"basis": "source-text", "sourceKey": src, "asInSource": asin}
def ZT(note=""):
    return {"basis": "executor-translation", "note": note or "執行者譯名，待審"}
def U(key, orig, zh, ech, parent, cites, zsrc, start=MS, end=None, note="", status="sourced"):
    n = key.split("-")[0]
    r = {"unitKey": key, "nameOrig": orig, "nameZh": zh, "echelon": ech, "parentKey": parent, "side": SIDE[n], "nation": n,
         "regimeSlug": RG[n], "period": {"start": start, "end": end, "startPrecision": "day" if start else None, "endPrecision": "day" if end else None},
         "periodNote": NOTE + (("；" + note) if note else ""), "citations": cites, "leads": [], "status": status, "note": "",
         "field_sources": {"nameZh": zsrc}}
    if zsrc["basis"] == "source-text":
        r["nameZhStatus"] = "from-source"
    units.append(r)

# ---------- 日軍 ----------
U("jp-ccaa", "中支那方面軍（Central China Area Army）", "華中方面軍", "army_group", None,
  [J("On 7 November, the Central Authorities organized the Central China Area")], ZT("日文原名中支那方面軍；中文通行譯名，待審"), start="1937-11-07",
  note="JM-179：11/7 臨時編成，統轄上海派遣軍與第十軍（戰鬥序列 12/1 才下達）")
U("jp-sea", "上海派遣軍（Shanghai Expeditionary Army）", "上海派遣軍", "army", "jp-ccaa",
  [J("the Shanghai Expeditionary Army landed at the"), JA("上海派遣軍ハ八月二十三日川沙鎮"), CH("15日日軍大本營下令編成上海派遣軍，以松井石根大將為司令官")],
  ZS("chang2016", "上海派遣軍"), start="1937-08-23", note="8/15 下令編成；8/23 登陸為本戰役在場起日；11/7 起隸中支那方面軍（之前直屬中央統帥部）")
U("jp-10-army", "第十軍（10th Army）", "第十軍", "army", "jp-ccaa",
  [JB("昭和十二年十月二十日第十軍ノ戦闘序列ヲ令セラル"), JB("五日午前三時三十分金出衛城南方予定泊地ニ投錨ヲ完了セリ"), CH("20日下達臨參命令第119號，命編組第十軍增援上海")],
  ZS("chang2016", "第十軍"), start="1937-11-05", note="10/20 下令編成；11/5 杭州灣（金山衛）登陸為在場起日。JACAR 翻刻作「金出衛」照錄")
U("jp-3-div", "第三師団（3d Division）", "第三師團", "division", "jp-sea",
  [J("the main force of which consisted ot the 3d and"), CH("準備以第十一師團（欠）及第三師團為基幹"), MN("23日晨日軍第3、11師團各以一部分別")],
  ZS("chang2016", "第三師團"), start="1937-08-23")
U("jp-11-div", "第十一師団（11th Division）", "第十一師團", "division", "jp-sea",
  [J("(minus the Amaya Detachment)"), CH("準備以第十一師團（欠）及第三師團為基幹"), MN("23日晨日軍第3、11師團各以一部分別")],
  ZS("chang2016", "第十一師團"), start="1937-08-23")
for k, o, zh, ord_ in [("jp-9-div", "第九師団（9th Division）", "第九師團", "9th Division"), ("jp-13-div", "第十三師団（13th Division）", "第十三師團", "13th Division"),
                       ("jp-101-div", "第百一師団（101st Division）", "第一〇一師團", "Division")]:
    cs = [J("from Japan to reinforce the Shanghai Expeditionary Army: 9th Division"), CH("增派第九、第十三及第101等3個師團增援上海")]
    if k == "jp-13-div": cs.append(MN("師團、第101師團及戰車聯隊、重砲兵聯隊"))
    if k == "jp-101-div": cs.append(MN("師團、第101師團及戰車聯隊、重砲兵聯隊"))
    if k == "jp-9-div": cs.append(MN("其第3、9、11師團及重籐旅團"))
    U(k, o, zh, "division", "jp-sea", cs, ZS("chang2016", {"jp-9-div": "第九", "jp-13-div": "第十三", "jp-101-div": "第101"}[k] + "（師團）") if k != "jp-101-div" else ZT("chang2016 作「第101」、mnd2017 作「第101師團」；中文數字寫法為執行者統一，待審"),
      start=None, note="JM-179 寫 9/11 自日本增援抵達；chang2016 寫 9/11 為臨參命令第九十九號下令日——起日兩說不一，留空（見 gaps）")
U("jp-16-div", "第十六師団（16th Division）", "第十六師團", "division", "jp-sea",
  [J("The 16th Division was assigned to the Shanghai Expeditionary Army on 30 October 1937"[:80]), CH("另從華北調用第十六師團受上海派遣軍之指揮"), MN("以新增之第16師配屬重藤旅團於白茆")],
  ZS("chang2016", "第十六師團"), start=None, note="10/30 隸上海派遣軍；白茆口登陸日 JM-179 文字 OCR 損壞（「]Jth」），JM-179 Map No. 1 圖上「13 NOV」標註屬地圖判讀；起日留空，11/13 只作候選")
units[-1]["startCandidate"] = {"value": "1937-11-13", "status": "candidate", "basis": "JM-179 OCR「]Jth」＋Map No. 1 圖上「13 NOV」（地圖未過 2 km，僅參考）"}
units[-1]["startUncertain"] = "OCR 讀值不確定：JM-179 原文「landed on the ]Jth」之「]Jth」讀作 13th 未經人工核對原掃描（主管 2026-11-13 16:14 Q5：欄位留空，11/13 只作候選）"
U("jp-6-div", "第六師団（6th Division）", "第六師團", "division", "jp-10-army",
  [JB("八口浦ニ於テ北支那方面ヨリ転用セラレタル第六師団及国崎支隊等ヲ掌握シ"), CH("由華北調用第六師團及第五師團的一部（國崎支隊）")], ZS("chang2016", "第六師團"), start="1937-11-05")
U("jp-18-div", "第十八師団（18th Division）", "第十八師團", "division", "jp-10-army",
  [JB("五島ニ於テ第十八師団ヲ"), CH("由滿洲調用第十八師團")], ZS("chang2016", "第十八師團"), start="1937-11-05")
U("jp-114-div", "第百十四師団（114th Division）", "第一一四師團", "division", "jp-10-army",
  [JB("第百十四属国ハ三十日大阪出発軍主力ニ追及ス"), CH("動員第114師團等")], ZT("chang2016 作「第114師團」；中文數字寫法為執行者統一，待審"), start=None,
  note="JACAR 翻刻「第百十四属国」照錄（應為師団之誤植）；只載 10/30 大阪出發追及主力，登陸日未載（起日空）")
U("jp-kunisaki-det", "国崎支隊（Kunisaki Detachment）", "國崎支隊", "detachment", "jp-10-army",
  [JB("八口浦ニ於テ北支那方面ヨリ転用セラレタル第六師団及国崎支隊等ヲ掌握シ"), CH("由華北調用第六師團及第五師團的一部（國崎支隊）")], ZS("chang2016", "國崎支隊"), start="1937-11-05",
  note="第五師團之一部（chang2016）；JM-179 註：主力為步兵第九旅團")
U("jp-shigeto-det", "重藤支隊（Shigeto Detachment）", "重藤支隊", "detachment", "jp-sea",
  [J("was commanded by Lt Gen Chiaki Shigeto"), MN("其第3、9、11師團及重籐旅團"), JD("（二）重藤兵団（重藤少将ノ指揮スル歩兵第三聯隊")], ZT("mnd2017 作「重籐旅團」、圖上作「重藤」；JM-179 作 Detachment，取支隊，待審"), start=None,
  note="JM-179 註：9/7 配屬上海派遣軍（OCR「7 Septenb er」），臺灣守備隊編成；抵達日未載（起日空）")
U("jp-amaya-det", "天谷支隊（Amaya Detachment）", "天谷支隊", "detachment", "jp-11-div",
  [J("(minus the Amaya Detachment)"), CH("9月2日，另從青島增援的天谷支隊從海路抵達吳淞外海")], ZS("chang2016", "天谷支隊"), start="1937-09-02",
  note="原屬第十一師團，8/15 先派大連；9/1 令歸建（JM-179）")
U("jp-shanghai-snlf", "上海海軍特別陸戦隊（Shanghai Special Naval Landing Force）", "上海海軍特別陸戰隊", "naval_infantry", None,
  [J("the Naval Special Landing"), CH("日軍兵力集結在其海軍司令部附近的特別陸戰隊不足5,000名")], ZT("chang2016 作「特別陸戰隊」；冠「上海海軍」為執行者補，待審"))
U("jp-3rd-fleet", "第三艦隊（3rd Fleet）", "第三艦隊", "fleet", None,
  [CH("其第三艦隊司令官長谷川清中將"), SU("日本第三艦隊並駛集黃浦江")], ZS("su2015", "第三艦隊"))

# ---------- 國軍 ----------
U("cn-3rd-war-zone", "第三戰區", "第三戰區", "army_group", None,
  [SU("顧祝同就任第三戰區副司令長官"), CH("另頒第四號訓令，對第三戰區（華東）的指導方針")], ZS("su2015", "第三戰區"), start=None,
  note="8/20 第四號訓令（chang2016）；戰區成立日未明載（起日空）")
U("cn-left-wing", "左翼軍", "左翼軍", "army_group", "cn-3rd-war-zone", [SU("〈對左翼軍各將領訓話〉（1937年10月29日）"), MN("中央與左翼軍被迫向")], ZS("su2015", "左翼軍"), start=None)
U("cn-central", "中央軍", "中央作戰軍", "army_group", "cn-3rd-war-zone", [MN("張治中集團軍(中央軍)")], ZT("mnd2017 作「中央軍」；為免與「中央軍（嫡系）」混淆加「作戰」，待審"), start=None)
U("cn-right-wing", "右翼軍", "右翼軍", "army_group", "cn-3rd-war-zone", [MN("以張發奎集團軍(右翼軍)任杭州灣北")], ZS("mnd2017", "右翼軍"), start=None)
U("cn-9-ag", "第九集團軍", "第九集團軍", "army", "cn-central",
  [SU("令第九集團軍（淞滬警備軍隊改編者）於明十四日拂曉開始攻擊虹口、楊樹浦"), MN("第9集團軍專責上海市區之作戰")], ZS("su2015", "第九集團軍"),
  note="8/13 夜軍委會令；隸中央軍據 mnd2017「張治中集團軍(中央軍)」")
U("cn-15-ag", "第十五集團軍", "第十五集團軍", "army", "cn-left-wing",
  [SU("表陳為第三戰區前敵總指揮兼第十五集團軍總司令"), MN("吳淞鎮以北歸新編之第15集團軍負責")], ZS("su2015", "第十五集團軍"), start=None,
  note="隸左翼軍據 mnd2017「陳誠集團軍(左翼軍)」敘述（該句在雙欄 PDF 中斷行，未取為引文）")
U("cn-19-ag", "第十九集團軍", "第十九集團軍", "army", None, [MN("第9、19兩集團軍所屬部隊於10日始沿")], ZT("mnd2017 作「19（集團軍）」；中文數字為執行者統一"), start=None)
U("cn-21-ag", "第二十一集團軍", "第二十一集團軍", "army", None, [MN("21集團軍固守瀏河鎮至嘉定一線")], ZT("mnd2017 作「第21集團軍」；中文數字為執行者統一"), start=None)
U("cn-songhu-garrison", "淞滬警備司令部", "淞滬警備司令部", "hq", None, [SU("淞滬警備司令楊虎所指揮之上海市保安總團")], ZT("su2015 作「淞滬警備司令」（職稱）；機關名為執行者補，待審"))
U("cn-18-corps", "第十八軍", "第十八軍", "corps", None,
  [SU("第十八軍（下轄第十一師、第十四師、第六十七師、第九十八師）"), CH("第十八軍羅卓英部第十一、十四、六十師")], ZS("su2015", "第十八軍"), start=None,
  note="su2015 列下轄 11、14、67、98 師；chang2016 寫「十一、十四、六十師」（疑脫字），見 gaps；上級出處未載")
U("cn-39-corps", "第三十九軍", "第三十九軍", "corps", None, [MN("第39軍之第56師及江蘇保安團")], ZT("mnd2017 作「第39軍」；中文數字為執行者統一"))
U("cn-78-corps", "第七十八軍", "第七十八軍", "corps", None, [SU("第七十八軍軍長宋希濂")], ZS("su2015", "第七十八軍"), start=None)
for k, zh, par, cs, st, nt in [
    ("cn-36-div", "第三十六師", "cn-78-corps", [SU("蔣復電令第三十六師提前開赴上海，限14日到達目的地")], "1937-08-14", "限 8/14 到達；隸第七十八軍出處未明言（依宋希濂兼任推定，待查）"),
    ("cn-87-div", "第八十七師", "cn-9-ag", [SU("京滬警備司令張治中所指揮之第八十七、八十八兩個師"), MN("第87師一部進駐吳淞鎮、劉家宅及舊市政府")], MS, ""),
    ("cn-88-div", "第八十八師", "cn-9-ag", [SU("京滬警備司令張治中所指揮之第八十七、八十八兩個師"), MN("第88師向東推進")], MS, ""),
    ("cn-56-div", "第五十六師", "cn-39-corps", [SU("並命駐蚌埠之第五十六師"), MN("第39軍之第56師及江蘇保安團")], MS, "chang2016 同句作「蚌埠之第五師」，與 su2015 不一（見 gaps）"),
    ("cn-57-div", "第五十七師", None, [MN("第57師由嘉興向龍華前進")], MS, ""),
    ("cn-98-div", "第九十八師", "cn-18-corps", [SU("第十八軍（下轄第十一師、第十四師、第六十七師、第九十八師）"), MN("第98師於12日由漢口向淞滬地區船運")], MS, ""),
    ("cn-11-div", "第十一師", "cn-18-corps", [SU("第十八軍（下轄第十一師、第十四師、第六十七師、第九十八師）"), CH("第十八軍羅卓英部第十一、十四、六十師")], None, ""),
    ("cn-14-div", "第十四師", "cn-18-corps", [SU("第十八軍（下轄第十一師、第十四師、第六十七師、第九十八師）"), CH("第十八軍羅卓英部第十一、十四、六十師")], None, ""),
    ("cn-67-div", "第六十七師", "cn-18-corps", [SU("第十八軍（下轄第十一師、第十四師、第六十七師、第九十八師）")], None, ""),
    ("cn-63-div", "第六十三師", "cn-right-wing", [MN("63師防守")], None, "金山衛正面僅一師（mnd2017 該句雙欄斷行，只取「63師防守」）；隸右翼軍為推定"),
    ("cn-107-div", "第一〇七師", None, [MN("8日，日軍擊退107師")], None, ""),
    ("cn-40-div", "第四十師", None, [MN("13日日軍擊破任江防之第40師")], None, "11/13 白茆口方面"),
]:
    z = ZS("su2015", zh) if any(c["sourceKey"] == "su2015" for c in cs) else ZT("mnd2017 用阿拉伯數字；中文數字為執行者統一")
    U(k, zh, zh, "division", par, cs, z, start=st, note=nt)
U("cn-ind-20-bde", "獨立第二十旅", "獨立第二十旅", "brigade", None, [SU("獨立第二十旅"), MN("獨立第20旅於12日晚進駐南翔鎮")], ZS("su2015", "獨立第二十旅"))

# ---------- R7 ----------
PI = json.loads((REPO / ".dev/battle/person-index.json").read_text())
def bio(pk):
    for v in (PI["generals"].values() if isinstance(PI["generals"], dict) else PI["generals"]):
        if v.get("personKey") == pk: return v["bioId"]
    raise SystemExit("no bio " + pk)
cmds, missing = [], []
def CM(unit, name, zh, pk, cites, zsrc, start=None, end=None, note="", nameOrig=None, prio=2, role="commander"):
    t = {"start": start, "end": end, "precision": {"start": "day" if start else None, "end": "day" if end else None}}
    rec = {"unitKey": unit, "role": role, "name": name, "nameZh": zh, "personKey": pk, "bioId": bio(pk) if pk else None, "tenure": t, "citations": cites,
           "bioStatus": "has_bio" if pk else "missing_bio", "note": note, "field_sources": {"nameZh": zsrc}}
    if zsrc["basis"] == "source-text": rec["nameZhStatus"] = "from-source"
    cmds.append(rec)
    if not pk:
        missing.append({"name": name, "nameOrig": nameOrig or name, "nameZh": zh, "unitKey": unit, "tenure": t, "citations": cites,
                        "priority": prio, "note": note, "unitKeys": [unit], "field_sources": {"nameZh": zsrc}} | ({"nameZhStatus": "from-source"} if zsrc["basis"] == "source-text" else {}))
CM("jp-sea", "Iwane Matsui", "松井石根", "iwanematsui", [CH("以松井石根大將為司令官")], ZS("chang2016", "松井石根"), end="1937-11-07", note="11/7 轉任中支那方面軍司令官（JM-179 註 14）")
CM("jp-ccaa", "Iwane Matsui", "松井石根", "iwanematsui", [J("Iwane Matsui")], ZS("chang2016", "松井石根"), start="1937-11-07")
CM("jp-sea", "Prince Yasuhiko Asaka", "朝香宮鳩彥王", None, [J("Lt Gen Yasuhiko")], ZT("中文名為執行者譯名（鳩彥王），待審"), start="1937-11-07", prio=1,
   note="JM-179 註 14 OCR 作「Yasuhiko As~ka」，只取未損片段", nameOrig="朝香宮鳩彦王（Asaka Yasuhiko）")
CM("jp-10-army", "Heisuke Yanagawa", "柳川平助", None, [J("Lt Gen Heisuke Yanagawa"), CH("司令官由柳川平助中將出任")], ZS("chang2016", "柳川平助"), prio=1, nameOrig="柳川平助")
CM("jp-shigeto-det", "Chiaki Shigeto", "重藤千秋", None, [J("was commanded by Lt Gen Chiaki Shigeto")], ZT("中文名依日文漢字，待審"), prio=2, nameOrig="重藤千秋")
CM("jp-3rd-fleet", "Kiyoshi Hasegawa", "長谷川清", None, [CH("其第三艦隊司令官長谷川清中將")], ZS("chang2016", "長谷川清"), prio=2, nameOrig="長谷川清")
CM("cn-3rd-war-zone", "Feng Yuxiang", "馮玉祥", "fengyuxiang", [SU("而第三戰區司令長官當時實由馮玉祥出任")], ZS("su2015", "馮玉祥"), note="su2015：戰區初期司令長官實由馮玉祥出任；蔣中正自兼之日期本輪出處未載（見 gaps）")
CM("cn-3rd-war-zone", "Gu Zhutong", "顧祝同", "guzhutong", [SU("顧祝同就任第三戰區副司令長官")], ZS("su2015", "顧祝同"), role="deputy_commander")
CM("cn-15-ag", "Chen Cheng", "陳誠", "chencheng", [SU("表陳為第三戰區前敵總指揮兼第十五集團軍總司令")], ZS("su2015", "陳誠"), note="引文稱「陳」，前句明言陳誠")
CM("cn-9-ag", "Zhang Zhizhong", "張治中", "zhangzhizhong", [SU("令第九集團軍（淞滬警備軍隊改編者）於明十四日拂曉開始攻擊虹口、楊樹浦"), MN("張治中集團軍(中央軍)")], ZS("su2015", "張治中"),
   note="su2015 該令文未點名；以 mnd2017「張治中集團軍(中央軍)」連結；後由朱紹良接替之日期本輪出處未載")
CM("cn-right-wing", "Zhang Fakui", "張發奎", "zhangfakui", [MN("以張發奎集團軍(右翼軍)任杭州灣北")], ZS("mnd2017", "張發奎"))
CM("cn-18-corps", "Luo Zhuoying", "羅卓英", "luozhuoying", [CH("第十八軍羅卓英部第十一、十四、六十師")], ZS("chang2016", "羅卓英"))
CM("cn-78-corps", "Song Xilian", "宋希濂", None, [SU("第七十八軍軍長宋希濂")], ZS("su2015", "宋希濂"), prio=2)
CM("cn-36-div", "Song Xilian", "宋希濂", None, [SU("第三十六師宋希濂部、第八十七師王敬久部、第八十八師孫元良部")], ZS("su2015", "宋希濂"), prio=2)
CM("cn-87-div", "Wang Jingjiu", "王敬久", None, [SU("第三十六師宋希濂部、第八十七師王敬久部、第八十八師孫元良部")], ZS("su2015", "王敬久"), prio=2)
CM("cn-88-div", "Sun Yuanliang", "孫元良", None, [SU("第三十六師宋希濂部、第八十七師王敬久部、第八十八師孫元良部")], ZS("su2015", "孫元良"), prio=2)
CM("cn-songhu-garrison", "Yang Hu", "楊虎", None, [SU("淞滬警備司令楊虎所指揮之上海市保安總團")], ZS("su2015", "楊虎"), prio=3)
mm = {}
for m in missing:
    if m["name"] in mm:
        a = mm[m["name"]]; a["unitKeys"].append(m["unitKey"]); a["citations"] += m["citations"]; a["priority"] = min(a["priority"], m["priority"])
    else: mm[m["name"]] = m
missing = list(mm.values())
hdr = lambda s: {"schema": f"battle-data/0.1 {s}", "researchedOn": "2026-11-13"}
r1 = hdr("r1") | {"gradePolicy": "AB-only (C only in leads)",
                  "sideNote": "side：axis＝日本；allied＝中華民國（1937 年尚無同盟國／軸心之分，沿用展示頁陣營代碼）",
                  "echelonNote": "army_group＝中支那方面軍、戰區、左翼／中央／右翼作戰軍；army＝日軍「軍」與國軍「集團軍」；corps＝國軍「軍」；detachment＝日軍支隊；海軍只到艦隊與陸戰隊",
                  "units": units}
r7 = hdr("r7") | {"gradePolicy": "AB-only", "commanders": cmds}
r7m = hdr("r7-missing") | {"priorityNote": "1=方面軍／軍司令官層級，建議先補；2=師／支隊／艦隊層級；3=機關首長。本輪不研究生平，不補主檔。", "people": missing}
for f, d in [("r1-units.json", r1), ("r7-commanders.json", r7), ("r7-missing-people.json", r7m)]:
    (OUT / f).write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n")
print("units", len(units), collections.Counter((u["nation"], u["echelon"]) for u in units))
print("cmds", len(cmds), "bio", sum(1 for c in cmds if c["personKey"]), "missing", len(missing))
