"""poland_1939 R3 文字位置、R5 交戰、R6 據點易手的建置腳本（由 .dev/battle/poland/build/r356.py 複製；引文經 tools/battles/citelib.py 逐字定位）。
用法：python3 -I tools/battles/builders/poland_1939_r356.py poland_1939（可重跑；重跑後須再跑 verify_quotes／crosscheck／mark_fields --apply）
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from citelib import Cites, REPO
if len(sys.argv) < 2 or sys.argv[1] != "poland_1939":
    raise SystemExit("用法：python3 -I tools/battles/builders/poland_1939_r356.py poland_1939（本 builder 內含 poland_1939 的研究資料，只接受此戰役代碼）")
BATTLE = sys.argv[1]
_C = Cites(BATTLE)
K, L, P, BP = (_C.short(k) for k in ("kennedy-dapam-20-255", "lemo-scriba-polen-1939", "ipn-suleja-wrzesien-1939", "bpb-vogel-lieb-blitzkriege"))
B = REPO
import json
OUT = B / "data/seed/battles" / BATTLE
_OP = json.loads((B / "data/seed/battles" / BATTLE / "osm-places.json").read_text())
OSM, PICK = _OP["results"], _OP.get("pick", {})
def place(k):
    if k is None: return {"nameOsm": None, "osm": None}
    x = OSM[k][PICK.get(k, 0)]
    return {"nameOsm": k, "osm": {"type": x["type"], "id": x["id"]}}
hdr = lambda s: {"schema": f"battle-data/0.1 {s}", "researchedOn": "2026-11-13"}
# ---------- R3 ----------
pos = []
def R3(unit, date, asin, pk, rel, cites, also=(), attr=None, dp="day", dnote=None):
    d = {"unitKey": unit, "date": date, "datePrecision": dp, "placeAsInSource": asin, "place": place(pk), "basis": "text", "relation": rel,
         "alsoPlaces": [dict(placeAsInSource=a, **place(b)) for a, b in also], "citations": cites}
    if attr: d["attributionNote"] = attr
    if dnote: d["dateNote"] = dnote
    pos.append(d)
R3("pl-armia-modlin", "1939-09-01", "Mławy", "Mława", "defending", [P("Armia „Modlin” gen. Emila Krukowicza-Przedżymirskiego broniła dostępu do Mławy"), K("the Novogrodsha Cavalry Brigade in the Mlawa area")],
   dp="approx", dnote="IPN 列於邊境戰（9/1–9/3）段；Kennedy 於 9/1 午後段落", attr="Kennedy 句只稱 Mlawa 地區之波軍單位，屬 Modlin Army 依上下文")
R3("de-i-ak", "1939-09-02", "Mlawa front", "Mława", "attacking", [K("On the Mlawa front I Corps failed to make any further progress")], dnote="Kennedy p.81 9/2 段落")
R3("de-i-ak", "1939-09-03", "Mlawa defenses", "Mława", "attacking", [K("by the attack of Corps Wodrig from the east, broke into the Mlawa defenses")], dp="approx", dnote="Kennedy p.82 9/3 段落（Third and Fourth Armies 會師節）", attr="句主語為 The I Corps（跨頁）")
R3("de-korps-wodrig", "1939-09-03", "Mlawa defenses (from the east)", "Mława", "attacking", [K("by the attack of Corps Wodrig from the east, broke into the Mlawa defenses")], dp="approx")
R3("de-xxi-ak", "1939-09-02", "Grudziadz", "Grudziądz", "advancing_toward", [K("in its advance toward Grudziadz on 2 September")])
R3("pl-16-dp", "1939-09-03", "Grudziadz area", "Grudziądz", "defending", [K("16th Infantry Division in the Grudziadz area on 3 September")])
R3("pl-armia-pomorze", "1939-09-03", "Borach Tucholskich", "Bory Tucholskie", "encircled", [P("została otoczona w Borach Tucholskich")], dp="approx", dnote="IPN 同段首句「Obrona pierwszej linii załamała się ostatecznie 3 września」", attr="引文主語為「Część armii „Pomorze”」")
R3("de-4-pz-div", "1939-09-08", "suburbs of Warsaw", "Warszawa", "reached", [K("reached the suburbs of Warsaw with its 4th Panzer Division on 8 September")])
R3("pl-naczelny-wodz", "1939-09-07", "Brześciu", "Brześć", "hq", [P("Naczelnego Wodza, który od 7 września stacjonował wraz ze sztabem w Brześciu")])
R3("pl-armia-poznan", "1939-09-09", "Łęczycę, Piątek i Łowicz", "Łęczyca", "attacking_toward", [P("9 września pojawił się promyk nadziei"), P("Kontruderzenie, skierowane na Łęczycę, Piątek i Łowicz")], also=[("Piątek", "Piątek"), ("Łowicz", "Łowicz")], attr="IPN：zwrot zaczepny znad Bzury siłami armii „Poznań” i „Pomorze”")
R3("pl-armia-pomorze", "1939-09-09", "Łęczycę, Piątek i Łowicz", "Łęczyca", "attacking_toward", [P("9 września pojawił się promyk nadziei"), P("dokonany siłami armii „Poznań” i „Pomorze”")], also=[("Piątek", "Piątek"), ("Łowicz", "Łowicz")])
R3("de-8-armee", "1939-09-07", "vicinity of Lodz", "Łódź", "hq", [K("On 7 September Eighth Army moved to the vicinity of Lodz")])
R3("de-8-armee", "1939-09-11", "Kutno", "Kutno", "assigned_operation", [K("On 11 September OKH placed Eighth Army in control of operations")], attr="同句後半 against the Polish forces about Kutno")
R3("pl-armia-poznan", "1939-09-11", "Kutno", "Kutno", "encircled", [K("hastened the encirclement of the Poznan Army at Kutno")], dp="approx", dnote="Kennedy p.102 9/11 前後段落")
R3("de-10-armee", "1939-09-09", "Konskie", "Końskie", "hq", [K("Tenth Army moved to Konskie on 9 September")])
R3("de-hgr-sued", "1939-09-13", "Kielce", "Kielce", "hq", [K("Army Group South moved its headquarters on 13 September to Kielce")])
R3("de-10-pz-div", "1939-09-14", "Brzesc", "Brześć", "reached", [K("On 14 September the 10th Panzer Division reported that its forward elements")], attr="同句後半 had reached Brzesc")
R3("de-20-mot-div", "1939-09-17", "the Citadel (Brzesc)", "Brześć", "captured", [K("The Citadel was finally taken on 17 September"), K("an infantry regiment of the 20th Motorized Infantry Division launched an assault")])
R3("de-3-pz-div", "1939-09-17", "Wlodowa (direction)", "Włodawa", "advancing_toward", [K("the 3d Panzer Division moved around the city to the east")], dp="approx", attr="同句後半 drove southward in the direction of Wlodowa；與 Citadel 攻克同時段")
R3("de-1-geb-div", "1939-09-12", "the city (Lwow)", "Lwów", "reached", [K("1st Mountain Division reached the fortifications of the city on 12 September")], attr="上文 direction of Lwow；為該師之 Schoerner 支隊")
R3("de-xviii-ak", "1939-09-14", "Lwow", "Lwów", "encircling", [K("Lwow was completely encircled by XVIII Corps units by 14 September")])
R3("pl-low", "1939-09-14", "Oksywie Flats", "Oksywie", "withdrew_to", [K("on 14 September Gdynia was taken"), K("The Polish force of Colonel Dabek was forced to retreat to the Oksywie Flats")])
R3("pl-obrona-warszawy", "1939-09-27", "Warsaw; eastern suburb of Praga", "Warszawa", "surrendered", [K("Hostilities ceased at 1400 on 27 September"), K("including the garrison in the eastern suburb of Praga")], also=[("Praga", "Praga")])
R3("pl-obrona-modlina", "1939-09-29", "Modlin", "Modlin", "surrendered", [K("Polish troops at Modlin laid down their arms in unconditional surrender"), K("Surrender of Modlin.")])
R3("pl-rejon-umocniony-hel", "1939-10-01", "Hela", "Hel", "surrendered", [K("On 1 October Rear Admiral J. Unrug, commander at Hela")])
R3("pl-sgo-polesie", "1939-10-04", "Kock", "Kock", "fighting", [K("Kock, where heavy fighting raged from 4 to 6 October"), P("pod Kockiem siły SGO „Polesie” gen. Franciszka Kleeberga")], attr="Kennedy 稱 the Kock force")
# ---------- R5 ----------
eng = []
def E(key, orig, zh, start, end, asin, pk, att, dfn, cites, status="sourced", note=None, cand=None, conflict=None, gap=None, prec="day"):
    d = {"key": key, "nameOrig": orig, "nameZh": zh, "nameZhBasis": "執行者譯名", "period": {"start": start, "end": end, "precision": prec},
         "place": dict(asInSource=asin, **place(pk)), "attackers": att, "defenders": dfn, "status": status, "citations": cites}
    if cand: d["candidateFrom"] = "demo-battle.json"; d["candidateId"] = cand
    if note: d["note"] = note
    if conflict: d["conflict"] = conflict
    if gap: d["gapReason"] = gap
    eng.append(d)
E("westerplatte", "Westerplatte", "西盤半島防禦戰", "1939-09-01", "1939-09-07", "Westerplatte", "Westerplatte", ["Linienschiff Schleswig-Holstein（未列 R1）"], ["pl-westerplatte"],
  [K("the Schleswig-Holstein commenced shelling the Polish fortress of Westerplatte"), P("Na Westerplatte już o 4:45 padły pierwsze pociski"), L("in den frühen Morgenstunden des 1. September 1939"), L("Um 4.45 Uhr eröffnete das Linienschiff"), P("Westerplatte, zamiast godzin 12, broniło się przez długich 7 dni"), P("7 września, oficerowie Wojska Polskiego z placówki na Westerplatte")], cand="e-westerplatte",
  note="止日 9/7 只有 IPN（7 日、照片說明 9/7 投降後）；Kennedy 未載投降日")
E("mokra", "Mokra", "莫克拉之戰", None, None, "Mokrą", "Mokra", ["de-4-pz-div"], ["Wołyńska Brygada Kawalerii（旅級，未列 R1）"],
  [P("na czele swej Wołyńskiej BK powstrzymał pod Mokrą 4. dywizję pancerną")], cand="e-mokra", note="IPN 未載日期（列於邊境戰段）；展示頁 9/1 未採", status="partial")
E("mlawa", "Mława", "姆瓦瓦之戰", "1939-09-01", "1939-09-03", "Mlawa area", "Mława", ["de-i-ak", "de-korps-wodrig", "de-3-armee"], ["pl-armia-modlin"],
  [K("German tank attacks were stopped with heavy loss by antitank fire"), K("the Novogrodsha Cavalry Brigade in the Mlawa area"), K("by the attack of Corps Wodrig from the east, broke into the Mlawa defenses"),
   P("Armia „Modlin” gen. Emila Krukowicza-Przedżymirskiego broniła dostępu do Mławy"), P("Obrona pierwszej linii załamała się ostatecznie 3 września")], cand="e-mlawa", note="止日 9/3 取 Kennedy 9/3 段落「broke into the Mlawa defenses」與 IPN 第一線崩潰 9/3")
E("tuchola", "Bory Tucholskie (Corridor)", "圖霍拉森林（走廊）之戰", "1939-09-01", "1939-09-03", "Borach Tucholskich", "Bory Tucholskie", ["de-4-armee", "de-xix-ak"], ["pl-armia-pomorze", "pl-9-dp", "pl-27-dp"],
  [K("Fourth Army gains of 2 September sealed off the Pomorze Army's 9th Infantry"), P("została otoczona w Borach Tucholskich"), P("oddziały 9. i 27. DP")], cand="e-tuchola", prec="approx",
  note="Kennedy 未用 Tuchola 地名（稱 Corridor）；止日取 IPN 第一線崩潰 9/3，推估")
E("wizna", "Wizna", "維茲納防禦戰", None, "1939-09-10", "Wizną / Wizna", "Wizna", ["de-xix-ak", "de-10-pz-div"], ["Odcinek Wizna（未列 R1）"],
  [K("The XIX Corps' 10th Panzer Division crossed the Narew at Wizna"), P("9 września Niemcy zajęli Wyszków. Dzień później zakończyła się bohaterska obrona"[:80]), P("schronów nad Wizną")], cand="e-wizna",
  note="起日出處未載；止日 9/10 由 IPN「9 września ... Dzień później」推得")
E("warsaw", "Siege of Warsaw", "華沙圍城戰", "1939-09-08", "1939-09-27", "Warsaw", "Warszawa", ["de-xvi-ak", "de-4-pz-div", "de-3-armee", "de-10-armee", "de-8-armee"], ["pl-obrona-warszawy"],
  [K("reached the suburbs of Warsaw with its 4th Panzer Division on 8 September"), P("8 września od strony Służewca i Szczęśliwic"), K("Hostilities ceased at 1400 on 27 September"), K("Surrender of Warsaw."),
   P("27 września skapitulowała broniąca się zaciekle Warszawa"), L("am 27. September bedingungslos")], cand="e-warsaw")
E("bzura", "Bzura / Kutno", "布楚拉河會戰（庫特諾包圍戰）", "1939-09-09", "1939-09-17", "Bzury; Kutno", "Kutno", ["de-8-armee", "de-10-armee", "de-xvi-ak", "de-xi-ak"], ["pl-armia-poznan", "pl-armia-pomorze"],
  [P("9 września pojawił się promyk nadziei"), P("Sprawił to zwrot zaczepny znad Bzury"), K("hastened the encirclement of the Poznan Army at Kutno"), K("Major Polish force destroyed at Kutno."), L("Schlacht an der Bzura")], cand="e-bzura",
  note="止日 9/17 取 Kennedy 年表「Major Polish force destroyed at Kutno」；IPN 記波軍攻勢持續到 9/12；展示頁起日 9/12 未採")
E("radom", "Radom", "拉多姆包圍戰", None, "1939-09-11", "Radom", "Radom", ["de-10-armee"], ["pl-armia-krakow", "pl-armia-prusy"],
  [K("Major Polish force destroyed at Radom."), K("remanants of the Cracow Army at Radom were about to be enveloped"), L("in der Kesselschlacht Radom noch westlich der Weichsel vernichtet")],
  note="非展示頁候選，依 Kennedy 年表與 LeMO 新增；Armia Prusy 參戰屬執行者依 IPN「rozbitą pod Piotrkowem」推定，未直接出處，列待查證")
E("lwow", "Lwów", "利沃夫圍城戰", "1939-09-12", "1939-09-21", "Lwow", "Lwów", ["de-xviii-ak", "de-1-geb-div", "su-ukrainian-front"], ["pl-obrona-lwowa"],
  [K("1st Mountain Division reached the fortifications of the city on 12 September"), K("The Polish garrison of Lwow abruptly and unexpectedly surrendered"), K("Surrender of Lwow."), P("postanowił skapitulować nie przed Niemcami, a Armią Czerwoną")], cand="e-lwow",
  conflict="受降方衝突：Kennedy 稱 9/21 向德軍第1山地師投降、城由蘇軍占領；IPN 稱 Langner 向紅軍投降（未載日期）。日期 9/21 只有 Kennedy；展示頁 9/22 未採")
E("brzesc", "Brześć (Brest-Litovsk)", "布列斯特要塞戰", "1939-09-14", "1939-09-17", "Brzesc; the Citadel", "Brześć", ["de-xix-ak", "de-10-pz-div", "de-20-mot-div"], ["Brześć 守軍（未列 R1）"],
  [K("On 14 September the 10th Panzer Division reported that its forward elements"), K("The Citadel was finally taken on 17 September"), K("The German XIX Corps captures Brzesc.")], cand="e-brest")
E("gdynia-oksywie", "Gdynia–Oksywie", "格丁尼亞—奧克夏維戰鬥", "1939-09-06", "1939-09-19", "Gdynia; Oksywie Flats", "Gdynia", ["Corps Kaupisch（未列 R1）"], ["pl-low"],
  [K("until 6 September, when the advancing German units began to encounter Polish"), K("on 14 September Gdynia was taken"), K("Oksywie was taken in the late afternoon"), K("the German attack of 19 September became a clearing operation")],
  note="非展示頁候選，依 Kennedy 新增")
E("modlin", "Modlin", "莫德林要塞戰", None, "1939-09-29", "Modlin", "Modlin", ["de-3-armee", "de-ii-ak", "de-8-armee"], ["pl-obrona-modlina"],
  [K("An armistice was arranged at 0730 on 28 September"), K("the formal surrender to Third Army's II Corps took place the following day"), K("Surrender of Modlin."), P("W dwa dni później w jej ślady poszedł Modlin"), L("am 28. September kapitulierenden Festung Modlin")], cand="e-modlin",
  conflict="止日：Kennedy 9/28 停火、9/29 正式投降（年表 9/29）；IPN 9/29；LeMO 9/28。取 9/29；起日出處未載（展示頁 9/17 未採）")
E("hel", "Hel", "海爾半島防禦戰", "1939-09-21", "1939-10-01", "Hela", "Hel Peninsula", ["de-207-inf-div 一個團（未列 R1）"], ["pl-rejon-umocniony-hel"],
  [K("made a limited advance out onto the peninsula on 21 September"), K("On 1 October Rear Admiral J. Unrug, commander at Hela"), K("accepted the German terms of unconditional surrender at 1700 the same day"), P("2 października złożyli broń obrońcy Helu")], cand="e-hel",
  conflict="止日：Kennedy 10/1 17:00 接受投降；IPN 10/2 繳械。取 Kennedy 10/1；起日取德軍首次地面推進 9/21（9/12 起已被切斷），展示頁 9/28 未採")
E("kock", "Kock", "科克之戰", "1939-10-04", "1939-10-06", "Kock", "Kock", ["de-10-armee"], ["pl-sgo-polesie"],
  [K("Kock, where heavy fighting raged from 4 to 6 October"), K("the Kock force surrendered on 6 October"), K("Destruction of last major Polish force at Kock."), P("Ostatnią bitwę kampanii wrześniowej stoczyły jednak pod Kockiem siły"[:80]), L("Letzte versprengte Truppenteile ergaben sich am 6. Oktober bei Kock")], cand="e-kock")
for key, zh, cand, cites, why in [
    ("tomaszow", "托馬舒夫盧貝爾斯基", "e-tomaszow", [], "已取得的 A/B 出處（Kennedy、IPN Suleja、LeMO、bpb）均未載托馬舒夫之戰"),
    ("wilno", "維爾諾", "e-wilno", [P("Broniło się Wilno.")], "IPN 只一句「Broniło się Wilno」，無日期、無部隊；只留候選"),
    ("grodno", "格羅德諾", "e-grodno", [P("Grodno skapitulowało dopiero po trzydniowych walkach")], "IPN 只一句，無日期、無部隊；只留候選"),
    ("szack", "沙茨克", "e-szack", [P("bili się pod Szackiem i Wytycznem")], "IPN 只一句（KOP，Orlik-Rückemann），無日期；只留候選")]:
    E(key, None, zh + "（候選名）", None, None, None, {"tomaszow": "Tomaszów Lubelski", "wilno": "Wilno", "grodno": "Grodno", "szack": "Szack"}[key], [], [], cites,
      status="gap" if not cites else "partial", cand=cand, gap=why)
# ---------- R6 ----------
sites = []
def S(asin, pk, date, ctrl, ev, cites, status="sourced", note=None, conflict=None, dp="day", timeNote=None):
    reg = {"axis": "deutsches-reich", "soviet": "soviet-union", "allied": "polish-republic", None: None}[ctrl]
    d = {"placeAsInSource": asin, "place": place(pk), "date": date, "datePrecision": dp, "controllerAfter": ctrl, "controllerRegimeSlug": reg,
         "sovereignRegimeSlug": "free-city-of-danzig" if pk in ("Gdańsk", "Westerplatte") else "polish-republic", "event": ev, "status": status, "citations": cites}
    if timeNote: d["timeNote"] = timeNote
    if note: d["note"] = note
    if conflict: d["conflict"] = conflict
    sites.append(d)
S("Danzig", "Gdańsk", "1939-09-01", "axis", "taken_without_fight", [K("Danzig was taken without a struggle by Brigade Eberhard"), L("Noch am selben Tag erklärte die deutsche Führung den Anschluss Danzigs")], note="Westerplatte 為但澤港內波蘭據點，主權歸屬依 R8 但澤自由市")
S("Westerplatte", "Westerplatte", "1939-09-07", "axis", "surrendered", [P("Westerplatte, zamiast godzin 12, broniło się przez długich 7 dni"), P("7 września, oficerowie Wojska Polskiego z placówki na Westerplatte")], note="只有 IPN 一族")
S("Mlawa defenses", "Mława", "1939-09-03", "axis", "defenders_withdrew", [K("broke into the Mlawa defenses and forced the stubborn defenders to withdraw")], dp="approx", note="Kennedy p.82 9/3 段落；控制方為德軍屬推定（守軍撤退）")
S("Wejherowo", "Wejherowo", "1939-09-09", "axis", "captured", [K("Wejherowo fell on 9 September")])
S("Puck (Putzig)", "Puck", "1939-09-09", "axis", "captured", [K("Corps Kaupisch made another important gain on 9 September"), K("captured the port of Puck (Putzig)")])
S("Wyszków", "Wyszków", "1939-09-09", "axis", "captured", [P("9 września Niemcy zajęli Wyszków")])
S("Gdynia", "Gdynia", "1939-09-14", "axis", "captured", [K("on 14 September Gdynia was taken")])
S("Brzesc (Citadel)", "Brześć", "1939-09-17", "axis", "captured", [K("The Citadel was finally taken on 17 September"), K("The German XIX Corps captures Brzesc.")], note="9/22 德蘇於此劃分界線（IPN 照片說明），移交蘇方之日期出處未載，不推定")
S("Oksywie", "Oksywie", "1939-09-19", "axis", "captured", [K("Oksywie was taken in the late afternoon"), K("the German attack of 19 September became a clearing operation")], timeNote="傍晚")
S("Lwow", "Lwów", "1939-09-21", "soviet", "surrendered", [K("surrendered to the 1st Mountain Division as it made ready to withdraw"), K("The occupation of the city was left to the Russians"), K("Surrender of Lwow."), P("postanowił skapitulować nie przed Niemcami, a Armią Czerwoną")],
  conflict="受降方：Kennedy 稱向德軍第1山地師投降、由蘇軍占領；IPN 稱向紅軍投降。controllerAfter 取實際占領方蘇軍；日期只有 Kennedy")
S("Warsaw", "Warszawa", "1939-09-27", "axis", "surrendered", [K("Hostilities ceased at 1400 on 27 September"), P("27 września skapitulowała broniąca się zaciekle Warszawa"), L("am 27. September bedingungslos")], timeNote="14:00 停火（Kennedy）")
S("Modlin", "Modlin", "1939-09-29", "axis", "surrendered", [K("the formal surrender to Third Army's II Corps took place the following day"), K("Surrender of Modlin."), P("W dwa dni później w jej ślady poszedł Modlin"), L("am 28. September kapitulierenden Festung Modlin")],
  conflict="Kennedy 9/28 07:30 停火、9/29 正式投降；IPN 9/29；LeMO 9/28")
S("Hela", "Hel", "1939-10-01", "axis", "surrendered", [K("accepted the German terms of unconditional surrender at 1700 the same day"), K("On 1 October Rear Admiral J. Unrug, commander at Hela"), P("2 października złożyli broń obrońcy Helu")], timeNote="17:00（Kennedy）",
  conflict="Kennedy 10/1 17:00 接受投降；IPN 10/2 繳械")
S("Kock", "Kock", "1939-10-06", "axis", "surrendered", [K("the Kock force surrendered on 6 October"), L("Letzte versprengte Truppenteile ergaben sich am 6. Oktober bei Kock")])
S("Grodno", "Grodno", None, "soviet", "capitulated", [P("Grodno skapitulowało dopiero po trzydniowych walkach")], status="partial", note="IPN 只一句：位於蘇聯入侵段落，日期與受降方未載；controllerAfter 依段落推定")
S("Cracow", "Kraków", None, "axis", "captured", [K("Fourteenth Army captured the key city of Cracow the same day")], status="partial", note="Kennedy「the same day」所指日期上文未明（約 9/6），日期留空")
for f, d in [("r3-unit-positions.json", hdr("r3") | {"note": "主期 1939-09-01～10-06；地點只給出處地名＋OSM 編號，不含座標；relation 為執行者歸類標籤；地圖 4 張全未過 2 km，R3 全部為文字出處", "positions": pos}),
             ("r5-engagements.json", hdr("r5") | {"note": "展示頁 16 場只作候選名單，欄位值不沿用；另依出處新增 Radom、Gdynia–Oksywie；conflict 欄記來源間日期／受降方差異", "engagements": eng}),
             ("r6-site-control.json", hdr("r6") | {"note": "controllerAfter：axis＝德軍、soviet＝蘇軍；controllerAfter 為 null 表示出處未載控制方；sovereignRegimeSlug＝當地主權國（但澤為自由市）", "sites": sites})]:
    (OUT / f).write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n")
print("R3", len(pos), "R5", len(eng), "R6", len(sites))
