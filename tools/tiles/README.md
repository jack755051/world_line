# tools/tiles — 疆界圖磚建置（ARCHITECTURE.md §9）

只讀開發庫（預設 docker 容器 `worldline-borders-dev-db`，5442）；不碰 5051、appdb_ww2、5432。
工具一律用 docker image，不做全域安裝。

| 檔案 | 用途 |
|---|---|
| `sql/label_points.sql` | 國名點：每個政權每個時期一點，在最大塊國土上以 polylabel 算出 |
| `compare.py` | 步驟 2 驗收：變動日＋50 個隨機日，`boundary_periods`／`label_points` 與第 1 層 API 的政權集合比對 |
| `build.sh` | 步驟 3：PostGIS 匯出 GeoJSONSeq → tippecanoe → `out/boundaries-v{hash}.pmtiles`、`out/manifest.json`、`out/build-report.json` |

```sh
python3 tools/tiles/compare.py            # 需 5052 API 在跑；結果寫到 tools/tiles/out/compare.json
zsh tools/tiles/build.sh                  # 約 1 分鐘
```

tippecanoe 映像（felt 沒有發布到 ghcr，先從原始碼建一次）：

```sh
docker build -t wl-tippecanoe:2.79.0 "https://github.com/felt/tippecanoe.git#2.79.0"
```

圖磚 schema 照 §9「介面」：圖層 `boundaries`（regime_id、start_day、end_day、color_idx、disputed、control_type）、
`labels`（regime_id、start_day、end_day、name_zh、name_local、area）；整數日自 1900-01-01 起算，`end_day` 不含當日。

`out/` 是建置產物，不進 git。
