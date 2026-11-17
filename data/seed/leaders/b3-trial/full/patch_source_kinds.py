#!/usr/bin/env python3
"""把網域歸類補進 run100/source-kind-overrides.json（寫庫腳本與 full/dryrun_full.py 共用）。可重跑：已存在且值相同就不動，值不同就中止。

依據：ARCHITECTURE §16 T1（A＝官方檔案、國家級傳記辭典、權威機構人名權威；B＝學術專書、具名作者／學術機構百科）。
歸類由 World Line 主管 2026-11-11 21:55 決定（Tai 授權範圍內）；之後新遇到的網域照同一原則加進 POLICY 並在報告列出；個人網站不收（值 null＝放棄）。
grade 不在 overrides（寫庫腳本取 seed citation 的 grade）；本腳本另輸出 domain-policy.json 供 dry-run 核對 seed grade 與政策是否一致。
用法：python3 -I data/seed/leaders/b3-trial/full/patch_source_kinds.py
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OVR = HERE.parent / "run100" / "source-kind-overrides.json"
POLICY = [  # (domain, source_kind, grade, 依據, 決定)
    ("lobid.org", "official_website", "A", "GND（德國國家圖書館人名權威檔）的官方鏡像；T1 權威機構人名權威", "主管 2026-11-11 21:55"),
    ("www.nids.mod.go.jp", "official_history", "A", "日本防衛省防衛研究所戰史研究中心（官方戰史）", "主管 2026-11-11 21:55"),
    ("www.dhm.de", "encyclopedia", "B", "Deutsches Historisches Museum LeMO 傳記（學術機構傳記）", "主管 2026-11-11 21:55"),
    ("millercenter.org", "encyclopedia", "B", "Miller Center, University of Virginia 總統傳記（學術機構傳記）", "主管 2026-11-11 21:55"),
    ("ebsco.com", "encyclopedia", "B", "EBSCO Research Starters（具名作者百科條目）", "主管 2026-11-11 21:55"),
    ("www.ebsco.com", "encyclopedia", "B", "EBSCO Research Starters（同上；batch003 來源用 www 主機名，寫庫腳本以完整主機名比對）", "主管 2026-11-11 21:55（同一網域補主機名）"),
    ("id.ndl.go.jp", "official_website", "A", "國立國會圖書館典據 Web NDL Authorities；T1 權威機構人名權威", "主管 2026-11-12 03:03"),
    ("ndl.go.jp", "official_website", "A", "日本國立國會圖書館官方頁（含近代日本人の肖像）", "主管 2026-11-12 03:03"),
    ("www.ndl.go.jp", "official_website", "A", "日本國立國會圖書館同上（www 主機名）", "主管 2026-11-12 03:03"),
    ("jacar.go.jp", "official_history", "A", "國立公文書館アジア歴史資料センター（JACAR）官方檔案", "主管 2026-11-12 03:03"),
    ("www.jacar.go.jp", "official_history", "A", "JACAR 同上（www 主機名）", "主管 2026-11-12 03:03"),
    ("jacar.archives.go.jp", "official_history", "A", "JACAR 官方檔案（archives.go.jp 主機）", "主管 2026-11-12 03:03"),
    ("nids.mod.go.jp", "official_history", "A", "日本防衛省防衛研究所戰史（無 www 主機名；www 已於 21:55 列入）", "主管 2026-11-11 21:55（同一網域補主機名）／主管 2026-11-12 03:03 確認"),
    ("kotobank.jp", "encyclopedia", "B", "Kotobank 具名條目：日本大百科全書、國史大辭典、世界大百科事典", "主管 2026-11-12 03:03"),
    ("www.kotobank.jp", "encyclopedia", "B", "Kotobank 同上（www 主機名）", "主管 2026-11-12 03:03"),
    # 英語國家將領（主管 2026-11-12 06:32）；主機名皆於 2026-11-12 06:3x 以一般 HTTPS（未用 -k）確認存在
    ("www.archives.gov", "archive", "A", "美國國家檔案館 NARA 官方頁（含總統圖書館 NARA 頁）", "主管 2026-11-12 06:32"),
    ("archives.gov", "archive", "A", "NARA 同上（無 www 主機名）", "主管 2026-11-12 06:32"),
    ("catalog.archives.gov", "archive", "A", "NARA 線上目錄（National Archives Catalog）", "主管 2026-11-12 06:32"),
    ("www.nationalarchives.gov.uk", "archive", "A", "英國國家檔案館（The National Archives）官方頁", "主管 2026-11-12 06:32"),
    ("nationalarchives.gov.uk", "archive", "A", "英國國家檔案館同上（無 www 主機名）", "主管 2026-11-12 06:32"),
    ("discovery.nationalarchives.gov.uk", "archive", "A", "英國國家檔案館 Discovery 目錄", "主管 2026-11-12 06:32"),
    ("history.army.mil", "official_history", "A", "美國陸軍軍史中心（U.S. Army Center of Military History）官方戰史", "主管 2026-11-12 06:32"),
    ("www.history.navy.mil", "official_history", "A", "美國海軍歷史與遺產司令部（NHHC）官方戰史", "主管 2026-11-12 06:32"),
    ("www.afhra.af.mil", "official_history", "A", "美國空軍歷史研究署（AFHRA）官方戰史", "主管 2026-11-12 06:32"),
    ("www.usmcu.edu", "official_history", "A", "美國陸戰隊大學（含 Marine Corps History Division）官方史料", "主管 2026-11-12 06:32"),
    ("www.raf.mod.uk", "official_history", "A", "英國皇家空軍官方網站（國防部，含官方歷史頁）", "主管 2026-11-12 06:32"),
    ("www.thegazette.co.uk", "official_website", "A", "The London Gazette 官方公報（任命公告）", "主管 2026-11-12 06:32"),
    ("www.oxforddnb.com", "encyclopedia", "B", "Oxford Dictionary of National Biography（訂閱制；只用公開摘要／首段，不登入）", "主管 2026-11-12 06:32"),
    ("oxforddnb.com", "encyclopedia", "B", "ODNB 同上（無 www 主機名）", "主管 2026-11-12 06:32"),
    ("www.anb.org", "encyclopedia", "B", "American National Biography（訂閱制；只用公開摘要／首段，不登入）", "主管 2026-11-12 06:32"),
    ("anb.org", "encyclopedia", "B", "ANB 同上（無 www 主機名）", "主管 2026-11-12 06:32"),
    ("academic.oup.com", "encyclopedia", "B", "OUP Academic：ODNB／ANB 現轉址主機（只限 /oxford-dictionary-of-national-biography、/american-national-biography 的公開內容）", "主管 2026-11-12 06:32"),
    ("www.nam.ac.uk", "encyclopedia", "B", "National Army Museum（英國國家陸軍博物館，具名機構）", "主管 2026-11-12 06:32"),
    # 寫庫前未歸類的 7 個網域（主管 2026-11-13 11:05（寫庫前 7 個未歸類網域，§16 T1））
    ("www.kantei.go.jp", "official_website", "A", "首相官邸（日本內閣官方網站）歷代內閣頁；官方機關", "主管 2026-11-13 11:05（寫庫前 7 個未歸類網域，§16 T1）"),
    ("www.normattiva.it", "official_record", "A", "Normattiva（義大利政府官方法規資料庫）；官方法規文本", "主管 2026-11-13 11:05（寫庫前 7 個未歸類網域，§16 T1）"),
    ("armed.mapn.ro", "official_website", "A", "羅馬尼亞國防部（Ministerul Apărării Naționale）官方網站", "主管 2026-11-13 11:05（寫庫前 7 個未歸類網域，§16 T1）"),
    ("finland.fi", "official_website", "A", "thisisFINLAND（芬蘭外交部營運之政府官方網站）", "主管 2026-11-13 11:05（寫庫前 7 個未歸類網域，§16 T1）"),
    ("www.ipsb.nina.gov.pl", "encyclopedia", "A", "Internetowy Polski Słownik Biograficzny（波蘭國家級傳記辭典 PSB 數位版，具名作者）", "主管 2026-11-13 11:05（寫庫前 7 個未歸類網域，§16 T1）"),
    ("avalon.law.yale.edu", "archive", "B", "Avalon Project（耶魯法學院 Lillian Goldman Law Library）學術機構文件庫；seed 另有 3 筆標 C，寫庫照 seed 等級", "主管 2026-11-13 11:05（寫庫前 7 個未歸類網域，§16 T1）"),
    ("marskinmaja.net", "official_website", "C", "Suomen Marsalkka Mannerheimin Metsästysmaja ry（具名登記協會）網站；具名 C", "主管 2026-11-13 11:05（寫庫前 7 個未歸類網域，§16 T1）"),
    # 禁用（source_kind None＝寫庫腳本 DROP；grade X）：主管 2026-11-12 22:08 套用 Tai 既有「個人網站不收」
    ("generals.dk", None, "X", "個人網站（Steen Ammentorp 個人經營的將領資料庫）；具名 C 須為具名作者或機構的正當出版物，個人網站不收", "主管 2026-11-12 22:08"),
    ("www.generals.dk", None, "X", "generals.dk 同上（www 主機名）", "主管 2026-11-12 22:08"),
]

# 主管 2026-11-13 11:05：寫庫前其餘 262 個未歸類網域依同一規則歸類，清單存 domain-policy-additions-20261113.json（含 review 旗標）
POLICY += [(x["domain"], x["source_kind"], x["grade"], x["basis"], x["decision"])
           for x in json.loads((Path(__file__).resolve().parent / "domain-policy-additions-20261113.json").read_text(encoding="utf-8"))]

# 禁用網域替換（banned-replace-2026-11-14）新增來源的未歸類網域：依 §16 T1 同一原則（Tai 2026-11-14「繼續處理」）。
# 等級仍取 seed citation 的 grade（轉錄本已依 Tai 2026-11-14 記 B）；共用主機（S3、RAF Museum 文件區）用完整 URL 當鍵。
_D = "Tai 2026-11-14（banned-replace 寫庫前未歸類網域，§16 T1 同一原則）"
POLICY += [
    ("teara.govt.nz", "encyclopedia", "A", "Dictionary of New Zealand Biography（紐西蘭國家級傳記辭典，Te Ara／文化遺產部）", _D),
    ("adb.anu.edu.au", "encyclopedia", "A", "Australian Dictionary of Biography（澳洲國家級傳記辭典，ANU）", _D),
    ("nzetc.victoria.ac.nz", "official_history", "B", "紐西蘭官方二戰戰史（War History Branch）經 NZETC 轉錄；原著 A，轉錄記 B", _D),
    ("https://s3-ap-southeast-2.amazonaws.com/awm-media/collection/RCDIG1070073/document/5519402.PDF", "official_history", "A",
     "澳洲官方戰史（Long, The Final Campaigns 第 5 章），AWM 官方數位化 PDF（AWM 的 S3 媒體庫）", _D),
    ("https://www.rafmuseum.org.uk/documents/Research/RAF-Historical-Society-Journals/Journal-8-Dr-Philip-Towle-on-Air-Control-Vincent-Orange.pdf", "peer_reviewed", "B",
     "RAF Historical Society Journal 第 8 期（Vincent Orange 具名論文），RAF Museum 文件區", _D),
    ("vintageaviationnews.com", "encyclopedia", "C", "Vintage Aviation News（具名記者的航空史文章）；具名 C，比照 historynet.com", _D),
    ("www.seaforces.org", "encyclopedia", "C", "seaforces.org（具名網站，轉載海軍官方傳記但未標原始出處）；具名 C", _D),
    ("www.oireachtas.ie", "official_website", "A", "愛爾蘭國會（Houses of the Oireachtas）官方議員名錄", "Tai 2026-11-15（B3 v3 寫庫前未歸類網域，§16 T1 同一原則）"),
    ("www.irishstatutebook.ie", "official_record", "A", "Irish Statute Book（愛爾蘭總檢察長辦公室，憲法與法令原文）", "Tai 2026-11-15（B3 v3 寫庫前未歸類網域，§16 T1 同一原則）"),
    ("digar.ee", "archive", "B", "DIGAR（愛沙尼亞國家圖書館數位典藏）收錄之出版品", "Tai 2026-11-15（B3 v3 寫庫前未歸類網域，§16 T1 同一原則）"),
    ("www.riigikogu.ee", "official_website", "A", "愛沙尼亞國會（Riigikogu）官方頁", "Tai 2026-11-15（B3 v3 寫庫前未歸類網域，§16 T1 同一原則）"),
    ("riigikogu.ee", "official_website", "A", "愛沙尼亞國會（Riigikogu）官方頁（無 www 主機名）", "Tai 2026-11-15（B3 v3 寫庫前未歸類網域，§16 T1 同一原則）"),
    ("www.ra.ee", "archive", "A", "愛沙尼亞國家檔案館（Rahvusarhiiv）", "Tai 2026-11-15（B3 v3 寫庫前未歸類網域，§16 T1 同一原則）"),
    ("www.nepjol.info", "peer_reviewed", "B", "NepJOL（尼泊爾學術期刊平台）具名論文", "Tai 2026-11-15（B3 v3 寫庫前未歸類網域，§16 T1 同一原則）"),
    ("www.berlin.de", "official_website", "A", "柏林市政府官方網站", "Tai 2026-11-15（B3 v3 寫庫前未歸類網域，§16 T1 同一原則）"),
    ("www.generalstaff.org", "official_history", "B", "英國官方戰史（Kirby, The War Against Japan Vol. IV, HMSO）掃描本，放在第三方網站；原著 A，第三方副本記 B", _D),
    ('academiahistoria.org.co', 'encyclopedia', 'B', '哥倫比亞歷史學院（國家學術機構）人物頁', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('api.oireachtas.ie', 'official_website', 'A', '愛爾蘭國會（Houses of the Oireachtas）議員資料 API', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('archives.senat.fr', 'official_website', 'A', '法國參議院圖書檔案處官方頁', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('archivo.presidencia.gub.uy', 'official_website', 'A', '烏拉圭總統府檔案官方頁', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('atom-museurepublica.museus.gov.br', 'archive', 'A', '巴西共和國博物館（IBRAM）檔案目錄', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('avoindata.eduskunta.fi', 'official_website', 'A', '芬蘭國會開放資料（議員資料）', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('biblioteca.parlamento.gub.uy:8008', 'official_website', 'A', '烏拉圭國會圖書館傳記查詢系統', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('country-studies.com', 'encyclopedia', 'B', '轉載美國國會圖書館 Federal Research Division 國家研究叢書；第三方轉載記 B', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('datom.colmex.mx', 'archive', 'B', 'El Colegio de México DATOM 檔案描述系統', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('documentacion.asambleanacional.gob.ec', 'official_history', 'B', '厄瓜多爾陸軍歷史研究中心《Historia general del Ejército ecuatoriano》（國會文獻庫收錄）', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('fapecft.org.mx', 'archive', 'B', 'Plutarco Elías Calles 與 Fernando Torreblanca 檔案基金會', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('guides.loc.gov', 'official_website', 'A', '美國國會圖書館研究指南', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('historiasuniversitarias.edu.uy', 'encyclopedia', 'B', '烏拉圭共和國大學 Historias Universitarias 人物條目', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('hoover.blogs.archives.gov', None, 'X', 'Hoover 總統圖書館部落格；主機名含 source-policy 禁用標籤 blogs（2026-11-17 誤歸類已更正，引用撤回）', "B3 v3 第二段寫庫後更正（source-policy bannedHostLabels）"),
    ('launiversidad.up.ac.pa', 'peer_reviewed', 'B', '巴拿馬大學官方刊物 La Universidad', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('orbilu.uni.lu', 'peer_reviewed', 'B', '盧森堡大學典藏庫 ORBilu 收錄之具名文章', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('portal.amelica.org', 'peer_reviewed', 'B', 'AmeliCA 學術期刊平台（Realidad，中美洲大學）', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('portalcris.vdu.lt', 'peer_reviewed', 'B', '維陶塔斯大學 CRIS 收錄之學術期刊論文（Istorija）', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('vdl.lu', 'official_website', 'A', '盧森堡市政府官方網站', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('www.bvfe.es', 'encyclopedia', 'B', 'Biblioteca Virtual de la Filología Española（馬德里康普頓斯大學）', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('www.fgv.br', 'encyclopedia', 'B', 'FGV CPDOC Dicionário Histórico-Biográfico Brasileiro（學術機構傳記辭典）', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('www.lituanistika.lt', 'peer_reviewed', 'B', 'Lituanistika 學術資料庫（期刊論文摘要頁）', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('www.lsim.lt', 'official_website', 'B', '立陶宛教育博物館（國家機構）具名文章', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('www.mg.gov.br', 'official_website', 'A', '巴西米納斯吉拉斯州政府官方網站', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('www.mindefensa.gov.co', 'official_website', 'A', '哥倫比亞國防部官方網站', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('www.monarchie.be', 'official_website', 'A', '比利時王室官方網站', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('www.museocostarica.go.cr', 'official_website', 'A', '哥斯大黎加國家博物館（文化部）', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('www.president.lv', 'official_website', 'A', '拉脫維亞總統府官方網站', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('www.presidentti.fi', 'official_website', 'A', '芬蘭總統府官方網站', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('www.saopaulo.sp.leg.br', 'official_website', 'A', '聖保羅市議會官方網站', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('www.scielo.org.mx', 'peer_reviewed', 'B', 'SciELO México 學術期刊（Relaciones，El Colegio de Michoacán）', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('www.senado.gov.co', 'official_website', 'A', '哥倫比亞參議院官方網站', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('www.silutevb.lt', 'official_website', 'B', '希盧泰公共圖書館（立陶宛公立機構）人物條目', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('www.sinabi.go.cr', 'official_website', 'A', '哥斯大黎加國家圖書館系統（www 主機名）', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('www.vestnesis.lv', 'official_website', 'B', 'Latvijas Vēstnesis（拉脫維亞官方公報出版社）具名文章', "B3 v3 第二段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('aktenreichskanzlei.bundesarchiv.de', 'official_record', 'A', '德國聯邦檔案館《Akten der Reichskanzlei》官方文件編纂', "B3 major-v2 batch001／005 寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('biography.wales', 'encyclopedia', 'A', '威爾斯國家圖書館 Dictionary of Welsh Biography（國家級傳記辭典）', "B3 major-v2 batch001／005 寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('bidenwhitehouse.archives.gov', 'official_website', 'A', '美國國家檔案館保存之白宮官網封存版', "B3 major-v2 batch001／005 寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-17「繼續處理」）"),
    ('bibliofep.fundacionempresaspolar.org', 'encyclopedia', 'B', 'Fundación Empresas Polar《Diccionario de Historia de Venezuela》具名條目（逐頁評等，部分 C）', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('www.royal.uk', 'official_website', 'A', '英國王室官方網站', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('sok.riksarkivet.se', 'encyclopedia', 'A', '瑞典國家檔案館 Svenskt biografiskt lexikon（國家級傳記辭典）', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('parlement.com', 'encyclopedia', 'B', 'Parlement.com（萊登大學 PDC／Montesquieu Instituut 人物條目）', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('www.parlement.com', 'encyclopedia', 'B', 'Parlement.com（同上，www 主機名）', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('nbl.snl.no', 'encyclopedia', 'B', 'Norsk biografisk leksikon／Store norske leksikon 具名條目', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('cpdoc.fgv.br', 'encyclopedia', 'B', 'FGV CPDOC Dicionário Histórico-Biográfico Brasileiro（學術機構傳記辭典）', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('www.mprs.mp.br', 'official_website', 'A', '巴西南大河州檢察署 Memorial 官方頁', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('sinabi.go.cr', 'official_website', 'A', '哥斯大黎加國家圖書館系統（文化部）', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('cambridge.org', 'peer_reviewed', 'B', 'Cambridge University Press 學術專書／期刊', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('www.chd.lu', 'official_website', 'A', '盧森堡國會（Chambre des Députés）官方頁', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('luxembourg.public.lu', 'official_website', 'A', '盧森堡政府新聞資訊處官方頁', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('sip.gouvernement.lu', 'official_website', 'A', '盧森堡國務部新聞資訊處官方頁', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('historisches-lexikon.li', 'encyclopedia', 'A', 'Historisches Lexikon des Fürstentums Liechtenstein（列支敦斯登研究所，國家級歷史辭典）', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('museu.presidencia.pt', 'official_website', 'A', '葡萄牙總統府博物館官方頁', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('www.bcn.cl', 'official_website', 'A', '智利國會圖書館（Biblioteca del Congreso Nacional）', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('www.memoriachilena.gob.cl', 'official_website', 'A', '智利國家圖書館 Memoria Chilena', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('journals.lib.unb.ca', 'peer_reviewed', 'B', 'International Hydrographic Review（UNB 期刊平台）', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('rec.gov.bt', 'official_history', 'A', '不丹王國政府皇家教育委員會《A History of Bhutan》官方教材', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('revistas.unanleon.edu.ni', 'peer_reviewed', 'B', 'Archivalia（UNAN-León 學術期刊）具名論文', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('encyklopedie.soc.cas.cz', 'encyclopedia', 'B', '捷克科學院社會學研究所 Sociologická encyklopedie 具名條目', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('www.parlament.gv.at', 'official_website', 'A', '奧地利國會官方頁', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('ojs.ehu.eus', 'peer_reviewed', 'B', 'Historia Contemporánea（巴斯克大學學術期刊）', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('www.argentina.gob.ar', 'official_website', 'A', '阿根廷總統府官方網站', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('www.casarosada.gob.ar', 'official_website', 'A', '阿根廷總統府 Casa Rosada 官方網站', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('www.kunaicho.go.jp', 'official_website', 'A', '日本宮內廳官方網站', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('origins.osu.edu', 'peer_reviewed', 'B', 'Origins（俄亥俄州立大學歷史系期刊）具名文章', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('old.lituanus.org', 'peer_reviewed', 'B', 'Lituanus 學術季刊具名文章', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('journals.lnb.lt', 'peer_reviewed', 'B', 'Parlamento studijos（立陶宛國家圖書館期刊平台）具名論文', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('ambassadehaiti-france.org', 'official_website', 'A', '海地駐法國大使館官方網站', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('archiwum.ipn.gov.pl', 'official_website', 'A', '波蘭國家記憶研究院（IPN）官方網站', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('www.presidencia.go.cr', 'official_website', 'A', '哥斯大黎加總統府官方網站', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('www.asamblea.gob.sv', 'official_record', 'A', '薩爾瓦多立法議會法令原文', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('kisebbsegkutato.tk.hu', 'peer_reviewed', 'B', '匈牙利研究機構具名專著', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('www.npshistory.com', 'archive', 'B', 'FDR 圖書館館藏文件編註本，放在第三方網站；原件 A，第三方副本記 B', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('www.whitehouse.gov', 'official_website', 'A', '美國白宮官方網站', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('www.govinfo.gov', 'official_record', 'A', '美國政府出版局 govinfo 官方出版品', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('www.fdrlibrary.org', 'official_website', 'A', 'FDR 總統圖書館（NARA）官方網站', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('nysl.nysed.gov', 'archive', 'A', '紐約州立圖書館《Public Papers of New York State Governors》', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('nysm.nysed.gov', 'official_website', 'A', '紐約州立博物館官方頁', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('cnhis.ncnu.edu.tw', 'peer_reviewed', 'B', '國立暨南國際大學歷史學系具名論文', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('www.prlib.ru', 'archive', 'A', '俄羅斯總統圖書館（Президентская библиотека）數位典藏', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('pravo.by', 'official_record', 'B', '白俄羅斯國家法律入口網轉錄之俄羅斯帝國基本法；原文 A，第三方轉錄記 B', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('www.hoover.org', 'peer_reviewed', 'B', 'Hoover Institution（史丹佛大學）Hoover Digest 具名文章', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('spbiiran.ru', 'peer_reviewed', 'B', 'Вестник архивиста 學術期刊具名論文', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('ejercito.defensa.gob.es', 'official_history', 'A', '西班牙陸軍（國防部）官方史', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('www.boe.es', 'official_record', 'A', '西班牙官方公報 BOE', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('boe.es', 'official_record', 'A', '西班牙官方公報 BOE（無 www 主機名）', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('www.congreso.es', 'official_website', 'A', '西班牙眾議院官方歷史頁', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('www5.tbmm.gov.tr', 'official_website', 'A', '土耳其大國民議會官方網站', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('cdn.tbmm.gov.tr', 'official_record', 'A', '土耳其大國民議會官方出版品', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('tbmm.gov.tr', 'official_website', 'A', '土耳其大國民議會官方網站', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
    ('atam.gov.tr', 'peer_reviewed', 'B', 'Atatürk Araştırma Merkezi（國家研究機構）具名論文', "B3 v3 第一段寫庫前未歸類網域，§16 T1 同一原則（Tai 2026-11-15「寫入」）"),
]

# 具名 C 級（Tai 本人 2026-11-12 06:34「將領生平來源放寬到具名 C 級」）：依每一頁的具名作者／具名出版機構判定，
# 不用網域白名單，所以不進 POLICY；規則另輸出 grade-c-policy.json，verify.py 對將領生平檔同步檢查。
GRADE_C = {
    "decision": "Tai 本人 2026-11-12 06:34（World Line 主管轉達）：將領生平來源放寬到具名 C 級",
    "scope": "只限將領生平（data/seed/leaders/generals-roster/bios；research.json 頂層 gradePolicy=ABC-2026-11-12）；B3 其他檔仍只收 A／B",
    "rule": "C＝具名作者或具名機構的正當出版物（主管 2026-11-12 22:08 重申；個人網站不算）（報紙／通訊社、大學、博物館、具名作者或出版者的軍事史網站、一般出版社書籍）；逐頁判定，sources.authors 或 publisher 至少一項非空，gradeBasis 寫出具名者",
    "always_forbidden": ["Wikipedia 及任何維基類（Wikiwand、Fandom 等）", "Wikidata", "百度", "無署名內容", "AI 生成內容站", "論壇／討論區／問答站", "部落格", "個人網站（除非由具名機構發布）", "generals.dk（個人網站；主管 2026-11-12 22:08 明列禁用）"],
    "banned_domains": [{"domain": "generals.dk", "decision": "主管 2026-11-12 22:08", "basis": "個人網站；具名 C＝具名作者或機構的正當出版物", "effective": "verify.py／apply_refill.py：生效後新增的來源一律擋；既有已 commit 引用暫不改，REFILL_REPORT 列待替換"}],
    "source_kind_hint": {"報紙／通訊社": "news", "大學／博物館": "official_website 或 encyclopedia（依頁面性質）", "軍事史網站": "encyclopedia"},
    "minimum_standard": "可只靠 C 達成 v3 最低標準；不可因缺 A／B 標來源不足",
    "t14": "T14 R2–R4 門檻（1 筆 A 或 2 筆獨立 B）不變；只有 C 支持者留 positions（必要時 R6 roleGap=source）",
    "db_note": "write_b3_paragraphs.py 目前會丟棄 grade 非 A/B 的 citation；寫庫前須由 Tai 決定 C 級如何入庫（不在本次範圍，未改）",
}

def main():
    ovr = json.loads(OVR.read_text(encoding="utf-8"))
    added = []
    for dom, kind, grade, basis, dec in POLICY:
        if dom in ovr:
            if ovr[dom] != kind:
                sys.exit(f"{dom} 已存在且值不同：{ovr[dom]!r} ≠ {kind!r}")
            continue
        ovr[dom] = kind; added.append(dom)
    OVR.write_text(json.dumps(dict(sorted(ovr.items())), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (HERE / "domain-policy.json").write_text(json.dumps([{"domain": d, "source_kind": k, "grade": g, "basis": b, "decision": x} for d, k, g, b, x in POLICY],
                                                      ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (HERE / "grade-c-policy.json").write_text(json.dumps(GRADE_C, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("added:", added or "none", "total overrides:", len(ovr))

if __name__ == "__main__":
    main()
