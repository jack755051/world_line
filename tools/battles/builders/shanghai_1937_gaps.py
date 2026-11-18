"""shanghai_1937 gaps.json（只追加，不刪；以 target 去重）的建置腳本。
用法：python3 -I tools/battles/builders/shanghai_1937_gaps.py shanghai_1937
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from citelib import REPO
if len(sys.argv) < 2 or sys.argv[1] != "shanghai_1937":
    raise SystemExit("用法：python3 -I tools/battles/builders/shanghai_1937_gaps.py shanghai_1937")
p = REPO / "data/seed/battles/shanghai_1937/gaps.json"
g = json.loads(p.read_text()) if p.exists() else {"schema": "battle-data/0.1 gaps", "gaps": []}
L = g["gaps"]
NEW = [
 ("source:tw-mnd-kangri-zhanshi", "source_unavailable", "國防部史政編譯局《抗日戰史》淞滬會戰各冊（及《抗日戰史（四）華東地區作戰》1994）無合法線上全文；只能經 mnd2017 轉引"),
 ("source:jp-senshi-sosho-086", "source_unavailable", "防衛研修所戦史室『戦史叢書086 支那事変陸軍作戦〈1〉』：NIDS 只公開目次，無全文；日方 A 級改以 JACAR 防衛研究所藏原始檔案（目錄頁「内容」欄翻刻）"),
 ("source:hsu-long-hsuen", "source_unavailable", "Hsu Long-hsuen & Chang Ming-kai, History of the Sino-Japanese War (1937–1945)：無可取得全文"),
 ("source:sinica", "source_partial", "中研院（近史所）可取得之相關檔僅蘇聖雄 2020〈空間換取時間？〉（臺大歷史學報，華北為主），未收；中方只有 tw-roc 一族"),
 ("source:jacar-images", "source_unavailable", "JACAR 檔案影像（含挿図、要図）須互動檢視器，不抓；只引目錄頁「内容」欄文字"),
 ("source:family-independence", "decision_needed", "tw-roc 族內（國史館館刊 2 文、國防部期刊 1 文）是否拆成兩族待主管裁示；目前保守合一，中方內部不互證"),
 ("source:jm179-ocr", "quality", "JM-179 為掃描 OCR，多處損字（如「lJ Auaaust」「]Jth」「As~ka」）；引文只取未損片段並照 OCR 原樣，損字處的日期不取"),
 ("r1:jp-reinforcement-dates", "date_conflict", "第九、第十三、第一〇一師團：JM-179 寫 9/11 自日本增援抵達，chang2016 寫 9/11 為臨參命令第九十九號（下令日）；mnd2017 敘述 9 月下旬陸續登陸。起日留空"),
 ("r1:cn-56-vs-5-div", "source_conflict", "8/11 由蚌埠調蘇州歸張治中指揮之師：su2015 作「第五十六師」，chang2016 作「第五師」；R1 依 su2015 與 mnd2017（第39軍之第56師）列第五十六師，第五師不建"),
 ("r1:cn-18-corps-divisions", "source_conflict", "第十八軍下轄：su2015 作十一、十四、六十七、九十八師；chang2016 作「十一、十四、六十師」（疑脫「七」字）；依 su2015"),
 ("r1:cn-8-10-ag", "unit_no_text_source", "第八集團軍（張發奎）、第十集團軍（劉建緒）等番號在本輪取得之 A/B 文字出處中未見（mnd2017 只稱「張發奎集團軍(右翼軍)」）；未建單位"),
 ("r1:cn-roster-partial", "partial_roster", "國軍參戰約 70 餘師（JM-179 註 9 稱最終 85 個中國師），R1 只列有 A/B 文字出處的 12 個師、1 旅；mnd2017 表三（開戰初期國軍指揮系統表，圖片）與圖上番號未建單位"),
 ("r1:jp-table-commanders", "commander_table_only", "第三師團長藤田進、第十一師團長山室宗武只見於 mnd2017 表四（圖片表格，轉引《抗日戰史》插表二），無文字引文，R7 不列"),
 ("r7:chiang-zhu-xue", "commander_no_source", "蔣中正兼第三戰區司令長官、朱紹良接任第九集團軍／中央作戰軍、薛岳（第十九集團軍）、廖磊（第二十一集團軍）之任期，本輪 A/B 文字出處未載；R7 不列"),
 ("name:nameJa", "name_no_source", "日方戰役名（上海事変／第二次上海事変等）本輪日方出處未見，nameJa 留空"),
 ("maps:all-fail-2km", "map_threshold", "已配準三張圖留一 95 百分位：jm179-map1 17.95 km、mnd2017 圖四 2.36 km、圖五 3.12 km，全未過 2 km（僅參考）；圖三控制點不足未配準，圖一／二／六未數位化。R3／R4 全靠文字"),
 ("r2:jm179-px-convention", "reading_method", "jm179-map1 第一次判讀 px 取部隊框中心、第二次取框旁文字中心，相距常超過 1.5% 圖寬容差，致多筆 notFoundInReading2／reading2Only；標註文字本身多一致，待統一 px 約定後重比"),
 ("r2:reading2-only-labels", "reading_incomplete", "第二次判讀多讀到的標註（如 fig4 之 58D(一部)、51D、16D(-) 等）第一次未列，未回補進 features（避免看過第二次後改第一次）"),
 ("r3:bazi-bridge-osm", "place_unresolved", "八字橋、得勝口、虹口、蘇州河：OSM Nominatim 查無 place 物件，R3／R5 只留出處地名"),
 ("r3:chuansha-ambiguity", "place_ambiguous", "JACAR「川沙鎮」與今浦東川沙同名；mnd2017 圖四標於長江岸（川沙口附近）。不給 OSM"),
 ("r4:1937-10-01-line", "front_no_vertices", "mnd2017 10/1 左翼退守「楊涇河西岸－陳家行－蘊藻濱之線」：河流與村宅級地名，依規則不作頂點"),
 ("r4:urban-front", "front_partial", "9/14、11/5 戰線南段（蘊藻濱、蘇州河左岸、北站、南站）為河流與車站，未數位化；兩線只覆蓋北段"),
 ("r5:suzhou-creek-start", "date_missing", "蘇州河之戰起日只到「10 月下旬」（JACAR 同月下旬、JM Toward the end of the month）；止日 11/9 只有 JACAR"),
 ("r5:baimao-date-ocr", "date_ocr", "白茆口登陸日依 JM-179 OCR「landed on the ]Jth」讀作 11/13，mnd2017 未載日期；待人工核對原掃描"),
 ("r6:dachang-date", "date_missing", "大場鎮失守：本輪 A/B 出處只到「十月下旬」（JACAR），常見之 10/26 未見 A/B 出處，R6 日期留空"),
 ("r6:zhabei-songjiang-suzhou", "site_no_date", "閘北日軍占領日、松江失守日、蘇州／嘉興／無錫實際占領日（JM 只記 11/19 抵達線、11/24 追擊界線）出處未載"),
 ("r6:wuxing-single", "single_family", "吳興 11/26 失陷只有 mnd2017（tw-roc 一族）"),
 ("r8:settlements", "sovereignty_gap", "主專案主權資料 1937-08-13 戰區框內只有 empire-of-japan、republic-of-china-nationalist（另 united-states-of-america 僅外框相交）；無上海公共租界／法租界紀錄，窗內無變更日，只一切片"),
 ("r8:occupation-not-sovereignty", "sovereignty_scope", "R8 為法理（de_jure）主權層；日軍占領區（R6）不改變主權，故 11/11 南市、11/19 常熟等不產生疆界切片"),
]
have = {x.get("target") for x in L}
for t, k, n in NEW:
    if t not in have: L.append({"target": t, "kind": k, "note": n, "checkedOn": "2026-11-13"})
p.write_text(json.dumps(g, ensure_ascii=False, indent=1) + "\n"); print(len(L))
