# 無生平人物補齊（gap-830）staged 檔格式 v2

每批一個資料夾 `bNN/`：`worklist.json`（由主程式產生：待研究的人名群組與任期 id）＋研究結果 `research.json`。

`research.json`：
```json
{
  "batch": "b01", "researchedOn": "2026-11-07",
  "people": [ P, ... ],
  "staging": [ {"groupKeys": ["…"], "names": ["…"], "why": "身分不確定／同名不同人／查無來源…", "clues": "…"} ]
}
```
`P`（一個人＝一份生平）與 batch p1 相同（見 `../batch-p1-20261107/SCHEMA.md`），另加：
- `groupKeys`：這個人涵蓋的 worklist 群組 key（別名可以多個，例如丹麥與冰島的 Christian X）。
- `recordIds`：只能用 worklist 裡這些群組的任期 id；**同名不同人**（例：羅馬尼亞與保加利亞的 Ferdinand I）要拆成兩個 P，各帶自己的任期 id。
- 日期：年精度寫 `YYYY-01-01`＋`precision: "year"`；月精度 `YYYY-MM-01`＋`"month"`。

`S`（來源）同 p1：`title, publisher, url, sourceKind, licenseCode, locator, evidence(≤25 字原文), accessedOn`。

規則（違反者整個人移到 staging）：
- 每個有值的欄位至少一個當天實際打開過的非 Wikidata／Wikipedia／百度來源；Wikidata 只記 Q 號。
- 來源說法衝突 → `conflicts`，該欄不給值。查不到 → 省略＋`unverified`。不憑記憶補。
- 政黨會隨時期變動、而來源沒寫期間者 → 不給值（`unverified`）。君主等無黨派者不寫政黨。
- 摘要：1–2 句中立事實，用自己的話改寫，只含來源寫到的事；不抄長段原文。
- 照片：Commons 檔案頁，**來源國與美國兩個授權模板都必須是 PD／CC0／CC BY／CC BY-SA**，作者或來源欄明確；拿不準就 null。
- 身分不確定（同名、只有姓、合議體成員）→ staging，不寫入。
