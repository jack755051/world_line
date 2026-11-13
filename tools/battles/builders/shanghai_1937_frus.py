"""shanghai_1937：新增獨立於 tw-roc 的來源家族 us-frus（美國國務院《Foreign Relations of the United States, 1937, The Far East》公開電報），
並把本輪（2026-11-13 主管 20:56「找中方資料」）查過但不可用／受阻的來源記成 gaps。
- 只用 history.state.gov 公開單篇文件頁（不登入、不繞過）；評 B：美國駐滬總領事 Gauss 同時代電報，戰況多據外國軍事觀察員，屬第三方紀錄、非參戰方檔案。
- 寫 battle.config.json（texts.readable／cite、sourceFamilies.map／frusNote）、sources.json、gaps.json（只追加、以 target 去重）。
用法：python3 -I tools/battles/builders/shanghai_1937_frus.py shanghai_1937（可重跑；之後跑 fetch_readable、r356、r4＋build_r4、五項檢查）
"""
import sys, json
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
if len(sys.argv) < 2 or sys.argv[1] != "shanghai_1937":
    raise SystemExit("用法：python3 -I tools/battles/builders/shanghai_1937_frus.py shanghai_1937")
D = REPO / "data/seed/battles/shanghai_1937"
DOCS = {  # key: (volume, doc, telegram date, Shanghai telegram no.)
 "frus1937v03-d590": ("v03", 590, "1937-09-14", "708"),
 "frus1937v03-d698": ("v03", 698, "1937-10-27", "893"),
 "frus1937v03-d709": ("v03", 709, "1937-11-01", "920"),
}
cp = D / "battle.config.json"; c = json.loads(cp.read_text())
sp = D / "sources.json"; s = json.loads(sp.read_text())
for k, (vol, n, d, no) in DOCS.items():
    url = f"https://history.state.gov/historicaldocuments/frus1937{vol}/d{n}"
    loc = f"FRUS 1937, The Far East, Vol. {'III' if vol == 'v03' else 'IV'}, Doc. {n}（Gauss 致國務卿電 No. {no}，{d}）"
    c["texts"]["readable"][k] = url
    c["texts"]["cite"][k] = {"kind": "single", "file": f"rd/{k}.txt", "locator": loc, "lang": "en"}
    c["sourceFamilies"]["map"][k] = "us-frus"
    s[k] = {"title": f"Foreign Relations of the United States, Diplomatic Papers, 1937, The Far East, Vol. {'III' if vol == 'v03' else 'IV'}, Document {n}",
            "authors": ["Clarence E. Gauss（美國駐上海總領事）"], "publisher": "U.S. Department of State, Office of the Historian（1954 年出版；線上 history.state.gov）",
            "url": url, "grade": "B", "family": "us-frus", "pageMethod": "history.state.gov 單篇文件頁",
            "gradeBasis": "同時代第三方官方電報（美國駐滬總領事）；戰況多據外國軍事觀察員與雙方發言，非參戰方原始檔案，評 B"}
c["sourceFamilies"]["frusNote"] = "us-frus（2026-11-13 主管 20:56 找中方獨立來源）：美國國務院 FRUS 公開電報，與 tw-roc（中華民國官方／國史館脈絡）及日方家族文本獨立；評 B。"
cp.write_text(json.dumps(c, ensure_ascii=False, indent=1) + "\n"); sp.write_text(json.dumps(s, ensure_ascii=False, indent=1) + "\n")
G = [
 ("source:國史館 drnh.gov.tw／ahonline.drnh.gov.tw", "source_unreachable", "2026-11-13 約 21:00 由 Tai 的 Mac 與 box 重試皆逾時（HTTP 000，15 秒）；未繞過"),
 ("source:中國第二歷史檔案館 shac.net.cn", "source_unreachable", "2026-11-13 約 21:00 連線失敗（HTTP 000）；已出版檔案彙編（如《中華民國史檔案資料匯編》《抗日戰爭正面戰場》）未見可公開閱讀之全文，不引用"),
 ("source:國防部史政編譯室公開 PDF（lib.mnd.gov.tw／modmhb.mnd.gov.tw）", "source_not_independent", "兩站 2026-11-13 連線失敗（HTTP 000）；且國防部戰史出版與 mnd2017 同屬 tw-roc 脈絡，即使取得也不能算獨立家族"),
 ("source:中研院近史所 mh.sinica.edu.tw 2015 何智霖、蘇聖雄〈初期重要戰役〉PDF", "source_not_independent", "可公開閱讀，但作者為國史館編者與 su2015 同一作者，據《陳誠回憶錄》、國史館檔等同一脈絡 → 歸 tw-roc，不算獨立家族"),
 ("source:中研院近史所 MHDB 近代史全文資料庫", "source_login_required", "需帳號登入；不登入、不繞過"),
 ("source:國立公共資訊圖書館 edata.nlpi.edu.tw《共赴國難─國共合作抗戰紀實》第四章", "source_grade_c", "可公開閱讀（大場 10/26 失守、27 日放棄北站江灣），但為通俗讀物、無出處註，評 C，不引用"),
 ("source:國家圖書館 臺灣記憶 tm.ncl.edu.tw", "source_not_searched", "可連線；館藏以臺灣主題為主，本輪未找到淞滬 1937 中方作戰紀錄，未深入檢索"),
 ("source:《抗日戰爭研究》等大陸期刊（CNKI）", "source_login_required", "全文需登入／付費；不登入、不繞過"),
 ("source:FRUS 1937 Vol. III d480–d800、Vol. IV d380–d540（Shanghai 電報）", "source_partial", "已掃描：可佐證 9/14 羅店—北站線、10/26 大場失守與當夜閘北撤退、10/30 夜閘北守軍被逐；未載中方部隊番號、指揮官與吳興（湖州）易手，R1／R7 中方資料仍只有 tw-roc"),
]
gp = D / "gaps.json"; g = json.loads(gp.read_text()); have = {x["target"] for x in g["gaps"]}; n = 0
for t, kind, note in G:
    if t in have: continue
    g["gaps"].append({"target": t, "kind": kind, "note": note, "checkedOn": "2026-11-13", "tool": "tools/battles/builders/shanghai_1937_frus.py"}); n += 1
gp.write_text(json.dumps(g, ensure_ascii=False, indent=1) + "\n")
print("ok sources", list(DOCS), "gaps added", n)
