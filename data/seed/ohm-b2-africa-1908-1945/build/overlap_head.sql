-- 跨政權疊合檢查（唯讀：只用 session 暫存表，最後 ROLLBACK）
\set ON_ERROR_STOP on
BEGIN;
CREATE TEMP TABLE c(cid text, slug text, s date, e date, gj text, layer text);
\copy c FROM pstdin WITH (FORMAT csv)
