"""poland_1939 R1 部隊名冊與 R7 指揮官／待補人物的建置腳本（由 .dev/battle/poland/build/r1r7.py 複製；引文經 tools/battles/citelib.py 逐字定位）。
用法：python3 -I tools/battles/builders/poland_1939_r1r7.py poland_1939（可重跑；重跑後須再跑 verify_quotes／crosscheck／mark_fields --apply）
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from citelib import Cites, REPO
if len(sys.argv) < 2 or sys.argv[1] != "poland_1939":
    raise SystemExit("用法：python3 -I tools/battles/builders/poland_1939_r1r7.py poland_1939（本 builder 內含 poland_1939 的研究資料，只接受此戰役代碼）")
BATTLE = sys.argv[1]
_C = Cites(BATTLE)
K, L, P, BP = (_C.short(k) for k in ("kennedy-dapam-20-255", "lemo-scriba-polen-1939", "ipn-suleja-wrzesien-1939", "bpb-vogel-lieb-blitzkriege"))
B = REPO
import json
OUT = B / "data/seed/battles" / BATTLE
MS, ME = "1939-09-01", None
NOTE = "起訖為本戰役主期（1939-09-01～10-06）內有出處的在場範圍，非單位編成／解編日；起日沒有出處者取主期起日（欄位內另標），止日未見出處者填 null"
RG = {"de": "deutsches-reich", "pl": "polish-republic", "su": "soviet-union"}
SIDE = {"de": "axis", "pl": "allied", "su": "soviet"}
units = []
def U(key, orig, zh, ech, parent, cites, start=MS, end=None, note="", status="sourced", leads=None):
    n = key.split("-")[0]
    units.append({"unitKey": key, "nameOrig": orig, "nameZh": zh, "echelon": ech, "parentKey": parent, "side": SIDE[n], "nation": n,
                  "regimeSlug": RG[n], "period": {"start": start, "end": end, "startPrecision": "day" if start else None, "endPrecision": "day" if end else None},
                  "periodNote": NOTE + (("；" + note) if note else ""), "citations": cites, "leads": leads or [], "status": status, "note": ""})
# ---------- 德軍 ----------
U("de-okh", "Oberkommando des Heeres (OKH)", "德國陸軍總司令部", "hq", None, [K("OKH directed the Army effort from a field headquarters at Zossen")])
U("de-hgr-nord", "Heeresgruppe Nord (Army Group North)", "北方集團軍群", "army_group", "de-okh", [K("as Bock's Army Group North moved into Poland"), L("Heeresgruppe Nord unter Generaloberst Fedor von Bock")])
U("de-hgr-sued", "Heeresgruppe Süd (Army Group South)", "南方集團軍群", "army_group", "de-okh", [K("The morning of 1 September was clear on the front of Rundstedt's Army Group South"[:80]), L("Heeresgruppe Süd unter Generaloberst Gerd von Rundstedt")])
U("de-3-armee", "3. Armee (Third Army)", "第3集團軍", "army", "de-hgr-nord", [K("Third Army debouched from East Prussia")])
U("de-4-armee", "4. Armee (Fourth Army)", "第4集團軍", "army", "de-hgr-nord", [K("Fourth Army attacked eastward across the Corridor from Pomerania")])
U("de-8-armee", "8. Armee (Eighth Army)", "第8集團軍", "army", "de-hgr-sued", [K("Eighth Army, the smallest of the three armies"), L("bereitete die deutsche 8. Armee den Angriff auf Warschau vor")])
U("de-10-armee", "10. Armee (Tenth Army)", "第10集團軍", "army", "de-hgr-sued", [K("Tenth Army would attack in the center of Army Group South")])
U("de-14-armee", "14. Armee (Fourteenth Army)", "第14集團軍", "army", "de-hgr-sued", [K("Fourteenth Army would commit the XVIII Corps")])
U("de-luftflotte-1", "Luftflotte 1 (First Air Force)", "第1航空隊", "air_command", None, [K("The First Air Force would operate in the area of")])
U("de-luftflotte-4", "Luftflotte 4 (Fourth Air Force)", "第4航空隊", "air_command", None, [K("The Fourth Air Force controlled 590 aircraft")])
for k, o, z, par, q in [
    ("de-i-ak", "I. Armeekorps (I Corps)", "第1軍", "de-3-armee", "with its I Corps and Corps Wodrig in line"),
    ("de-korps-wodrig", "Korps Wodrig (Corps Wodrig)", "沃德里希軍", "de-3-armee", "A provisional corps, called Wodrig after its commander"),
    ("de-xxi-ak", "XXI. Armeekorps (XXI Corps)", "第21軍", "de-3-armee", "southwestward on Grudziadz with its XXI Corps"),
    ("de-korps-brand", "Korps Brand (Corps Brand)", "布蘭德軍", "de-3-armee", "This force, named Brand, had only two brigades"),
    ("de-xix-ak", "XIX. Armeekorps (mot.) (XIX Corps)", "第19（摩托化）軍", "de-4-armee", "The XIX Corps, an active command formed in the course of the summer"),
    ("de-ii-ak", "II. Armeekorps (II Corps)", "第2軍", "de-4-armee", "II Corps would commit two infantry divisions"),
    ("de-iii-ak", "III. Armeekorps (III Corps)", "第3軍", "de-4-armee", "The III Corps would control one infantry division"),
    ("de-xiii-ak", "XIII. Armeekorps (XIII Corps)", "第13軍", "de-8-armee", "would have on its right XIII Corps with two infantry divisions"),
    ("de-x-ak", "X. Armeekorps (X Corps)", "第10軍", "de-8-armee", "The X Corps with two infantry divisions"),
    ("de-xv-ak", "XV. Armeekorps (mot.) (XV Corps)", "第15（摩托化）軍", "de-10-armee", "On the right XV Corps would commit one light division"),
    ("de-iv-ak", "IV. Armeekorps (IV Corps)", "第4軍", "de-10-armee", "In the right center IV Corps would have two infantry divisions"),
    ("de-xvi-ak", "XVI. Armeekorps (mot.) (XVI Corps)", "第16（摩托化）軍", "de-10-armee", "The XVI Corps, consisting of two Panzer and two infantry divisions"),
    ("de-xi-ak", "XI. Armeekorps (XI Corps)", "第11軍", "de-10-armee", "The XI Corps would be on the left of the Tenth Army front"),
    ("de-xiv-ak", "XIV. Armeekorps (mot.) (XIV Corps)", "第14（摩托化）軍", "de-10-armee", "The XIV Corps, with two motorized infantry divisions"),
    ("de-xviii-ak", "XVIII. Armeekorps (XVIII Corps)", "第18軍", "de-14-armee", "the XVIII Corps, made up of one mountain, one light,"),
    ("de-xvii-ak", "XVII. Armeekorps (XVII Corps)", "第17軍", "de-14-armee", "The XVII Corps would form the center of the Fourteenth Army line"),
    ("de-viii-ak", "VIII. Armeekorps (VIII Corps)", "第8軍", "de-14-armee", "held by the VIII Corps, with one Panzer and two infantry divisions"),
    ("de-vii-ak", "VII. Armeekorps (VII Corps)", "第7軍", "de-hgr-sued", "one infantry division of the VII Corps"),
]:
    U(k, o, z, "corps", par, [K(q)])
U("de-xxii-ak", "XXII. Armeekorps (mot.) (XXII Corps)", "第22（摩托化）軍", "corps", "de-14-armee", [K("The XXII Corps was operational under Fourteenth Army control on 4 September")], start="1939-09-04")
U("de-gruppe-falkenhorst", "Gruppe Falkenhorst (Group Falkenhorst)", "法爾肯霍斯特集群", "corps", "de-hgr-nord", [K("was redesignated Group Falkenhorst, after its commander")], start=None,
  note="由 XXI 軍改稱；改稱日期出處未載（起日空）", )
U("de-gruppe-gienanth", "Gruppe Gienanth (Group Gienanth)", "吉南特集群", "corps", "de-8-armee", [K("into a task force known as Group Gienanth")], start=None, note="臨時編組；成立日期出處未載（起日空）")
for k, o, z, par, cs, st in [
    ("de-pz-div-kempf", "Panzer-Division Kempf", "肯普夫裝甲師", "de-i-ak", [K("committed to operations as Panzer Division Kempf")], MS),
    ("de-10-pz-div", "10. Panzer-Division", "第10裝甲師", "de-hgr-nord", [K("The 10th Panzer Division had been added to Army Group North")], MS),
    ("de-3-pz-div", "3. Panzer-Division", "第3裝甲師", "de-xix-ak", [K("followed by the 3d Panzer Division, which had meanwhile rejoined the corps")], MS),
    ("de-20-mot-div", "20. Infanterie-Division (mot.)", "第20摩托化步兵師", "de-xix-ak", [K("The 20th Motorized Infantry Division arrived as the first of the XIX Corps units")], MS),
    ("de-2-mot-div", "2. Infanterie-Division (mot.)", "第2摩托化步兵師", "de-xix-ak", [K("the 2d Motorized Infantry Division began moving southward to rejoin XIX Corps")], MS),
    ("de-4-pz-div", "4. Panzer-Division", "第4裝甲師", "de-xvi-ak", [K("XVI Corps reached the suburbs of Warsaw with its 4th Panzer Division"), P("powstrzymał pod Mokrą 4. dywizję pancerną")], MS),
    ("de-1-pz-div", "1. Panzer-Division", "第1裝甲師", "de-xvi-ak", [K("its 1st Panzer Division penetrated to the Vistula")], MS),
    ("de-2-pz-div", "2. Panzer-Division", "第2裝甲師", "de-hgr-sued", [K("The 2d Panzer Division of Army Group South")], MS),
    ("de-5-pz-div", "5. Panzer-Division", "第5裝甲師", None, [P("13. pułku strzelców 5. Dywizji Pancernej")], MS),
    ("de-1-geb-div", "1. Gebirgs-Division", "第1山地師", "de-xviii-ak", [K("the XVIII Corps' 1st Mountain Division")], MS),
    ("de-50-inf-div", "50. Infanterie-Division", "第50步兵師", "de-hgr-nord", [K("redesignated the 50th Infantry Division")], MS),
]:
    U(k, o, z, "division", par, cs, start=st)
# ---------- 波軍 ----------
U("pl-naczelny-wodz", "Naczelny Wódz i sztab (Polish High Command)", "波蘭總司令與總參謀部", "hq", None,
  [P("Naczelnego Wodza, który od 7 września stacjonował wraz ze sztabem w Brześciu"), K("the Polish High Command had established headquarters")])
for k, o, z, ech, cs, st, en, nt in [
    ("pl-armia-modlin", "Armia „Modlin” (Modlin Army)", "莫德林集團軍", "army", [K("the direct route to Warsaw (Modlin Army)"), P("Armia „Modlin” gen. Emila Krukowicza-Przedżymirskiego")], MS, None, ""),
    ("pl-sgo-narew", "Samodzielna Grupa Operacyjna „Narew” (Narew Group)", "納雷夫獨立作戰群", "army", [K("the frontier with Lithuania (Narew Group)")], MS, None, "Kennedy 稱 Narew Group；SGO 為集團軍級獨立作戰群"),
    ("pl-armia-pomorze", "Armia „Pomorze” (Pomorze Army)", "波美拉尼亞集團軍", "army", [K("(Pomorze Army), under the command of Maj. Gen. W. Bortnowski"), P("armię „Pomorze” gen. Władysława Bortnowskiego")], MS, None, ""),
    ("pl-armia-poznan", "Armia „Poznań” (Poznan Army)", "波茲南集團軍", "army", [K("for the defense of the Poznan salient (Poznan Army)"), P("dokonany siłami armii „Poznań” i „Pomorze”")], MS, None, ""),
    ("pl-armia-lodz", "Armia „Łódź” (Lodz Army)", "羅茲集團軍", "army", [K("held the Lodz area (Lodz Army)"), P("armii „Łódź” (gen. Juliusza Rómmla)")], MS, None, ""),
    ("pl-armia-krakow", "Armia „Kraków” (Cracow Army)", "克拉科夫集團軍", "army", [K("vital Cracow region (Cracow Army)"), P("„Kraków” (gen. Antoniego Szyllinga)")], MS, None, ""),
    ("pl-armia-karpaty", "Armia „Karpaty” (Carpathian Army)", "喀爾巴阡集團軍", "army", [K("The Carpathian Army was formed under Maj. Gen. K. Fabrycy"), P("współdziałanie armiom „Kraków” i „Karpaty”")], MS, None, ""),
    ("pl-armia-prusy", "Armia „Prusy”（odwód）", "普魯士集團軍（總預備隊）", "army", [P("odwodową armię „Prusy”, rozbitą pod Piotrkowem")], MS, None, "Kennedy 僅稱 general reserve，未用 Prusy 之名；指揮官出處未載"),
    ("pl-armia-lublin", "Armia „Lublin”", "盧布林集團軍", "army", [P("już 4 września Rydz-Śmigły nakazał utworzenie armii „Lublin”")], "1939-09-04", None, "9/4 為下令組建日"),
    ("pl-front-poludniowy", "Front Południowy (gen. Sosnkowski)", "南方方面軍", "army_group", [P("wojska frontu południowego na czele z gen. Kazimierzem Sosnkowskim")], None, None, "組建日期出處未載"),
    ("pl-sgo-polesie", "Samodzielna Grupa Operacyjna „Polesie”", "波萊西獨立作戰群", "army", [P("pod Kockiem siły SGO „Polesie” gen. Franciszka Kleeberga"), K("the Kock force surrendered on 6 October")], None, "1939-10-06", "Kennedy 稱 the Kock force，未用 SGO Polesie 之名，視為同一部隊屬執行者判讀"),
    ("pl-obrona-warszawy", "Obrona Warszawy (Warsaw garrison)", "華沙守軍", "army", [K("the garrison of Warsaw was composed"), P("27 września skapitulowała broniąca się zaciekle Warszawa")], None, "1939-09-27", "Kennedy 稱 garrison of Warsaw"),
    ("pl-obrona-modlina", "Twierdza Modlin (Modlin force)", "莫德林要塞守軍", "army", [K("General Thommee, commander of the Modlin force"), K("the formal surrender to Third Army's II Corps took place the following day")], None, "1939-09-29", "Kennedy：9/28 07:30 停火、翌日正式投降；IPN「W dwa dni później」＝9/29；LeMO 作 9/28"),
    ("pl-low", "Lądowa Obrona Wybrzeża (Gdynia area force)", "陸上海岸防衛（格丁尼亞）", "division", [K("The port area of Gdynia also organized a defense force"), P("siły komandora Józefa Unruga i płk Stanisława Dąbka")], MS, None, "Kennedy 稱 small division 規模"),
    ("pl-rejon-umocniony-hel", "Rejon Umocniony Hel (Hela)", "海爾半島要塞區", "division", [K("Rear Admiral J. Unrug, commander at Hela"), P("2 października złożyli broń obrońcy Helu")], MS, "1939-10-02", "投降日：IPN 10/2；Kennedy 記 10/1 請求談判，見 R6"),
    ("pl-westerplatte", "Wojskowa Składnica Tranzytowa na Westerplatte", "西盤半島軍需轉運站守軍", "garrison", [K("the Polish fortress of Westerplatte in Danzig Harbor"), P("Westerplatte, zamiast godzin 12, broniło się przez długich 7 dni")], MS, "1939-09-07", "止日 9/7 取 IPN 照片說明「7 września ... chwilę po kapitulacji」"),
    ("pl-obrona-lwowa", "Obrona Lwowa (Lwow garrison)", "利沃夫守軍", "army", [K("garrison of 12,000 men"), P("dowódca obrony Lwowa, gen. Władysław Langner")], None, None, "投降日見 R6（9/21 對 9/22 待定）"),
]:
    U(k, o, z, ech, "pl-naczelny-wodz" if ech in ("army", "army_group") else None, cs, start=st, end=en, note=nt)
units[-1]  # noop
# Westerplatte 止日引文補一條
for u in units:
    if u["unitKey"] == "pl-westerplatte":
        u["citations"].append(P("7 września, oficerowie Wojska Polskiego z placówki na Westerplatte"))
for k, o, z, par, cs in [
    ("pl-7-dp", "7 Dywizja Piechoty", "第7步兵師", "pl-armia-krakow", [K("the Cracow Army's 7th Infantry Division"), P("osamotniona 7. DP, okrążona i zniszczona")]),
    ("pl-6-dp", "6 Dywizja Piechoty", "第6步兵師", "pl-armia-krakow", [K("the 6th Infantry Division of the Cracow Army")]),
    ("pl-21-dpg", "21 Dywizja Piechoty Górskiej", "第21山地步兵師", "pl-armia-krakow", [K("the Cracow Army's 21st Mountain Division")]),
    ("pl-23-dp", "23 Dywizja Piechoty", "第23步兵師", "pl-armia-krakow", [K("the Cracow Army's 23d Infantry Division")]),
    ("pl-9-dp", "9 Dywizja Piechoty", "第9步兵師", "pl-armia-pomorze", [K("sealed off the Pomorze Army's 9th Infantry Division"), P("oddziały 9. i 27. DP")]),
    ("pl-27-dp", "27 Dywizja Piechoty", "第27步兵師", "pl-armia-pomorze", [K("and the 27th Infantry Division, which had been identifi"[:0] or "and the 27th Infantry Division"), P("oddziały 9. i 27. DP")]),
    ("pl-16-dp", "16 Dywizja Piechoty", "第16步兵師", "pl-armia-pomorze", [K("identified the Pomorze Army's 16th Infantry Division")]),
    ("pl-10-dp", "10 Dywizja Piechoty", "第10步兵師", "pl-armia-lodz", [K("the 10th Infantry Division of the Lodz Army")]),
    ("pl-28-dp", "28 Dywizja Piechoty", "第28步兵師", "pl-armia-lodz", [K("28th and 30th Infantry Divisions and Wolynska Cavalry Brigade of the Lodz Army")]),
    ("pl-30-dp", "30 Dywizja Piechoty", "第30步兵師", "pl-armia-lodz", [K("28th and 30th Infantry Divisions and Wolynska Cavalry Brigade of the Lodz Army")]),
    ("pl-14-dp", "14 Dywizja Piechoty", "第14步兵師", "pl-armia-poznan", [K("the 14th and 25th Infantry Divisions"), K("Wielkopolska Cavalry Brigade of the Poznan Army")]),
    ("pl-25-dp", "25 Dywizja Piechoty", "第25步兵師", "pl-armia-poznan", [K("the 14th and 25th Infantry Divisions"), K("Wielkopolska Cavalry Brigade of the Poznan Army")]),
    ("pl-8-dp", "8 Dywizja Piechoty", "第8步兵師", "pl-armia-modlin", [P("Siły armii „Modlin”, po przełamaniu obrony Mazowieckiej BK i rozbiciu 8. DP")]),
    ("pl-18-dp", "18 Dywizja Piechoty", "第18步兵師", None, [P("Podlaskiej Brygady Kawalerii i 18. DP")]),
    ("pl-5-dp", "5 Dywizja Piechoty", "第5步兵師", "pl-naczelny-wodz", [K("The Polish 5th Infantry Division from the general reserve")]),
    ("pl-12-dp", "12 Dywizja Piechoty", "第12步兵師", "pl-naczelny-wodz", [K("the 12th Infantry Division from the general reserve")]),
]:
    U(k, o, z, "division", par, cs)
# ---------- 蘇軍 ----------
U("su-belorussian-front", "Belorusskiy front (White Russian Front)", "白俄羅斯方面軍", "army_group", None,
  [K("The White Russian Front, in the north, was commanded by Army Commander"), P("17 września, znienacka"), L("mit dem Überfall von zwei Heeresgruppen der Roten Armee auf Ostpolen")], start="1939-09-17")
U("su-ukrainian-front", "Ukrainskiy front (Ukrainian Front)", "烏克蘭方面軍", "army_group", None,
  [K("The Ukrainian Front, on the south, was commanded by Army Commander Timoshenko"), P("17 września, znienacka"), L("mit dem Überfall von zwei Heeresgruppen der Roten Armee auf Ostpolen")], start="1939-09-17")

# ---------- R7 ----------
PI = json.loads((B / ".dev/battle/person-index.json").read_text())
def bio(pk):
    for v in (PI["generals"].values() if isinstance(PI["generals"], dict) else PI["generals"]):
        if v.get("personKey") == pk: return v["bioId"]
    raise SystemExit("no bio " + pk)
cmds, missing = [], []
def CM(unit, name, zh, pk, cites, start=None, end=None, note="", nameOrig=None, prio=2):
    t = {"start": start, "end": end, "precision": {"start": "day" if start else None, "end": "day" if end else None}}
    if pk:
        cmds.append({"unitKey": unit, "name": name, "nameZh": zh, "personKey": pk, "bioId": bio(pk), "tenure": t, "citations": cites,
                     "bioStatus": "has_bio", "note": note})
    else:
        cmds.append({"unitKey": unit, "name": name, "nameZh": zh, "personKey": None, "bioId": None, "tenure": t, "citations": cites,
                     "bioStatus": "missing_bio", "note": note})
        missing.append({"name": name, "nameOrig": nameOrig or name, "nameZh": zh, "unitKey": unit, "tenure": t, "citations": cites,
                        "priority": prio, "note": note, "nameZhNeedsReview": True, "unitKeys": [unit]})
PRE = "引文為戰前任命／編組敘述，起日不在主期出處內（空）"
CM("de-okh", "Walther von Brauchitsch", "瓦爾特·馮·布勞希奇", "walthervonbrauchitsch", [K("a telephone conversation with Brauchitsch on 2 September"), K("General von Brauchitsch was still the Army's commander in chief")], note=PRE)
CM("de-hgr-nord", "Fedor von Bock", "費多爾·馮·博克", "fedorvonbock", [K("Heeresgruppenkommomdo 1, under Generaloberst Fedor von Bock"), L("Heeresgruppe Nord unter Generaloberst Fedor von Bock")], note=PRE)
CM("de-hgr-sued", "Gerd von Rundstedt", "格特·馮·倫德施泰特", "gerdvonrundstedt", [K("a provisional headquarters under Generaloberst Gerd von Rundstedt"), L("Heeresgruppe Süd unter Generaloberst Gerd von Rundstedt")], note=PRE)
CM("de-3-armee", "Georg von Küchler", "格奧爾格·馮·屈希勒", "georgvonkuchler", [K("under command of General der Artillerie Georg von Kuechler")], note=PRE)
CM("de-4-armee", "Günther von Kluge", "君特·馮·克魯格", "gunthervonkluge", [K("General der Artillerie Guenther von Kluge")], note=PRE)
CM("de-8-armee", "Johannes Blaskowitz", "約翰內斯·布拉斯科維茨", None, [K("under General der Infanterie Johannes Blaskowitz"), K("The Eighth Army Commander, General Blaskowitz")], prio=1)
CM("de-10-armee", "Walther von Reichenau", "瓦爾特·馮·賴歇瑙", None, [K("General der Artillerie Walther von Reichenau")], prio=1, note=PRE)
CM("de-14-armee", "Wilhelm List", "威廉·利斯特", "wilhelmlist", [K("Generaloberst Wilhelm List, in that order")], note=PRE)
CM("de-luftflotte-1", "Albert Kesselring", "阿爾貝特·凱塞林", "albertkesselring", [K("commanded at that time by General der Flieger Albert Kesselring")], note=PRE)
CM("de-luftflotte-4", "Alexander Löhr", "亞歷山大·勒爾", None, [K("General der Flieger Alexander Loehr, respectively")], prio=2, note=PRE)
CM("de-xix-ak", "Heinz Guderian", "海因茨·古德里安", "heinzguderian", [K("was under General der Panzertruppen Heinz Guderian"), P("generał wojsk pancernych Heinz Guderian")], note=PRE)
CM("de-korps-wodrig", "Wodrig", "沃德里希", None, [K("A provisional corps, called Wodrig after its commander")], prio=2, note="原文只有姓")
CM("de-korps-brand", "Brand", "布蘭德", None, [K("This force, named Brand, had only two brigades")], prio=3, note="原文只稱部隊以 Brand 為名，未明言為指揮官姓名，待查證")
CM("de-gruppe-falkenhorst", "Falkenhorst", "法爾肯霍斯特", None, [K("was redesignated Group Falkenhorst, after its commander")], prio=2, note="原文只有姓")
CM("de-gruppe-gienanth", "Gienanth", "吉南特", None, [K("into a task force known as Group Gienanth")], prio=3, note="原文只稱部隊名，未明言指揮官，待查證")
CM("de-pz-div-kempf", "Kempf", "肯普夫", None, [K("committed to operations as Panzer Division Kempf")], prio=3, note="原文只稱部隊名，未明言指揮官，待查證")
CM("pl-naczelny-wodz", "Edward Rydz-Śmigły", "愛德華·雷茲-希米格維", "edwardsmigły-rydz", [L("Die polnische Heeresleitung hatte unter Marschall Eduard Rydz-Śmigły"), P("Rydz-Śmigły nie wydał rozkazu podjęcia walki z nowym agresorem")])
CM("pl-armia-modlin", "Emil Krukowicz-Przedrzymirski", "埃米爾·克魯科維奇-普熱傑米爾斯基", None, [K("Brig. Gen. E. Przedzymirski-Krukowicz"), P("Armia „Modlin” gen. Emila Krukowicza-Przedżymirskiego")], prio=1, note="Kennedy 拼 Przedzymirski-Krukowicz；IPN 拼 Krukowicz-Przedżymirski；人名拼法待審")
CM("pl-sgo-narew", "Czesław Młot-Fijałkowski", "切斯瓦夫·姆沃特-菲亞烏科夫斯基", None, [K("under Maj. Gen. C. Mlot-Fijalkowski")], prio=1, note=PRE)
CM("pl-armia-pomorze", "Władysław Bortnowski", "瓦迪斯瓦夫·博爾特諾夫斯基", None, [K("(Pomorze Army), under the command of Maj. Gen. W. Bortnowski"), P("armię „Pomorze” gen. Władysława Bortnowskiego")], prio=1)
CM("pl-armia-poznan", "Tadeusz Kutrzeba", "塔德烏什·庫特熱巴", None, [K("the command of Maj. Gen. T. Kutrzeba"), P("podlegające rozkazom gen. Kutrzeby siły Wielkopolskiej BK")], prio=1)
CM("pl-armia-lodz", "Juliusz Rómmel", "尤柳什·羅梅爾", None, [K("under command of Maj. Gen. J. Rommel"), P("armii „Łódź” (gen. Juliusza Rómmla)")], prio=1, note="Kennedy 拼 Rommel；與主檔 Erwin Rommel（erwinrommel）不是同一人，不得連結")
CM("pl-obrona-warszawy", "Juliusz Rómmel", "尤柳什·羅梅爾", None, [K("under General Rommel, former commander"), P("dowództwo nad wojskiem przejął z rąk gen. Waleriana Czumy gen. Rómmel")], prio=1, note="與主檔 Erwin Rommel 不是同一人；接替 Czuma 日期出處未載")
CM("pl-armia-krakow", "Antoni Szylling", "安東尼·希林", None, [K("the force of Brig. Gen. A. Szylling"), P("„Kraków” (gen. Antoniego Szyllinga)")], prio=1)
CM("pl-armia-karpaty", "Kazimierz Fabrycy", "卡齊米日·法布里齊", None, [K("The Carpathian Army was formed under Maj. Gen. K. Fabrycy")], prio=1, note=PRE)
CM("pl-armia-lublin", "Tadeusz Piskor", "塔德烏什·皮斯科爾", None, [P("nakazał utworzenie armii „Lublin” (gen. Tadeusz Piskor)")], start="1939-09-04", prio=1)
CM("pl-sgo-polesie", "Franciszek Kleeberg", "弗朗齊歇克·克萊貝格", None, [P("pod Kockiem siły SGO „Polesie” gen. Franciszka Kleeberga")], end="1939-10-06", prio=1, note="止日依 Kennedy Kock 投降 10/6（部隊止日）")
CM("pl-front-poludniowy", "Kazimierz Sosnkowski", "卡齊米日·索斯恩科夫斯基", None, [P("wojska frontu południowego na czele z gen. Kazimierzem Sosnkowskim")], prio=1)
CM("pl-obrona-lwowa", "Władysław Langner", "瓦迪斯瓦夫·朗格納", None, [P("dowódca obrony Lwowa, gen. Władysław Langner")], prio=1)
CM("pl-obrona-modlina", "Thommée", "托梅", None, [K("General Thommee, commander of the Modlin force")], end="1939-09-29", prio=2, note="原文只有姓（Kennedy 拼 Thommee）")
CM("pl-rejon-umocniony-hel", "Józef Unrug", "約瑟夫·翁魯格", None, [K("Rear Admiral J. Unrug, commander at Hela"), P("siły komandora Józefa Unruga i płk Stanisława Dąbka")], prio=1, note="Kennedy 稱 Rear Admiral，IPN 稱 komandor；軍銜不一致待審")
CM("pl-low", "Stanisław Dąbek", "斯坦尼斯瓦夫·東貝克", None, [K("under the command of a Colonel Dabek"), P("siły komandora Józefa Unruga i płk Stanisława Dąbka")], prio=2)
CM("pl-westerplatte", "Henryk Sucharski", "亨里克·蘇哈爾斯基", None, [P("Dowodzący obroną mjr Henryk Sucharski")], end="1939-09-07", prio=2)
CM("su-belorussian-front", "Kovalev", "科瓦廖夫", None, [K("Kovalev, with headquarters in Minsk")], start="1939-09-17", prio=1, note="原文只有姓（Mikhail Kovalyov，待審）")
CM("su-ukrainian-front", "Semyon Timoshenko", "謝苗·鐵木辛哥", "semyontimoshenko", [K("The Ukrainian Front, on the south, was commanded by Army Commander Timoshenko")], start="1939-09-17")

mm = {}
for m in missing:
    if m["name"] in mm:
        a = mm[m["name"]]; a["unitKeys"].append(m["unitKey"]); a["citations"] += m["citations"]; a["priority"] = min(a["priority"], m["priority"])
        a["note"] = (a["note"] + "；" + m["note"]).strip("；")
    else: mm[m["name"]] = m
missing = list(mm.values())
hdr = lambda s: {"schema": f"battle-data/0.1 {s}", "researchedOn": "2026-11-13"}
r1 = hdr("r1") | {"gradePolicy": "AB-only (C only in leads)", "sideNote": "side：axis＝德國；allied＝波蘭；soviet＝蘇聯（1939 年非同盟國亦非軸心）", "units": units}
r7 = hdr("r7") | {"gradePolicy": "AB-only", "commanders": cmds}
r7m = hdr("r7-missing") | {"priorityNote": "1=集團軍／方面軍層級或戰役主角，建議先補；2=軍、要塞或臨時集群；3=原文未明言為指揮官。本輪不研究生平，不補主檔。", "people": missing}
for f, d in [("r1-units.json", r1), ("r7-commanders.json", r7), ("r7-missing-people.json", r7m)]:
    (OUT / f).write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n")
import collections
print("units", len(units), collections.Counter((u["nation"], u["echelon"]) for u in units))
print("cmds", len(cmds), "bio", sum(1 for c in cmds if c["personKey"]), "missing", len(missing))
