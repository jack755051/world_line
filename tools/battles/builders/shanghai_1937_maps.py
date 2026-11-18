"""shanghai_1937 地圖目錄（map-catalog.json）與 maps/SHA256SUMS.txt 的建置腳本。
用法：python3 -I tools/battles/builders/shanghai_1937_maps.py shanghai_1937（可重跑；數值由 digitized/<mapKey>.json（georef.py 輸出）讀入）
"""
import sys, json, hashlib
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
if len(sys.argv) < 2 or sys.argv[1] != "shanghai_1937":
    raise SystemExit("用法：python3 -I tools/battles/builders/shanghai_1937_maps.py shanghai_1937")
D = REPO / "data/seed/battles/shanghai_1937"
JM = "https://www.ibiblio.org/hyperwar/Japan/Monos/pdfs/JM-179/JM-179.pdf"
MN = "https://navy.mnd.gov.tw/Files/Paper/3-%E5%AD%AB%E5%AD%90%E5%85%B5%E6%B3%95%E8%99%9B%E5%AF%A6.pdf"
MNC = "張琪閔、蕭新民〈從孫子兵法「虛實」觀點淺談1937年淞滬會戰〉，《海軍學術雙月刊》51:4（2017），圖{n}（轉載蔣緯國《國民革命戰史》第三部第五卷{a}）"
maps = [
 ("jm179-map1", "Japanese Monograph No. 179, Map No. 1 'Shanghai Operation 23 Aug–24 Nov 1937'（PDF 第 18 頁）", JM, "B", "1937-11-24", None),
 ("mnd2017-fig1", MNC.split("，圖")[0] + "，圖一（出處見原文圖說，未核對是否轉載蔣緯國）", MN, "B", None, "戰前態勢概覽圖（非本戰役主期態勢），比例過小；只入目錄，未數位化"),
 ("mnd2017-fig2", MNC.format(n="二", a="附圖六"), MN, "B", "1937-08-20", "市區圖：可辨識之地物幾乎全為設施（車站、碼頭、學校、公園），依 controlPointRule 皆不得作控制點；未配準（未跑任何擬合即決定）"),
 ("mnd2017-fig3", MNC.format(n="三", a="附圖六"), MN, "B", "1937-09-10", "可用城鎮控制點不足 7 點：多數城鎮符號被部隊標註遮蓋或為村宅級地名（依 controlPointRule 排除）；未配準（未跑任何擬合即決定）"),
 ("mnd2017-fig4", MNC.format(n="四", a="附圖八"), MN, "B", "1937-09-13", None),
 ("mnd2017-fig5", MNC.format(n="五", a="附圖12"), MN, "B", "1937-11-05", None),
 ("mnd2017-fig6", MNC.format(n="六", a="附圖二"), MN, "B", None, "轉進時期全區圖，646 px 寬下地名與部隊字樣多不可辨；未數位化"),
]
rows = []
for mk, cit, url, g, md, why in maps:
    r = {"mapKey": mk, "file": f"maps/{mk}.jpg", "citation": cit, "url": url, "grade": g, "mapDate": md}
    p = D / "digitized" / f"{mk}.json"
    if p.exists():
        m = json.loads(p.read_text()); th = m["threshold"]
        rd = D / "checks/label-reading2" / f"{mk}.json"
        r |= {"digitized": True, "secondReading": rd.exists(), "controlPoints": len(m["control_points"]),
              "loo_p95_km": th["loo_p95_km"], "passes": th["passes"], "referenceOnly": th.get("referenceOnly"),
              "controlPointExclusions": len(th.get("controlPointExclusions", [])),
              "exclusionsAllDecidedBeforeResiduals": all(x.get("decidedBeforeResiduals") for x in th.get("controlPointExclusions", [])),
              "use": "可取部隊位置／前線頂點" if th["passes"] else "僅供參考（標註判讀與 unitKey 對應仍做）"}
    else:
        r |= {"digitized": False, "secondReading": False, "controlPoints": None, "loo_p95_km": None, "passes": False, "use": "僅入目錄", "notDigitizedReason": why}
    rows.append(r)
(D / "map-catalog.json").write_text(json.dumps({"schema": "battle-data/0.1 map-catalog", "researchedOn": "2026-11-13",
  "rule": "留一法 95 百分位 ≤ 2 km 才可取部隊位置／前線頂點；未過者僅供參考。圖檔不進版控，只留 maps/SHA256SUMS.txt；控制點排除理由須在看殘差前定好，看過殘差後才排除任何一點者整張圖僅參考（主管 2026-11-13 15:33，tools/battles/georef.py 強制）",
  "maps": rows}, ensure_ascii=False, indent=1) + "\n")
lines = [f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.name}" for f in sorted((D / "maps").glob("*.jpg"))]
(D / "maps/SHA256SUMS.txt").write_text("\n".join(lines) + "\n")
print(len(rows), "maps;", len(lines), "checksums")
