using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace WorldLine.Api.Migrations
{
    /// <summary>
    /// EF 模型無法表達的 DB 層約束（手寫 SQL）：
    /// - I3：同政權、同時間不可有兩筆「現行（未被取代）且非爭議」的疆域 → EXCLUDE USING gist（DEFERRABLE，
    ///   讓「新增新版本 + 標記舊版本被取代」可在同一交易內完成）。
    /// - I5：regimes / regime_aliases / regime_territories / regime_relations 禁止 DELETE 與 TRUNCATE；
    ///   regime_territories 只允許「把現行版本標記為被取代」這一種更新，其餘欄位不可變；
    ///   regimes / regime_aliases / regime_relations 的 UPDATE 必須帶修改原因
    ///   （交易內 `SET LOCAL world_line.change_reason = '...'`），舊值/新值寫入 data_revisions。
    /// - 憲法 §4：regimes.status 只允許 existing → split / abdicated / destroyed（後端仍是唯一信任來源，此為縱深防禦）。
    /// </summary>
    public partial class IntegrityAndHistory : Migration
    {
        private static readonly string[] AppendOnlyTables =
            ["regimes", "regime_aliases", "regime_territories", "regime_relations"];

        private static readonly string[] RevisionedTables =
            ["regimes", "regime_aliases", "regime_relations"];

        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            // ---- I3 ----
            migrationBuilder.Sql(@"
ALTER TABLE regime_territories
  ADD CONSTRAINT ex_regime_territories_official_no_overlap
  EXCLUDE USING gist (regime_id WITH =, valid_period WITH &&)
  WHERE (superseded_by IS NULL AND NOT is_disputed)
  DEFERRABLE INITIALLY DEFERRED;");

            // ---- I5：修訂紀錄表 ----
            migrationBuilder.Sql(@"
CREATE TABLE data_revisions (
  id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  table_name    text        NOT NULL,
  row_id        uuid        NOT NULL,
  operation     text        NOT NULL CHECK (operation = 'UPDATE'),
  old_row       jsonb       NOT NULL,
  new_row       jsonb       NOT NULL,
  change_reason text        NOT NULL CHECK (btrim(change_reason) <> ''),
  changed_at    timestamptz NOT NULL DEFAULT now(),
  changed_by    text        NOT NULL DEFAULT current_user
);
CREATE INDEX ix_data_revisions_table_row ON data_revisions (table_name, row_id, changed_at);
COMMENT ON TABLE data_revisions IS 'I5：政權/代稱/關係的每次修改都保留舊值、新值、原因與時間戳（疆域另以 superseded_by 版本鏈保存）';");

            // ---- I5：共用函式 ----
            migrationBuilder.Sql(@"
CREATE FUNCTION wl_change_reason() RETURNS text
LANGUAGE sql STABLE AS $$
  SELECT nullif(btrim(current_setting('world_line.change_reason', true)), '')
$$;

CREATE FUNCTION wl_forbid_delete() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'I5: % 的資料不可刪除或清空；請以修正（新版本或附原因的更新）取代', TG_TABLE_NAME
    USING ERRCODE = 'restrict_violation';
END
$$;

CREATE FUNCTION wl_record_revision() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
  reason text := wl_change_reason();
BEGIN
  IF to_jsonb(NEW) = to_jsonb(OLD) THEN
    RETURN NEW;
  END IF;
  IF reason IS NULL THEN
    RAISE EXCEPTION 'I5: 更新 % 必須提供修改原因（SET LOCAL world_line.change_reason = ...）', TG_TABLE_NAME
      USING ERRCODE = 'check_violation';
  END IF;
  INSERT INTO data_revisions (table_name, row_id, operation, old_row, new_row, change_reason)
  VALUES (TG_TABLE_NAME, OLD.id, TG_OP, to_jsonb(OLD), to_jsonb(NEW), reason);
  RETURN NEW;
END
$$;

CREATE FUNCTION wl_regimes_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.status IS DISTINCT FROM OLD.status
     AND NOT (OLD.status = 'existing' AND NEW.status IN ('split', 'abdicated', 'destroyed')) THEN
    RAISE EXCEPTION '憲法 §4: 不合法的政權狀態轉換 % -> %', OLD.status, NEW.status
      USING ERRCODE = 'check_violation';
  END IF;
  IF NEW.id IS DISTINCT FROM OLD.id OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'regimes.id / created_at 不可修改' USING ERRCODE = 'check_violation';
  END IF;
  NEW.updated_at := now();
  RETURN NEW;
END
$$;

CREATE FUNCTION wl_regime_territories_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.superseded_by IS NOT NULL THEN
    RAISE EXCEPTION 'I5: 已被取代的疆域版本 % 不可再修改', OLD.id USING ERRCODE = 'check_violation';
  END IF;
  IF NEW.id IS DISTINCT FROM OLD.id
     OR NEW.regime_id IS DISTINCT FROM OLD.regime_id
     OR NEW.valid_period IS DISTINCT FROM OLD.valid_period
     OR NEW.geom IS DISTINCT FROM OLD.geom
     OR NEW.is_disputed IS DISTINCT FROM OLD.is_disputed
     OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'I5: 疆域內容不可覆蓋；請新增新版本並把舊版本的 superseded_by 指向它'
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END
$$;");

            // ---- 觸發器（同表多個 BEFORE 觸發器依名稱字母序執行：trg_10 guard → trg_20 revision）----
            foreach (var table in AppendOnlyTables)
            {
                migrationBuilder.Sql($@"
CREATE TRIGGER trg_00_{table}_forbid_delete BEFORE DELETE ON {table}
  FOR EACH ROW EXECUTE FUNCTION wl_forbid_delete();
CREATE TRIGGER trg_00_{table}_forbid_truncate BEFORE TRUNCATE ON {table}
  FOR EACH STATEMENT EXECUTE FUNCTION wl_forbid_delete();");
            }

            migrationBuilder.Sql(@"
CREATE TRIGGER trg_10_regimes_guard BEFORE UPDATE ON regimes
  FOR EACH ROW EXECUTE FUNCTION wl_regimes_guard();
CREATE TRIGGER trg_10_regime_territories_guard BEFORE UPDATE ON regime_territories
  FOR EACH ROW EXECUTE FUNCTION wl_regime_territories_guard();");

            foreach (var table in RevisionedTables)
            {
                migrationBuilder.Sql($@"
CREATE TRIGGER trg_20_{table}_revision BEFORE UPDATE ON {table}
  FOR EACH ROW EXECUTE FUNCTION wl_record_revision();");
            }
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            foreach (var table in RevisionedTables)
                migrationBuilder.Sql($"DROP TRIGGER IF EXISTS trg_20_{table}_revision ON {table};");

            migrationBuilder.Sql(@"
DROP TRIGGER IF EXISTS trg_10_regimes_guard ON regimes;
DROP TRIGGER IF EXISTS trg_10_regime_territories_guard ON regime_territories;");

            foreach (var table in AppendOnlyTables)
                migrationBuilder.Sql($@"
DROP TRIGGER IF EXISTS trg_00_{table}_forbid_delete ON {table};
DROP TRIGGER IF EXISTS trg_00_{table}_forbid_truncate ON {table};");

            migrationBuilder.Sql(@"
DROP FUNCTION IF EXISTS wl_regime_territories_guard();
DROP FUNCTION IF EXISTS wl_regimes_guard();
DROP FUNCTION IF EXISTS wl_record_revision();
DROP FUNCTION IF EXISTS wl_forbid_delete();
DROP FUNCTION IF EXISTS wl_change_reason();
DROP TABLE IF EXISTS data_revisions;
ALTER TABLE regime_territories DROP CONSTRAINT IF EXISTS ex_regime_territories_official_no_overlap;");
        }
    }
}
