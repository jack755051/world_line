# B3 試跑對齊 ARCHITECTURE.md b0b0e0f（人物／角色／經歷三層）

## 做法
- `python3 -I align_b0b0e0f.py`：讀 `batchNN/research.json`（原檔不動），輸出 `batchNN/research.aligned.json` 與 `align-report.json`。冪等：連跑兩次，所有輸出逐位元相同（已驗，無時間戳）。
- 只搬移／改名／加標記；不新增或改寫引文、日期、出處。未建任何角色資料、未寫庫。
- `verify.py` 偵測頂層 `alignedTo == "b0b0e0f"` 時加跑對齊檢查（見檔頭 11–13），其餘原檢查保留；對齊檔報告為 `batchNN/verify-aligned-report.json`（含原文逐字核對，rawChecked=true）。原 `research.json` 仍可用舊規則驗證。

## 轉換規則
1. `positions[*].roleKind` → `positionKind`，值照搬（值域仍為原 7 種，僅供參考）。
2. 元首／首腦／實際掌權者 → 移入 `roleCandidates`（保留原欄位含 `roleKind` 原名、citations；加 `candidateRoleKind`、`reason`）。判斷（腳本內 `HEAD_PATTERNS`／`GUARD`／`PERSON_OVERRIDES`）：
   - 任一語種標題含副職／機構內職務字樣（副、議長、主席、黨、house of、governor…）一律不算首腦；
   - 標題起首為總統／國王／皇帝／首相／總理／攝政／獨裁者…等才算 head_of_state／head_of_government／de_facto_leader；
   - 標題無法判斷、需依內容者，用個案覆寫表（僅 2 筆，見下）。
3. T14 重疊類別留在 positions，加 `t14Overlap`：`positionKind=minister`→`cabinet`；`military_command`→`general`；標題含總督／governor 且標題或機構含殖民／屬地／佔領字樣→`occupation_colonial`（優先於前兩者）。

## 統計（詳見 `align-report.json`，含每筆人物 key＋職稱）
- 改名（roleKind→positionKind）：**63** 筆（b01 5、b02 13、b03 9、b04 2、b05 5、b06 4、b07 5、b08 9、b09 3、b10 8）。
- 移成候選角色：**2** 筆（de_facto_leader 2，head_of_state 0，head_of_government 0）。原因：試跑研究時 verify 已禁止元首／首腦職位，故 positions 本來就幾乎沒有這類項。
- T14 標記：**31** 筆（cabinet 19、general 11、occupation_colonial 1）。
- verify（對齊檔）：10 批全部 ok，無錯誤。

## 需 Tai 決定的個案
1. **蘇共總書記**（`su-stalin` / `stalin-gensec`）、**國民黨總裁**（`cn-chiang-kai-shek` / `chiang-tsung-tsai`）：標題無法自動判斷，我以個案覆寫為 `de_facto_leader` 候選。黨職是否算「實際掌權者」角色、或留在經歷層為 `party`，請決定。同類的 `cardenas-pnr-president`、`ginestal-nationalist-directorate`（黨主席）、`talat cup-secretary-general` 我**沒**移，理由是當時並非實際掌權者；標準是我主觀判斷。
2. **`general` 標記的邊界**：`military_command` 全標 general，其中含非嚴格將領者：黃埔軍校校長、多明尼加國家警察首長（`natl-police-chief-1924`）、陸軍總監等。T14 若只收「將領」，這幾筆要改。
3. **`cabinet` 的邊界**：含海軍助理部長（`fdr-asst-sec-navy`）、副總理（`choibalsan-deputy-pm`）、副部長（`deputy-defence-1932`）、瑞士聯邦部門主管。是否算閣員待 T14。
4. **尚未捕捉的元首／首腦任期**：positions 內若有以非標題形式（如「總統府」、君主的任期）描述的，規則不會抓到；`roleCandidates` 的完整度只涵蓋 positions 現有項目。元首／首腦任期仍依 §16.9 T13 另案處理。
5. **`roleCandidates` 內仍保留原名 `roleKind`**（為「保留原欄位」）；如要與角色層命名 `role_kind` 統一，請告知。
