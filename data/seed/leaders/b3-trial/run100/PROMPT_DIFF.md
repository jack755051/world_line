# run100 提示 vs 試跑提示（.dev/cc-b3trial-loop.sh 產生的 b06／b10 sonnet／opus task）差異

依據：Tai 2026-11-11 12:12 ①②④（T14 ③仍未決，照現行 b0b0e0f）；段祺瑞（b06）、費薩爾一世（b10）0 段落個案；b06／b10 review.json 的 issues。

## 研究提示（PROMPT_research.md）
1. **輸出格式改成 b0b0e0f 對齊格式**：頂層加 `alignedTo="b0b0e0f"`，verify.py 直接跑對齊檢查 11–14；不再事後用 align_b0b0e0f.py 轉換。
2. `positions[].roleKind` → **`positionKind`**；值域不得有 head_of_state／head_of_government／de_facto_leader，也不得有 party；原 7 值只供參考。
3. 新增 **`roleCandidates[]`**：元首、首腦、實際掌權者與**所有黨職**寫在這裡，種類欄位 **`role_kind`**（不用 roleKind／candidateRoleKind），每筆要有 citations＋reason。試跑的 Q4 是「元首／首腦一律不建」，現在改成：名單 5442 任期不重建，名單外、1908–1945、來源明寫者寫成候選。
4. **黨職一律 de_facto_leader**（Tai 12:12 ②），reason 寫固定字句；不明確是否黨職 → 留 positions，加 `partyPostAmbiguous`＋理由。
5. **T14**：閣員／將領／佔領殖民長官留 positions，加 `t14Overlap`（cabinet／general／occupation_colonial），寫明「T14 未決，不要套用 T14_RECOMMENDATION」。
6. 必讀從 b3-sample 範本改成 ALIGN.md＋試跑的 research.aligned.json，另加讀 ARCHITECTURE T11／T12／T14。
7. **新增「搜尋策略」一節**：5 類來源（權威檔→國家辭典／官方頁→具名機構百科→條約法律／國聯文件→學術出版），並依地區（歐洲、東歐、東亞、西亞北非、拉美、南亞東南亞）列出具體起點網站；規定要用原文語言和轉寫變體查詢；網站回 403 或挑戰頁時換同類來源。
8. **新增「最低嘗試」**：寫 0 段之前，至少要做完 4 種來源類型、8 次查詢（原文語言至少 2 次）、實抓 3 頁。
9. **新增每人 `searchLog[]`**：記錄步驟、來源類型、查詢字串、網址、結果代碼、備註。
10. **寫作門檻寫清楚**：有 1 個 A／B 就寫 1 段＋待查證；只有未評等來源就 0 段，引文放候選；確實查無就 0 段，gap 摘要 searchLog。
11. Q9 寫明未評等：無具名作者的百科（EWB 無署名條目，費薩爾一世的情況）、無作者無書目的館藏圖說（段祺瑞的港大圖說）。
12. Q2 改成**每個子句**都要對到 quote（試跑每批審查要補 20–30 筆）；quote 必須是完整語意片段，不可截掉受詞或謂語。
13. 新增 Q8：datePrecision 只在 quote 含日期時填。gapKind conflict 只用於兩份已抓來源互相矛盾。另寫明不可替原文補主語（皆出自 b06 issues）。
14. 段落 period 的迄點依段內最後一件事定（出自 b10 issues）。
15. 路徑改成 run100/batchNN 與 /tmp/b3run100/batchNN/raw。名單來源改為 selection100.json；名單註明地區、厚薄屬推定。
16. 結尾回覆加上候選角色數、searchLog 筆數、推定與實查不符處。

## 審查提示（PROMPT_review.md）
1. 規則不再重抄，改成「研究者規則全部同樣適用」，並指向 PROMPT_research.md（避免兩份分歧）。
2. 新增第 5 項，審查對齊格式：positionKind、roleCandidates.role_kind、黨職是否移入候選、partyPostAmbiguous、t14Overlap。審查可以調整欄位歸類，但不可新增事實。
3. 新增第 6 項，審查薄人物的 searchLog：最低嘗試未達、或手上有 A／B 卻寫 0 段，都判 returned，並寫出建議的下一個具體來源。
4. 第 3 項明列：無署名百科和館藏圖說要降為未評等（試跑 b06、b08–b10 的做法）。
5. review.json 新增 `promptVersion`、`deletedRoleCandidates`、`movedToRoleCandidates`、`movedToPositions`、`addedCitations`、`searchLogShort`；people 加 `roleCandidates`、`searchLogSteps`。

## 不變（保留）
引文 NFC ≤80 字元、逐字、不截斷；A／B 等級定義；§16.3.2 Q1–Q10；原文用 curl 存到 /tmp（不加 -k），並寫 rawmap；不用 Wikipedia／Wikidata／百度；不繞過防機器人驗證；不寫庫、不連 DB、不 commit／push；verify 必須 ok 且 rawChecked=true，不可改 verify.py；BATCH_RESULT 結尾行；Sonnet 研究＋Opus 審查，都開新 session。
