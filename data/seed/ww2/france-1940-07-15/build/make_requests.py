"""產生 M0 第一筆真實資料的 POST 請求 JSON（不送出）。{{...}} 為送出時由前一步回應的 id 取代。"""
import json, os
T = os.path.dirname(os.path.abspath(__file__)) + '/../'
R = T + 'requests/'
os.makedirs(R, exist_ok=True)
def w(name, obj):
    json.dump(obj, open(R + name, 'w'), ensure_ascii=False, indent=2); print(name)

sources = {
 "SRC_LECONTE": {
  "sourceKind": "map",
  "title": "Nouvelle carte de France par régions administratives au 1.800.000e (ligne de démarcation)",
  "publisher": "Éditions André Leconte (Paris)",
  "publishedText": "1940–1943（館方著錄年代區間；確切印行年待核）",
  "licenseCode": "cc0",
  "licenseEvidenceUrl": "https://www.parismuseescollections.paris.fr/fr/musee-jean-moulin/oeuvres/nouvelle-carte-de-france-par-regions-administratives-au-1800000e-ligne-de",
  "url": "https://upload.wikimedia.org/wikipedia/commons/7/7a/Nouvelle_carte_de_France_par_r%C3%A9gions_administratives_au_1.800.000e_%28ligne_de_d%C3%A9marcation%29%2C_2015.3.1.230%281%29.jpg",
  "catalogId": "Musée de la Libération de Paris – musée Jean Moulin, inv. 2015.3.1.230",
  "localCopyPath": "/workspace/world-line-ww2/trace/leconte-2015.3.1.230-recto.jpg",
  "note": "比例尺 1:1,800,000，印有分界線。Paris Musées 開放內容以 CC0 釋出。"
 },
 "SRC_USMA15": {
  "sourceKind": "atlas_map",
  "title": "Western Europe 1940: Campaign in the West — The Pursuit, 13–25 June 1940",
  "publisher": "United States Military Academy, Department of History",
  "publishedText": "West Point Atlas, World War II European Theater（USMA 網站版）",
  "licenseCode": "us_federal_pd",
  "licenseEvidenceUrl": "https://commons.wikimedia.org/wiki/File:1940FranceJune.jpg",
  "url": "https://s3.amazonaws.com/usma-media/inline-images/academics/academic_departments/history/WWII%20Europe%20Med/WWIIEurope15.jpg",
  "catalogId": "USMA WWII Europe/Med, Map 15",
  "localCopyPath": "/workspace/world-line-ww2/trace/WWIIEurope15.jpg",
  "note": "美國陸軍官校作品，17 U.S.C. §105 公有領域（Commons 標 PD-USGov-Military-Army）。圖上藍線是 6/25 德軍最遠推進線，不是分界線。"
 },
 "SRC_AIN": {
  "sourceKind": "dataset",
  "title": "Ligne de démarcation",
  "publisher": "Département de l'Ain",
  "licenseCode": "licence_ouverte_2",
  "licenseEvidenceUrl": "https://www.data.gouv.fr/datasets/ligne-de-demarcation",
  "url": "https://departement-ain.opendata.arcgis.com/api/download/v1/items/73760b9eff0849f6afedc3d8b68b98ce/geojson?layers=5",
  "localCopyPath": "/workspace/world-line-ww2/trace/ain-ligne-demarcation.geojson",
  "note": "全線 LineString（2,938 點，約 1,219 km），依停戰協定文字與 Michelin 1:200,000 地圖建置。只作 auxiliary_geometry。"
 },
 "SRC_NE10M": {
  "sourceKind": "dataset",
  "title": "Natural Earth 1:10m Cultural Vectors — Admin 0 Countries",
  "publisher": "Natural Earth",
  "licenseCode": "public_domain",
  "licenseEvidenceUrl": "https://www.naturalearthdata.com/about/terms-of-use/",
  "url": "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_0_countries.geojson",
  "localCopyPath": "/workspace/world-line-ww2/trace/ne_10m_admin_0_countries.geojson",
  "note": "現代法國國界與海岸線（1:10M），用來裁切。licenseCode 'public_domain' 不在 PRD 清單，待拍板。"
 }
}
for i, (k, v) in enumerate(sources.items(), 1):
    w(f'01-source-{i}-{k.lower()}.json', {"_placeholder": k, "_post": "/api/v1/sources", "body": v})

w('02-regime-deutsches-reich.json', {"_placeholder": "REGIME_DE", "_post": "/api/v1/regimes", "body": {
  "slug": "deutsches-reich", "wikidataQid": "Q7318",
  "names": [{"nameKind": "self", "originalText": "Deutsches Reich", "originalLang": "de",
             "display": {"zh-Hant": "德意志國", "en": "German Reich"}, "isPrimary": True}]}})
w('03-theater-west-europe.json', {"_placeholder": "THEATER_WE", "_post": "/api/v1/theaters", "body": {
  "code": "west-europe", "name": {"zh-Hant": "西歐戰區", "en": "Western Europe"}}})
w('04-snapshot-1940-07-15.json', {"_placeholder": "SNAPSHOT", "_post": "/api/v1/control-snapshots", "body": {
  "theaterId": "{{THEATER_WE}}", "asOf": "1940-07-15", "attestation": "point",
  "title": {"zh-Hant": "法國分界線生效後（1940-07-15）", "en": "France after the demarcation line took effect (1940-07-15)"},
  "asOfNote": {"zh-Hant": "Leconte 分界線圖印行於 1940–1943，只畫分界線，不是當日快照；以 7 月中德軍退回分界線後的狀態為準。",
               "en": "The Leconte map (printed 1940–43) shows the line itself, not a dated snapshot; taken as the situation after German forces withdrew to the line in mid-July."}}})

geom = json.load(open(T + 'occupied-zone-1940-07-15.geojson'))['features'][0]['geometry']
w('05-control-record-occupied-zone.json', {"_placeholder": "CONTROL_RECORD", "_post": "/api/v1/control-records", "body": {
  "controllerRegimeId": "{{REGIME_DE}}", "snapshotId": "{{SNAPSHOT}}", "controlType": "military_occupation",
  "validPeriod": {"start": "1940-07-15", "end": "1942-11-11"},
  "isDisputed": False,
  "geometry": geom,
  "citations": [
   {"sourceId": "{{SRC_LECONTE}}", "role": "primary",
    "locator": "Leconte《Nouvelle carte de France… au 1.800.000e (ligne de démarcation)》單張圖正面；Musée de la Libération de Paris 館藏號 2015.3.1.230",
    "evidenceNote": "圖上印出的分界線。北側佔領區的範圍以此目視核對（以 27 個控制點配準，RMSE ≈ 13 px ≈ 2.4 km）。"},
   {"sourceId": "{{SRC_AIN}}", "role": "auxiliary_geometry",
    "locator": "data.gouv.fr「Ligne de démarcation」，layer 5（LineString）",
    "evidenceNote": "分界線的實際座標取自這份資料，向兩端延長 0.05° 後切割法國本土。"},
   {"sourceId": "{{SRC_NE10M}}", "role": "auxiliary_geometry",
    "locator": "ne_10m_admin_0_countries，ADM0_A3=FRA，取本土部分 box(-6,41,10,52)",
    "evidenceNote": "提供法國本土外框與島嶼，用的是現代國界。"},
   {"sourceId": "{{SRC_USMA15}}", "role": "date_check",
    "locator": "West Point Atlas WWII Europe, Map 15「Campaign in the West, The Pursuit, 13–25 June」",
    "evidenceNote": "顯示 6/25 德軍推進已越過後來的分界線（到 Lyon、Bordeaux 以南），可佐證 7 月中退回分界線之前，佔領狀態還不是這條線；不提供分界線本身。"}
  ]}})
