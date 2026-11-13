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
# ── 主管 2026-11-13 20:22：停止配準，改以文字＋地名座標畫近似前線（文字推定、待查證）。點位由 claude -p 自 Kennedy 摘出（.dev/battle/poland/work/fronts/）。
_op = json.loads((D / "osm-places.json").read_text()); _co = _op.get("coords", {})
def tv(name, osmq, note):
    r = _op["results"][osmq][0]; key = {"relation": "R", "way": "W", "node": "N"}[r["type"]] + str(r["id"])
    c = _co.get(key) or ({"lon": r["lon"], "lat": r["lat"]} if "lon" in r else None)
    return {"lonlat": [round(c["lon"], 5), round(c["lat"], 5)] if c else None, "px": None, "nearPlace": name, "osm": {"type": r["type"], "id": r["id"]}, "vertexNote": note}
TI = {"basis": "text", "estimate": "推估", "status": "待查證", "inference": "文字推定",
      "method": "文字推定（text-inferred）：只取原文點名的到達城鎮，取 OSM 城鎮中心，依北→南以直線相連；河名（無渡河點）不取點",
      "precision_m": None, "precisionNote": "點與點之間為直線，不代表實際戰線走向；誤差可達數十公里。僅供示意，待查證"}
fronts += [
 dict(TI, date="1939-09-05", dateNote="9/5–9/6 原文到達點（±1 天）", lineKey="de-advance-1939-09-05-text", lineKind="front", side="de", label="德軍前鋒（9/5 前後，文字推定）",
      vertices=[tv("Grudziądz", "Grudziądz", "原文 southeast of Grudziadz on 6 September（第 3、4 軍團會合）"), tv("Kraków", "Kraków", "原文 Cracow had been taken（9/6）")],
      citations=[K("Fourth Armies southeast of Grudziadz on 6 September,"), K("Cracow had been taken and remanants of the Cracow Army at Radom")],
      readNote="另 Tenth Army units were across the Pilica by 5 September（只有河名，未取點）"),
 dict(TI, date="1939-09-10", dateNote="9/10 原文到達點", lineKey="de-advance-1939-09-10-text", lineKind="front", side="de", label="德軍前鋒（9/10，文字推定）",
      vertices=[tv("Zambrów", "Zambrów", "原文 of Zambrow on 10 September"), tv("Przemyśl", "Przemyśl", "原文 crossed the San north and south of Przemysl（9/10）")],
      citations=[K("of Zambrow on 10 September. Units of the 10th Panzer Division"), K("Fourteenth Army right crossed the San north and south of Przemysl,")],
      readNote="兩端點之間（Vistula 中段、華沙周邊）原文無 9/10 具名點；Corps Wodrig 渡 Bug 河只有河名"),
 dict(TI, date="1939-09-17", dateNote="9/17 原文到達點", lineKey="de-advance-1939-09-17-text", lineKind="front", side="de", label="德軍前鋒（9/17，文字推定）",
      vertices=[tv("Białystok", "Białystok", "原文 XXI Corps in the Bialystok area"), tv("Brześć", "Brześć", "原文 XIX Corps in the Brzesc region"),
                tv("Lublin", "Lublin", "原文 Lublin was entered on 17 September"), tv("Biłgoraj", "Biłgoraj", "原文 Bilgoraj was taken（同段，日期未單獨寫明）")],
      citations=[K("Units of the XXI Corps in the Bialystok area and a motorized"), K("division of XIX Corps in the Brzesc region had already advanced"),
                 K("though stiff fighting continued southeast of the city, and Lublin"), K("On Tenth Army's eastern front, meanwhile, Bilgoraj was taken")],
      readNote="蘇軍 9/17 前鋒只有 IPN 圖說 Mołodeczno 一點，不成線；Kutno、Warsaw 為波軍被圍區，不列入前線"),
]
(D / "r4-text-vertices.json").write_text(json.dumps({"schema": "battle-data/0.1 r4-text-vertices", "researchedOn": "2026-11-13",
  "note": "tools/battles/build_r4.py 讀入；文字推得的頂點一律推估", "fronts": fronts}, ensure_ascii=False, indent=1) + "\n")
s = (D / "battle.config.json").read_text()
_cfg = json.loads((D / "battle.config.json").read_text()); _g = _cfg["r4"]["dateGapNotes"]
_g.update({"1939-09-01": "9/1 起始態勢＝開戰時國界，見 R8 疆界切片；文字只有 Danzig 一點，不另畫前線（文字推定，主管 20:22）",
  "1939-09-28": "文字推定：9/28 原文只有被圍區（Modlin、Warsaw 9/27）與 Narew–Vistula–San 河名分界線，無具名到達點，不成線",
  "1939-10-06": "文字推定：10/6 原文只有 Kock／Lublin 投降，無德蘇分界線具名點；10/1 分界線見 de-su-demarcation-1939-10-01",
  "1939-10-01": "10/1 只有德蘇分界線北端 Ostrołęka–Ostrów Mazowiecka 一段（文字推定）；另 Hela 10/1 請降為被圍區"})
(D / "battle.config.json").write_text(json.dumps(_cfg, ensure_ascii=False, indent=1) + "\n")
s = s.replace('"dateGapNotes": {}', '"dateGapNotes": {"1939-09-20": "Kennedy p.118：9/20 下令撤至 Narew–Vistula–San 河線，原文只有河名、無點名城鎮，未數位化", "1939-09-01": "9/1 起始態勢＝開戰時國界，見 R8 疆界切片；不另畫前線"}')
print("ok")
