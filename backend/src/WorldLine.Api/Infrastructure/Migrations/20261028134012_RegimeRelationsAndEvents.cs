using System;
using Microsoft.EntityFrameworkCore.Migrations;
using NetTopologySuite.Geometries;
using NpgsqlTypes;

#nullable disable

namespace WorldLine.Api.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class RegimeRelationsAndEvents : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "historical_events",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    event_kind = table.Column<string>(type: "character varying(16)", maxLength: 16, nullable: false),
                    parent_event_id = table.Column<Guid>(type: "uuid", nullable: true),
                    summary = table.Column<string>(type: "jsonb", nullable: true),
                    occurred = table.Column<NpgsqlRange<DateOnly>>(type: "daterange", nullable: false),
                    date_precision = table.Column<string>(type: "character varying(8)", maxLength: 8, nullable: false),
                    local_time_zone = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: true),
                    time_note = table.Column<string>(type: "jsonb", nullable: true),
                    location = table.Column<Geometry>(type: "geometry(Geometry,4326)", nullable: true),
                    retracted_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    retraction_reason = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    updated_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    version = table.Column<int>(type: "integer", nullable: false, defaultValue: 0)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_historical_events", x => x.id);
                    table.CheckConstraint("ck_historical_events_kind", "event_kind IN ('war', 'campaign', 'battle', 'treaty', 'armistice', 'surrender', 'political', 'atrocity')");
                    table.CheckConstraint("ck_historical_events_occurred_bounded", "NOT lower_inf(occurred) AND NOT upper_inf(occurred)");
                    table.CheckConstraint("ck_historical_events_precision", "date_precision IN ('day', 'month', 'year')");
                    table.CheckConstraint("ck_historical_events_time_note_object", "time_note IS NULL OR jsonb_typeof(time_note) = 'object'");
                    table.ForeignKey(
                        name: "fk_historical_events_historical_events_parent_event_id",
                        column: x => x.parent_event_id,
                        principalTable: "historical_events",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "regime_relations",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    regime_a_id = table.Column<Guid>(type: "uuid", nullable: false),
                    regime_b_id = table.Column<Guid>(type: "uuid", nullable: false),
                    relation_type = table.Column<string>(type: "character varying(24)", maxLength: 24, nullable: false),
                    valid_period = table.Column<NpgsqlRange<DateOnly>>(type: "daterange", nullable: false),
                    start_uncertainty = table.Column<NpgsqlRange<DateOnly>>(type: "daterange", nullable: true),
                    end_uncertainty = table.Column<NpgsqlRange<DateOnly>>(type: "daterange", nullable: true),
                    note = table.Column<string>(type: "jsonb", nullable: true),
                    retracted_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    retraction_reason = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    version = table.Column<int>(type: "integer", nullable: false, defaultValue: 0)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_regime_relations", x => x.id);
                    table.CheckConstraint("ck_regime_relations_distinct", "regime_a_id <> regime_b_id");
                    table.CheckConstraint("ck_regime_relations_note_object", "note IS NULL OR jsonb_typeof(note) = 'object'");
                    table.CheckConstraint("ck_regime_relations_start_bounded", "NOT lower_inf(valid_period)");
                    table.CheckConstraint("ck_regime_relations_type", "relation_type IN ('at_war', 'alliance', 'non_aggression_pact', 'patron_puppet', 'trade')");
                    table.ForeignKey(
                        name: "fk_regime_relations_regimes_regime_a_id",
                        column: x => x.regime_a_id,
                        principalTable: "regimes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_regime_relations_regimes_regime_b_id",
                        column: x => x.regime_b_id,
                        principalTable: "regimes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "ix_events_occurred",
                table: "historical_events",
                column: "occurred")
                .Annotation("Npgsql:IndexMethod", "gist");

            migrationBuilder.CreateIndex(
                name: "ix_historical_events_parent_event_id",
                table: "historical_events",
                column: "parent_event_id");

            migrationBuilder.CreateIndex(
                name: "ix_regime_relations_period",
                table: "regime_relations",
                column: "valid_period")
                .Annotation("Npgsql:IndexMethod", "gist");

            migrationBuilder.CreateIndex(
                name: "ix_regime_relations_regime_a_id",
                table: "regime_relations",
                column: "regime_a_id");

            migrationBuilder.CreateIndex(
                name: "ix_regime_relations_regime_b_id",
                table: "regime_relations",
                column: "regime_b_id");

            // I5：新表同樣禁止 DELETE／TRUNCATE（函式於 M0VersionGuards 建立）
            foreach (var t in new[] { "regime_relations", "historical_events" })
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
            throw new NotSupportedException("RegimeRelationsAndEvents 不支援 Down（會刪除史料）；請改開新資料庫。");
        }
    }
}
