# generals.dk 替換後的任期核對（Sonnet，新 session）

授權：Tai 2026-11-13 10:32（World Line 主管轉達）。前一輪已替每批寫好 `.dev/gendk/<TIER>-b<NN>/replace.json`（移除 generals.dk、補替代來源）。但有些職位的起訖日原本**只有 generals.dk 撐**，移除後就沒有來源了。這一輪要核對這些日期。規則：不可編造；新來源與既有值不同時以新來源為準；查不到就標「待查證」。不寫庫、不 push、不 git add／commit、不切分支、不改程式。

## 要核對的職位（這些職位原本都引用過 generals.dk）
{{INVENTORY}}

## 對每個職位
1. 讀 research.json（`data/seed/leaders/generals-roster/bios/<TIER>/batch<NN>/research.json`）中該職位的 citations，再讀 replace.json 裡對它的 addCitations／set。
2. 移除 generals.dk 後，看剩下的 citation quote（既有的與新加的），連同 set 後的 period，逐一核對起日、迄日：quote 有沒有寫出那個日期，並且精度相符。精度相符的意思是：日精度的日期要寫到日，月精度要寫到月，年精度要寫到年。
3. 有寫到、精度也相符：不用動。
4. 有寫到，但精度較粗（例如只寫年份）：在 replace.json 該 item 的 `set` 寫入降精度後的值。Q3 規則：起日寫該單位第一天，例如 1931 年 → "1931-01-01"＋year；迄日寫下一單位的第一天，例如到 1934 年 → "1935-01-01"＋year，到 1944 年 8 月 → "1944-09-01"＋month。`basis` 填支撐的 sourceKey，`diff` 寫「原：…（僅 generals.dk）；依 <key>：…」。如果該 item 原本就有 `set`，就合併進去，不要覆蓋別的欄位。
5. 完全沒寫到：可以再查**最多 2 個** A／B／具名 C 來源，例如官方傳記、國家傳記辭典、官方戰史、具名博物館或大學。找到就照前一輪格式加 `rg-` source、fetch 與 citation（原文存 `~/wl-source-cache/gendk-<TIER>-b<NN>/`；轉文字用 `python3 ~/wl-source-cache/totxt.py in.html out.txt`）。找不到，就把該端點設成 null，對應精度也設 null，寫在 `set`，`diff` 寫明。再在該人加：
   `"addGaps": [{"target": "position:<key>", "gapKind": "not_found", "note": "待查證：缺起日（原僅 generals.dk 支撐，已移除）"}]`，迄日則寫「缺迄日」。起日迄日都缺時，分兩筆 gap，note 不同。
   **起日與迄日都沒有任何來源時**，期間設成 {"start": null, "end": null}，兩個精度都設 null。這是允許的。
6. 禁用：generals.dk 與所有個人網站、Wikipedia／Wikidata（只可當線索）、百度、維基類、論壇、部落格；不用 `curl -k`，不登入，不繞過防機器人頁。quote 逐字、NFC 後 ≤80 字。

## 自檢（每批必做，直到 ok=true）
`python3 -I data/seed/leaders/generals-roster/bios/refill/patch_replace_gendk.py --check <TIER> <NN> .dev/gendk/<TIER>-b<NN>/replace.json`

## 結尾
每個職位一行：`<key>：不變｜降精度（原→新，依據 key）｜新來源（key、grade）｜待查證（哪一端）`，最後每批一行 `BATCH_RESULT <TIER>/<NN>=ok|fail`。
