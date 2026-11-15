# 匯入報告：dunkirk-1940

由 `tools/import_battle_data.py` 產生，來源 `data/seed/battles/dunkirk_1940/`。這份報告列出「來源檔有、但展示頁用不上或只能降級使用」的部分，是給主線補資料用的。

| 項目 | 來源檔 | 匯入 | 說明 |
|---|---|---|---|
| 名冊單位（R1） | 67 | 64 | 未匯入 3 個標為查無：fr-68-di、fr-32-di、de-luftflotte-2；只有一個來源的 62 個 |
| 指揮官（R7） | 41 | 41 | |
| 文字位置（R3） | 138 | 138 | 其中 44 筆畫上地圖（該單位當天沒有圖上位置、且關係表示部隊所在）；其餘只顯示在單位卡片 |
| 態勢圖 | 8 | 6 | 未通過配準門檻不用：usma-13-4jun；同日多張只取一張的標註 |
| 圖上標註 | 477 | 411 | **已對到名冊 212 個**；其餘 155 個位置歸成 81 個「圖上標註」 |
| 前線（R4 主期，讀圖） | 27 | 27 | 推估，虛線 |
| 前線（R4 前段，文字） | 7 | 7 | |
| 交戰（R5） | 28 | 17 | 未匯入：cand-hannut（來源檔標為查無）；cand-sedan（來源檔標為查無）；cand-dinant（來源檔標為查無）；cand-gembloux（來源檔標為查無）；cand-stonne（來源檔標為查無）；cand-montcornet（來源檔標為查無）；cand-abbeville（來源檔標為查無）；cand-arras（來源檔標為查無）；cand-aa（來源檔標為查無）；cand-boulogne（來源檔標為查無）；cand-abb2（來源檔標為查無） |
| 據點（R6） | 23 | 22 筆／15 處 | 控制方未載的 8 筆照樣帶入，標待查證 |

## 沒有上圖的圖上標註

師以下（旅、團、營）不上圖（憲法 Decision 5）：56 個位置、52 種標號：1 GDS B?、1 Gds Bde、1 HAA Regt、10 BDE、11 BDE、11 Mot Bde、110 RI、12 BDE、126 BDE、129 RI、137 RI、138 BDE、139 BDE、139 Bde、14 A/Tk Regt、14 Ter Regt、145 Bde Gp、15 Regional Regt、150 BDE、150 RI、151 BDE、151 Bde、16 & 53 Fd Regts、16 Fd Regt、18 Fd Regt、19 Fd Regt、2 Fd Regt、208 RI、22 Fd Regt、225 RI、27 A Fd Regt、270 RI、3 BDE、30 Fd Regt、310 RI、341 RI、407 AR、48 RI、53 Fd Regt、65 RI、7 & 76 Fd Regt、7 Gds Bde、8 BDE、8 Zouaves、88 A Fd Regt、9 BDE、91 & 92 Fd Regts、92 Fd Regt、GRD 9?、Mot Regt "Grossdeutschland"、Recce G? GRD 92、SS "Adolf Hitler" Regt。

## 示意圖形

示意箭頭 3 支（取自 `data/campaigns/dunkirk_1940.json`，每支掛在一段官方戰史引文上；只表示方向，不是實際路線）。
沒有畫的 4 支：Diksmuide→Nieuwpoort（起點 Diksmuide 與部隊番號為推定，未核實；終點已核實）；Nieuwpoort→De Panne（攻擊方向與部隊番號未核實；僅攻擊地點已核實）；Veurne→De Panne（同上）；Hoymille→Teteghem（終點 Teteghem 為推定方向，未核實）。

## 還缺什麼

1. **圖上標註沒有對到名冊**：155 個位置的 `unitKey` 都是空的。補上之後重跑，這些位置就會直接掛到名冊單位上，卡片才看得到指揮官與出處。
2. **沒有控制區**：來源檔沒有可以圍成面的前線（主期各日是分段的線，5/30 之後沒有線），所以地圖不塗陣營底色。
3. **疆界（R8）只有紀錄編號**，沒有幾何；展示頁離線讀不到，底圖仍是現代國界。
4. **查不到座標的地名**：無。
5. **主期六個階段沒有摘要文字**（研究檔只有名稱與起訖）。
