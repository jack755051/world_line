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
]
have = {x.get("target") for x in L}
for t, k, n in NEW:
    if t not in have: L.append({"target": t, "kind": k, "note": n, "checkedOn": "2026-11-13"})
p.write_text(json.dumps(g, ensure_ascii=False, indent=1) + "\n"); print(len(L))
