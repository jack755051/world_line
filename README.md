# World Line

以 GIS 與時間軸呈現世界歷史的網頁專案：在同一時間點比較多個政權的疆域、名稱與互動，保留史觀差異、時間不確定性與史料修正歷程。第一階段為 1908-01-01～1945-09-30（一戰、戰間期、二戰），涵蓋全世界所有國家與殖民地；一級行政區排在全球國家補全之後，二級以下行政區不在第一階段範圍。

## 目前狀態

進度以 [`ARCHITECTURE.md`](ARCHITECTURE.md) 為唯一依據（Tai 2026-11-03 決定）：里程碑、模組、已完成／未完成／未決定事項都寫在那裡。

摘要（2026-11-03）：前後端骨架、1908–1945 主權圖層、控制區、衝突、首都、領導人與生平、右側面板、跳年掃描動畫都已實作；目前進行中的是 M1 地圖標籤與遮擋。

## 文件

| 文件 | 用途 |
|---|---|
| [架構文件](ARCHITECTURE.md) | 模組、資料流、介面與進度（進度唯一依據） |
| [業務憲法](.claude/constitutions/world-line.md) | 業務規則 SSOT |
| [PRD（第一階段 1908–1945）](.claude/prds/world-line-ww2.md) | 第一階段規格：範圍、資料模型、API、頁面、里程碑 |
| [執行計畫](.claude/plans/world-line-ww2-plan.md) | 任務順序與進度（核取方塊為準） |
| [史料來源調查](docs/research/ww2-data-sources.md) | 二戰可用資料集與地圖、缺口、工時估算 |


## 結構

```
world_line/
├── backend/                 ASP.NET API（Dockerfile → worldline-api 映像）
├── frontend/                Angular 前端（deploy/Dockerfile.web → worldline-web 映像）
├── tools/tiles/out/         PMTiles 圖磚與 overlay.json（不進 git，scp/rsync 到 VPS）
├── deploy/
│   ├── Dockerfile.web       前端 production build＋nginx
│   └── nginx.web.conf       SPA fallback、/api → api、/tiles → martin、快取標頭
├── scripts/prod-images.sh   正式映像 build / push（linux/amd64）
├── compose.yaml             開發環境
├── docker-compose.prod.yml  正式環境（VPS）
└── env.prod.example         正式環境變數範本（複製成 .env.prod，不進版控）
```

## 正式環境交付物

| 項目 | 位置 | 說明 |
|---|---|---|
| api 映像 | `registry.digitalocean.com/sanring/worldline-api:<API_IMAGE_TAG>` | DigitalOcean Container Registry（私有） |
| web 映像 | `jackdai850817/worldline-web:<WEB_IMAGE_TAG>` | Docker Hub（公開）；前端靜態檔＋nginx |
| compose | `docker-compose.prod.yml` | postgres、redis、api、martin、web；只有 web 綁 `127.0.0.1:4080` |
| 環境檔 | `.env.prod`（由 `env.prod.example` 複製） | 映像標籤、埠、Postgres 帳密、API key |
| 圖磚 | `tiles/`（VPS 上） | `boundaries.pmtiles`、`overlay.pmtiles`、`overlay.json` 與其版本檔 |
| 資料庫備份 | `restore/worldline.dump`（VPS 上） | 第一次上線用 `pg_restore` 還原 |

正式架構：Cloudflare（TLS 終止）→ Tunnel → VPS `127.0.0.1:4080`（web/nginx）→ 容器內網路的 api、martin；postgres、redis 不綁任何主機埠。redis 目前 API 尚未使用（預留）。

## 開發環境啟動

```bash
cp .env.example .env          # 填開發用值
docker compose up -d          # 開發用 compose.yaml
cd frontend && pnpm install && pnpm start
```

## 正式映像建置與推送（本機）

```bash
cp env.prod.example .env.prod         # 第一次：填 POSTGRES_USER、POSTGRES_PASSWORD、WORLDLINE_API_KEY

docker login registry.digitalocean.com   # 推 api 用（DO 讀寫 token）
docker login                             # 推 web 用（Docker Hub jackdai850817）

./scripts/prod-images.sh build-push        # api、web 都建＋推（沿用 .env.prod 標籤）
./scripts/prod-images.sh build-push api    # 只建＋推 api，並把 API_IMAGE_TAG 改成年月日時分
./scripts/prod-images.sh build-push web    # 只建＋推 web，並把 WEB_IMAGE_TAG 改成年月日時分
./scripts/prod-images.sh build             # 只建置不推（驗證用）

ssh root@<VPS_IP> 'mkdir -p ~/worldline/tiles ~/worldline/restore'
scp docker-compose.prod.yml .env.prod root@<VPS_IP>:~/worldline/
```

映像一律 `linux/amd64`（腳本設定 `DOCKER_DEFAULT_PLATFORM=linux/amd64`）。

## 圖磚檔上傳

```bash
# 實體版本檔與 symlink 一起傳（rsync -a 保留 symlink）
rsync -av tools/tiles/out/boundaries*.pmtiles tools/tiles/out/overlay*.pmtiles tools/tiles/out/overlay*.json \
  root@<VPS_IP>:~/worldline/tiles/
ssh root@<VPS_IP> 'ls -l ~/worldline/tiles/boundaries.pmtiles ~/worldline/tiles/overlay.pmtiles ~/worldline/tiles/overlay.json'
```

換新版圖磚：傳新版本檔、改 symlink，再 `docker compose -f docker-compose.prod.yml --env-file .env.prod restart martin`。

## 資料搬遷（開發庫 → 正式庫，第一次上線）

```bash
# 1) 本機匯出（只讀；開發庫 worldline-borders-dev-db / worldline_borders_dev）
docker exec worldline-borders-dev-db pg_dump -U <開發庫使用者> -d worldline_borders_dev -Fc -f /tmp/worldline.dump
docker cp worldline-borders-dev-db:/tmp/worldline.dump ./worldline.dump

# 2) 傳到 VPS
scp worldline.dump root@<VPS_IP>:~/worldline/restore/
```

```bash
# 3) VPS：只啟 postgres
cd ~/worldline
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d postgres
set -a; . ./.env.prod; set +a

# 4) 確認版本：PostgreSQL 18.x / PostGIS 3.6.x
docker compose -f docker-compose.prod.yml --env-file .env.prod exec postgres \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select version();" -c "select postgis_full_version();"

# 5) 還原
docker compose -f docker-compose.prod.yml --env-file .env.prod exec postgres \
  pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-privileges /restore/worldline.dump
```

## VPS：啟動／停止／更新

```bash
cd ~/worldline
docker login registry.digitalocean.com          # 用 DO 唯讀 token（api 是私有映像）

docker compose -f docker-compose.prod.yml --env-file .env.prod pull
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --remove-orphans

# 只更新單一服務（本機 build-push 後，把新的 .env.prod scp 過來）
docker compose -f docker-compose.prod.yml --env-file .env.prod pull api
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --force-recreate api

docker compose -f docker-compose.prod.yml --env-file .env.prod ps
docker compose -f docker-compose.prod.yml --env-file .env.prod down
# docker compose -f docker-compose.prod.yml --env-file .env.prod down -v   # 慎用：會刪資料庫 volume
```

### 改 .env.prod 後重建

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --force-recreate
```

### Logs

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f --tail 100 api
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f --tail 100 web
```

### 在 VPS 驗健康

```bash
curl -s http://127.0.0.1:4080/api/healthz                 # {"status":"Healthy","checks":{"db":"Healthy"}}
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:4080/
curl -s http://127.0.0.1:4080/tiles/boundaries | head -c 200
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:4080/tiles/overlay.json
```

## Cloudflare Tunnel

```bash
# VPS 安裝 cloudflared（Debian/Ubuntu）
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main" | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt-get update && sudo apt-get install -y cloudflared

# Zero Trust → Networks → Tunnels 建立 tunnel 後，複製 token：
sudo cloudflared service install <token>
sudo systemctl enable --now cloudflared
systemctl status cloudflared
```

Public Hostname 對應：

| Hostname | Type | URL |
|---|---|---|
| `<World Line 網域>` | HTTP | `http://127.0.0.1:4080` |

Cloudflare 網域設定：SSL/TLS → Edge Certificates 開 **Always Use HTTPS** 與 **HSTS**。VPS 防火牆不需開 80/443（Tunnel 是對外連線）。

重建前的程式碼與文件（三國示範版，M1～M3）可在 git 歷史 `7f0853d` 取回。
