"""shanghai_1937 R4 文字頂點（r4-text-vertices.json）與 battle.config r4 設定的建置腳本（引文經 tools/battles/citelib.py 逐字定位）。
用法：python3 -I tools/battles/builders/shanghai_1937_r4.py shanghai_1937；之後 python3 -I tools/battles/build_r4.py shanghai_1937
頂點座標：osm-places.json 的 admin_centre／label place 節點（依 georef.config.json lonlatRule＋Amendment），否則該筆結果須為 place 類；河流、車站、村宅級地名不作頂點。
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from citelib import Cites, REPO
if len(sys.argv) < 2 or sys.argv[1] != "shanghai_1937":
    raise SystemExit("用法：python3 -I tools/battles/builders/shanghai_1937_r4.py shanghai_1937")
BATTLE = sys.argv[1]
_C = Cites(BATTLE)
J, MN = _C.short("jm179"), _C.short("mnd2017")
F590 = _C.short("frus1937v03-d590")  # 主管 2026-11-13 20:56：us-frus（B）
D = REPO / "data/seed/battles" / BATTLE
o = json.loads((D / "osm-places.json").read_text())
def v(k, asin, note):
    ac = o.get("adminCentre", {}).get(k)
    if ac:
        n = ac["node"]; return {"lonlat": [round(n["lon"], 5), round(n["lat"], 5)], "px": None, "nearPlace": asin, "osm": {"type": "node", "id": n["id"]}, "vertexNote": note}
    x = o["results"][k][0]
    assert x["class"] == "place", k
    return {"lonlat": [round(x["lon"], 5), round(x["lat"], 5)], "px": None, "nearPlace": asin, "osm": {"type": x["type"], "id": x["id"]}, "vertexNote": note}
BASE = {"basis": "text", "estimate": "推估", "precision_m": None}
fronts = [
 BASE | {"date": "1937-09-14", "dateNote": "mnd2017：中央軍與左翼軍「於9月14日前退守」", "lineKey": "cn-front-1937-09-14", "lineKind": "front", "side": "allied",
  "label": "國軍守勢線（瀏河鎮－羅店－蘊藻濱－江灣－北站）",
  "vertices": [v("浏河镇", "瀏河鎮", "取 OSM 鎮 place 節點"), v("罗店镇", "羅店", "取 OSM 鎮 place 節點"), v("江湾镇#2", "江灣", "取 OSM quarter 節點（江灣舊鎮）")],
  "method": "文字頂點：只取原文點名之城鎮；蘊藻濱（河）與北站（車站，1937 站址與今不同）未作頂點",
  "precisionNote": "城鎮中心代替線位，誤差可達數公里；蘊藻濱段與北站端未數位化",
  "citations": [MN("團軍(左翼軍)於9月14日前退守瀏河鎮－羅"), MN("店－蘊藻濱－江灣－北站之線。日軍自14日"), F590("orderly Chinese withdrawal to a line running from Lotien southeast"), F590("in a fairly straight line to the North Station in Chapei")],
  "readNote": "mnd2017 雙欄 PDF，兩行屬同一欄相鄰行；FRUS 9/14 電只載羅店—北站段（未提瀏河），與 mnd2017 同線之南段一致"},
 BASE | {"date": "1937-11-05", "dateNote": "mnd2017：「至11月5日雙方對峙於」", "lineKey": "cn-jp-front-1937-11-05", "lineKind": "front", "side": "allied|axis",
  "label": "雙方對峙線（瀏河鎮－羅店西方－蘇州河左岸至南站）",
  "vertices": [v("浏河镇", "瀏河鎮", "取 OSM 鎮 place 節點"), v("罗店镇", "羅店西方", "原文羅店「西方」；取羅店鎮節點，實際線位在其西")],
  "method": "文字頂點：只取原文點名之城鎮；蘇州河左岸（河）與南站（車站）未作頂點",
  "precisionNote": "只覆蓋北端一小段；羅店西方偏移未量化",
  "citations": [MN("11月5日雙方對峙於瀏河鎮－羅店西方－蘇"), MN("州河左岸至南站之線"), MN("瀏河鎮－羅店北方－蘇州河左岸至南站轉移")],
  "readNote": "同文前句：10/22 反擊失利後中央與左翼軍向「瀏河鎮－羅店北方－蘇州河左岸至南站」轉移（日期未明），與 11/5 線幾同"},
 BASE | {"date": "1937-11-19", "dateNote": "JM-179：on 19 November；mnd2017：19日", "lineKey": "jp-advance-1937-11-19", "lineKind": "front", "side": "axis",
  "label": "日軍追擊抵達線（常熟－蘇州－嘉興）",
  "vertices": [v("常熟", "Changshu／常熟", "取 OSM 城市 admin_centre 節點"), v("苏州", "Suchou／吳縣", "取 OSM 城市 admin_centre 節點"), v("嘉兴", "Chiahsing／嘉興", "取 OSM 城市 admin_centre 節點")],
  "method": "文字頂點：原文點名三城（OSM 城市中心）", "precisionNote": "城市中心代替線位；抵達線為先頭部隊位置，非連續戰線",
  "citations": [J("advanced to the line connecting Cba~ahu, Suchou and ClUAhai!lg"), J("on 19 ~ovEmber"), MN("常熟、吳興、嘉興之線(達日軍大本營原定"), MN("追擊，先頭已進抵至常熟-吳縣-嘉興之線，")],
  "readNote": "mnd2017 兩處中段一作吳興、一作吳縣；採吳縣（＝蘇州，與 JM 一致）"},
 BASE | {"date": "1937-11-24", "dateNote": "JM-179：on the 24th", "lineKey": "jp-pursuit-boundary-1937-11-24", "lineKind": "boundary", "side": "axis",
  "label": "日軍追擊界線延伸（青陽鎮－無錫－吳興）",
  "vertices": [v("青阳镇", "Chingyangchen／青陽鎮", "取 OSM 鎮 admin_centre 節點（江陰青陽）"), v("无锡", "Wuhsi／無錫", "取 OSM 城市 label 節點"), v("湖州", "Wuhsing／吳興", "取 OSM 湖州 admin_centre 節點")],
  "method": "文字頂點：原文點名三地（OSM 中心）", "precisionNote": "作戰界線（大本營追擊限制線），非戰線",
  "citations": [J("Hence, on the 24th, the pursuit boundary was · extended to"), J("the line connect:ing Chingyangchen, Wubsi and Wuhsing.")]},
]
(D / "r4-text-vertices.json").write_text(json.dumps({"schema": "battle-data/0.1 r4-text-vertices", "researchedOn": "2026-11-13",
  "note": "tools/battles/build_r4.py 讀入；文字推得的頂點一律推估", "fronts": fronts}, ensure_ascii=False, indent=1) + "\n")
cp = D / "battle.config.json"; cfg = json.loads(cp.read_text())
cfg["r4"] = {"maps": ["jm179-map1", "mnd2017-fig4", "mnd2017-fig5"], "box": cfg["r8"]["box"],
  "dates": ["1937-08-13", "1937-08-23", "1937-09-14", "1937-10-01", "1937-11-05", "1937-11-13", "1937-11-19", "1937-11-24", "1937-11-26"],
  "dateGapNotes": {
   "1937-08-13": "開戰日：國軍圍攻虹口、楊樹浦日軍據點（市區），出處只有據點名（八字橋、持志大學等設施），無可作頂點之城鎮",
   "1937-08-23": "日軍吳淞、川沙口登陸日：只有登陸點，無連續戰線文字",
   "1937-10-01": "mnd2017：左翼退守「楊涇河西岸－陳家行－蘊藻濱之線」，三者為河流與村宅級地名，依規則不作頂點",
   "1937-11-13": "白茆口登陸日：只有登陸點",
   "1937-11-24": "當日只有日軍追擊界線（boundary，已收文字頂點），無戰線",
   "1937-11-26": "主期止日（吳興失陷）：出處無當日戰線"},
  "defaultGapNote": "jm179-map1、mnd2017 圖四／圖五皆未過 2 km 門檻（僅參考），圖三未配準；該日無文字頂點"}
cp.write_text(json.dumps(cfg, ensure_ascii=False, indent=1) + "\n")
print(len(fronts), "text fronts")
