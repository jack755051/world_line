# World Line

一個以地理資訊系統（GIS）與地圖為核心，呈現世界歷史事件、朝代疆域與時間軸變化的網頁專案。使用者可以在地圖上瀏覽不同時間點的歷史事件、國界變遷與重大戰爭、貿易路線等，透過時間軸拖動觀察世界歷史的演進。

## 技術架構

- **前端**：Angular（`app/`）
- **後端**：.NET Web API（`api/`）
- **資料庫**：PostgreSQL（可搭配 PostGIS 儲存地理空間資料）
- **快取**：Redis
- **容器化**：Docker Compose 一鍵啟動所有服務

## 專案結構

```
.
├── api/                       # .NET 後端 API
├── app/                       # Angular 前端
├── .claude/
│   └── constitutions/         # 業務憲法（SSOT，見下方「開發工具」）
├── .env                       # 本機環境變數（不進版控）
├── .env.example                # 環境變數範本
├── docker-compose.yml          # 服務編排設定
└── README.md
```

## 快速開始

1. 複製環境變數範本並依需求調整：

   ```bash
   cp .env.example .env
   ```

2. 使用 Docker Compose 啟動所有服務：

   ```bash
   docker compose up --build
   ```

3. 服務位置：

   | 服務 | 位址 |
   | --- | --- |
   | 前端（Angular / Nginx） | http://localhost:4200 |
   | 後端 API（.NET） | http://localhost:5000 |
   | PostgreSQL | localhost:5432 |
   | Redis | localhost:6379 |

## 開發工具

這個 repo 的業務憲法（`.claude/constitutions/world-line.md`）與後續 PRD 是用 [sanring-claude-pack](https://github.com/sanringtech/sanring-claude-pack)（Claude Code plugin）以訪談式流程產出的。這個工具**不是** app 程式碼，不會 vendor 進 repo，若要在其他機器上重現同樣的 `/supervisor:*` 工作流程，安裝方式：

```bash
/plugin marketplace add sanringtech/sanring-claude-pack
/plugin install sanring-claude-pack@sanring
/reload-plugins
```

常用指令：`/supervisor:constitution`（憲法）、`/supervisor:prd`（PRD）、`/supervisor:roadmap`（roadmap）。

## 本機開發（不使用 Docker）

**後端**

```bash
cd api
dotnet run
```

**前端**

```bash
cd app
npm install
npm start
```
