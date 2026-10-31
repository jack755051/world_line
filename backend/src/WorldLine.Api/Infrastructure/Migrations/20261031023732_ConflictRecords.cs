using System;
using Microsoft.EntityFrameworkCore.Migrations;
using NetTopologySuite.Geometries;
using NpgsqlTypes;

#nullable disable

namespace WorldLine.Api.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class ConflictRecords : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "conflict_records",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    regime_a_id = table.Column<Guid>(type: "uuid", nullable: false),
                    regime_b_id = table.Column<Guid>(type: "uuid", nullable: false),
                    start_event_id = table.Column<Guid>(type: "uuid", nullable: false),
                    end_event_id = table.Column<Guid>(type: "uuid", nullable: true),
                    valid_period = table.Column<NpgsqlRange<DateOnly>>(type: "daterange", nullable: false),
                    location = table.Column<Point>(type: "geometry(Point,4326)", nullable: false),
                    location_method = table.Column<string>(type: "text", nullable: false),
                    note = table.Column<string>(type: "jsonb", nullable: true),
                    retracted_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    retraction_reason = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    version = table.Column<int>(type: "integer", nullable: false, defaultValue: 0)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_conflict_records", x => x.id);
                    table.CheckConstraint("ck_conflict_records_distinct_regimes", "regime_a_id <> regime_b_id");
                    table.CheckConstraint("ck_conflict_records_location_method_not_blank", "btrim(location_method) <> ''");
                    table.CheckConstraint("ck_conflict_records_note_object", "note IS NULL OR jsonb_typeof(note) = 'object'");
                    table.CheckConstraint("ck_conflict_records_retraction_reason", "retracted_at IS NULL OR retraction_reason IS NOT NULL");
                    table.CheckConstraint("ck_conflict_records_start_bounded", "NOT lower_inf(valid_period) AND NOT isempty(valid_period)");
                    table.ForeignKey(
                        name: "fk_conflict_records_historical_events_end_event_id",
                        column: x => x.end_event_id,
                        principalTable: "historical_events",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_conflict_records_historical_events_start_event_id",
                        column: x => x.start_event_id,
                        principalTable: "historical_events",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_conflict_records_regimes_regime_a_id",
                        column: x => x.regime_a_id,
                        principalTable: "regimes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_conflict_records_regimes_regime_b_id",
                        column: x => x.regime_b_id,
                        principalTable: "regimes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "ix_conflict_records_end_event_id",
                table: "conflict_records",
                column: "end_event_id");

            migrationBuilder.CreateIndex(
                name: "ix_conflict_records_regime_a_id",
                table: "conflict_records",
                column: "regime_a_id");

            migrationBuilder.CreateIndex(
                name: "ix_conflict_records_regime_b_id",
                table: "conflict_records",
                column: "regime_b_id");

            migrationBuilder.CreateIndex(
                name: "ix_conflict_records_start_event_id",
                table: "conflict_records",
                column: "start_event_id");

            migrationBuilder.CreateIndex(
                name: "ix_conflict_records_valid_period",
                table: "conflict_records",
                column: "valid_period")
                .Annotation("Npgsql:IndexMethod", "gist");

            // I5：不可刪除；只允許「一次」寫入撤回（retracted_at＋retraction_reason），其他欄位不可改；修正＝撤回後新增
            migrationBuilder.Sql("""
                CREATE FUNCTION wl_conflict_guard_update() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                  IF OLD.retracted_at IS NOT NULL THEN
                    RAISE EXCEPTION 'I5：衝突紀錄 % 已撤回，不可再修改', OLD.id
                      USING ERRCODE = 'restrict_violation';
                  END IF;
                  IF (to_jsonb(NEW) - 'retracted_at' - 'retraction_reason')
                     IS DISTINCT FROM (to_jsonb(OLD) - 'retracted_at' - 'retraction_reason') THEN
                    RAISE EXCEPTION 'I5：衝突紀錄 % 只允許寫入撤回（retracted_at／retraction_reason）；修正請撤回後新增', OLD.id
                      USING ERRCODE = 'restrict_violation';
                  END IF;
                  RETURN NEW;
                END $$;

                CREATE TRIGGER trg_conflict_records_guard_update BEFORE UPDATE ON conflict_records
                  FOR EACH ROW EXECUTE FUNCTION wl_conflict_guard_update();
                CREATE TRIGGER trg_conflict_records_forbid_delete BEFORE DELETE ON conflict_records
                  FOR EACH ROW EXECUTE FUNCTION wl_forbid_delete();
                CREATE TRIGGER trg_conflict_records_forbid_truncate BEFORE TRUNCATE ON conflict_records
                  FOR EACH STATEMENT EXECUTE FUNCTION wl_forbid_delete();
                """);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            throw new NotSupportedException("ConflictRecords 不支援 Down（會刪除史料）；請改開新資料庫。");
        }
    }
}
