# tools/tiles — 疆界圖磚建置（ARCHITECTURE.md §9）

只讀開發庫（預設 docker 容器 `worldline-borders-dev-db`，5442）；不碰 5051、appdb_ww2、5432。

| 檔案 | 用途 |
|---|---|
| `sql/label_points.sql` | 國名點：每個政權每個時期一點，在最大塊國土上以 polylabel 算出 |
| `compare.py` | 步驟 2 驗收：變動日＋50 個隨機日，`boundary_periods`／`label_points` 與第 1 層 API 的政權集合比對 |

```sh
python3 tools/tiles/compare.py            # 需 5052 API 在跑；結果寫到 tools/tiles/out/compare.json
```

`out/` 是建置產物，不進 git。
