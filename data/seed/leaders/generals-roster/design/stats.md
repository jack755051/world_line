# 人物事實分層：佐證統計（2026-11-12T21:41:42+08:00）

快照；主迴圈已於 2026-11-12 21:29 結束（commit 52fd188）。min-check 以 check_min.check() 對現行 research.json 重算（不讀 retry 前的 min-check.json）。網域以引文（paragraph／position／roleCandidate citations）計，people＝至少一筆引文用到該網域的人數。費用含 .dev/cc-generals-*.json＋cc-person-facts-design.json＋cc-person-facts-estimate.json（若已存在）。

research.json 檔數：73

## min-check

- S：102 人（列 102；重複鍵 []），達標 44，未達標 58（已標來源不足 58，未標 0）；任期完整 323/413（缺迄待查 85、缺起或迄 5）；無戰役 23；無指揮職 10
  - 扣已知重複（['chesternimitz']）：101 人，達標 44，未達標 57
  - 未達標原因（可重複）：{'職位缺起訖': 46, '字數<300': 7, '無指揮職': 10, '無戰役': 23, '段落<3': 4}
  - 原因組合：{'職位缺起訖': 30, '職位缺起訖+無戰役': 10, '無戰役': 6, '段落<3+字數<300+無指揮職+無戰役': 4, '職位缺起訖+無指揮職+無戰役': 2, '職位缺起訖+無指揮職': 2, '字數<300+無指揮職': 1, '字數<300+職位缺起訖': 1, '無指揮職': 1, '字數<300+職位缺起訖+無戰役': 1}
- A：256 人（列 256；重複鍵 []），達標 104，未達標 152（已標來源不足 152，未標 0）；任期完整 846/1137（缺迄待查 263、缺起或迄 28）；無戰役 43；無指揮職 15
  - 扣已知重複（['小泽治三郎']）：255 人，達標 103，未達標 152
  - 未達標原因（可重複）：{'職位缺起訖': 126, '字數<300': 7, '無指揮職': 15, '無戰役': 43, '段落<3': 3}
  - 原因組合：{'職位缺起訖': 104, '職位缺起訖+無戰役': 18, '無戰役': 13, '無指揮職': 4, '無指揮職+無戰役': 4, '段落<3+字數<300+無指揮職+無戰役': 3, '字數<300+無指揮職+無戰役': 2, '字數<300+職位缺起訖+無戰役': 2, '職位缺起訖+無指揮職+無戰役': 1, '職位缺起訖+無指揮職': 1}
- S 名單中沒有 min-check 的人：['heinzguderian']
- min-check.json（retry 前）與重算結果不同：22 人（Counter({'A': 19, 'S': 3})）：['A/batch006 maximilianvonweichs', 'A/batch010 sirwilliamrobertson1stbaronet', 'A/batch017 thomasckinkaid', 'A/batch017 frankjackfletcher', 'A/batch017 terrydelamesaallensr', 'A/batch021 matomeugaki', 'A/batch021 rikichiando', 'A/batch021 小泽治三郎', 'A/batch021 jisaburoozawa', 'A/batch021 kuniakikoiso', 'A/batch022 yamagata', 'A/batch028 沈鴻烈', 'A/batch031 chenmingshu', 'A/batch045 edmundherring', 'A/batch047 arthurconingham', 'A/batch048 keithpark', 'A/batch048 αλεξανδροςπαπαγος', 'A/batch049 ναπολεωνζερβας', 'A/batch049 conradhelfrich', 'S/batch001 erwinrommel', 'S/batch006 albertkesselring', 'S/batch006 herbertkitchener1stearlkitchener']

## 費用

- 合計 USD 205.9376
- 分類：{'A-retry': {'files': 30, 'usd': 55.3426}, 'A-sonnet': {'files': 59, 'usd': 91.0038}, 'S-retry': {'files': 12, 'usd': 17.9307}, 'S-sonnet': {'files': 22, 'usd': 36.5628}, 'insuff-S-sonnet': {'files': 2, 'usd': 1.8818}, 'other:cc-generals-roster.json': {'files': 1, 'usd': 1.4243}, 'other:cc-person-facts-design.json': {'files': 1, 'usd': 1.6258}, 'other:cc-person-facts-estimate.json': {'files': 1, 'usd': 0.1657}}
- 每人平均（主迴圈 sonnet＋retry）：S 0.5343、A 0.5717

## 各國籍網域命中（前 12，依人數）

### 其他（59 人）

| 網域 | 引文 | A | B | C | 人數 | 覆蓋率 |
|---|---|---|---|---|---|---|
| kotobank.jp | 155 | 0 | 99 | 56 | 11 | 19% |
| blf.fi | 281 | 281 | 0 | 0 | 9 | 15% |
| uppslagsverket.fi | 67 | 0 | 0 | 67 | 5 | 8% |
| rul.fi | 53 | 0 | 0 | 53 | 5 | 8% |
| generals.dk | 15 | 0 | 0 | 15 | 5 | 8% |
| resources.huygens.knaw.nl | 126 | 126 | 0 | 0 | 4 | 7% |
| deutsche-biographie.de | 66 | 66 | 0 | 0 | 4 | 7% |
| encyclopedia.com | 15 | 0 | 14 | 1 | 4 | 7% |
| history.state.gov | 10 | 10 | 0 | 0 | 4 | 7% |
| dergipark.org.tr | 63 | 0 | 12 | 51 | 3 | 5% |
| ipn.gov.pl | 54 | 54 | 0 | 0 | 3 | 5% |
| biographien.ac.at | 36 | 36 | 0 | 0 | 3 | 5% |

### 中國（59 人）

| 網域 | 引文 | A | B | C | 人數 | 覆蓋率 |
|---|---|---|---|---|---|---|
| gpost.lib.nccu.edu.tw | 281 | 0 | 281 | 0 | 22 | 37% |
| cpc.people.com.cn | 601 | 89 | 0 | 512 | 19 | 32% |
| kotobank.jp | 244 | 0 | 228 | 16 | 18 | 30% |
| mh.sinica.edu.tw | 95 | 15 | 80 | 0 | 13 | 22% |
| drnh.gov.tw | 39 | 11 | 28 | 0 | 11 | 19% |
| dangshi.people.com.cn | 48 | 0 | 0 | 48 | 7 | 12% |
| mnd.gov.tw | 67 | 26 | 15 | 26 | 6 | 10% |
| xboorman.enpchina.eu | 84 | 0 | 84 | 0 | 4 | 7% |
| twstudy.iis.sinica.edu.tw | 10 | 9 | 1 | 0 | 3 | 5% |
| history.state.gov | 3 | 3 | 0 | 0 | 3 | 5% |
| sdaj.hunan.gov.cn | 25 | 25 | 0 | 0 | 2 | 3% |
| ahonline.drnh.gov.tw | 24 | 24 | 0 | 0 | 2 | 3% |

### 德國（51 人）

| 網域 | 引文 | A | B | C | 人數 | 覆蓋率 |
|---|---|---|---|---|---|---|
| deutsche-biographie.de | 1191 | 1191 | 0 | 0 | 47 | 92% |
| dhm.de | 577 | 0 | 577 | 0 | 26 | 51% |
| bundesarchiv.de | 23 | 23 | 0 | 0 | 6 | 12% |
| biographien.ac.at | 34 | 34 | 0 | 0 | 3 | 6% |
| apps.bundesarchiv.de | 25 | 25 | 0 | 0 | 3 | 6% |
| lobid.org | 14 | 14 | 0 | 0 | 3 | 6% |
| treccani.it | 18 | 0 | 18 | 0 | 2 | 4% |
| avalon.law.yale.edu | 13 | 0 | 2 | 11 | 2 | 4% |
| warfarehistorynetwork.com | 10 | 0 | 9 | 1 | 2 | 4% |
| open-data.bundesarchiv.de | 2 | 2 | 0 | 0 | 2 | 4% |
| open.ifz-muenchen.de | 52 | 0 | 52 | 0 | 1 | 2% |
| snl.no | 21 | 0 | 21 | 0 | 1 | 2% |

### 英國（42 人）

| 網域 | 引文 | A | B | C | 人數 | 覆蓋率 |
|---|---|---|---|---|---|---|
| api.parliament.uk | 49 | 49 | 0 | 0 | 16 | 38% |
| encyclopedia.com | 97 | 0 | 97 | 0 | 10 | 24% |
| snl.no | 126 | 0 | 126 | 0 | 8 | 19% |
| ibiblio.org | 117 | 117 | 0 | 0 | 8 | 19% |
| ebsco.com | 99 | 0 | 99 | 0 | 7 | 17% |
| nam.ac.uk | 94 | 0 | 94 | 0 | 6 | 14% |
| awm.gov.au | 81 | 81 | 0 | 0 | 5 | 12% |
| discovery.nationalarchives.gov.uk | 28 | 28 | 0 | 0 | 4 | 10% |
| thegazette.co.uk | 18 | 18 | 0 | 0 | 4 | 10% |
| assets.publishing.service.gov.uk | 17 | 17 | 0 | 0 | 4 | 10% |
| rmg.co.uk | 60 | 0 | 60 | 0 | 3 | 7% |
| kcl.ac.uk | 42 | 0 | 42 | 0 | 3 | 7% |

### 美國（38 人）

| 網域 | 引文 | A | B | C | 人數 | 覆蓋率 |
|---|---|---|---|---|---|---|
| usna.edu | 72 | 62 | 10 | 0 | 6 | 16% |
| historyofwar.org | 157 | 0 | 0 | 157 | 5 | 13% |
| ibiblio.org | 74 | 66 | 0 | 8 | 5 | 13% |
| airandspaceforces.com | 66 | 0 | 0 | 66 | 5 | 13% |
| encyclopedia.com | 53 | 0 | 53 | 0 | 5 | 13% |
| historynet.com | 85 | 0 | 0 | 85 | 4 | 10% |
| tshaonline.org | 68 | 0 | 38 | 30 | 4 | 10% |
| eisenhowerlibrary.gov | 28 | 28 | 0 | 0 | 3 | 8% |
| generals.dk | 28 | 0 | 0 | 28 | 3 | 8% |
| history.navy.mil | 92 | 92 | 0 | 0 | 2 | 5% |
| historicmissourians.shsmo.org | 71 | 0 | 71 | 0 | 2 | 5% |
| warfarehistorynetwork.com | 27 | 0 | 0 | 27 | 2 | 5% |

### 日本（30 人）

| 網域 | 引文 | A | B | C | 人數 | 覆蓋率 |
|---|---|---|---|---|---|---|
| kotobank.jp | 334 | 0 | 118 | 216 | 20 | 67% |
| nids.mod.go.jp | 251 | 246 | 5 | 0 | 17 | 57% |
| jacar.go.jp | 31 | 31 | 0 | 0 | 10 | 33% |
| ndl.go.jp | 69 | 69 | 0 | 0 | 6 | 20% |
| kantei.go.jp | 28 | 28 | 0 | 0 | 5 | 17% |
| ndlsearch.ndl.go.jp | 69 | 69 | 0 | 0 | 4 | 13% |
| ibiblio.org | 27 | 0 | 27 | 0 | 4 | 13% |
| shoryobu.kunaicho.go.jp | 21 | 21 | 0 | 0 | 1 | 3% |
| jacar.archives.go.jp | 5 | 5 | 0 | 0 | 1 | 3% |
| historynet.com | 4 | 0 | 0 | 4 | 1 | 3% |
| mod.go.jp | 4 | 0 | 4 | 0 | 1 | 3% |
| id.ndl.go.jp | 4 | 4 | 0 | 0 | 1 | 3% |

### 蘇俄（30 人）

| 網域 | 引文 | A | B | C | 人數 | 覆蓋率 |
|---|---|---|---|---|---|---|
| encyclopedia.com | 246 | 0 | 241 | 5 | 16 | 53% |
| vle.lt | 218 | 0 | 0 | 218 | 12 | 40% |
| kotobank.jp | 86 | 0 | 86 | 0 | 8 | 27% |
| spartacus-educational.com | 17 | 0 | 0 | 17 | 5 | 17% |
| booksite.ru | 102 | 0 | 0 | 102 | 4 | 13% |
| qr.gbumac.ru | 78 | 0 | 0 | 78 | 3 | 10% |
| encspb.ru | 53 | 0 | 26 | 27 | 3 | 10% |
| gw2ru.com | 20 | 0 | 0 | 20 | 2 | 7% |
| generals.dk | 9 | 0 | 0 | 9 | 2 | 7% |
| historyofwar.org | 25 | 0 | 0 | 25 | 1 | 3% |
| bsuedu.ru | 10 | 0 | 0 | 10 | 1 | 3% |
| sakharov-center.ru | 10 | 0 | 0 | 10 | 1 | 3% |

### 大英國協（22 人）

| 網域 | 引文 | A | B | C | 人數 | 覆蓋率 |
|---|---|---|---|---|---|---|
| awm.gov.au | 318 | 318 | 0 | 0 | 14 | 64% |
| aif.adfa.edu.au | 204 | 0 | 0 | 204 | 5 | 23% |
| historyofwar.org | 78 | 0 | 0 | 78 | 5 | 23% |
| rafweb.org | 82 | 0 | 0 | 82 | 3 | 14% |
| ibiblio.org | 29 | 22 | 0 | 7 | 3 | 14% |
| junobeach.org | 46 | 0 | 0 | 46 | 2 | 9% |
| thegazette.co.uk | 16 | 16 | 0 | 0 | 2 | 9% |
| biographi.ca | 49 | 49 | 0 | 0 | 1 | 4% |
| historyisnowmagazine.com | 32 | 0 | 0 | 32 | 1 | 4% |
| campcolumbia.com.au | 15 | 0 | 0 | 15 | 1 | 4% |
| nam.ac.uk | 12 | 0 | 12 | 0 | 1 | 4% |
| aviationmuseumwa.org.au | 11 | 0 | 0 | 11 | 1 | 4% |

### 法國（16 人）

| 網域 | 引文 | A | B | C | 人數 | 覆蓋率 |
|---|---|---|---|---|---|---|
| defense.gouv.fr | 317 | 317 | 0 | 0 | 10 | 62% |
| academie-francaise.fr | 132 | 132 | 0 | 0 | 6 | 38% |
| servicehistorique.sga.defense.gouv.fr | 19 | 19 | 0 | 0 | 4 | 25% |
| larousse.fr | 47 | 0 | 0 | 47 | 3 | 19% |
| treccani.it | 8 | 0 | 8 | 0 | 3 | 19% |
| encyclopedia.com | 19 | 0 | 0 | 19 | 2 | 12% |
| archivesdiplomatiques.diplomatie.gouv.fr | 6 | 6 | 0 | 0 | 2 | 12% |
| ordredelaliberation.fr | 56 | 56 | 0 | 0 | 1 | 6% |
| elysee.fr | 41 | 41 | 0 | 0 | 1 | 6% |
| theatrum-belli.com | 7 | 0 | 0 | 7 | 1 | 6% |
| lesclesdumoyenorient.com | 4 | 0 | 4 | 0 | 1 | 6% |
| universalis.fr | 3 | 0 | 3 | 0 | 1 | 6% |

### 義大利（11 人）

| 網域 | 引文 | A | B | C | 人數 | 覆蓋率 |
|---|---|---|---|---|---|---|
| treccani.it | 457 | 451 | 6 | 0 | 10 | 91% |
| warfarehistorynetwork.com | 5 | 0 | 0 | 5 | 1 | 9% |
| poliziadistato.it | 3 | 3 | 0 | 0 | 1 | 9% |
| avvenire.it | 2 | 0 | 0 | 2 | 1 | 9% |
| anpi.it | 1 | 0 | 0 | 1 | 1 | 9% |
| normattiva.it | 1 | 1 | 0 | 0 | 1 | 9% |

## B3（b3-trial，34 檔、159 個不同 key，無國籍欄）前 15

| 網域 | 引文 | A | B | C | 人數 |
|---|---|---|---|---|---|
| encyclopedia.com | 992 | 0 | 992 | 0 | 43 |
| treccani.it | 198 | 98 | 100 | 0 | 10 |
| lobid.org | 40 | 40 | 0 | 0 | 10 |
| deutsche-biographie.de | 82 | 82 | 0 | 0 | 8 |
| ebsco.com | 62 | 0 | 62 | 0 | 8 |
| hls-dhs-dss.ch | 126 | 126 | 0 | 0 | 7 |
| lex.dk | 61 | 0 | 61 | 0 | 6 |
| history.state.gov | 54 | 54 | 0 | 0 | 5 |
| encyclopediaofukraine.com | 66 | 0 | 66 | 0 | 3 |
| islamansiklopedisi.org.tr | 57 | 0 | 57 | 0 | 3 |
| mek.oszk.hu | 47 | 27 | 20 | 0 | 3 |
| www3.congreso.gob.pe | 37 | 37 | 0 | 0 | 3 |
| ndl.go.jp | 30 | 30 | 0 | 0 | 3 |
| tile.loc.gov | 19 | 19 | 0 | 0 | 3 |
| id.loc.gov | 15 | 15 | 0 | 0 | 3 |
