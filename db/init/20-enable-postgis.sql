-- 啟用 PostGIS（PRD §5：GEOMETRY(MultiPolygon, 4326) 等空間欄位需要）
-- 僅在 postgres 資料目錄「首次初始化」時由 docker-entrypoint 執行；IF NOT EXISTS 可安全重複執行。
CREATE EXTENSION IF NOT EXISTS postgis;
