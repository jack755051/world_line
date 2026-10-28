using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace WorldLine.Api.Migrations
{
    /// <summary>
    /// M2 的 DB 層縱深防禦（手寫 SQL，延續 IntegrityAndHistory）：
    /// - data_revisions.row_id 改為 text：historical_events 的主鍵是 slug（varchar），其餘表仍是 uuid（以文字形式保存）。
    /// - I5：新增的事件／觀點／爭議／地名／年號／標籤／觀察者分類 一律禁止 DELETE 與 TRUNCATE。
    /// - I5：historical_events / 觀點 / 爭議 / 地名 / 年號 的 UPDATE 必須帶修改原因，舊值/新值寫入 data_revisions
    ///   （EF 端由 WorldLineDbContext.ChangeReason 自動 set_config；version 由 EF 自動遞增）。
    /// - regimes.existence_period 去掉 EF 加欄位時的暫時預設值。
    /// - 疆域 guard 擴充：is_illustrative 與 source 也屬於「不可覆蓋」的內容，要改只能出新版本。
    /// </summary>
    public partial class M2IntegrityTriggers : Migration
    {
        private static readonly string[] AppendOnlyTables =
        [
            "historical_events", "historical_event_perspectives", "historical_event_controversies",
            "historical_event_tag_map", "event_tags", "observer_categories", "place_names", "reign_eras",
        ];

        private static readonly string[] RevisionedTables =
        [
            "historical_events", "historical_event_perspectives", "historical_event_controversies",
            "place_names", "reign_eras",
        ];

        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            // 新增 NOT NULL 欄位時 EF 會帶一個暫時預設值（empty range）；拿掉，讓「未給存續期間」直接以 NOT NULL 拒絕（I1 精神）
            migrationBuilder.Sql("ALTER TABLE regimes ALTER COLUMN existence_period DROP DEFAULT;");

            migrationBuilder.Sql(@"
ALTER TABLE data_revisions ALTER COLUMN row_id TYPE text USING row_id::text;
COMMENT ON COLUMN data_revisions.row_id IS '被修改列的主鍵（uuid 或事件 slug，以文字保存）';");

            migrationBuilder.Sql(@"
CREATE OR REPLACE FUNCTION wl_regime_territories_guard() RETURNS trigger
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
     OR NEW.is_illustrative IS DISTINCT FROM OLD.is_illustrative
     OR NEW.source IS DISTINCT FROM OLD.source
     OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'I5: 疆域內容不可覆蓋；請新增新版本並把舊版本的 superseded_by 指向它'
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END
$$;");

            foreach (var table in AppendOnlyTables)
            {
                migrationBuilder.Sql($@"
CREATE TRIGGER trg_00_{table}_forbid_delete BEFORE DELETE ON {table}
  FOR EACH ROW EXECUTE FUNCTION wl_forbid_delete();
CREATE TRIGGER trg_00_{table}_forbid_truncate BEFORE TRUNCATE ON {table}
  FOR EACH STATEMENT EXECUTE FUNCTION wl_forbid_delete();");
            }

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

            foreach (var table in AppendOnlyTables)
                migrationBuilder.Sql($@"
DROP TRIGGER IF EXISTS trg_00_{table}_forbid_delete ON {table};
DROP TRIGGER IF EXISTS trg_00_{table}_forbid_truncate ON {table};");

            migrationBuilder.Sql(@"
CREATE OR REPLACE FUNCTION wl_regime_territories_guard() RETURNS trigger
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

            // 回退時 row_id 轉回 uuid 只在全部都是 uuid 時可行（含事件 slug 的修訂紀錄會使此步失敗，屬預期：不丟資料）
            migrationBuilder.Sql("ALTER TABLE data_revisions ALTER COLUMN row_id TYPE uuid USING row_id::uuid;");
        }
    }
}
