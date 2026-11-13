# 淞滬 1937 線上史料改道：進度（暫停於 2026-11-13 20:23，主管 20:22 改先做波蘭）

取代 MANUAL-SOURCES.md 的圖書館取頁路線（Tai 不拍照）。本檔只記錄已查到的線上來源與缺口；尚未改動任何 builder、資料或檢查數字（仍為 35/74/72）。

## 已查到、可用（JACAR 目錄頁「内容」欄，jp-jacar 家族，A；尚未寫入 sources.json）
- C11111926900 歩兵第34連隊 大場鎮附近戦闘詳報「戦闘及戦闘成果ノ概要」：十月二十五日「同日正午頃敵ノ主陣地ヲ奪取シタリ」、「二十七日蘇州河ニ敵ヲ圧迫セリ」。未明載大場鎮陷落日 → 大場仍維持「十月下旬」裁示（10/25、10/26 皆為候選）。
- C11111935000 歩兵第38連隊 滸浦鎮附近戦闘詳報第1号（11/14–15）：情報「佐々木支隊ハ本十三日重藤兵団ニ続イテ上陸シ」。支持重藤兵團、佐佐木支隊 11/13（或之前）登陸，但未出現「白茆口」地名，且同段轉錄作「十二月十三日夜徐六経口沖ニ着」（月份與標題 11/14–15 矛盾）→ 白茆口日期仍留空，11/13 候選加此 A 級旁證。
- 其他可引內容欄：C11111751300／C11111967600（第9師団作戦経過 第2章）、C11111803500（歩68 I 大場鎮）、C11111812400（歩68 III 大場鎮）、C11111855500/855600（独立攻城重砲兵第2大隊 11/10–15、上軍作命甲第172号）、C11111920500（中支方面地上作戦経過 目次，含「第十六師団、重藤支隊ノ白茆口上陸」章名）。
- 限制：JACAR 内容欄只轉錄約 300 字；全文需看影像（未做 OCR）。

## 缺口（不繞過）
- NIDS 戦史叢書 086 全文（SoshoView?kanno=086）：「メンテナンス中」並有 JS 指紋反機器人腳本。
- 國史館 www.drnh.gov.tw、ahonline.drnh.gov.tw：2026-11-13 約 20:20 連線逾時（HTTP 000／504）。事略稿本 40 補編無線上 PDF。
- 中研院 MHDB（近代史全文資料庫，含中華民國史事日誌）：需帳號登入。
- 近史所檔案館 archives.sinica.edu.tw：可連線，但館藏以外交／經濟檔為主，未完成檢索即暫停。
- JACAR 中方鹵獲文件：檢索未找到淞滬戰役的中方命令譯文。
- 結論（暫停時）：尚無獨立於 tw-roc 的中方 A/B 家族；中方事實維持 B→C。

## 剩餘工作
1. 將上列 JACAR 條目加入 config texts.readable/cite 與 sources.json（jp-jacar，A），fetch_readable 抓取。
2. builders 加引文與日期旁證；gaps builder 追加上列缺口。
3. 重跑 verify_quotes / crosscheck / mark_fields，對照 35/74/72。
4. MANUAL-SOURCES.md 以補丁標作廢並指向本檔（已加作廢註記）。

成本：此輪 claude -p $0；淞滬累計 $1.76（上限 $15）。

## 恢復（2026-11-13 20:56 主管／Tai：找資料；不寫庫）
- JACAR C11111926900、C11111935000 以 builder `tools/battles/builders/shanghai_1937_jacar2.py` 加入（jp-jacar，A），引文加在大場鎮（R5／R6）與白茆口候選旁證（R3／R5／R6）、重藤支隊（R1）；五項檢查重跑後仍為 35/74/72（同屬 jp-jacar 家族，且所掛紀錄原本已是多家族或同家族）。commit b220a68。
- 新獨立家族 **us-frus**（評 B）：美國國務院 FRUS 1937 The Far East 公開單篇文件頁，builder `tools/battles/builders/shanghai_1937_frus.py`。
  - Vol. III Doc. 590（9/14 電）：羅店—北站線 → R4 cn-front-1937-09-14。
  - Vol. III Doc. 698（10/27 電）：前夜攻占大場、閘北—江灣全面撤退、晨見北站日旗 → R6 閘北、R6 大場鎮、R5 閘北八百壯士。
  - Vol. III Doc. 709（11/1 電）：30 日夜閘北守軍被逐、300 人退入英軍防線 → R5 閘北八百壯士（止日只作候選 10/30，與通說不一）。
- 中方紀錄升級：R5 zhabei-800、R6 閘北 由 C（tw-roc 單一來源降級）→ B 已查證；R4 9/14 國軍守勢線 C → B（前線仍為推估、待查證）。日方 R6 大場鎮 → A 已查證（日期欄依 Q6 不改；FRUS 指 10/26，待主管裁示）。
- 檢查：已查證 38、單一來源 70、單一且只有 B（降 C）69（原 35/74/72）；引文 261 筆全 verbatim。
- 缺口（gaps.json，tool=shanghai_1937_frus.py，9 筆）：國史館逾時、二檔館連不上且彙編無公開全文、國防部史政站連不上且屬 tw-roc、近史所 2015 何智霖／蘇聖雄 PDF 屬 tw-roc、MHDB 需登入、nlpi《共赴國難》為 C、臺灣記憶未見淞滬中方紀錄、CNKI 需登入、FRUS 未載中方番號／指揮官／吳興。
- 仍無：中方 R1 部隊（26）、R7 指揮官（13）、R7 待補人物（5）的獨立家族。
- 成本：claude -p $0；淞滬累計 $1.76（上限 $15）。

## 主管 2026-11-13 21:24 裁示與寫庫前準備（不寫庫）
- 裁示寫入 `shanghai_1937_rulings.py`（rulings["2026-11-13 21:24"]，含逐筆 overrides，由 r356 builder 套用）：
  (a) 大場鎮日期改 1937-10-26，只由 FRUS 支持 → `confidenceRuling.basisFamilies=["us-frus"]`（crosscheck.py 新支援），待查證、單一來源、有效等級 C；「十月下旬」留在 dateNote／dateRange。
  (b) 閘北八百壯士：10/30 只作 endCandidate，寫入 conflict，period.end 留空。(c) 波蘭 9/1 標籤不處理。
- 五項檢查（crosscheck 以 --apply 重寫各檔 confidence；前兩輪 b220a68／181258e 漏了 --apply，本次一併補回）：已查證 37、單一來源 71、單一且只有 B（降 C）70；引文 261 筆全 verbatim。
- 寫庫準備：`shanghai_1937_dbconfig.py`（db.sideRegimes：axis＝empire-of-japan、allied＝republic-of-china-nationalist）、`osm_coords.py`（補 20 個座標）、`write_battle_sql.py shanghai_1937`、`db_write.py shanghai_1937` dry-run（交易內 ROLLBACK；之後重數：未留下任何列）。報告見 `db/`。實寫待 Tai 另行同意。
