# 法、英政權與 1940 控制區（DRAFT）

> **狀態：DRAFT — 待 Tai 檢查。尚未寫入 appdb_ww2。**
> 預設 dry-run：`python3 send_seed.py`；Tai 同意後 `--send`。標 ⚠ 的待決請求另需 `--include-pending`。
> 前置 id（SNAP_0715、SRC_LECONTE、SRC_AIN、SRC_TRF、SRC_USMA15）讀 `../france-1940-07-15/sent-ids.json`。

## Tai 的決定（2026-10-30）

- 先補法國與英國的政權與 1940 控制區，讓地圖看得到德、法、英之間的領土變化；缺口 API 之後再做。
- 陣營依憲法 §6；英、法（第三共和）、自由法國屬同盟，維琪屬共同交戰／合作；每段都要有文件化的正式依據。英法 1940 年的「同盟」依據若有爭議，列出候選由 Tai 決定。

## 政權

目前 API 的政權只有名稱，沒有起訖欄位（`regime_status_periods`／`regime_transitions` 屬缺口 API，尚未實作）。下表的起訖日只記在這裡，不送進 DB。

| 代號 | slug | 自稱 | 起訖（本批依據） | 出處 |
|---|---|---|---|---|
| REGIME_FR3 | french-third-republic | République française | …～1940-07-10（最後一天） | JO 1940-07-11 n° 167 p. 4513：7-10 憲法性法律（Lebrun 以共和國總統公布） |
| REGIME_FR_STATE | french-state-vichy | État français | 1940-07-11～ | 同上（授權頒布「法蘭西國」憲法）；7-11 Acte constitutionnel n° 1 原文**未核對**（JO 7-12 期沒有公有領域掃描可開） |
| REGIME_FR_LIBRE | free-france | France libre | **待 Tai 拍板**（候選見下） | — |
| REGIME_UK | united-kingdom | United Kingdom of Great Britain and Northern Ireland | 本期間無變動 | — |

## 控制區

| 紀錄 | 控制方 | 期間 [start, end) | 類型 | 面積 | 幾何來源 | primary |
|---|---|---|---|---|---|---|
| CR_VICHY_FREE | 法蘭西國 | 1940-07-15 – 1942-11-11（起日不確定 07-11～07-15） | direct_rule | 219,166 km² | 分界線：Ain 座標（對照 Leconte，與 CR_MAIN 共用）；外框：TRF-GIS 1940；扣除與義大利接壤的 5 省 | Leconte（cc0） |
| CR_UK_HOME ⚠ | 英國 | 1939-09-03 – 1945-09-03 | direct_rule | 243,783 km² | Natural Earth 10m admin-0 GBR（公有領域），排除 Rockall | USMA Map 2（us_federal_pd） |

- 維琪自由區與法國那批全部控制區（含待決的東北禁區）在 1e-5° 網格上的交集面積都是 0。
- **義大利佔領區**：沒有合格來源（`docs/research/ww2-data-sources.md` §4.3）。為了不把義大利佔領的市鎮標成維琪，Basses-Alpes、Hautes-Alpes、Alpes-Maritimes、Savoie、Haute-Savoie 五省（27,586 km²）不畫，地圖上是「控制資料缺」（R9）。
- **自由區迄日 1942-11-11** 沿用 CR_MAIN（Anton 行動），本批引用的來源沒有明文寫出這個日期。
- **Rockall** 1955 年才由英國宣布併入，1940 年不屬英國，從 Natural Earth 的 GBR 排除。
- ⚠ CR_UK_HOME：起訖不是來源明文（起日取英國參戰日、迄日取第一階段終點），待 Tai 拍板。

## 陣營

| 代號 | 政權 | 陣營 | 期間 | primary | date_check | 狀態 |
|---|---|---|---|---|---|---|
| AL_FR_STATE_COBEL | 法蘭西國 | co_belligerent | 1940-07-11 – （未定） | DGFP D IX pp. 671–676，停戰協定第 III、X 條 | JO 1940-07-11 p. 4513 | 預設送出 |
| AL_UK_ALLIES_1939 ⚠ | 英國 | allies | 1939-09-03 – （未定） | FRUS 1939 v. I, Doc. 419, p. 414 | — | 待決 |
| AL_FR3_ALLIES_1939 ⚠ | 第三共和 | allies | 1939-09-03 – 1940-06-25 | FRUS 1939 v. I, Doc. 421, p. 415 | DGFP D IX，停戰協定第 I、XXIII 條 | 待決 |

### 待 Tai 拍板：「同盟」的正式依據

憲法 §6：「軸心與同盟只依有文件的正式加入（例：三國同盟條約簽署日、聯合國家宣言簽署日或參戰日）判定」。

- **英國**
  - A：參戰日 1939-09-03（FRUS 1939 v. I, Doc. 419, p. 414）。目前的請求檔用這個。
  - B：聯合國家宣言 1942-01-01（FRUS 1942 v. I, Doc. 18, pp. 25–26）。1939-09 到 1941-12 就沒有陣營。
- **第三共和**
  - A：參戰日 1939-09-03（FRUS 1939 v. I, Doc. 421, p. 415）到停戰生效 1940-06-25。目前的請求檔用這個。
  - 1940-03-28 英法聯合聲明（互不單獨媾和）：沒找到美國聯邦或其他有使用權的全文出處，未列入。
  - 第三共和沒有簽聯合國家宣言（法國 1944-12-26 才加入，當時是臨時政府）。
  - 1940-06-25 到 07-10 第三共和屬哪一陣營：不推定。
- **自由法國**（沒有建請求）
  - 政權起日候選：1940-06-18 de Gaulle 廣播、1940-06-23／28 英國承認（FRUS 1940 v. I, Doc. 235, pp. 266–267 記英國 6-23 晚間宣布承認 de Gaulle 的 National Committee）、1940-08-07 邱吉爾－de Gaulle 協定。
  - 同盟依據候選：1940-08-07 協定（英國 Cmd. 6220，皇家著作權；在美國可能因 URAA 回復保護，使用權待確認）、1941-09-24 聖詹姆斯宮同盟國會議（未找到可核對頁碼的公有領域全文）。
  - 自由法國沒有簽聯合國家宣言。

## 沒有寫的

- **海峽群島**（德國 1940-06-30 起佔領 Guernsey、07-01 Jersey）：R7 要求控制紀錄的 primary 是有使用權的地圖並標圖號，目前沒找到。USMA Map 15 只標地名，Map 53 是 1944 年。英國官方戰史（HMSO 1950 年代）在英國已過皇家著作權期，但在美國可能因 URAA 回復保護，使用權待確認。
- **義大利佔領區**：同上，沒有合格來源。
- **停戰前快照**（例：1940-06-04、06-12）：USMA Map 13「Situation 4 June 1940」、Map 14「Situation 12 June 1940」是公有領域，可當來源；要數位化戰線並決定「交戰中」範圍，工作量另估，本批只提案。
- **第三共和 1940-06-25～07-10 的非佔領區控制**：在 07-15 快照之前，本批不做。
- **英國海外領地、曼島**：不在本批範圍。曼島是皇家屬地，不屬英國本土。

## 來源

| 代號 | 種類 | 授權 | 用途 |
|---|---|---|---|
| SRC_JO_19400711 | official_record | pd_expired（官方法令；Commons 標 Public domain） | date_check |
| SRC_DGFP_D9 | official_record | us_federal_pd（國務院 Publication 6312） | 陣營 primary、date_check |
| SRC_FRUS_1939_I | official_record | us_federal_pd | 陣營 primary、date_check |
| SRC_USMA02 | atlas_map | us_federal_pd | 英國本土 primary |
| SRC_NATURAL_EARTH | dataset | public_domain | auxiliary_geometry |

沿用法國那批：SRC_LECONTE（cc0）、SRC_AIN、SRC_TRF（cc_by）、SRC_USMA15。

## 檔案

- `zones-fr-uk-1940.geojson`：維琪自由區、英國本土，以及扣掉的 5 省（GAP_ALPINE，只供檢查，不送出）。
- `requests/`：依檔名順序送出。
- `send_seed.py`：送出工具。
- `build/make_fruk.py`：幾何（box 上 `~/.venvs/gis/bin/python`，讀 `/workspace/world-line-ww2/trace/`）。
- `build/make_requests_fruk.py`：產生請求檔。
- 測試 `SeedFrUk1940Tests`：在 Testcontainers 重播法國、陣營與本批（含待決、不含待決兩種）。
