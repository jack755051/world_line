# us-participants（舊事件事後追加美國為參與方；DRAFT，待 Tai 檢查）

Tai 2026-10-31 選方案 A：「用 A，追加參與方」。這 7 個事件寫入時開發庫還沒有美國政權（REGIME_US 在 borders-us 批才建立），
用 337ffca 的 `POST /api/v1/events/{id}/participants` 事後追加；只新增、理由必填，原有參與方、引用、事件欄位都不動。
**只寫入開發庫** worldline-borders-dev（API 127.0.0.1:5052）。

| 事件 | 角色 | 理由摘要 |
|---|---|---|
| EV_TORCH 盟軍登陸北非 1942-11-08 | belligerent | 美軍為登陸主力 |
| EV_IT_ARMISTICE 義大利停戰 1943-09-08 | signatory | 史密斯代表艾森豪簽字 |
| EV_CASERTA 卡塞塔投降 1945-04-29 | belligerent | 投降對象含美國第五軍團；盟方簽字人為英國摩根中將，故不記為簽署方 |
| EV_DE_SURRENDER 德國投降 1945-05-08 | signatory | 蘭斯投降書由史密斯代表 SHAEF 簽字 |
| EV_PARIS 盟軍進入巴黎 1944-08-25 | belligerent | 美軍第 4 步兵師同日入城 |
| EV_GPRF_RECOG 承認法國臨時政府 1944-10-23 | other | 美國為承認國之一 |
| EV_HU_ARMISTICE 匈牙利停戰 1945-01-20 | signatory | 伏羅希洛夫代表蘇英美簽字 |

## 待查證
- 追加理由本身尚未附 FRUS 頁碼（API 的追加只收理由文字，不收引用）；事件原有引用不變。之後若要補引用，需另議做法。
- 卡塞塔：美國的角色記為交戰方（belligerent），是否改記簽署方待拍板。

用法：`/tmp/send.sh us-participants us-participants [--send]`（id 表 .dev/sent-ids.us-participants-dev.json；409 視為已追加）。
