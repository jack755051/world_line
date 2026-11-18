using System;
using Microsoft.EntityFrameworkCore.Migrations;
using NetTopologySuite.Geometries;
using NpgsqlTypes;

#nullable disable

namespace WorldLine.Api.Infrastructure.Migrations
{
    /// <summary>
    /// 戰役 C1（ARCHITECTURE §19.1、§19.5 C1，D13＝A′，2026-11-11，新增式）：新表 battle_profiles、battle_phases、
    /// battle_map_features、battle_units 與各自的 citation 表（§16.4.1／§19.1.7 統一欄位）。
    /// 不改任何既有表。person_event_participations、battle_figures 留到 C3／C4。
    /// I5：八張表全部禁止 DELETE、撤回後不可改回（trigger 以 SQL 建立）。
    /// 寫入層檢查（不在 DB）：event_kind='battle'、交戰方 ≥ 2、階段 period 落在 occurred 內、quote ≤ 80 字。
    /// 只寫檔，未套用到任何資料庫（Tai 2026-11-11 派工）。
    /// </summary>
    public partial class BattleC1 : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "battle_profiles",
                columns: table => new
                {
                    event_id = table.Column<Guid>(type: "uuid", nullable: false),
                    slug = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: false),
                    name = table.Column<string>(type: "jsonb", nullable: false),
                    objective = table.Column<string>(type: "jsonb", nullable: false),
                    objective_kind = table.Column<string>(type: "character varying(8)", maxLength: 8, nullable: false),
                    theater_area = table.Column<MultiPolygon>(type: "geometry(MultiPolygon,4326)", nullable: true),
                    conflict_record_id = table.Column<Guid>(type: "uuid", nullable: true),
                    outcome_kind = table.Column<string>(type: "character varying(16)", maxLength: 16, nullable: true),
                    outcome_text = table.Column<string>(type: "jsonb", nullable: true),
                    control_change = table.Column<string>(type: "jsonb", nullable: false),
                    status = table.Column<string>(type: "character varying(8)", maxLength: 8, nullable: false, defaultValue: "pending"),
                    retracted_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    retraction_reason = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_battle_profiles", x => x.event_id);
                    table.CheckConstraint("ck_battle_profiles_control_change_object", "jsonb_typeof(control_change) = 'object'");
                    table.CheckConstraint("ck_battle_profiles_name_object", "jsonb_typeof(name) = 'object'");
                    table.CheckConstraint("ck_battle_profiles_objective_kind", "objective_kind IN ('place', 'line', 'regime')");
                    table.CheckConstraint("ck_battle_profiles_objective_object", "jsonb_typeof(objective) = 'object'");
                    table.CheckConstraint("ck_battle_profiles_outcome_kind", "outcome_kind IS NULL OR outcome_kind IN ('decisive', 'indecisive', 'withdrawal', 'stalemate', 'other')");
                    table.CheckConstraint("ck_battle_profiles_outcome_text_object", "outcome_text IS NULL OR jsonb_typeof(outcome_text) = 'object'");
                    table.CheckConstraint("ck_battle_profiles_retraction_reason", "retracted_at IS NULL OR retraction_reason IS NOT NULL");
                    table.CheckConstraint("ck_battle_profiles_slug", "slug ~ '^[a-z0-9]+([_-][a-z0-9]+)*$'");
                    table.CheckConstraint("ck_battle_profiles_status", "status IN ('verified', 'pending')");
                    table.ForeignKey(
                        name: "fk_battle_profiles_conflict_records_conflict_record_id",
                        column: x => x.conflict_record_id,
                        principalTable: "conflict_records",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_battle_profiles_historical_events_event_id",
                        column: x => x.event_id,
                        principalTable: "historical_events",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "battle_units",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    event_id = table.Column<Guid>(type: "uuid", nullable: false),
                    side_regime_id = table.Column<Guid>(type: "uuid", nullable: false),
                    parent_unit_id = table.Column<Guid>(type: "uuid", nullable: true),
                    unit_name = table.Column<string>(type: "jsonb", nullable: false),
                    unit_echelon = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: true),
                    status = table.Column<string>(type: "character varying(8)", maxLength: 8, nullable: false, defaultValue: "pending"),
                    retracted_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    retraction_reason = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_battle_units", x => x.id);
                    table.CheckConstraint("ck_battle_units_not_own_parent", "parent_unit_id IS NULL OR parent_unit_id <> id");
                    table.CheckConstraint("ck_battle_units_retraction_reason", "retracted_at IS NULL OR retraction_reason IS NOT NULL");
                    table.CheckConstraint("ck_battle_units_status", "status IN ('verified', 'pending')");
                    table.CheckConstraint("ck_battle_units_unit_name_object", "jsonb_typeof(unit_name) = 'object'");
                    table.ForeignKey(
                        name: "fk_battle_units_battle_units_parent_unit_id",
                        column: x => x.parent_unit_id,
                        principalTable: "battle_units",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_battle_units_historical_events_event_id",
                        column: x => x.event_id,
                        principalTable: "historical_events",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_battle_units_regimes_side_regime_id",
                        column: x => x.side_regime_id,
                        principalTable: "regimes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "battle_phases",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    event_id = table.Column<Guid>(type: "uuid", nullable: false),
                    seq = table.Column<int>(type: "integer", nullable: false),
                    name = table.Column<string>(type: "jsonb", nullable: false),
                    period = table.Column<NpgsqlRange<DateOnly>>(type: "daterange", nullable: false),
                    start_precision = table.Column<string>(type: "character varying(8)", maxLength: 8, nullable: false),
                    end_precision = table.Column<string>(type: "character varying(8)", maxLength: 8, nullable: false),
                    summary = table.Column<string>(type: "jsonb", nullable: true),
                    status = table.Column<string>(type: "character varying(8)", maxLength: 8, nullable: false, defaultValue: "pending"),
                    retracted_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    retraction_reason = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_battle_phases", x => x.id);
                    table.CheckConstraint("ck_battle_phases_end_precision", "end_precision IN ('day', 'month', 'year')");
                    table.CheckConstraint("ck_battle_phases_name_object", "jsonb_typeof(name) = 'object'");
                    table.CheckConstraint("ck_battle_phases_period_bounded", "NOT isempty(period) AND NOT lower_inf(period) AND NOT upper_inf(period)");
                    table.CheckConstraint("ck_battle_phases_retraction_reason", "retracted_at IS NULL OR retraction_reason IS NOT NULL");
                    table.CheckConstraint("ck_battle_phases_seq", "seq >= 1");
                    table.CheckConstraint("ck_battle_phases_start_precision", "start_precision IN ('day', 'month', 'year')");
                    table.CheckConstraint("ck_battle_phases_status", "status IN ('verified', 'pending')");
                    table.CheckConstraint("ck_battle_phases_summary_object", "summary IS NULL OR jsonb_typeof(summary) = 'object'");
                    table.ForeignKey(
                        name: "fk_battle_phases_battle_profiles_event_id",
                        column: x => x.event_id,
                        principalTable: "battle_profiles",
                        principalColumn: "event_id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "battle_profile_citations",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    event_id = table.Column<Guid>(type: "uuid", nullable: false),
                    field = table.Column<string>(type: "character varying(16)", maxLength: 16, nullable: false),
                    source_id = table.Column<Guid>(type: "uuid", nullable: false),
                    locator = table.Column<string>(type: "text", nullable: false),
                    quote = table.Column<string>(type: "text", nullable: false),
                    quote_lang = table.Column<string>(type: "character varying(35)", maxLength: 35, nullable: true),
                    evidence_note = table.Column<string>(type: "text", nullable: true),
                    accessed_on = table.Column<DateOnly>(type: "date", nullable: false),
                    grade = table.Column<string>(type: "character varying(1)", maxLength: 1, nullable: false),
                    date_precision = table.Column<string>(type: "character varying(8)", maxLength: 8, nullable: true),
                    policy_version = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: true),
                    retracted_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    retraction_reason = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_battle_profile_citations", x => x.id);
                    table.CheckConstraint("ck_battle_profile_citations_date_precision", "date_precision IS NULL OR date_precision IN ('day', 'month', 'year')");
                    table.CheckConstraint("ck_battle_profile_citations_field", "field IN ('objective', 'control_change', 'outcome', 'theater_area', 'name')");
                    table.CheckConstraint("ck_battle_profile_citations_grade", "grade IN ('A', 'B')");
                    table.CheckConstraint("ck_battle_profile_citations_locator_not_blank", "btrim(locator) <> ''");
                    table.CheckConstraint("ck_battle_profile_citations_quote_not_blank", "btrim(quote) <> ''");
                    table.CheckConstraint("ck_battle_profile_citations_retraction_reason", "retracted_at IS NULL OR retraction_reason IS NOT NULL");
                    table.ForeignKey(
                        name: "fk_battle_profile_citations_battle_profiles_event_id",
                        column: x => x.event_id,
                        principalTable: "battle_profiles",
                        principalColumn: "event_id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_battle_profile_citations_sources_source_id",
                        column: x => x.source_id,
                        principalTable: "sources",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "battle_unit_citations",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    unit_id = table.Column<Guid>(type: "uuid", nullable: false),
                    source_id = table.Column<Guid>(type: "uuid", nullable: false),
                    locator = table.Column<string>(type: "text", nullable: false),
                    quote = table.Column<string>(type: "text", nullable: false),
                    quote_lang = table.Column<string>(type: "character varying(35)", maxLength: 35, nullable: true),
                    evidence_note = table.Column<string>(type: "text", nullable: true),
                    accessed_on = table.Column<DateOnly>(type: "date", nullable: false),
                    grade = table.Column<string>(type: "character varying(1)", maxLength: 1, nullable: false),
                    date_precision = table.Column<string>(type: "character varying(8)", maxLength: 8, nullable: true),
                    policy_version = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: true),
                    retracted_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    retraction_reason = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_battle_unit_citations", x => x.id);
                    table.CheckConstraint("ck_battle_unit_citations_date_precision", "date_precision IS NULL OR date_precision IN ('day', 'month', 'year')");
                    table.CheckConstraint("ck_battle_unit_citations_grade", "grade IN ('A', 'B')");
                    table.CheckConstraint("ck_battle_unit_citations_locator_not_blank", "btrim(locator) <> ''");
                    table.CheckConstraint("ck_battle_unit_citations_quote_not_blank", "btrim(quote) <> ''");
                    table.CheckConstraint("ck_battle_unit_citations_retraction_reason", "retracted_at IS NULL OR retraction_reason IS NOT NULL");
                    table.ForeignKey(
                        name: "fk_battle_unit_citations_battle_units_unit_id",
                        column: x => x.unit_id,
                        principalTable: "battle_units",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_battle_unit_citations_sources_source_id",
                        column: x => x.source_id,
                        principalTable: "sources",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "battle_map_features",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    phase_id = table.Column<Guid>(type: "uuid", nullable: false),
                    feature_key = table.Column<string>(type: "character varying(96)", maxLength: 96, nullable: false),
                    feature_kind = table.Column<string>(type: "character varying(8)", maxLength: 8, nullable: false),
                    side_regime_id = table.Column<Guid>(type: "uuid", nullable: true),
                    side_camp = table.Column<string>(type: "character varying(16)", maxLength: 16, nullable: true),
                    geom = table.Column<Geometry>(type: "geometry(Geometry,4326)", nullable: false),
                    label = table.Column<string>(type: "jsonb", nullable: true),
                    props = table.Column<string>(type: "jsonb", nullable: true),
                    geom_basis = table.Column<string>(type: "character varying(16)", maxLength: 16, nullable: false),
                    status = table.Column<string>(type: "character varying(8)", maxLength: 8, nullable: false, defaultValue: "pending"),
                    retracted_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    retraction_reason = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_battle_map_features", x => x.id);
                    table.CheckConstraint("ck_battle_map_features_derived_not_verified", "geom_basis <> 'derived' OR status <> 'verified'");
                    table.CheckConstraint("ck_battle_map_features_feature_key_not_blank", "btrim(feature_key) <> ''");
                    table.CheckConstraint("ck_battle_map_features_feature_kind", "feature_kind IN ('front', 'arrow', 'site')");
                    table.CheckConstraint("ck_battle_map_features_geom_basis", "geom_basis IN ('source_map', 'source_text', 'derived')");
                    table.CheckConstraint("ck_battle_map_features_geom_kind", "(feature_kind = 'front' AND GeometryType(geom) IN ('LINESTRING', 'MULTILINESTRING')) OR (feature_kind = 'arrow' AND GeometryType(geom) = 'LINESTRING') OR (feature_kind = 'site' AND GeometryType(geom) = 'POINT')");
                    table.CheckConstraint("ck_battle_map_features_geom_srid", "ST_SRID(geom) = 4326");
                    table.CheckConstraint("ck_battle_map_features_label_object", "label IS NULL OR jsonb_typeof(label) = 'object'");
                    table.CheckConstraint("ck_battle_map_features_props_object", "props IS NULL OR jsonb_typeof(props) = 'object'");
                    table.CheckConstraint("ck_battle_map_features_retraction_reason", "retracted_at IS NULL OR retraction_reason IS NOT NULL");
                    table.CheckConstraint("ck_battle_map_features_side_camp", "side_camp IS NULL OR side_camp IN ('allied', 'axis', 'soviet', 'contested', 'unknown')");
                    table.CheckConstraint("ck_battle_map_features_status", "status IN ('verified', 'pending')");
                    table.ForeignKey(
                        name: "fk_battle_map_features_battle_phases_phase_id",
                        column: x => x.phase_id,
                        principalTable: "battle_phases",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_battle_map_features_regimes_side_regime_id",
                        column: x => x.side_regime_id,
                        principalTable: "regimes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "battle_phase_citations",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    phase_id = table.Column<Guid>(type: "uuid", nullable: false),
                    claim_span = table.Column<NpgsqlRange<int>>(type: "int4range", nullable: true),
                    source_id = table.Column<Guid>(type: "uuid", nullable: false),
                    locator = table.Column<string>(type: "text", nullable: false),
                    quote = table.Column<string>(type: "text", nullable: false),
                    quote_lang = table.Column<string>(type: "character varying(35)", maxLength: 35, nullable: true),
                    evidence_note = table.Column<string>(type: "text", nullable: true),
                    accessed_on = table.Column<DateOnly>(type: "date", nullable: false),
                    grade = table.Column<string>(type: "character varying(1)", maxLength: 1, nullable: false),
                    date_precision = table.Column<string>(type: "character varying(8)", maxLength: 8, nullable: true),
                    policy_version = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: true),
                    retracted_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    retraction_reason = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_battle_phase_citations", x => x.id);
                    table.CheckConstraint("ck_battle_phase_citations_claim_span", "claim_span IS NULL OR (NOT isempty(claim_span) AND lower(claim_span) >= 0)");
                    table.CheckConstraint("ck_battle_phase_citations_date_precision", "date_precision IS NULL OR date_precision IN ('day', 'month', 'year')");
                    table.CheckConstraint("ck_battle_phase_citations_grade", "grade IN ('A', 'B')");
                    table.CheckConstraint("ck_battle_phase_citations_locator_not_blank", "btrim(locator) <> ''");
                    table.CheckConstraint("ck_battle_phase_citations_quote_not_blank", "btrim(quote) <> ''");
                    table.CheckConstraint("ck_battle_phase_citations_retraction_reason", "retracted_at IS NULL OR retraction_reason IS NOT NULL");
                    table.ForeignKey(
                        name: "fk_battle_phase_citations_battle_phases_phase_id",
                        column: x => x.phase_id,
                        principalTable: "battle_phases",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_battle_phase_citations_sources_source_id",
                        column: x => x.source_id,
                        principalTable: "sources",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "battle_map_feature_citations",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    feature_id = table.Column<Guid>(type: "uuid", nullable: false),
                    source_id = table.Column<Guid>(type: "uuid", nullable: false),
                    locator = table.Column<string>(type: "text", nullable: false),
                    quote = table.Column<string>(type: "text", nullable: false),
                    quote_lang = table.Column<string>(type: "character varying(35)", maxLength: 35, nullable: true),
                    evidence_note = table.Column<string>(type: "text", nullable: true),
                    accessed_on = table.Column<DateOnly>(type: "date", nullable: false),
                    grade = table.Column<string>(type: "character varying(1)", maxLength: 1, nullable: false),
                    date_precision = table.Column<string>(type: "character varying(8)", maxLength: 8, nullable: true),
                    policy_version = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: true),
                    retracted_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    retraction_reason = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_battle_map_feature_citations", x => x.id);
                    table.CheckConstraint("ck_battle_map_feature_citations_date_precision", "date_precision IS NULL OR date_precision IN ('day', 'month', 'year')");
                    table.CheckConstraint("ck_battle_map_feature_citations_grade", "grade IN ('A', 'B')");
                    table.CheckConstraint("ck_battle_map_feature_citations_locator_not_blank", "btrim(locator) <> ''");
                    table.CheckConstraint("ck_battle_map_feature_citations_quote_not_blank", "btrim(quote) <> ''");
                    table.CheckConstraint("ck_battle_map_feature_citations_retraction_reason", "retracted_at IS NULL OR retraction_reason IS NOT NULL");
                    table.ForeignKey(
                        name: "fk_battle_map_feature_citations_battle_map_features_feature_id",
                        column: x => x.feature_id,
                        principalTable: "battle_map_features",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_battle_map_feature_citations_sources_source_id",
                        column: x => x.source_id,
                        principalTable: "sources",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "ix_battle_map_feature_citations_feature_id",
                table: "battle_map_feature_citations",
                column: "feature_id");

            migrationBuilder.CreateIndex(
                name: "ix_battle_map_feature_citations_source_id",
                table: "battle_map_feature_citations",
                column: "source_id");

            migrationBuilder.CreateIndex(
                name: "ix_battle_map_features_feature_key",
                table: "battle_map_features",
                column: "feature_key",
                unique: true,
                filter: "retracted_at IS NULL");

            migrationBuilder.CreateIndex(
                name: "ix_battle_map_features_geom",
                table: "battle_map_features",
                column: "geom")
                .Annotation("Npgsql:IndexMethod", "gist");

            migrationBuilder.CreateIndex(
                name: "ix_battle_map_features_phase_id_feature_kind",
                table: "battle_map_features",
                columns: new[] { "phase_id", "feature_kind" });

            migrationBuilder.CreateIndex(
                name: "ix_battle_map_features_side_regime_id",
                table: "battle_map_features",
                column: "side_regime_id");

            migrationBuilder.CreateIndex(
                name: "ix_battle_phase_citations_phase_id",
                table: "battle_phase_citations",
                column: "phase_id");

            migrationBuilder.CreateIndex(
                name: "ix_battle_phase_citations_source_id",
                table: "battle_phase_citations",
                column: "source_id");

            migrationBuilder.CreateIndex(
                name: "ix_battle_phases_event_id_seq",
                table: "battle_phases",
                columns: new[] { "event_id", "seq" },
                unique: true,
                filter: "retracted_at IS NULL");

            migrationBuilder.CreateIndex(
                name: "ix_battle_profile_citations_event_id",
                table: "battle_profile_citations",
                column: "event_id");

            migrationBuilder.CreateIndex(
                name: "ix_battle_profile_citations_source_id",
                table: "battle_profile_citations",
                column: "source_id");

            migrationBuilder.CreateIndex(
                name: "ix_battle_profiles_conflict_record_id",
                table: "battle_profiles",
                column: "conflict_record_id");

            migrationBuilder.CreateIndex(
                name: "ix_battle_profiles_slug",
                table: "battle_profiles",
                column: "slug",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ix_battle_profiles_theater_area",
                table: "battle_profiles",
                column: "theater_area")
                .Annotation("Npgsql:IndexMethod", "gist");

            migrationBuilder.CreateIndex(
                name: "ix_battle_unit_citations_source_id",
                table: "battle_unit_citations",
                column: "source_id");

            migrationBuilder.CreateIndex(
                name: "ix_battle_unit_citations_unit_id",
                table: "battle_unit_citations",
                column: "unit_id");

            migrationBuilder.CreateIndex(
                name: "ix_battle_units_event_id",
                table: "battle_units",
                column: "event_id");

            migrationBuilder.CreateIndex(
                name: "ix_battle_units_parent_unit_id",
                table: "battle_units",
                column: "parent_unit_id");

            migrationBuilder.CreateIndex(
                name: "ix_battle_units_side_regime_id",
                table: "battle_units",
                column: "side_regime_id");

            // I5：只能軟撤回、不能 DELETE；撤回後不可改回。battle_profiles 以 event_id 為主鍵，其餘以 id。
            migrationBuilder.Sql("""
                CREATE OR REPLACE FUNCTION fn_battle_rows_guard()
                RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    IF TG_OP = 'DELETE' THEN
                        RAISE EXCEPTION '% I5: 不可刪除，請改用撤回', TG_TABLE_NAME;
                    END IF;
                    IF OLD.retracted_at IS NOT NULL AND NEW.retracted_at IS NULL THEN
                        RAISE EXCEPTION '% I5: retracted_at 不可撤銷', TG_TABLE_NAME;
                    END IF;
                    RETURN NEW;
                END;
                $$;
                CREATE TRIGGER trg_battle_profiles_guard BEFORE UPDATE OR DELETE ON battle_profiles
                FOR EACH ROW EXECUTE FUNCTION fn_battle_rows_guard();
                CREATE TRIGGER trg_battle_phases_guard BEFORE UPDATE OR DELETE ON battle_phases
                FOR EACH ROW EXECUTE FUNCTION fn_battle_rows_guard();
                CREATE TRIGGER trg_battle_map_features_guard BEFORE UPDATE OR DELETE ON battle_map_features
                FOR EACH ROW EXECUTE FUNCTION fn_battle_rows_guard();
                CREATE TRIGGER trg_battle_units_guard BEFORE UPDATE OR DELETE ON battle_units
                FOR EACH ROW EXECUTE FUNCTION fn_battle_rows_guard();
                CREATE TRIGGER trg_battle_profile_citations_guard BEFORE UPDATE OR DELETE ON battle_profile_citations
                FOR EACH ROW EXECUTE FUNCTION fn_battle_rows_guard();
                CREATE TRIGGER trg_battle_phase_citations_guard BEFORE UPDATE OR DELETE ON battle_phase_citations
                FOR EACH ROW EXECUTE FUNCTION fn_battle_rows_guard();
                CREATE TRIGGER trg_battle_map_feature_citations_guard BEFORE UPDATE OR DELETE ON battle_map_feature_citations
                FOR EACH ROW EXECUTE FUNCTION fn_battle_rows_guard();
                CREATE TRIGGER trg_battle_unit_citations_guard BEFORE UPDATE OR DELETE ON battle_unit_citations
                FOR EACH ROW EXECUTE FUNCTION fn_battle_rows_guard();
                """);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql("DROP TRIGGER IF EXISTS trg_battle_profiles_guard ON battle_profiles; DROP TRIGGER IF EXISTS trg_battle_phases_guard ON battle_phases; DROP TRIGGER IF EXISTS trg_battle_map_features_guard ON battle_map_features; DROP TRIGGER IF EXISTS trg_battle_units_guard ON battle_units; DROP TRIGGER IF EXISTS trg_battle_profile_citations_guard ON battle_profile_citations; DROP TRIGGER IF EXISTS trg_battle_phase_citations_guard ON battle_phase_citations; DROP TRIGGER IF EXISTS trg_battle_map_feature_citations_guard ON battle_map_feature_citations; DROP TRIGGER IF EXISTS trg_battle_unit_citations_guard ON battle_unit_citations; DROP FUNCTION IF EXISTS fn_battle_rows_guard();");

            migrationBuilder.DropTable(
                name: "battle_map_feature_citations");

            migrationBuilder.DropTable(
                name: "battle_phase_citations");

            migrationBuilder.DropTable(
                name: "battle_profile_citations");

            migrationBuilder.DropTable(
                name: "battle_unit_citations");

            migrationBuilder.DropTable(
                name: "battle_map_features");

            migrationBuilder.DropTable(
                name: "battle_units");

            migrationBuilder.DropTable(
                name: "battle_phases");

            migrationBuilder.DropTable(
                name: "battle_profiles");
        }
    }
}
