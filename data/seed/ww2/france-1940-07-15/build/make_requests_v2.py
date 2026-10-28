"""v2：產生 POST 請求 JSON（不送出）。{{...}} 由前一步回應的 id 取代。
_meta.requiresDecision = true 的檔案，send_seed.py 預設跳過（需 --include-pending）。"""
import json, os, glob
B = os.path.dirname(os.path.abspath(__file__))
T = B + '/../'
R = T + 'requests/'
os.makedirs(R, exist_ok=True)
for old in glob.glob(R + '*.json'): os.remove(old)
Z = json.load(open(B + '/zones-v2.json'))
def w(name, obj):
    json.dump(obj, open(R + name, 'w'), ensure_ascii=False, indent=2); print(name)
def req(ph, post, body, **meta): return {"_placeholder": ph, "_post": post, **({"_meta": meta} if meta else {}), "body": body}

S = {
 "SRC_LECONTE": {"sourceKind": "map",
  "title": "Nouvelle carte de France par régions administratives au 1.800.000e (ligne de démarcation)",
  "publisher": "Éditions André Leconte (Paris)", "publishedText": "1940–1943（館方著錄年代區間；確切印行年待核）",
  "licenseCode": "cc0",
  "licenseEvidenceUrl": "https://www.parismuseescollections.paris.fr/fr/musee-jean-moulin/oeuvres/nouvelle-carte-de-france-par-regions-administratives-au-1800000e-ligne-de",
  "url": "https://upload.wikimedia.org/wikipedia/commons/7/7a/Nouvelle_carte_de_France_par_r%C3%A9gions_administratives_au_1.800.000e_%28ligne_de_d%C3%A9marcation%29%2C_2015.3.1.230%281%29.jpg",
  "catalogId": "Musée de la Libération de Paris – musée Jean Moulin, inv. 2015.3.1.230",
  "localCopyPath": "/workspace/world-line-ww2/trace/leconte-2015.3.1.230-recto.jpg",
  "note": "比例尺 1:1,800,000；印有分界線與省界。沒有 ligne du Nord-Est。Tai 2026-10-28 核可作為主要引用。"},
 "SRC_USMA15": {"sourceKind": "atlas_map",
  "title": "Western Europe 1940: Campaign in the West — The Pursuit, 13–25 June 1940",
  "publisher": "United States Military Academy, Department of History",
  "publishedText": "West Point Atlas, World War II European Theater（USMA 網站版）", "licenseCode": "us_federal_pd",
  "licenseEvidenceUrl": "https://commons.wikimedia.org/wiki/File:1940FranceJune.jpg",
  "url": "https://s3.amazonaws.com/usma-media/inline-images/academics/academic_departments/history/WWII%20Europe%20Med/WWIIEurope15.jpg",
  "catalogId": "USMA WWII Europe/Med, Map 15", "localCopyPath": "/workspace/world-line-ww2/trace/WWIIEurope15.jpg",
  "note": "17 U.S.C. §105 公有領域。圖上藍線是 6/25 德軍最遠推進線，不是分界線；Tai 核可只作 date_check。"},
 "SRC_AIN": {"sourceKind": "dataset", "title": "Ligne de démarcation", "publisher": "Département de l'Ain",
  "licenseCode": "licence_ouverte_2", "licenseEvidenceUrl": "https://www.data.gouv.fr/datasets/ligne-de-demarcation",
  "url": "https://departement-ain.opendata.arcgis.com/api/download/v1/items/73760b9eff0849f6afedc3d8b68b98ce/geojson?layers=5",
  "localCopyPath": "/workspace/world-line-ww2/trace/ain-ligne-demarcation.geojson",
  "note": "依停戰協定文字與 Michelin 1:200,000 建置的分界線（2,938 點）。授權不在允許清單，只作 auxiliary_geometry。"},
 "SRC_TRF": {"sourceKind": "dataset", "title": "TRF-GIS Départements (1870–1940): DEPARTEMENTS_1940",
  "publisher": "Harvard Dataverse (Victor Gay, Toulouse School of Economics)", "authors": "Victor Gay",
  "publishedText": "2020-09-22；v2.0 (2021-05)；資料論文 Gay 2021, Historical Methods 54(4):189–207",
  "licenseCode": "cc_by", "licenseEvidenceUrl": "https://doi.org/10.7910/DVN/ULQYM5",
  "url": "https://dataverse.harvard.edu/api/access/datafile/4083523", "catalogId": "doi:10.7910/DVN/ULQYM5",
  "localCopyPath": "/workspace/world-line-ww2/trace/trf-gis/DEPARTEMENTS_1940.shp",
  "note": "1940 年法國本土 90 省（含 Seine、Seine-et-Oise、Corse 單一省；Alpes-Maritimes 不含 Tende/La Brigue）。以現代市鎮界（GEOFLA 2011）組成，Lambert-93 轉 WGS84。CC BY 4.0：需署名 Victor Gay / TRF-GIS。"},
 "SRC_PERSEUS": {"sourceKind": "map", "title": "Carte régionale et zonale de la France occupée de 1940 à 1943",
  "publisher": "Wikimedia Commons（使用者 Perseus112）", "authors": "Perseus112",
  "publishedText": "2025-11-09（現代自製圖，宣稱參考 1943 年印行地圖與多種文獻）", "licenseCode": "cc_by_sa",
  "licenseEvidenceUrl": "https://commons.wikimedia.org/wiki/File:Carte_r%C3%A9gionale_et_zonale_de_la_France_occup%C3%A9e_de_1940_%C3%A0_1943.png",
  "url": "https://upload.wikimedia.org/wikipedia/commons/a/aa/Carte_r%C3%A9gionale_et_zonale_de_la_France_occup%C3%A9e_de_1940_%C3%A0_1943.png",
  "localCopyPath": "/workspace/world-line-ww2/trace/perseus112/full.png",
  "note": "現代自製圖（Own work）。依 R7 精神不應作為 primary；目前只有這份圖可取得 ligne du Nord-Est 的連續線形。待 Tai 決定。"},
 "SRC_DEJONGHE": {"sourceKind": "peer_reviewed",
  "title": "Le Nord et le Pas-de-Calais pendant la première année d'occupation : un régime d'exception",
  "publisher": "Revue du Nord（Université Lille 3）", "authors": "Étienne Dejonghe",
  "publishedText": "Revue du Nord 76 (306), 1994, pp. 487–499. doi:10.3406/rnord.1994.4922",
  "url": "https://www.persee.fr/doc/rnord_0035-2624_1994_num_76_306_4922", "catalogId": "doi:10.3406/rnord.1994.4922",
  "note": "p. 489–490：6/6/1940 OKW 令與 6/13 Hitler 決定 Nord、Pas-de-Calais 留在布魯塞爾軍管下；Nord-Est Linie 於 1941-12 撤除。"},
 "SRC_EHRI_RWD20": {"sourceKind": "official_record",
  "title": "Militärbefehlshaber in Belgien und Nordfrankreich und nachgeordnete Dienststellen – Amtsdrucksachen（館藏說明）",
  "publisher": "Bundesarchiv（經 EHRI Portal）", "catalogId": "Bundesarchiv RWD 20",
  "url": "https://portal.ehri-project.eu/units/de-002525-rwd_20",
  "note": "說明：1940-06-01 任命比利時－北法軍事指揮官；北法 12,355 km²；1944-07 改為 Wehrmachtbefehlshaber 並設 Reichskommissar。"},
 "SRC_CPH_AM": {"sourceKind": "peer_reviewed", "title": "Alzacja i Lotaryngia w latach 1940–1945",
  "publisher": "Czasopismo Prawno-Historyczne（Uniwersytet im. Adama Mickiewicza w Poznaniu）",
  "url": "https://presstoarch.amu.edu.pl/index.php/cph/article/view/50477",
  "note": "1940-08-02 Hitler 任命 Wagner、Bürckel 為亞爾薩斯、洛林民政長官（CdZ）。作者、卷期、頁碼待核（期刊網站 2026-10-28 無法開啟）。"},
}
for i, (k, v) in enumerate(S.items(), 1): w(f'01-source-{i}-{k.lower()}.json', req(k, '/api/v1/sources', v))

w('02-regime-deutsches-reich.json', req('REGIME_DE', '/api/v1/regimes', {
  "slug": "deutsches-reich", "wikidataQid": "Q7318",
  "names": [{"nameKind": "self", "originalText": "Deutsches Reich", "originalLang": "de",
             "display": {"zh-Hant": "德意志國", "en": "German Reich"}, "isPrimary": True}]}))
w('03-theater-west-europe.json', req('THEATER_WE', '/api/v1/theaters', {"code": "west-europe", "name": {"zh-Hant": "西歐戰區", "en": "Western Europe"}}))
w('04-snapshot-1-1940-07-15.json', req('SNAP_0715', '/api/v1/control-snapshots', {
  "theaterId": "{{THEATER_WE}}", "asOf": "1940-07-15", "attestation": "point",
  "title": {"zh-Hant": "法國分界線生效後（1940-07-15）", "en": "France after the demarcation line took effect (1940-07-15)"},
  "asOfNote": {"zh-Hant": "Leconte 分界線圖印行於 1940–1943，畫的是分界線本身，不是當日快照；取 7 月中德軍退回分界線後的狀態。",
               "en": "The Leconte map (printed 1940–43) shows the line itself, not a dated snapshot; taken as the situation after German forces withdrew to the line in mid-July."}}))
w('04-snapshot-2-1940-08-15.json', req('SNAP_0815', '/api/v1/control-snapshots', {
  "theaterId": "{{THEATER_WE}}", "asOf": "1940-08-15", "attestation": "point",
  "title": {"zh-Hant": "東北線與亞爾薩斯－摩澤爾民政長官生效後（1940-08-15）", "en": "After the Nord-Est line and the Alsace-Moselle CdZ took effect (1940-08-15)"},
  "asOfNote": {"zh-Hant": "ligne du Nord-Est 1940-07-20 施行；CdZ 1940-08-02 任命。", "en": "Nord-Est line applied 20 July 1940; CdZ appointed 2 August 1940."}}))

def C(src, role, loc, note): return {"sourceId": "{{%s}}" % src, "role": role, "locator": loc, "evidenceNote": note}
LEC_LINE = C('SRC_LECONTE', 'primary', 'Leconte 單張圖正面，館藏號 2015.3.1.230：分界線', '圖上印出的分界線；描線以 27 個控制點配準後目視核對（RMSE ≈ 13 px ≈ 2.4 km）。')
LEC_DEP = lambda deps: C('SRC_LECONTE', 'primary', f'Leconte 單張圖正面，館藏號 2015.3.1.230：{deps} 省界', '圖上印出的 1940 年前後省界，與 TRF-GIS 1940 省界目視吻合。控制身分本身不在圖上，由 date_check 文獻佐證。')
AIN = C('SRC_AIN', 'auxiliary_geometry', 'data.gouv.fr「Ligne de démarcation」layer 5（LineString）', '分界線座標（兩端延長 0.05° 後切割）。')
TRF = lambda what: C('SRC_TRF', 'auxiliary_geometry', 'DEPARTEMENTS_1940（doi:10.7910/DVN/ULQYM5）', what)
PER = C('SRC_PERSEUS', 'auxiliary_geometry', 'Commons 原檔 5910×5351，圖例 #5「Zone Interdite ou Zone Rouge」', 'ligne du Nord-Est 線形：核心色像素骨架化，37 個控制點配準（RMSE 1.2 px ≈ 0.2 km）。')
USMA = C('SRC_USMA15', 'date_check', 'West Point Atlas WWII Europe, Map 15', '6/25 德軍推進範圍越過後來的分界線，佐證 7 月中才退回分界線。')
DEJ = lambda pg, note: C('SRC_DEJONGHE', 'date_check', f'Revue du Nord 76 (306), 1994, {pg}', note)

def geo(k): return Z[k]
recs = [
 ('05-control-1-main.json', 'CR_MAIN', dict(boundarySource='分界線：圖描（Ain 座標，對照 Leconte）；東側：ligne du Nord-Est（Perseus112 向量化）；北、東北：1940 省界（Nord、Pas-de-Calais、Moselle）；外框：TRF-GIS 1940'),
  {"controllerRegimeId": "{{REGIME_DE}}", "snapshotId": "{{SNAP_0715}}", "controlType": "military_occupation",
   "validPeriod": {"start": "1940-07-15", "end": "1942-11-11"}, "startUncertainty": {"start": "1940-06-25", "end": "1940-07-16"},
   "isDisputed": False, "geometry": geo('main'),
   "citations": [LEC_LINE, AIN, TRF('外框與北部、東北的省界。'), PER, USMA]}),
 ('05-control-2-nord-pas-de-calais.json', 'CR_NORD', dict(boundarySource='省界組合：Nord (59) + Pas-de-Calais (62)，TRF-GIS 1940'),
  {"controllerRegimeId": "{{REGIME_DE}}", "snapshotId": "{{SNAP_0715}}", "controlType": "military_occupation",
   "validPeriod": {"start": "1940-06-04", "end": "1944-07-16"},
   "startUncertainty": {"start": "1940-05-28", "end": "1940-06-14"}, "endUncertainty": {"start": "1944-07-12", "end": "1944-07-17"},
   "isDisputed": False, "geometry": geo('nord'),
   "citations": [LEC_DEP('Nord、Pas-de-Calais'), TRF('Nord、Pas-de-Calais 兩省 1940 年省界的聯集。'),
                 DEJ('pp. 489–490', '1940-06-06 OKW 令、06-13 Hitler 決定兩省留在布魯塞爾軍事指揮官下。'),
                 C('SRC_EHRI_RWD20', 'date_check', 'Bundesarchiv RWD 20 館藏說明', '1940-06-01 任命 Militärbefehlshaber Belgien-Nordfrankreich；1944-07 改制。')]}),
 ('05-control-3a-alsace-moselle-military.json', 'CR_AM_MIL', dict(boundarySource='省界組合：Moselle (57) + Bas-Rhin (67) + Haut-Rhin (68)，TRF-GIS 1940'),
  {"controllerRegimeId": "{{REGIME_DE}}", "snapshotId": "{{SNAP_0715}}", "controlType": "military_occupation",
   "validPeriod": {"start": "1940-07-15", "end": "1940-08-02"}, "startUncertainty": {"start": "1940-06-17", "end": "1940-07-16"},
   "isDisputed": False, "geometry": geo('am'),
   "citations": [LEC_DEP('Moselle、Bas-Rhin、Haut-Rhin'), TRF('三省 1940 年省界的聯集。'),
                 C('SRC_CPH_AM', 'date_check', '全文（頁碼待核）', '8/2 起改由民政長官管轄，此前為軍事佔領。')]}),
 ('05-control-3b-alsace-moselle-cdz.json', 'CR_AM_CDZ', dict(boundarySource='省界組合：Moselle (57) + Bas-Rhin (67) + Haut-Rhin (68)，TRF-GIS 1940'),
  {"controllerRegimeId": "{{REGIME_DE}}", "snapshotId": "{{SNAP_0815}}", "controlType": "direct_rule",
   "validPeriod": {"start": "1940-08-02", "end": "1944-11-22"}, "endUncertainty": {"start": "1944-11-19", "end": "1945-03-21"},
   "isDisputed": False, "geometry": geo('am'),
   "citations": [LEC_DEP('Moselle、Bas-Rhin、Haut-Rhin'), TRF('三省 1940 年省界的聯集。'),
                 C('SRC_CPH_AM', 'date_check', '全文（頁碼待核）', '1940-08-02 Hitler 任命 Wagner（Elsass）、Bürckel（Lothringen）為 CdZ，事實併入。')]}),
 ('05-control-4a-zone-reservee-pre.json', 'CR_ZI_PRE', dict(requiresDecision=True, boundarySource='西界：ligne du Nord-Est（Perseus112 向量化）；南界：分界線（圖描）；其餘：1940 省界',
   reason='東北線生效（07-20）前的過渡紀錄；primary 只能用 Perseus112 自製圖，待 Tai 決定。'),
  {"controllerRegimeId": "{{REGIME_DE}}", "snapshotId": "{{SNAP_0715}}", "controlType": "military_occupation",
   "validPeriod": {"start": "1940-07-15", "end": "1940-07-20"}, "isDisputed": False, "geometry": geo('zi'),
   "citations": [C('SRC_PERSEUS', 'primary', 'Commons 原檔 5910×5351，圖例 #5「Zone Interdite ou Zone Rouge」', '東北線線形（現代自製圖，待決）。'),
                 AIN, TRF('北、東側省界與外框。')]}),
 ('05-control-4b-zone-reservee.json', 'CR_ZI', dict(requiresDecision=True, boundarySource='西界：ligne du Nord-Est（Perseus112 向量化）；南界：分界線（圖描）；其餘：1940 省界',
   reason='primary 只能用 Perseus112 自製圖（R7 精神不採用自製），待 Tai 決定或另找合格地圖。'),
  {"controllerRegimeId": "{{REGIME_DE}}", "snapshotId": "{{SNAP_0815}}", "controlType": "military_occupation",
   "validPeriod": {"start": "1940-07-20", "end": "1942-11-11"}, "startUncertainty": {"start": "1940-06-23", "end": "1940-07-21"},
   "isDisputed": False, "geometry": geo('zi'),
   "citations": [C('SRC_PERSEUS', 'primary', 'Commons 原檔 5910×5351，圖例 #5「Zone Interdite ou Zone Rouge」', '東北線線形（現代自製圖，待決）。'),
                 AIN, TRF('北、東側省界與外框。'),
                 DEJ('p. 490', '「la création (décrétée le 23 juin) d’une Nord-Est Linie」；1941-12 撤除。')]}),
]
for name, ph, meta, body in recs: w(name, req(ph, '/api/v1/control-records', body, **meta))

# 供檢查用的 GeoJSON（每區一個 feature）
props = {
 'main': {"record": "CR_MAIN", "name": {"zh-Hant": "本體軍事佔領區", "en": "Main German military occupation zone"}, "periods": ["[1940-07-15, 1942-11-11) military_occupation"]},
 'nord': {"record": "CR_NORD", "name": {"zh-Hant": "北部兩省（歸布魯塞爾軍管）", "en": "Nord & Pas-de-Calais (MBH Belgien-Nordfrankreich)"}, "periods": ["[1940-06-04, 1944-07-16) military_occupation"]},
 'am': {"record": "CR_AM_MIL + CR_AM_CDZ", "name": {"zh-Hant": "亞爾薩斯－摩澤爾", "en": "Alsace-Moselle"}, "periods": ["[1940-07-15, 1940-08-02) military_occupation", "[1940-08-02, 1944-11-22) direct_rule (CdZ)"]},
 'zi': {"record": "CR_ZI_PRE + CR_ZI（待決）", "name": {"zh-Hant": "東北禁區（zone réservée）", "en": "North-east reserved zone"}, "periods": ["[1940-07-15, 1940-07-20) military_occupation", "[1940-07-20, 1942-11-11) military_occupation"]},
}
src_note = {k: m['boundarySource'] for _, ph, m, _ in recs for k in [{'CR_MAIN': 'main', 'CR_NORD': 'nord', 'CR_AM_MIL': 'am', 'CR_ZI': 'zi'}.get(ph)] if k}
fc = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {**props[k], "boundarySource": src_note[k], "status": "DRAFT v2 — 待 Tai 檢查，未寫入資料庫"}, "geometry": Z[k]} for k in props]}
json.dump(fc, open(T + 'zones-1940-v2.geojson', 'w'), ensure_ascii=False)
print('zones-1940-v2.geojson')
