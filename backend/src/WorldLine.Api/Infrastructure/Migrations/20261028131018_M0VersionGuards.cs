using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace WorldLine.Api.Infrastructure.Migrations
{
    /// <summary>
    /// I5 修正保留（PRD §6.2）：DB 層 trigger。
    /// - 所有 M0 表禁止 DELETE／TRUNCATE（撤回用撤回版本或 retracted_at）。
    /// - control_record_versions：只能 INSERT；舊版本只允許「一次」寫入 superseded_by＋superseded_at，其他欄位不可改。
    /// - control_records（身分）與 control_record_citations（引用）寫入後不可修改。
    /// 錯誤碼一律 restrict_violation（23001），API 轉成 409。
    /// </summary>
    public partial class M0VersionGuards : Migration
    {
        private static readonly string[] Tables =
        [
            "sources", "regimes", "regime_names", "theaters", "control_snapshots",
            "control_records", "control_record_versions", "control_record_citations", "reference_land",
        ];

        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql("""
                CREATE FUNCTION wl_forbid_delete() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                  RAISE EXCEPTION 'I5：% 不可刪除（請改用撤回版本或 retracted_at）', TG_TABLE_NAME
                    USING ERRCODE = 'restrict_violation';
                END $$;

                CREATE FUNCTION wl_forbid_update() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                  RAISE EXCEPTION 'I5：% 寫入後不可修改', TG_TABLE_NAME
                    USING ERRCODE = 'restrict_violation';
                END $$;

                CREATE FUNCTION wl_crv_guard_update() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                  IF OLD.superseded_by IS NOT NULL THEN
                    RAISE EXCEPTION 'I5：版本 % 已被取代，不可再修改', OLD.id
                      USING ERRCODE = 'restrict_violation';
                  END IF;
                  IF (to_jsonb(NEW) - 'superseded_by' - 'superseded_at')
                     IS DISTINCT FROM (to_jsonb(OLD) - 'superseded_by' - 'superseded_at') THEN
                    RAISE EXCEPTION 'I5：版本 % 只允許寫入 superseded_by／superseded_at；修正請新增版本', OLD.id
                      USING ERRCODE = 'restrict_violation';
                  END IF;
                  IF NEW.superseded_by IS NULL OR NEW.superseded_at IS NULL OR NEW.superseded_by = OLD.id THEN
                    RAISE EXCEPTION 'I5：取代版本時 superseded_by 與 superseded_at 必須同時寫入，且不可指向自己'
                      USING ERRCODE = 'restrict_violation';
                  END IF;
                  RETURN NEW;
                END $$;

                CREATE TRIGGER trg_crv_guard_update BEFORE UPDATE ON control_record_versions
                  FOR EACH ROW EXECUTE FUNCTION wl_crv_guard_update();
                CREATE TRIGGER trg_control_records_forbid_update BEFORE UPDATE ON control_records
                  FOR EACH ROW EXECUTE FUNCTION wl_forbid_update();
                CREATE TRIGGER trg_crc_forbid_update BEFORE UPDATE ON control_record_citations
                  FOR EACH ROW EXECUTE FUNCTION wl_forbid_update();
                """);

            foreach (var t in Tables)
            {
                migrationBuilder.Sql($"""
                    CREATE TRIGGER trg_{t}_forbid_delete BEFORE DELETE ON {t}
                      FOR EACH ROW EXECUTE FUNCTION wl_forbid_delete();
                    CREATE TRIGGER trg_{t}_forbid_truncate BEFORE TRUNCATE ON {t}
                      FOR EACH STATEMENT EXECUTE FUNCTION wl_forbid_delete();
                    """);
            }
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            throw new NotSupportedException("M0VersionGuards 不支援 Down（I5 保護不可移除）。");
        }
    }
}
