#!/usr/bin/env python3
"""舊格式人物生平（gap-830／batch-p1-20261107）出處補等級（來源規則 I6／D4；Tai 2026-11-14 選「依建議」＝做法 3）。

舊格式的出處直接內嵌在欄位裡（url、title、publisher、sourceKind），沒有作者欄。依網域評等：
- 先用主管既有決定（b3-trial/full/domain-policy.json，2026-11-11～14）；
- 其餘照同一尺度（下方 GRADES）：政府／議會／總統府／國家檔案館／權威人名檔／國家級傳記辭典＝A；
  具名學術期刊、學術機構與資料庫＝B；博物館介紹、新聞、一般機構網站＝C；個人網站與私人彙編＝X；
  第三方轉錄或鏡像且原件是 A 者記 B；web.archive.org 依原網址的網域評。
- 一般百科（同站有署名與不署名條目，B／C 要逐頁看作者）不評，加 gradePending 說明，留待逐頁確認。
X 級出處不刪（舊格式欄位可能只有這一筆），只標 X；稽核與寫庫程式會把 X 視為不可當出處。
用法（repo 根目錄）：python3 -I data/seed/leaders/gap-830/apply_source_grades.py [--apply]
"""
import json, glob, sys, collections
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parents[4]
RUN = "old-format-grade-2026-11-14"
POLICY = {x["domain"].lower(): x for x in json.loads((REPO / "data/seed/leaders/b3-trial/full/domain-policy.json").read_text())}

PENDING = {  # 同站署名與不署名條目並存：B／C 需逐頁確認具名作者
    "www.encyclopedia.com", "encyclopedia.com", "www.vle.lt", "vle.lt", "snl.no", "lex.dk", "www.encyclopediaofukraine.com",
    "encyclopediaofukraine.com", "www.enciclopedia.cat", "enciclopedia.cat",
}
A_ = "A"; B_ = "B"; C_ = "C"; X_ = "X"
GRADES = {
    # 權威人名檔／國家級傳記辭典與百科
    "d-nb.info": (A_, "德國國家圖書館 GND 人名權威檔"), "catalogue.bnf.fr": (A_, "法國國家圖書館目錄／人名權威"),
    "www.idref.fr": (A_, "法國高教書目中心 IdRef 人名權威檔"), "hls-dhs-dss.ch": (A_, "瑞士歷史辭典（國家級，具名作者）"),
    "www.deutsche-biographie.de": (A_, "Deutsche Biographie（NDB／ADB，巴伐利亞科學院歷史委員會）"),
    "kansallisbiografia.fi": (A_, "芬蘭國家傳記（Kansallisbiografia，SKS）"), "historia-hispanica.rah.es": (A_, "西班牙皇家歷史學院 Diccionario Biográfico Español"),
    "biografiskleksikon.lex.dk": (A_, "丹麥傳記辭典（Dansk Biografisk Leksikon）"), "nbl.snl.no": (A_, "挪威人物辭典（Norsk biografisk leksikon，具名作者）"),
    "sok.riksarkivet.se": (A_, "瑞典國家檔案館（含 Svenskt biografiskt lexikon）"), "historisches-lexikon.li": (A_, "列支敦斯登歷史辭典（國家級）"),
    "www.kaowarsom.be": (A_, "比利時皇家海外科學院 Biographie Belge d'Outre-Mer"), "mek.oszk.hu": (A_, "匈牙利國家圖書館 MEK 數位版《Magyar Életrajzi Lexikon》（國家級傳記辭典）"),
    "www.georgianencyclopedia.ge": (A_, "喬治亞百科（喬治亞國家科學院編纂）"), "dichp.bnportugal.gov.pt": (A_, "葡萄牙國家圖書館 Dicionário de Historiadores Portugueses"),
    # 政府、議會、王室／總統府、國家檔案館、官方公報
    "cdn.www.gob.pe": (A_, "秘魯政府官方文件"), "history.state.gov": (A_, "美國國務院史政室"), "www.museu.presidencia.pt": (A_, "葡萄牙總統府博物館（總統府官方）"),
    "www.vestnesis.lv": (A_, "拉脫維亞官方公報"), "download.data.public.lu": (A_, "盧森堡政府開放資料"), "www.parlament.gv.at": (A_, "奧地利國會"),
    "valitsus.ee": (A_, "愛沙尼亞政府"), "arquivo.presidencia.pt": (A_, "葡萄牙總統府檔案"), "www.arquivo.presidencia.pt": (A_, "葡萄牙總統府檔案"),
    "www.president.lv": (A_, "拉脫維亞總統府"), "president.lv": (A_, "拉脫維亞總統府"), "mzv.gov.cz": (A_, "捷克外交部"), "www.congreso.es": (A_, "西班牙國會"),
    "monarchie.lu": (A_, "盧森堡大公室官方網站"), "www.monarchie.lu": (A_, "盧森堡大公室官方網站"), "valtioneuvosto.fi": (A_, "芬蘭政府"),
    "www.forseti.is": (A_, "冰島總統府"), "www.vatican.va": (A_, "聖座官方網站"), "www.presidentti.fi": (A_, "芬蘭總統府"), "www.stjornarradid.is": (A_, "冰島政府"),
    "ambassadehaiti-france.org": (A_, "海地駐法大使館（政府）"), "avoindata.eduskunta.fi": (A_, "芬蘭國會開放資料"), "sip.gouvernement.lu": (A_, "盧森堡政府新聞資訊處"),
    "libr.sejm.gov.pl": (A_, "波蘭眾議院圖書館"), "european-union.europa.eu": (A_, "歐盟官方網站"), "www.ra.ee": (A_, "愛沙尼亞國家檔案館"),
    "mfa.gov.az": (A_, "亞塞拜然外交部"), "president.ee": (A_, "愛沙尼亞總統府"), "www.icm.gov.mo": (A_, "澳門特區政府文化局"), "www.milliarxiv.gov.az": (A_, "亞塞拜然國家檔案局"),
    "www.portugal.gov.pt": (A_, "葡萄牙政府"), "portugal.gov.pt": (A_, "葡萄牙政府"), "www.archivonacional.go.cr": (A_, "哥斯大黎加國家檔案館"),
    "binal.ac.pa": (A_, "巴拿馬國家圖書館"), "www.kunaicho.go.jp": (A_, "日本宮內廳"), "www.gov.ie": (A_, "愛爾蘭政府（總理府）"), "www.nacr.cz": (A_, "捷克國家檔案館"),
    "preslib.az": (A_, "亞塞拜然總統府圖書館"), "www.dziejesejmu.pl": (A_, "波蘭眾議院辦公廳"), "1920.gov.pl": (A_, "波蘭新檔案館（AAN）官方入口"),
    "eng.ipn.gov.pl": (A_, "波蘭國家記憶研究院（比照 ipn.gov.pl）"), "www.presidencia.pt": (A_, "葡萄牙總統府"), "www.pj.gov.py": (A_, "巴拉圭司法院"),
    "expinterweb.mites.gob.es": (A_, "西班牙勞動部中央檔案"), "imprensanacional.pt": (A_, "葡萄牙國家印務局"), "www.ktb.gov.tr": (A_, "土耳其文化觀光部"),
    "fuerstenhaus.li": (A_, "列支敦斯登親王室官方網站"), "ambasadat.gov.al": (A_, "阿爾巴尼亞駐外使領館（政府）"), "archives.government.bg": (A_, "保加利亞國家檔案局"),
    "mfa.bg": (A_, "保加利亞外交部"), "journaldemonaco.gouv.mc": (A_, "摩納哥政府公報"), "memoriahistorica.senadord.gob.do": (A_, "多明尼加參議院"),
    "www.tse.go.cr": (A_, "哥斯大黎加最高選舉法院"), "www.icj-cij.org": (A_, "國際法院官方網站"), "www.tirol.gv.at": (A_, "提洛邦政府"), "gov.ro": (A_, "羅馬尼亞政府"),
    "www.bccr.fi.cr": (A_, "哥斯大黎加中央銀行"), "www.kungligaslotten.se": (A_, "瑞典王室官方網站"), "www.monarchie.be": (A_, "比利時王室官方網站"),
    "www.vdl.lu": (A_, "盧森堡市政府"), "malmo.se": (A_, "瑪律默市政府"), "www.roscommoncoco.ie": (A_, "羅斯康芒郡議會"), "www.asuncion.gov.py": (A_, "亞松森市政府"),
    "intezet.nori.gov.hu": (A_, "匈牙利國家遺產研究所（國家公墓）"), "atom.hunabyggd.is": (A_, "冰島地區公共檔案館人名權威紀錄"),
    "www.congreso.gob.pe": (A_, "秘魯國會（國會博物館具名專文）"), "www.valitsus.ee": (A_, "愛沙尼亞政府"),
    "www.nato.int": (A_, "北約官方網站（歷任秘書長）"), "patriarhia.ro": (A_, "羅馬尼亞東正教牧首區官方網站（歷任牧首）"),
    "encykorea.aks.ac.kr": (A_, "韓國學中央研究院《韓國民族文化大百科》（國家級，具名作者）"),
    "vlex.com.pe": (B_, "vLex 法律資料庫收錄之官方法令（第三方轉錄，原件 A 記 B）"), "aman.ro": (C_, "Aman 博物館（克拉約瓦）介紹頁"),
    # batch-p1-20261107（roc／su-tr／us-es.json）
    "ataturkansiklopedisi.gov.tr": (A_, "Atatürk Ansiklopedisi（土耳其 Atatürk 研究中心，國家機構編纂）"),
    "sunology.yatsen.gov.tw": (A_, "國立國父紀念館（政府機關）"), "museum.mof.gov.tw": (A_, "財政部財政史料陳列室（政府機關）"),
    "www.tccb.gov.tr": (A_, "土耳其總統府"), "guides.loc.gov": (A_, "美國國會圖書館研究指南"), "www.tbmm.gov.tr": (A_, "土耳其大國民議會"),
    "hoover.archives.gov": (A_, "胡佛總統圖書館（NARA）"), "www.fdrlibrary.org": (A_, "羅斯福總統圖書館（NARA）"), "www.mfa.gov.tr": (A_, "土耳其外交部"),
    "www.ly.gov.tw": (A_, "立法院"), "dict.revised.moe.edu.tw": (A_, "教育部《重編國語辭典修訂本》"), "www.basbakanlik.gov.tr": (A_, "土耳其總理府（已停用網站）"),
    "museopresidentes.org.mx": (C_, "Museo de los Presidentes Coahuilenses（博物館出版品）"), "www.gobiernoenlinea.ve": (A_, "委內瑞拉政府入口網站（存檔）"),
    "www.knowbysight.info": (C_, "網站轉載之《Справочник по истории КПСС и Советского Союза 1898–1991》；編者與授權待確認，保守記 C"),
    # 學術機構、期刊、學術資料庫
    "www.parlement.com": (B_, "萊頓大學議會文獻中心（PDC）"), "islamansiklopedisi.org.tr": (B_, "TDV İslâm Ansiklopedisi（具名學者條目）"),
    "tekst.devb.be": (B_, "Nieuwe Encyclopedie van de Vlaamse Beweging（具名作者學術百科）"), "cbdb.fas.harvard.edu": (B_, "哈佛中國歷代人物傳記資料庫（學術資料庫）"),
    "www.biolex.ios-regensburg.de": (B_, "雷根斯堡東南歐研究所傳記辭典（具名作者）"), "impactum-journals.uc.pt": (B_, "科英布拉大學學術期刊"),
    "portal.ehri-project.eu": (B_, "EHRI 歐洲大屠殺研究基礎設施檔案著錄"), "pdba.georgetown.edu": (B_, "喬治城大學拉美研究中心政治資料庫"),
    "www.journalbelgianhistory.be": (B_, "比利時當代史學報"), "ylioppilasmatrikkeli.fi": (B_, "赫爾辛基大學學生名冊（大學紀錄）"),
    "cedoc.sisbib.unmsm.edu.pe": (B_, "聖馬爾科斯大學文獻中心"), "collections.ascsa.edu.gr": (B_, "雅典美國古典研究學院 Gennadius 圖書館檔案"),
    "www.cidob.org": (B_, "CIDOB 研究中心具名人物傳記"), "journals.lib.unb.ca": (B_, "International Hydrographic Review（學術期刊）"),
    "repositorio.ulisboa.pt": (B_, "里斯本大學機構典藏"), "real.mtak.hu": (B_, "匈牙利科學院典藏庫"), "375humanistia.helsinki.fi": (B_, "赫爾辛基大學文學院具名專文"),
    "nepalica.hadw-bw.de": (B_, "海德堡科學院 Nepalica 計畫"), "www.flu.cas.cz": (B_, "捷克科學院哲學研究所"), "ego-plone.uni-trier.de": (B_, "萊布尼茲歐洲史研究所 EGO"),
    "archivo.revistas.ucr.ac.cr": (B_, "哥斯大黎加大學史學期刊"), "cis01.central.ucv.ro": (B_, "克拉約瓦大學政治學期刊"), "e-aoi.uzh.ch": (B_, "蘇黎世大學亞洲東方研究所"),
    "journal.fi": (B_, "芬蘭歷史學會期刊 Ennen ja nyt"), "doi.org": (B_, "基輔大學學報（DOI 學術論文）"), "repositorio.ucp.pt": (B_, "葡萄牙天主教大學機構典藏（具名論文）"),
    "helda.helsinki.fi": (B_, "赫爾辛基大學機構典藏"), "www.rcin.org.pl": (B_, "波蘭科學院歷史研究所出版之部長會議紀錄"), "www.biblos.pk.edu.pl": (B_, "克拉科夫工業大學圖書館"),
    "atom-2.rbge.org.uk": (B_, "愛丁堡皇家植物園檔案館人名權威紀錄（比照 b3 rbge-wangchuck）"), "istanbulansiklopedisi.org": (B_, "İstanbul Ansiklopedisi（Kadir Has 大學，具名學術條目）"),
    # 第三方轉錄／鏡像（原件 A 記 B）
    "countrystudies.us": (B_, "美國國會圖書館國別研究的第三方鏡像（原件 A，轉錄記 B）"), "www.leybook.com": (B_, "尼加拉瓜官方公報條文的第三方轉錄（原件 A，轉錄記 B）"),
    "ikon.mn": (B_, "新聞站轉錄 1924 年蒙古憲法原文（原件 A，轉錄記 B）"),
    # 具名機構但不到 B：博物館介紹、新聞、一般機構網站
    "www.bta.bg": (C_, "保加利亞通訊社（新聞）"), "history.ru": (C_, "俄羅斯軍事歷史學會網站"), "www.portalguarani.com": (C_, "Portal Guaraní（轉載出版書籍內容）"),
    "hhjyy.tjl.tj.cn": (C_, "天津圖書館文化資訊網人物介紹"), "www.kudyznudy.cz": (C_, "捷克觀光局"), "cardinals.fiu.edu": (C_, "FIU 圖書館收錄之 Salvador Miranda 樞機名錄"),
    "sajurin.enriquebolanos.org": (C_, "Fundación Enrique Bolaños 數位化期刊"), "www.cnn.gr": (C_, "CNN Greece（新聞）"), "www.hoy.com.py": (C_, "Hoy（新聞）"),
    "www.abc.com.py": (C_, "ABC Color（新聞）"), "www.laestrella.com.pa": (C_, "La Estrella de Panamá（新聞，具名作者）"), "www.prensalibre.com": (C_, "Prensa Libre（新聞）"),
    "www.biografiasyvidas.com": (C_, "Biografías y Vidas（具名出版機構）"), "www.bbs.bt": (C_, "不丹國家廣播公司（新聞）"), "www.hungarianarchives.org": (C_, "美國匈牙利圖書館與史學會"),
    "royalfamily.org": (C_, "塞爾維亞王室辦公室網站（非政府）"), "explore.moadoph.gov.au": (C_, "澳洲民主博物館介紹頁"), "www.galeriadelascoleccionesreales.es": (C_, "西班牙皇家收藏館介紹頁"),
    "peles.ro": (C_, "佩萊什國家博物館介紹頁"), "envechi.peles.ro": (C_, "佩萊什國家博物館介紹頁"), "www.helsinki.fi": (C_, "赫爾辛基大學博物館介紹頁"),
    "www.uned.es": (C_, "UNED 共濟會歷史虛擬博物館介紹頁"), "manioc.org": (C_, "Manioc 數位圖書館收錄之舊版歷史教科書"), "www.manioc.org": (C_, "Manioc 數位圖書館收錄之舊版歷史教科書"),
    "beta-omk.manioc.org": (C_, "Manioc 數位圖書館收錄之舊版歷史教科書"),
    # 個人網站／私人彙編
    "www.catholic-hierarchy.org": (X_, "個人網站（David M. Cheney）"), "www.archontology.org": (X_, "私人彙編（比照 rulers.org）"),
}


def grade_for(url):
    h = (urlparse(url or "").hostname or "").lower()
    if h == "web.archive.org":  # 依原網址評
        inner = (url or "").split("/web/", 1)[-1].split("/", 1)[-1]
        g = grade_for(inner)
        return (g[0], "web.archive.org 存檔原頁；" + g[1]) if g else None
    for k in (h, h.removeprefix("www."), "www." + h):
        if k in PENDING:
            return "PENDING", None
        if k in POLICY and POLICY[k].get("grade"):
            return POLICY[k]["grade"], "主管既有網域決定：" + POLICY[k]["basis"]
        if k in GRADES:
            return GRADES[k]
    return None


def main():
    apply = "--apply" in sys.argv
    files = sorted(glob.glob(str(REPO / "data/seed/leaders/gap-830/*/research.json")) +
                   glob.glob(str(REPO / "data/seed/leaders/batch-p1-20261107/**/research.json"), recursive=True) +
                   [str(REPO / "data/seed/leaders/batch-p1-20261107" / n) for n in ("roc.json", "su-tr.json", "us-es.json", "death-precision.json")])
    stat, unknown = collections.Counter(), collections.Counter()
    for f in files:
        raw = Path(f).read_text(); d = json.loads(raw)
        def walk(o):
            if isinstance(o, dict):
                if "url" in o and "sourceKind" in o and "grade" not in o:
                    g = grade_for(o["url"])
                    if g is None:
                        unknown[(urlparse(o["url"] or "").hostname or "")] += 1
                    elif g[0] == "PENDING":
                        o["gradePending"] = "同站署名與不署名條目並存，B／C 需逐頁確認具名作者（%s）" % RUN; stat["pending"] += 1
                    else:
                        o["grade"], o["gradeBasis"] = g[0], g[1] + "（%s）" % RUN; stat[g[0]] += 1
                for v in o.values(): walk(v)
            elif isinstance(o, list):
                for v in o: walk(v)
        walk(d)
        if apply:
            ind = 2 if raw.startswith("{\n  ") else 1
            Path(f).write_text(json.dumps(d, ensure_ascii=False, indent=ind) + ("\n" if raw.endswith("\n") else ""))
    print(json.dumps({"apply": apply, "graded": dict(stat), "unknown_hosts": dict(unknown)}, ensure_ascii=False, indent=1))
    return 1 if unknown else 0


if __name__ == "__main__":
    sys.exit(main())
