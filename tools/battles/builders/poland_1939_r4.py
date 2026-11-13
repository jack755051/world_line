"""poland_1939 R4 文字頂點（r4-text-vertices.json）與 battle.config r4.dateGapNotes的建置腳本（由 .dev/battle/poland/build/r4.py 複製；引文經 tools/battles/citelib.py 逐字定位）。
用法：python3 -I tools/battles/builders/poland_1939_r4.py poland_1939（可重跑；重跑後須再跑 verify_quotes／crosscheck／mark_fields --apply）
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from citelib import Cites, REPO
if len(sys.argv) < 2 or sys.argv[1] != "poland_1939":
    raise SystemExit("用法：python3 -I tools/battles/builders/poland_1939_r4.py poland_1939（本 builder 內含 poland_1939 的研究資料，只接受此戰役代碼）")
BATTLE = sys.argv[1]
_C = Cites(BATTLE)
K, L, P, BP = (_C.short(k) for k in ("kennedy-dapam-20-255", "lemo-scriba-polen-1939", "ipn-suleja-wrzesien-1939", "bpb-vogel-lieb-blitzkriege"))
B = REPO
import json
D = B / "data/seed/battles" / BATTLE
o = json.loads((B / "data/seed/battles" / BATTLE / "osm-places.json").read_text())["withCoords"]
v = lambda k, note: {"lonlat": [round(o[k]["lon"], 5), round(o[k]["lat"], 5)], "px": None, "nearPlace": k, "osm": {"type": o[k]["type"], "id": o[k]["id"]}, "vertexNote": note}
fronts = [{
  "date": "1939-10-01", "dateNote": "Kennedy p.118–119：10/1 OKH 通知南方集團軍群分界線再次變更",
  "lineKey": "de-su-demarcation-1939-10-01", "lineKind": "boundary", "side": "de|su", "label": "德蘇分界線（10/1 變更後）",
  "vertices": [v("Ostrołęka", "原文 to Ostroleka；取 OSM 城鎮中心"), v("Ostrów Mazowiecka", "原文 past Ostrow Mazowiecka；取 OSM 城鎮中心")],
  "basis": "text", "estimate": "推估",
  "method": "文字頂點：只取原文明確點名的城鎮（OSM Nominatim 中心點）；Pisa／Narew 河段、布格河、Tomaszów 以東某點、San 河至斯洛伐克邊界等河段未數位化",
  "precision_m": None, "precisionNote": "城鎮中心代替河線，誤差可達數公里；線段只覆蓋全線北端一小段",
  "citations": [K("Pisia and Narew Eivers to Ostroleka, thence past Ostrow Mazowiecka to the Bug"), K("south along the latter to a point east of Tomaszow, west to the San")],
  "readNote": "Kennedy 原文 Eivers 為 Rivers 之掃描錯字，引文照錄"}]
(D / "r4-text-vertices.json").write_text(json.dumps({"schema": "battle-data/0.1 r4-text-vertices", "researchedOn": "2026-11-13",
  "note": "tools/battles/build_r4.py 讀入；文字推得的頂點一律推估", "fronts": fronts}, ensure_ascii=False, indent=1) + "\n")
s = (D / "battle.config.json").read_text()
s = s.replace('"dateGapNotes": {}', '"dateGapNotes": {"1939-09-20": "Kennedy p.118：9/20 下令撤至 Narew–Vistula–San 河線，原文只有河名、無點名城鎮，未數位化", "1939-09-01": "9/1 起始態勢＝開戰時國界，見 R8 疆界切片；不另畫前線"}')
(D / "battle.config.json").write_text(s); print("ok")
