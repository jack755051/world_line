"""Ellis 出版年：以美國國會圖書館（LoC）目錄紀錄核實 HMSO 初版（主管 2026-11-13 11:38 Q8）。

紀錄：LCCN 54001808（LoC 紀錄號 6044946），MODS https://lccn.loc.gov/54001808/mods，2026-11-13 取用：
  出版地 London；出版者 H.M. Stat. Off.；dateIssued 1953；xviii, 425 p. illus., ports., maps (part fold. col., 1 in pocket) 25 cm；附勘誤條。
HyperWar 封面頁的 1954 視為再印或轉錄差異，不採。只改 sources.json 的 ellis 條與 gaps.json 的出版年條。
"""
import json
from pathlib import Path

D = Path(__file__).resolve().parent.parent
S, G = D / "sources.json", D / "gaps.json"
s = json.loads(S.read_text()); e = s["ellis-war-in-france-flanders"]
e.update({"year": 1953, "edition": "HMSO 初版（London: H.M. Stationery Office, 1953）；HyperWar 封面頁作 1954，不採",
          "catalogue": {"library": "Library of Congress", "recordUrl": "https://lccn.loc.gov/54001808", "recordId": "LCCN 54001808（LoC 6044946）",
                        "field": "MODS dateIssued＝1953；placeTerm＝London；name＝H.M. Stat. Off.；extent＝xviii, 425 p. … maps (part fold. col., 1 in pocket)；note＝Erratum slip inserted",
                        "verified": True, "checkedOn": "2026-11-13"},
          "mapsNote": "LoC 紀錄載原書地圖部分為彩色摺頁；HyperWar 圖檔為灰階掃描，顏色（英紅、法綠、比棕、德藍）已失"})
e.pop("yearCandidates", None)
S.write_text(json.dumps(s, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
g = json.loads(G.read_text())
for x in g["gaps"]:
    if x["target"].startswith("ellis.year"):
        x.update({"kind": "resolved", "resolution": "LoC 目錄 LCCN 54001808：London, H.M. Stat. Off., 1953（HMSO 初版）。研究檔 gap「1953 vs 1954」以 1953 結案；1954 為 HyperWar 封面頁所載，不採。",
                  "resolvedOn": "2026-11-13", "resolvedBy": "執行者以 lccn.loc.gov MODS 紀錄核實（先前 WorldCat 等目錄 403）"})
G.write_text(json.dumps(g, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("ok")
