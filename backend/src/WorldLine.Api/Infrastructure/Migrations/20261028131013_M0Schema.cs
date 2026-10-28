using System;
using Microsoft.EntityFrameworkCore.Migrations;
using NetTopologySuite.Geometries;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;
using NpgsqlTypes;

#nullable disable

namespace WorldLine.Api.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class M0Schema : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AlterDatabase()
                .Annotation("Npgsql:PostgresExtension:btree_gist", ",,")
                .Annotation("Npgsql:PostgresExtension:postgis", ",,");

            migrationBuilder.CreateTable(
                name: "regimes",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    slug = table.Column<string>(type: "character varying(80)", maxLength: 80, nullable: false),
                    wikidata_qid = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: true),
                    retracted_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    retraction_reason = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    updated_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    version = table.Column<int>(type: "integer", nullable: false, defaultValue: 0)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_regimes", x => x.id);
                });

            migrationBuilder.CreateTable(
                name: "sources",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    source_kind = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: false),
                    title = table.Column<string>(type: "text", nullable: false),
                    publisher = table.Column<string>(type: "text", nullable: false),
                    authors = table.Column<string>(type: "text", nullable: true),
                    published_text = table.Column<string>(type: "text", nullable: true),
                    license_code = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: true),
                    license_evidence_url = table.Column<string>(type: "text", nullable: true),
                    url = table.Column<string>(type: "text", nullable: true),
                    archive_url = table.Column<string>(type: "text", nullable: true),
                    local_copy_path = table.Column<string>(type: "text", nullable: true),
                    catalog_id = table.Column<string>(type: "text", nullable: true),
                    note = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    updated_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    version = table.Column<int>(type: "integer", nullable: false, defaultValue: 0)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_sources", x => x.id);
                    table.CheckConstraint("ck_sources_publisher_not_blank", "btrim(publisher) <> ''");
                    table.CheckConstraint("ck_sources_source_kind", "source_kind IN ('map', 'atlas_map', 'treaty', 'official_record', 'trial_record', 'peer_reviewed', 'official_history', 'dataset')");
                });

            migrationBuilder.CreateTable(
                name: "theaters",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    code = table.Column<string>(type: "character varying(40)", maxLength: 40, nullable: false),
                    name = table.Column<string>(type: "jsonb", nullable: false),
                    extent = table.Column<MultiPolygon>(type: "geometry(MultiPolygon,4326)", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_theaters", x => x.id);
                });

            migrationBuilder.CreateTable(
                name: "control_records",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    controller_regime_id = table.Column<Guid>(type: "uuid", nullable: false),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_control_records", x => x.id);
                    table.ForeignKey(
                        name: "fk_control_records_regimes_controller_regime_id",
                        column: x => x.controller_regime_id,
                        principalTable: "regimes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "regime_names",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    regime_id = table.Column<Guid>(type: "uuid", nullable: false),
                    name_kind = table.Column<string>(type: "character varying(8)", maxLength: 8, nullable: false),
                    original_text = table.Column<string>(type: "text", nullable: false),
                    original_lang = table.Column<string>(type: "character varying(16)", maxLength: 16, nullable: false),
                    display = table.Column<string>(type: "jsonb", nullable: false),
                    observer_regime_id = table.Column<Guid>(type: "uuid", nullable: true),
                    valid_period = table.Column<NpgsqlRange<DateOnly>>(type: "daterange", nullable: true),
                    is_primary = table.Column<bool>(type: "boolean", nullable: false, defaultValue: false),
                    retracted_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    retraction_reason = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    version = table.Column<int>(type: "integer", nullable: false, defaultValue: 0)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_regime_names", x => x.id);
                    table.CheckConstraint("ck_regime_names_display_object", "jsonb_typeof(display) = 'object'");
                    table.CheckConstraint("ck_regime_names_exonym_observer", "name_kind = 'self' OR observer_regime_id IS NOT NULL");
                    table.CheckConstraint("ck_regime_names_name_kind", "name_kind IN ('self', 'exonym')");
                    table.ForeignKey(
                        name: "fk_regime_names_regimes_observer_regime_id",
                        column: x => x.observer_regime_id,
                        principalTable: "regimes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_regime_names_regimes_regime_id",
                        column: x => x.regime_id,
                        principalTable: "regimes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "reference_land",
                columns: table => new
                {
                    id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    geom = table.Column<MultiPolygon>(type: "geometry(MultiPolygon,4326)", nullable: false),
                    source_id = table.Column<Guid>(type: "uuid", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_reference_land", x => x.id);
                    table.ForeignKey(
                        name: "fk_reference_land_sources_source_id",
                        column: x => x.source_id,
                        principalTable: "sources",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "control_snapshots",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    theater_id = table.Column<Guid>(type: "uuid", nullable: false),
                    as_of = table.Column<DateOnly>(type: "date", nullable: false),
                    as_of_note = table.Column<string>(type: "jsonb", nullable: true),
                    attestation = table.Column<string>(type: "character varying(8)", maxLength: 8, nullable: false, defaultValue: "point"),
                    attested_period = table.Column<NpgsqlRange<DateOnly>>(type: "daterange", nullable: true),
                    title = table.Column<string>(type: "jsonb", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_control_snapshots", x => x.id);
                    table.CheckConstraint("ck_control_snapshots_attestation", "attestation IN ('point', 'interval')");
                    table.CheckConstraint("ck_control_snapshots_interval_period", "(attestation = 'interval') = (attested_period IS NOT NULL)");
                    table.ForeignKey(
                        name: "fk_control_snapshots_theaters_theater_id",
                        column: x => x.theater_id,
                        principalTable: "theaters",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "control_record_versions",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    control_record_id = table.Column<Guid>(type: "uuid", nullable: false),
                    snapshot_id = table.Column<Guid>(type: "uuid", nullable: false),
                    control_type = table.Column<string>(type: "character varying(24)", maxLength: 24, nullable: false),
                    patron_regime_id = table.Column<Guid>(type: "uuid", nullable: true),
                    valid_period = table.Column<NpgsqlRange<DateOnly>>(type: "daterange", nullable: false),
                    start_uncertainty = table.Column<NpgsqlRange<DateOnly>>(type: "daterange", nullable: true),
                    end_uncertainty = table.Column<NpgsqlRange<DateOnly>>(type: "daterange", nullable: true),
                    geom = table.Column<MultiPolygon>(type: "geometry(MultiPolygon,4326)", nullable: false),
                    is_disputed = table.Column<bool>(type: "boolean", nullable: false, defaultValue: false),
                    is_retraction = table.Column<bool>(type: "boolean", nullable: false, defaultValue: false),
                    revision_reason = table.Column<string>(type: "text", nullable: true),
                    superseded_by = table.Column<Guid>(type: "uuid", nullable: true),
                    superseded_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_control_record_versions", x => x.id);
                    table.CheckConstraint("ck_crv_control_type", "control_type IN ('direct_rule', 'military_occupation', 'puppet_administration', 'partial', 'contested')");
                    table.CheckConstraint("ck_crv_geom_valid", "ST_IsValid(geom)");
                    table.CheckConstraint("ck_crv_valid_period_bounded", "NOT lower_inf(valid_period) AND NOT upper_inf(valid_period)");
                    table.ForeignKey(
                        name: "fk_control_record_versions_control_record_versions_superseded_",
                        column: x => x.superseded_by,
                        principalTable: "control_record_versions",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_control_record_versions_control_records_control_record_id",
                        column: x => x.control_record_id,
                        principalTable: "control_records",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_control_record_versions_control_snapshots_snapshot_id",
                        column: x => x.snapshot_id,
                        principalTable: "control_snapshots",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_control_record_versions_regimes_patron_regime_id",
                        column: x => x.patron_regime_id,
                        principalTable: "regimes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "control_record_citations",
                columns: table => new
                {
                    control_record_version_id = table.Column<Guid>(type: "uuid", nullable: false),
                    source_id = table.Column<Guid>(type: "uuid", nullable: false),
                    locator = table.Column<string>(type: "text", nullable: false),
                    role = table.Column<string>(type: "character varying(24)", maxLength: 24, nullable: false, defaultValue: "primary"),
                    evidence_note = table.Column<string>(type: "text", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_control_record_citations", x => new { x.control_record_version_id, x.source_id, x.locator });
                    table.CheckConstraint("ck_crc_role", "role IN ('primary', 'auxiliary_geometry', 'date_check')");
                    table.ForeignKey(
                        name: "fk_control_record_citations_control_record_versions_control_re",
                        column: x => x.control_record_version_id,
                        principalTable: "control_record_versions",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_control_record_citations_sources_source_id",
                        column: x => x.source_id,
                        principalTable: "sources",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "ix_control_record_citations_source_id",
                table: "control_record_citations",
                column: "source_id");

            migrationBuilder.CreateIndex(
                name: "ix_control_record_versions_control_record_id",
                table: "control_record_versions",
                column: "control_record_id");

            migrationBuilder.CreateIndex(
                name: "ix_control_record_versions_patron_regime_id",
                table: "control_record_versions",
                column: "patron_regime_id");

            migrationBuilder.CreateIndex(
                name: "ix_control_record_versions_snapshot_id",
                table: "control_record_versions",
                column: "snapshot_id");

            migrationBuilder.CreateIndex(
                name: "ix_control_record_versions_superseded_by",
                table: "control_record_versions",
                column: "superseded_by");

            migrationBuilder.CreateIndex(
                name: "ix_crv_current_geom",
                table: "control_record_versions",
                column: "geom",
                filter: "superseded_by IS NULL")
                .Annotation("Npgsql:IndexMethod", "gist");

            migrationBuilder.CreateIndex(
                name: "ix_crv_current_period",
                table: "control_record_versions",
                column: "valid_period",
                filter: "superseded_by IS NULL")
                .Annotation("Npgsql:IndexMethod", "gist");

            migrationBuilder.CreateIndex(
                name: "ix_control_records_controller_regime_id",
                table: "control_records",
                column: "controller_regime_id");

            migrationBuilder.CreateIndex(
                name: "ix_control_snapshots_theater_id_as_of",
                table: "control_snapshots",
                columns: new[] { "theater_id", "as_of" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ix_reference_land_geom",
                table: "reference_land",
                column: "geom")
                .Annotation("Npgsql:IndexMethod", "gist");

            migrationBuilder.CreateIndex(
                name: "ix_reference_land_source_id",
                table: "reference_land",
                column: "source_id");

            migrationBuilder.CreateIndex(
                name: "ix_regime_names_observer_regime_id",
                table: "regime_names",
                column: "observer_regime_id");

            migrationBuilder.CreateIndex(
                name: "ix_regime_names_regime_id",
                table: "regime_names",
                column: "regime_id");

            migrationBuilder.CreateIndex(
                name: "ix_regimes_slug",
                table: "regimes",
                column: "slug",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ix_theaters_code",
                table: "theaters",
                column: "code",
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            // I5／「不刪資料」：不提供會刪表的 Down。要重建請另開新資料庫。
            throw new NotSupportedException("M0Schema 不支援 Down（會刪除史料）；請改開新資料庫。");
        }
    }
}
