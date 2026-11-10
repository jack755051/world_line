# 5052 API 比對（80 字引文寫入前後，2026-11-10）

只讀 GET 同一組 10 個端點（同 .dev/b2-api-snap/snap.sh；快照存 .dev/quotewrite-api-snap/{pre,pre2,post}，不進版控）。5052 未重啟。

| 端點 | HTTP | bytes | sha256 前 12 | 寫入前→後 |
|---|---|---|---|---|
| bio-inonu | 200 | 12684 | 9a5af1a38628 | 相同 |
| bio-jiang | 200 | 14421 | 954aab2145c1 | 相同 |
| bio-pats | 200 | 15222 | 5d3e1e79ea98 | 相同 |
| leaders-1939-09-01 | 200 | 142707 | bcb66183cbea | 相同 |
| leaders-1945-09-15 | 200 | 126404 | 16a72620b0ee | 相同 |
| regime-japan | 200 | 380 | 786bfc74bd05 | 相同 |
| regime-japan-events | 200 | 31115 | ebc84c918d90 | 相同 |
| regime-uk | 200 | 439 | 0293fc039589 | 相同 |
| source-1 | 200 | 828 | c0587369f0ce | 相同 |
| sovereignty-1939-09-01 | 200 | 8888278 | 7846c6ed5e23 | 相同 |

- 寫入前取兩次（pre、pre2）一致，且與 B2 寫入後快照（.dev/b2-api-snap/post-write）逐位元相同。
- 寫入後 10／10 逐位元相同（HTTP 碼、大小、雜湊皆同）。
- 原因：目前 API 回應不含 quote 欄（後端只有 Domain/Entities.cs 有 Quote，DTO 未輸出），故生平端點也不變；bio-pats 有 5 筆本次寫入的 citation，回應仍相同。
