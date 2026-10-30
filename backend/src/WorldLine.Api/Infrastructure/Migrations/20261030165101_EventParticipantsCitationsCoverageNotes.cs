using System;
using Microsoft.EntityFrameworkCore.Migrations;
using NetTopologySuite.Geometries;
using NpgsqlTypes;

#nullable disable

namespace WorldLine.Api.Infrastructure.Migrations
{
    /// <summary>事件參與方、事件引用（PRD §6.3 event_participants／event_citations）與涵蓋備註（control_coverage_notes，R9）。2026-10-31，AI 提案・待拍板。</summary>
    public partial class EventParticipantsCitationsCoverageNotes : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "control_coverage_notes",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    theater_id = table.Column<Guid>(type: "uuid", nullable: true),
                    geom = table.Column<MultiPolygon>(type: "geometry(MultiPolygon,4326)", nullable: false),
                    valid_period = table.Column<NpgsqlRange<DateOnly>>(type: "daterange", nullable: false),
                    reason = table.Column<string>(type: "character varying(24)", maxLength: 24, nullable: false),
                    note = table.Column<string>(type: "jsonb", nullable: true),
                    research_ref = table.Column<string>(type: "text", nullable: true),
                    retracted_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    retraction_reason = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    version = table.Column<int>(type: "integer", nullable: false, defaultValue: 0)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_control_coverage_notes", x => x.id);
                    table.CheckConstraint("ck_control_coverage_notes_note_object", "note IS NULL OR jsonb_typeof(note) = 'object'");
                    table.CheckConstraint("ck_control_coverage_notes_period_bounded", "NOT lower_inf(valid_period) AND NOT upper_inf(valid_period) AND NOT isempty(valid_period)");
                    table.CheckConstraint("ck_control_coverage_notes_reason", "reason IN ('no_qualified_source', 'not_yet_digitized')");
                    table.CheckConstraint("ck_control_coverage_notes_retraction_reason", "retracted_at IS NULL OR retraction_reason IS NOT NULL");
                    table.ForeignKey(
                        name: "fk_control_coverage_notes_theaters_theater_id",
                        column: x => x.theater_id,
                        principalTable: "theaters",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "event_citations",
                columns: table => new
                {
                    event_id = table.Column<Guid>(type: "uuid", nullable: false),
                    source_id = table.Column<Guid>(type: "uuid", nullable: false),
                    locator = table.Column<string>(type: "text", nullable: false),
                    evidence_note = table.Column<string>(type: "text", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_event_citations", x => new { x.event_id, x.source_id, x.locator });
                    table.ForeignKey(
                        name: "fk_event_citations_historical_events_event_id",
                        column: x => x.event_id,
                        principalTable: "historical_events",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_event_citations_sources_source_id",
                        column: x => x.source_id,
                        principalTable: "sources",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "event_participants",
                columns: table => new
                {
                    event_id = table.Column<Guid>(type: "uuid", nullable: false),
                    regime_id = table.Column<Guid>(type: "uuid", nullable: false),
                    role = table.Column<string>(type: "character varying(16)", maxLength: 16, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_event_participants", x => new { x.event_id, x.regime_id, x.role });
                    table.CheckConstraint("ck_event_participants_role", "role IN ('belligerent', 'signatory', 'perpetrator', 'other')");
                    table.ForeignKey(
                        name: "fk_event_participants_historical_events_event_id",
                        column: x => x.event_id,
                        principalTable: "historical_events",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_event_participants_regimes_regime_id",
                        column: x => x.regime_id,
                        principalTable: "regimes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "ix_control_coverage_notes_geom",
                table: "control_coverage_notes",
                column: "geom")
                .Annotation("Npgsql:IndexMethod", "gist");

            migrationBuilder.CreateIndex(
                name: "ix_control_coverage_notes_theater_id",
                table: "control_coverage_notes",
                column: "theater_id");

            migrationBuilder.CreateIndex(
                name: "ix_control_coverage_notes_valid_period",
                table: "control_coverage_notes",
                column: "valid_period")
                .Annotation("Npgsql:IndexMethod", "gist");

            migrationBuilder.CreateIndex(
                name: "ix_event_citations_source_id",
                table: "event_citations",
                column: "source_id");

            migrationBuilder.CreateIndex(
                name: "ix_event_participants_regime_id",
                table: "event_participants",
                column: "regime_id");

            // I5：事件參與方、事件引用寫入後不可改、不可刪；涵蓋備註只允許「一次」寫入撤回，其他欄位不可改、不可刪
            migrationBuilder.Sql("""
                CREATE FUNCTION wl_coverage_note_guard_update() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                  IF OLD.retracted_at IS NOT NULL THEN
                    RAISE EXCEPTION 'I5：涵蓋備註 % 已撤回，不可再修改', OLD.id
                      USING ERRCODE = 'restrict_violation';
                  END IF;
                  IF (to_jsonb(NEW) - 'retracted_at' - 'retraction_reason')
                     IS DISTINCT FROM (to_jsonb(OLD) - 'retracted_at' - 'retraction_reason') THEN
                    RAISE EXCEPTION 'I5：涵蓋備註 % 只允許寫入撤回（retracted_at／retraction_reason）；修正請撤回後新增', OLD.id
                      USING ERRCODE = 'restrict_violation';
                  END IF;
                  RETURN NEW;
                END $$;

                CREATE TRIGGER trg_control_coverage_notes_guard_update BEFORE UPDATE ON control_coverage_notes
                  FOR EACH ROW EXECUTE FUNCTION wl_coverage_note_guard_update();
                CREATE TRIGGER trg_event_participants_forbid_update BEFORE UPDATE ON event_participants
                  FOR EACH ROW EXECUTE FUNCTION wl_forbid_update();
                CREATE TRIGGER trg_event_citations_forbid_update BEFORE UPDATE ON event_citations
                  FOR EACH ROW EXECUTE FUNCTION wl_forbid_update();
                """);
            foreach (var t in new[] { "event_participants", "event_citations", "control_coverage_notes" })
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
            throw new NotSupportedException("EventParticipantsCitationsCoverageNotes 不支援 Down（會刪除史料）；請改開新資料庫。");
        }
    }
}
