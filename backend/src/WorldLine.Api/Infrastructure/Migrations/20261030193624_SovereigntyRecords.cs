using System;
using Microsoft.EntityFrameworkCore.Migrations;
using NetTopologySuite.Geometries;
using NpgsqlTypes;

#nullable disable

namespace WorldLine.Api.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class SovereigntyRecords : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "sovereignty_records",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    regime_id = table.Column<Guid>(type: "uuid", nullable: false),
                    geom = table.Column<MultiPolygon>(type: "geometry(MultiPolygon,4326)", nullable: false),
                    valid_period = table.Column<NpgsqlRange<DateOnly>>(type: "daterange", nullable: false),
                    layer_status = table.Column<string>(type: "character varying(16)", maxLength: 16, nullable: false),
                    start_event_id = table.Column<Guid>(type: "uuid", nullable: true),
                    end_event_id = table.Column<Guid>(type: "uuid", nullable: true),
                    geometry_source_id = table.Column<Guid>(type: "uuid", nullable: false),
                    geometry_locator = table.Column<string>(type: "text", nullable: false),
                    geometry_license = table.Column<string>(type: "character varying(16)", maxLength: 16, nullable: false),
                    attribution = table.Column<string>(type: "text", nullable: true),
                    ohm_relation_id = table.Column<long>(type: "bigint", nullable: true),
                    ohm_version = table.Column<int>(type: "integer", nullable: true),
                    ohm_fetched_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    ohm_start_raw = table.Column<string>(type: "text", nullable: true),
                    ohm_end_raw = table.Column<string>(type: "text", nullable: true),
                    provenance = table.Column<string>(type: "jsonb", nullable: true),
                    note = table.Column<string>(type: "jsonb", nullable: true),
                    retracted_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    retraction_reason = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    version = table.Column<int>(type: "integer", nullable: false, defaultValue: 0)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_sovereignty_records", x => x.id);
                    table.CheckConstraint("ck_sovereignty_records_attribution", "geometry_license NOT IN ('cc_by', 'cc_by_sa') OR attribution IS NOT NULL");
                    table.CheckConstraint("ck_sovereignty_records_geometry_license", "geometry_license IN ('cc_by', 'cc_by_sa', 'cc0', 'pd_expired', 'us_federal_pd')");
                    table.CheckConstraint("ck_sovereignty_records_layer_status", "layer_status IN ('de_jure', 'not_sovereign')");
                    table.CheckConstraint("ck_sovereignty_records_note_object", "note IS NULL OR jsonb_typeof(note) = 'object'");
                    table.CheckConstraint("ck_sovereignty_records_ohm_pinned", "ohm_relation_id IS NULL OR (ohm_version IS NOT NULL AND ohm_fetched_at IS NOT NULL)");
                    table.CheckConstraint("ck_sovereignty_records_provenance_object", "provenance IS NULL OR jsonb_typeof(provenance) = 'object'");
                    table.CheckConstraint("ck_sovereignty_records_retraction_reason", "retracted_at IS NULL OR retraction_reason IS NOT NULL");
                    table.CheckConstraint("ck_sovereignty_records_start_bounded", "NOT lower_inf(valid_period) AND NOT isempty(valid_period)");
                    table.ForeignKey(
                        name: "fk_sovereignty_records_historical_events_end_event_id",
                        column: x => x.end_event_id,
                        principalTable: "historical_events",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_sovereignty_records_historical_events_start_event_id",
                        column: x => x.start_event_id,
                        principalTable: "historical_events",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_sovereignty_records_regimes_regime_id",
                        column: x => x.regime_id,
                        principalTable: "regimes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_sovereignty_records_sources_geometry_source_id",
                        column: x => x.geometry_source_id,
                        principalTable: "sources",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "ix_sovereignty_records_end_event_id",
                table: "sovereignty_records",
                column: "end_event_id");

            migrationBuilder.CreateIndex(
                name: "ix_sovereignty_records_geom",
                table: "sovereignty_records",
                column: "geom")
                .Annotation("Npgsql:IndexMethod", "gist");

            migrationBuilder.CreateIndex(
                name: "ix_sovereignty_records_geometry_source_id",
                table: "sovereignty_records",
                column: "geometry_source_id");

            migrationBuilder.CreateIndex(
                name: "ix_sovereignty_records_regime_id",
                table: "sovereignty_records",
                column: "regime_id");

            migrationBuilder.CreateIndex(
                name: "ix_sovereignty_records_start_event_id",
                table: "sovereignty_records",
                column: "start_event_id");

            migrationBuilder.CreateIndex(
                name: "ix_sovereignty_records_valid_period",
                table: "sovereignty_records",
                column: "valid_period")
                .Annotation("Npgsql:IndexMethod", "gist");

            // 同一政權的有效紀錄期間不可重疊（撤回的不算）
            migrationBuilder.Sql("""
                ALTER TABLE sovereignty_records
                  ADD CONSTRAINT ex_sovereignty_records_no_overlap
                  EXCLUDE USING gist (regime_id WITH =, valid_period WITH &&) WHERE (retracted_at IS NULL);
                """);

            // I5：不可刪除；只允許「一次」寫入撤回（retracted_at＋retraction_reason），其他欄位不可改；修正＝撤回後新增
            migrationBuilder.Sql("""
                CREATE FUNCTION wl_sovereignty_guard_update() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                  IF OLD.retracted_at IS NOT NULL THEN
                    RAISE EXCEPTION 'I5：主權紀錄 % 已撤回，不可再修改', OLD.id
                      USING ERRCODE = 'restrict_violation';
                  END IF;
                  IF (to_jsonb(NEW) - 'retracted_at' - 'retraction_reason')
                     IS DISTINCT FROM (to_jsonb(OLD) - 'retracted_at' - 'retraction_reason') THEN
                    RAISE EXCEPTION 'I5：主權紀錄 % 只允許寫入撤回（retracted_at／retraction_reason）；修正請撤回後新增', OLD.id
                      USING ERRCODE = 'restrict_violation';
                  END IF;
                  RETURN NEW;
                END $$;

                CREATE TRIGGER trg_sovereignty_records_guard_update BEFORE UPDATE ON sovereignty_records
                  FOR EACH ROW EXECUTE FUNCTION wl_sovereignty_guard_update();
                CREATE TRIGGER trg_sovereignty_records_forbid_delete BEFORE DELETE ON sovereignty_records
                  FOR EACH ROW EXECUTE FUNCTION wl_forbid_delete();
                CREATE TRIGGER trg_sovereignty_records_forbid_truncate BEFORE TRUNCATE ON sovereignty_records
                  FOR EACH STATEMENT EXECUTE FUNCTION wl_forbid_delete();
                """);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            throw new NotSupportedException("SovereigntyRecords 不支援 Down（會刪除史料）；請改開新資料庫。");
        }
    }
}
