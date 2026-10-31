#!/usr/bin/env python3
"""補南歐、東南歐、法國、比利時、丹麥、芬蘭、捷克斯洛伐克的空白：1941（OHM 起始日）～1945-05-09（DRAFT，待 Tai 檢查）。
幾何：固定版本 OHM（ohm-manifest.json；新抓的關係 Overpass osm_base 2026-10-31T09:55:15Z，沿用的關係保留原抓取時間與版本），
同一天互不重疊（本檔末的檢查，另以 API 抽樣日檢查與既有紀錄不重疊）。
修正規則：同一 OHM 版本跨越原本 1942-07-01／1943-01-01 試驗邊界的紀錄，撤回後合併成一筆（從 OHM 起始日到下一次變動）；不刪除。
沒有正式出處的分段日依 OHM，事件標待查證，不補造；OHM 沒有版本的時段留白並在 README 列出。
"""
import json, os, datetime
from shapely.geometry import shape, mapping, MultiPolygon, Polygon, box
from shapely.ops import unary_union
from shapely.validation import make_valid
from shapely import set_precision
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); OUT = os.path.join(ROOT, 'requests')
MAN = {r['ohm_relation_id']: r for r in json.load(open(os.path.join(ROOT, 'ohm-manifest.json')))}
g = {f['id']: make_valid(shape(f['geometry'])) for f in json.load(open(os.path.join(ROOT, 'borders-ohm-1943-1945-south.geojson')))['features']}
F45 = {f['id']: make_valid(shape(f['geometry'])) for f in json.load(open(os.path.join(ROOT, '..', 'borders-1943-1945', 'borders-1943-1945-derived.geojson')))['features']}
def polys(x):
    if isinstance(x, Polygon): return [x]
    if isinstance(x, MultiPolygon): return list(x.geoms)
    return [p for y in getattr(x, 'geoms', []) for p in polys(y)]
def clean(x, keep=lambda p: True):
    x = make_valid(set_precision(make_valid(x), 1e-4))
    return MultiPolygon([p for p in polys(x) if p.area > 1e-5 and keep(p)])
def G(x): return g[x] if isinstance(x, int) else F45[x] if isinstance(x, str) and x in F45 else x
U = lambda *xs: unary_union([G(x) for x in xs])
def D(a, *bs): return clean(G(a).difference(U(*bs))) if bs else clean(G(a))
N40 = box(-12, 40, 42, 72)
CORSICA = box(8.3, 41.3, 9.7, 43.1)
TR = clean(g[2693255].difference(g[2693259]), keep=lambda p: p.centroid.x > 28.5 and p.area > 0.01)
SUALL = U('F45_SU_3', 'F45_SU_4', 'F45_SU_5', 'F45_SU_6', 'F45_SU_7', 'F45_SU_8', 'F45_SU_9')
FR45 = clean(g[2696301])
S40 = box(-12, 30, 42, 40)
DFY = 2923084
geo = {
    'S_IT_1': D(2747829), 'S_IT_OCC_FR': D(2747832, 2747829),
    'S_FR_V1': clean(g[2747869].intersection(N40)), 'S_FR_V2': clean(g[2696300].intersection(N40)), 'S_FR_V2B': clean(g[2696300].intersection(N40).difference(CORSICA)),
    'S_IT_K1': D(2794960, 2696300), 'S_IT_K2': D(2794960, 2800536, 2696300), 'S_IT_K3': D(2956707, 2800536), 'S_IT_K4': D(2956707), 'S_IT_K5': D(2794959), 'S_IT_K6': D(2795081),
    'S_AMGOT': D(2800536), 'S_RSI_1': D(2794958), 'S_RSI_2': D(2794957), 'S_DEIT_1': D(2961564), 'S_DEIT_2': D(2961564, 2795081),
    'S_DODEC': D(2920370),
    'S_AL_IT': D(2695459), 'S_AL_DE': D(2800553), 'S_AL_DG': D(2878108),
    'S_ME_IT': D(2695479), 'S_ME_DE': D(2855621),
    'S_HR_1': D(2692713), 'S_HR_2': D(2747830), 'S_RS': D(2692357),
    'S_BG_1': D(2695478), 'S_BG_2': D(2920397), 'S_BG_3': D(2848877),
    'S_GR_1': D(2920398, 2695478), 'S_GR_2': D(2920398, 2920397), 'S_GR_3': D(2920399, 2920370), 'S_GR_4': D(2920399, 2920370),
    'S_HU_1': D(2692359), 'S_HU_3': D(2878067),
    'S_RO_1': clean(g[2693255].difference(TR)), 'S_TR': TR, 'S_RO_2': D(2693255, SUALL), 'S_RO_3': D(2877966),
    'S_DK': D(2851793), 'S_FI': D(2855285), 'S_CS_1': D(2747847), 'S_CS_2': D(2692766),
    'S_RKBN': D(2748552), 'S_BE_1': D(2692857, 'F45_DE_A', 'F45_DE_B'), 'S_BE_2': D(2692857),
    'S_ALG': clean(g[2747869].intersection(S40)), 'S_ALG_COR': clean(g[2747869].intersection(S40).union(g[2696300].intersection(CORSICA))),
    'S_FRP_1': D(FR45, 'F45_DE_A', 2748552, 2956943), 'S_FRP_2': D(FR45, 'F45_DE_A', 'F45_DE_B'), 'S_FRP_3': clean(FR45),
    'S_DFY_1': D(DFY, 2747830, 2855621, 2692359, 2800553, 2961564, 'F45_DE_A', 2848877),
    'S_DFY_2': D(DFY, 2747830, 2855621, 2692359, 2878108, 2961564, 'F45_DE_A', 2848877),
    'S_DFY_3': D(DFY, 2747830, 2692359, 2878108, 2961564, 'F45_DE_A', 2848877),
    'S_DFY_4': D(DFY, 2747830, 2878067, 2878108, 2961564, 'F45_DE_B', 2848877),
    'S_DFY_6': D(DFY, 2747830, 2878067, 2878108, 2795081, 2848877),
}
geo['S_DFY_5'] = clean(g[DFY].difference(U(2747830, 2878067, 2878108, geo['S_DEIT_2'], 2795081, 'F45_DE_B', 2848877)))

# ---------------- 紀錄（placeholder, regime, geom, main rel, rels, locator, layer, start, end, sev, eev, note zh, note en） ----------------
L = lambda *rs: ' − '.join(f'relation/{r} v{MAN[r]["ohm_version"]}' for r in rs)
LN40 = lambda r: f'relation/{r} v{MAN[r]["ohm_version"]} ∩ 北緯 40 度以北'
T = '1943-09-08'
R = [
 ('SOVB_IT_1', 'REGIME_IT', 'S_IT_1', 2747829, [2747829], L(2747829), 'de_jure', '1941-04-18', T, 'EV_ROME_AGREEMENTS', 'EV_IT_ARMISTICE',
  '義大利事實國界（含併入的盧布爾雅那、達爾馬提亞等）。OHM 2747829 於 1942-11-11 結束，之後的 2747832 只多出義軍佔領的法國地區（另畫非主權），本表沿用到 1943-09-08 停戰。',
  'Italy (de facto, OHM 2747829) to the armistice of 8 Sep 1943; Italian-occupied French territory is drawn separately.'),
 ('SOVB_IT_OCC_FR', 'REGIME_IT_OCC_FR', 'S_IT_OCC_FR', 2747832, [2747832, 2747829], L(2747832, 2747829), 'not_sovereign', '1942-11-11', T, 'EV_IT_OCC_FR', 'EV_IT_ARMISTICE',
  '非主權：義大利佔領的法國地區（科西嘉與東南部）＝OHM 2747832 − 2747829；1943-09-08 停戰後由德軍接管（併入法蘭西國 2696300 範圍）。', 'Not sovereign: Italian-occupied French territory until the Italian armistice.'),
 ('SOVB_FR_V1', 'REGIME_FR_STATE', 'S_FR_V1', 2747869, [2747869], LN40(2747869), 'not_sovereign', '1942-11-11', T, 'EV_ANTON', 'EV_IT_ARMISTICE',
  '非主權：1942-11-11 起德國全面佔領法國本土（FRUS 1942 II Doc. 207）。只含法國本土（北緯 40 度以北）；阿爾及利亞留白（待查證）。', 'Not sovereign from 11 Nov 1942; metropolitan France only.'),
 ('SOVB_FR_V2', 'REGIME_FR_STATE', 'S_FR_V2', 2696300, [2696300], LN40(2696300), 'not_sovereign', T, '1943-10-04', 'EV_IT_ARMISTICE', 'EV_CORSICA',
  '非主權：德國佔領下的法國本土；1943-09-08 起含原義佔區（OHM 2696300）。科西嘉 09-08～10-04 仍畫在此（實際德、義、自由法國軍交戰中，簡化）。', 'Not sovereign: German-occupied metropolitan France incl. the former Italian zone and Corsica (simplified).'),
 ('SOVB_FR_V2B', 'REGIME_FR_STATE', 'S_FR_V2B', 2696300, [2696300], LN40(2696300) + ' − 科西嘉', 'not_sovereign', '1943-10-04', '1944-08-09', 'EV_CORSICA', 'EV_FR_0809',
  '非主權：德國佔領下的法國本土（不含 1943-10-04 解放的科西嘉）。', 'Not sovereign: German-occupied metropolitan France (without Corsica).'),
 ('SOVB_IT_K1', 'REGIME_IT', 'S_IT_K1', 2794960, [2794960, 2696300], L(2794960, 2696300), 'de_jure', T, '1943-09-17', 'EV_IT_ARMISTICE', 'EV_AMGOT',
  '停戰後義大利王國（巴多格里奧政府）轄區（OHM 2794960，南義、薩丁尼亞；OHM 也含科西嘉，這裡扣掉，科西嘉畫在法國）。北義 09-08～09-23（德軍佔領、社會共和國成立前）OHM 沒有版本，留白。', 'Kingdom of Italy (Badoglio) after the armistice; northern Italy 8–23 Sep 1943 left blank (no OHM version).'),
 ('SOVB_IT_K2', 'REGIME_IT', 'S_IT_K2', 2794960, [2794960, 2800536, 2696300], L(2794960, 2800536, 2696300), 'de_jure', '1943-09-17', '1943-11-14', 'EV_AMGOT', 'EV_IT_1943_11', '義大利王國轄區扣除盟軍軍政府（AMGOT）地區。', 'Kingdom of Italy minus the AMGOT area.'),
 ('SOVB_IT_K3', 'REGIME_IT', 'S_IT_K3', 2956707, [2956707, 2800536], L(2956707, 2800536), 'de_jure', '1943-11-14', '1944-03-01', 'EV_IT_1943_11', 'EV_AMGOT_END',
  '義大利王國轄區（OHM 2956707；另有一筆完全相同的 2956734，未使用）扣除 AMGOT 地區。', 'Kingdom of Italy (OHM 2956707; identical duplicate 2956734 not used) minus AMGOT.'),
 ('SOVB_IT_K4', 'REGIME_IT', 'S_IT_K4', 2956707, [2956707], L(2956707), 'de_jure', '1944-03-01', '1944-08-25', 'EV_AMGOT_END', 'EV_IT_1944_08', '義大利王國轄區（AMGOT 地區交還後）。', 'Kingdom of Italy after AMGOT areas were handed back.'),
 ('SOVB_IT_K5', 'REGIME_IT', 'S_IT_K5', 2794959, [2794959], L(2794959), 'de_jure', '1944-08-25', '1945-04-29', 'EV_IT_1944_08', 'EV_CASERTA', '義大利王國轄區隨盟軍推進擴大（OHM 2794959）。', 'Kingdom of Italy, enlarged with the Allied advance (OHM).'),
 ('SOVB_IT_K6', 'REGIME_IT', 'S_IT_K6', 2795081, [2795081], L(2795081), 'de_jure', '1945-04-29', '1945-05-09', 'EV_CASERTA', None, '卡塞塔投降後的義大利（OHM 2795081）。', 'Italy after the Caserta surrender (OHM 2795081).'),
 ('SOVB_AMGOT', 'REGIME_AMGOT', 'S_AMGOT', 2800536, [2800536], L(2800536), 'not_sovereign', '1943-09-17', '1944-03-01', 'EV_AMGOT', 'EV_AMGOT_END',
  '非主權：盟軍佔領區軍政府（AMGOT）。OHM 起始 1943-09-17（實際西西里 1943 年 7 月起即由盟軍軍政府管理，待查證）、結束只標 1944-03，取 03-01。', 'Not sovereign: AMGOT (OHM dates; Sicily was under AMG from July 1943, pending).'),
 ('SOVB_RSI_1', 'REGIME_IT_RSI', 'S_RSI_1', 2794958, [2794958], L(2794958), 'not_sovereign', '1943-09-23', '1944-08-25', 'EV_RSI', 'EV_IT_1944_08',
  '非主權：德國扶植的義大利社會共和國（FRUS 1943 II Doc. 331 稱 newly established “Republican Fascist” Government），實際在德軍佔領下。', 'Not sovereign: the German-sponsored Italian Social Republic.'),
 ('SOVB_RSI_2', 'REGIME_IT_RSI', 'S_RSI_2', 2794957, [2794957], L(2794957), 'not_sovereign', '1944-08-25', '1945-04-29', 'EV_IT_1944_08', 'EV_CASERTA', '非主權：義大利社會共和國（隨盟軍推進縮小）。', 'Not sovereign: Italian Social Republic (shrinking).'),
 ('SOVB_DEIT_1', 'REGIME_DE_OCC_IT', 'S_DEIT_1', 2961564, [2961564], L(2961564), 'not_sovereign', '1943-09-10', '1945-04-29', 'EV_IT_ARMISTICE', 'EV_CASERTA',
  '非主權：德軍直接管轄的義大利地區（OHM「German occupation of Italy」；阿爾卑斯山麓、亞得里亞海沿岸兩個作戰區），不屬社會共和國。', 'Not sovereign: Italian areas under direct German administration (OHM).'),
 ('SOVB_DEIT_2', 'REGIME_DE_OCC_IT', 'S_DEIT_2', 2961564, [2961564, 2795081], L(2961564, 2795081), 'not_sovereign', '1945-04-29', '1945-05-08', 'EV_CASERTA', 'EV_DE_SURRENDER',
  '非主權：卡塞塔投降不含伊松佐河以東的威尼斯朱利亞（FRUS 1945 III Doc. 558 註），本表至德國投降仍畫為德軍管轄（實際 5 月初南斯拉夫軍進入，待查證）。', 'Not sovereign: Venezia Giulia east of the Isonzo, excluded from the Caserta surrender.'),
 ('SOVB_DODEC', 'REGIME_DE_DODECANESE', 'S_DODEC', 2920370, [2920370], L(2920370), 'not_sovereign', '1943-09-11', '1945-05-08', 'EV_IT_ARMISTICE', 'EV_DE_SURRENDER',
  '非主權：德軍佔領的多德卡尼斯群島（OHM，1943-09-11 起）。1945-05-08 後的英軍佔領未建，留白。', 'Not sovereign: German-occupied Dodecanese (OHM).'),
 ('SOVB_AL_IT', 'REGIME_AL_IT', 'S_AL_IT', 2695459, [2695459], L(2695459), 'de_jure', '1941-06-07', T, 'EV_AL_1941', 'EV_IT_ARMISTICE', '義屬阿爾巴尼亞（OHM，含科索沃等），沿用 1939–1941 紀錄的處理。', 'Italian-ruled Albania (OHM).'),
 ('SOVB_AL_DE', 'REGIME_DE_OCC_AL', 'S_AL_DE', 2800553, [2800553], L(2800553), 'not_sovereign', T, '1944-11-29', 'EV_IT_ARMISTICE', 'EV_AL_DG', '非主權：德軍佔領下的阿爾巴尼亞（含科索沃）。', 'Not sovereign: German-occupied Albania.'),
 ('SOVB_AL_DG', 'REGIME_AL_DG', 'S_AL_DG', 2878108, [2878108], L(2878108), 'de_jure', '1944-11-29', '1945-05-09', 'EV_AL_DG', None,
  '阿爾巴尼亞民主政府（OHM 2878108；科索沃改屬南斯拉夫）。美英當時未承認（FRUS 1944 III Doc. 209），層級暫列國界，待查證。', 'Democratic Government of Albania (not then recognized by the US/UK; pending).'),
 ('SOVB_ME_IT', 'REGIME_ME_GOV', 'S_ME_IT', 2695479, [2695479], L(2695479), 'not_sovereign', '1941-10-03', T, 'EV_ME_GOV', 'EV_IT_ARMISTICE', '非主權：義大利佔領下的蒙特內哥羅總督轄區。', 'Not sovereign: Italian Governorate of Montenegro.'),
 ('SOVB_ME_DE', 'REGIME_DE_OCC_ME', 'S_ME_DE', 2855621, [2855621], L(2855621), 'not_sovereign', '1943-09-12', '1944-12-15', 'EV_IT_ARMISTICE', 'EV_ME_LIB',
  '非主權：德軍佔領下的蒙特內哥羅（OHM admin_level 3）。09-08～09-12 OHM 沒有版本，留白。', 'Not sovereign: German-occupied Montenegro; 8–12 Sep 1943 blank.'),
 ('SOVB_HR_1', 'REGIME_HR', 'S_HR_1', 2692713, [2692713], L(2692713), 'de_jure', '1941-04-10', '1943-09-10', 'EV_NDH', 'EV_IT_ARMISTICE', '克羅埃西亞獨立國（OHM；軸心扶植）。', 'Independent State of Croatia (OHM; Axis-sponsored).'),
 ('SOVB_HR_2', 'REGIME_HR', 'S_HR_2', 2747830, [2747830], L(2747830), 'de_jure', '1943-09-10', '1945-05-09', 'EV_IT_ARMISTICE', None,
  '克羅埃西亞獨立國，義大利停戰後併入原義佔達爾馬提亞（OHM 2747830，結束日 1945-05-15）。實際 1944–45 年大片地區由游擊隊控制，OHM 未分，簡化。', 'NDH incl. Dalmatia after the Italian armistice (OHM); Partisan-held areas not separated.'),
 ('SOVB_RS', 'REGIME_RS_MILCMD', 'S_RS', 2692357, [2692357], L(2692357), 'not_sovereign', '1941-04-22', '1944-10-22', 'EV_RS_OCC', 'EV_BELGRADE', '非主權：德國佔領下的塞爾維亞（軍事指揮官轄區）。', 'Not sovereign: German-occupied Serbia.'),
 ('SOVB_BG_1', 'REGIME_BG', 'S_BG_1', 2695478, [2695478], L(2695478), 'de_jure', '1941-04-30', '1943-07-01', 'EV_BG_OCC', 'EV_BG_1943', '保加利亞事實國界（OHM，含佔領併入的色雷斯、馬其頓）。', 'Bulgaria (de facto, OHM).'),
 ('SOVB_BG_2', 'REGIME_BG', 'S_BG_2', 2920397, [2920397], L(2920397), 'de_jure', '1943-07-01', '1944-08-26', 'EV_BG_1943', 'EV_BG_NEUTRAL', '保加利亞事實國界（OHM 2920397，起始日只標 1943-07）。', 'Bulgaria (OHM; start date given only as 1943-07).'),
 ('SOVB_BG_3', 'REGIME_BG', 'S_BG_3', 2848877, [2848877], L(2848877), 'de_jure', '1944-08-26', '1945-05-09', 'EV_BG_NEUTRAL', None, '保加利亞宣布中立、撤出佔領區後的國界（OHM 2848877）。', 'Bulgaria after declaring neutrality and withdrawing (OHM).'),
 ('SOVB_GR_1', 'REGIME_GR_OCC', 'S_GR_1', 2920398, [2920398, 2695478], L(2920398, 2695478), 'not_sovereign', '1941-04-30', '1943-07-01', 'EV_GR_OCC', 'EV_BG_1943', '非主權：軸心佔領下的希臘；保加利亞佔領併入的部分已扣除。OHM 沒有德、義佔領區的分區幾何。', 'Not sovereign: Axis-occupied Greece.'),
 ('SOVB_GR_2', 'REGIME_GR_OCC', 'S_GR_2', 2920398, [2920398, 2920397], L(2920398, 2920397), 'not_sovereign', '1943-07-01', '1944-08-26', 'EV_BG_1943', 'EV_BG_NEUTRAL', '非主權：軸心佔領下的希臘（扣除保加利亞 1943-07 版國界）。', 'Not sovereign: Axis-occupied Greece.'),
 ('SOVB_GR_3', 'REGIME_GR_OCC', 'S_GR_3', 2920399, [2920399, 2920370], L(2920399, 2920370), 'not_sovereign', '1944-08-26', '1944-10-12', 'EV_BG_NEUTRAL', 'EV_GR_LIB', '非主權：德軍撤離前的希臘（保加利亞已撤出，OHM 2920399）。', 'Not sovereign: Greece before the German withdrawal.'),
 ('SOVB_GR_4', 'REGIME_GR', 'S_GR_4', 2920399, [2920399, 2920370], L(2920399, 2920370), 'de_jure', '1944-10-12', '1945-05-09', 'EV_GR_LIB', None,
  '希臘王國：雅典 1944-10-12 解放、政府 10-18 返回（FRUS 1944 V Doc. 143、228）。克里特等地德軍到 1945-05 仍據守，OHM 未分，簡化。', 'Kingdom of Greece from the liberation of Athens; German-held Crete etc. not separated.'),
 ('SOVB_HU_1', 'REGIME_HU', 'S_HU_1', 2692359, [2692359], L(2692359), 'de_jure', '1941-12-14', '1944-03-19', 'EV_HU_YU_1941', 'EV_HU_OCC', '匈牙利事實國界（OHM 2692359）。', 'Hungary (de facto, OHM).'),
 ('SOVB_HU_2', 'REGIME_HU', 'S_HU_1', 2692359, [2692359], L(2692359), 'not_sovereign', '1944-03-19', '1945-02-01', 'EV_HU_OCC', 'EV_HU_ARMISTICE',
  '非主權：1944-03-19 德軍佔領匈牙利（FRUS 1944 III Doc. 787）。OHM 2692359 結束日只標「1944」，延用到 1945-02-01 匈牙利共和國版本開始（待查證）；1944 秋起蘇軍佔領東部，OHM 未分，簡化。', 'Not sovereign: German occupation from 19 Mar 1944; OHM end given only as 1944, extended to 1 Feb 1945 (pending).'),
 ('SOVB_HU_3', 'REGIME_HU_PROV', 'S_HU_3', 2878067, [2878067], L(2878067), 'de_jure', '1945-02-01', '1945-05-09', 'EV_HU_ARMISTICE', None,
  '匈牙利臨時國民政府（1945-01-20 與盟國簽停戰協定，FRUS 1945 IV Doc. 761），國界回到 1938 年前（OHM 2878067）。西部到 1945 年 4 月仍有德軍，簡化。', 'Hungarian provisional government, pre-1938 frontiers (OHM).'),
 ('SOVB_RO_1', 'REGIME_RO', 'S_RO_1', 2693255, [2693255, 2693259], L(2693255) + ' − 外涅斯特里亞', 'de_jure', '1941-08-19', '1944-04-02', 'EV_RO_REGAIN', 'EV_PRUT',
  '羅馬尼亞事實國界（含收回的比薩拉比亞、北布科維納）；外涅斯特里亞另畫為非主權。', 'Romania incl. Bessarabia and northern Bukovina; Transnistria separate.'),
 ('SOVB_TR', 'REGIME_TRANSNISTRIA', 'S_TR', 2693255, [2693255, 2693259], f'{L(2693255)} − {L(2693259)}（德涅斯特河以東）', 'not_sovereign', '1941-08-19', '1944-04-02', 'EV_TRANSNISTRIA', 'EV_PRUT',
  '非主權：羅馬尼亞佔領的外涅斯特里亞（FRUS 1941 I Doc. 350）。', 'Not sovereign: Romanian-occupied Transnistria.'),
 ('SOVB_RO_2', 'REGIME_RO', 'S_RO_2', 2693255, [2693255, 2851156, 2852346, 2957472], L(2693255) + ' − 同期蘇聯紀錄', 'de_jure', '1944-04-02', '1945-03-09', 'EV_PRUT', 'EV_RO_TRANSYLVANIA',
  '羅馬尼亞（不含蘇軍收復的比薩拉比亞、北布科維納）。OHM 1944-04～1945-03 沒有羅馬尼亞版本：以 2693255 扣掉同期蘇聯紀錄表示（待查證）。北特蘭西瓦尼亞此期間仍畫在匈牙利。', 'Romania minus Soviet-retaken areas; OHM has no version for Apr 1944–Mar 1945 (pending).'),
 ('SOVB_RO_3', 'REGIME_RO', 'S_RO_3', 2877966, [2877966], L(2877966), 'de_jure', '1945-03-09', '1945-05-09', 'EV_RO_TRANSYLVANIA', None,
  '羅馬尼亞，北特蘭西瓦尼亞 1945-03-09 起交回羅馬尼亞管理（FRUS 1945 V Doc. 370）。1945-02-01～03-09 北特蘭西瓦尼亞留白（蘇軍管理，待查證）。', 'Romania with northern Transylvania from 9 Mar 1945.'),
 ('SOVB_DK_1', 'REGIME_DK', 'S_DK', 2851793, [2851793], L(2851793), 'not_sovereign', '1944-06-17', '1945-05-05', 'EV_ICELAND', 'EV_DK_LIB', '非主權：德國佔領下的丹麥（冰島 1944-06-17 成為共和國後的 OHM 版本）。', 'Not sovereign: German-occupied Denmark.'),
 ('SOVB_DK_2', 'REGIME_DK', 'S_DK', 2851793, [2851793], L(2851793), 'de_jure', '1945-05-05', '1945-05-09', 'EV_DK_LIB', None, '丹麥王國（德軍投降、解放後）。', 'Kingdom of Denmark after liberation.'),
 ('SOVB_FI', 'REGIME_FI', 'S_FI', 2855285, [2855285], L(2855285), 'de_jure', '1944-09-19', '1945-05-09', 'EV_FI_ARMISTICE', None, '芬蘭（停戰協定後，佩察莫歸還蘇聯）。', 'Finland after the armistice.'),
 ('SOVB_CS_1', 'REGIME_CS', 'S_CS_1', 2747847, [2747847], L(2747847), 'de_jure', '1945-04-04', '1945-05-08', 'EV_KOSICE', 'EV_DE_SURRENDER',
  '捷克斯洛伐克共和國（科希策政府）在蘇軍解放的斯洛伐克。OHM 這段沒有版本：以斯洛伐克國 2747847 的邊界表示（待查證）；波希米亞、摩拉維亞到 05-08 仍屬德國；斯洛伐克南部 1938 年割給匈牙利的地區 1945-02-01 起留白。', 'Czechoslovak Republic in Soviet-liberated Slovakia (OHM has no version; Slovak State outline used, pending).'),
 ('SOVB_CS_2', 'REGIME_CS', 'S_CS_2', 2692766, [2692766], L(2692766), 'de_jure', '1945-05-08', '1945-05-09', 'EV_DE_SURRENDER', None, '捷克斯洛伐克共和國（OHM 2692766，1945-05-08 起）。', 'Czechoslovak Republic (OHM, from 8 May 1945).'),
 ('SOVB_RKBN', 'REGIME_RK_BNF', 'S_RKBN', 2748552, [2748552], L(2748552), 'not_sovereign', '1944-07-18', '1944-09-03', 'EV_RKBN', 'EV_BRUSSELS', '非主權：比利時—北法帝國專員公署（軍政改民政）。', 'Not sovereign: Reichskommissariat Belgien-Nordfrankreich.'),
 ('SOVB_BE_1', 'REGIME_BE', 'S_BE_1', 2692857, [2692857, 2692712], L(2692857, 2692712), 'de_jure', '1944-09-03', '1945-05-08', 'EV_BRUSSELS', 'EV_DE_SURRENDER',
  '比利時王國（布魯塞爾 1944-09-03 解放）；OHM 2692857 起始只標「1945」，提前用於 1944-09（待查證）；歐本—馬爾梅迪到 05-08 仍畫在德國。', 'Belgium from the liberation of Brussels (OHM start given only as 1945; pending).'),
 ('SOVB_BE_2', 'REGIME_BE', 'S_BE_2', 2692857, [2692857], L(2692857), 'de_jure', '1945-05-08', '1945-05-09', 'EV_DE_SURRENDER', None, '比利時王國（含歐本—馬爾梅迪）。', 'Belgium incl. Eupen-Malmedy.'),
 ('SOVB_FRP_1', 'REGIME_FR_PROV', 'S_FRP_1', 2696301, [2696301, 2692712, 2748552, 2956943], L(2696301) + ' − 同期德國、比北法專員公署、被佔摩納哥', 'de_jure', '1944-08-09', '1944-09-03', 'EV_FR_0809', 'EV_BRUSSELS',
  '法蘭西共和國臨時政府（含阿爾及利亞北部）。OHM 1944-08-09～1945-04-22 沒有法國版本：以 1945-04-22 版（2696301）扣掉同期德國等紀錄表示（待查證）；實際解放是逐步的（巴黎 08-25），簡化。', 'Provisional Government of the French Republic; OHM has no version for Aug 1944–Apr 1945 (1945 outline used, pending); liberation was gradual.'),
 ('SOVB_FRP_2', 'REGIME_FR_PROV', 'S_FRP_2', 2696301, [2696301, 2692712], L(2696301) + ' − 同期德國', 'de_jure', '1944-09-03', '1945-05-08', 'EV_BRUSSELS', 'EV_DE_SURRENDER',
  '法蘭西共和國臨時政府（美英蘇 1944-10-23 承認，FRUS 1944 III Doc. 692）。亞爾薩斯—洛林到 05-08 仍畫在德國（依 OHM 德國版本），簡化。', 'Provisional Government of the French Republic (recognized 23 Oct 1944).'),
 ('SOVB_FRP_3', 'REGIME_FR_PROV', 'S_FRP_3', 2696301, [2696301], L(2696301), 'de_jure', '1945-05-08', '1945-05-09', 'EV_DE_SURRENDER', None, '法蘭西共和國臨時政府（含亞爾薩斯—洛林）。', 'Provisional Government incl. Alsace-Lorraine.'),
 ('SOVB_ALG_1', 'REGIME_FNA_ALLIED', 'S_ALG', 2747869, [2747869], f'relation/2747869 v{MAN[2747869]["ohm_version"]} ∩ 北緯 40 度以南（阿爾及利亞北部）', 'not_sovereign', '1942-11-08', '1943-06-03', 'EV_TORCH', 'EV_CFLN',
  '非主權：1942-11-08 盟軍登陸後的阿爾及利亞北部，由盟軍軍事佔領，達爾朗（12-24 遇刺後由吉羅）以高級專員行使民政；美方不承認當地任何政府（FRUS 1942 II Doc. 469）。至 1943-06-03 法蘭西民族解放委員會成立（FRUS 1943 II Doc. 104）。突尼西亞、摩洛哥不在資料範圍內。幾何同 borders-1942-fix 的 SOVF_ALGERIA（撤回後延長）。',
  'Not sovereign: northern Algeria under Allied military occupation from 8 Nov 1942 until the French Committee of National Liberation was formed on 3 Jun 1943.'),
 ('SOVB_ALG_2', 'REGIME_CFLN', 'S_ALG', 2747869, [2747869], f'relation/2747869 v{MAN[2747869]["ohm_version"]} ∩ 北緯 40 度以南（阿爾及利亞北部）', 'de_jure', '1943-06-03', '1943-10-04', 'EV_CFLN', 'EV_CORSICA',
  '法蘭西民族解放委員會（阿爾及爾，FRUS 1943 II Doc. 104）治理的阿爾及利亞北部；盟軍仍駐軍。層級暫列國界（待查證）。', 'Northern Algeria under the French Committee of National Liberation (Algiers).'),
 ('SOVB_CFLN_2', 'REGIME_CFLN', 'S_ALG_COR', 2747869, [2747869, 2696300], f'relation/2747869 v{MAN[2747869]["ohm_version"]} ∩ 北緯 40 度以南 ∪ relation/2696300 v{MAN[2696300]["ohm_version"]} 的科西嘉', 'de_jure', '1943-10-04', '1944-08-09', 'EV_CORSICA', 'EV_FR_0809',
  '法蘭西民族解放委員會治理的阿爾及利亞北部與科西嘉（10-04 解放，待查證）。1944-06-03 該委員會改稱法蘭西共和國臨時政府，本表簡化為 1944-08-09 起併入臨時政府紀錄（待查證）。層級暫列國界。',
  'Northern Algeria and Corsica under the CFLN; merged into the Provisional Government record from 9 Aug 1944 (simplified).'),
]
DFYN = '南斯拉夫民主聯邦（OHM 2923084）扣掉同期仍由他方控制的地區。1945-03-07 狄托—舒巴希奇聯合政府成立前為游擊隊控制區，OHM 未分，層級暫列國界（待查證）。'
DFYE = 'Democratic Federal Yugoslavia (OHM) minus areas still held by others.'
for i, (s, e, sev, eev, rels) in enumerate([
        ('1944-10-22', '1944-11-29', 'EV_BELGRADE', 'EV_AL_DG', [2747830, 2855621, 2692359, 2800553, 2961564, 2692712, 2848877]),
        ('1944-11-29', '1944-12-15', 'EV_AL_DG', 'EV_ME_LIB', [2747830, 2855621, 2692359, 2878108, 2961564, 2692712, 2848877]),
        ('1944-12-15', '1945-02-01', 'EV_ME_LIB', 'EV_HU_ARMISTICE', [2747830, 2692359, 2878108, 2961564, 2692712, 2848877]),
        ('1945-02-01', '1945-04-29', 'EV_HU_ARMISTICE', 'EV_CASERTA', [2747830, 2878067, 2878108, 2961564, 2692712, 2848877]),
        ('1945-04-29', '1945-05-08', 'EV_CASERTA', 'EV_DE_SURRENDER', [2747830, 2878067, 2878108, 2961564, 2795081, 2692712, 2848877]),
        ('1945-05-08', '1945-05-09', 'EV_DE_SURRENDER', None, [2747830, 2878067, 2878108, 2795081, 2848877])], 1):
    R.append((f'SOVB_DFY_{i}', 'REGIME_DFY', f'S_DFY_{i}', DFY, [DFY] + rels, f'relation/{DFY} v{MAN[DFY]["ohm_version"]} − 同期其他紀錄（' + '、'.join(str(r) for r in rels) + '）',
              'de_jure', s, e, sev, eev, DFYN, DFYE))

# ---------------- 同一天不重疊 ----------------
def days(): 
    ds = sorted({r[7] for r in R} | {r[8] for r in R})
    return [d for d in ds if d < '1945-05-09']
active = lambda d: [r for r in R if r[7] <= d < r[8]]
bad = []
for d in days():
    rs = active(d)
    for i, a in enumerate(rs):
        for b in rs[i + 1:]:
            x = geo[a[2]].intersection(geo[b[2]]).area
            if x > 1e-3: bad.append((d, a[0], b[0], round(x, 4)))
assert not bad, bad
# 同一政權期間不重疊
for i, a in enumerate(R):
    for b in R[i + 1:]:
        if a[1] == b[1]: assert a[8] <= b[7] or b[8] <= a[7], (a[0], b[0])
qa = {k: {'area_deg2': round(v.area, 3), 'polygons': len(v.geoms), 'bounds': [round(b, 2) for b in v.bounds]} for k, v in geo.items()}
json.dump({'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'id': k, 'properties': {}, 'geometry': mapping(v)} for k, v in geo.items()]},
          open(os.path.join(ROOT, 'borders-1943-1945-south-derived.geojson'), 'w'), separators=(',', ':'))
json.dump(qa, open(os.path.join(ROOT, 'qa.json'), 'w'), indent=1)
json.dump([{'ph': r[0], 'regime': r[1], 'geom': r[2], 'start': r[7], 'end': r[8]} for r in R], open(os.path.join(HERE, 'records.json'), 'w'), indent=0)
exec(open(os.path.join(HERE, 'requests_part.py'), encoding='utf-8').read())
