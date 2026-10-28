using System;
using Microsoft.EntityFrameworkCore.Migrations;
using NetTopologySuite.Geometries;
using NpgsqlTypes;

#nullable disable

namespace WorldLine.Api.Migrations
{
    /// <inheritdoc />
    public partial class InitialSchema : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AlterDatabase()
                .Annotation("Npgsql:PostgresExtension:btree_gist", ",,")
                .Annotation("Npgsql:PostgresExtension:postgis", ",,");

            migrationBuilder.CreateTable(
                name: "lineage_presets",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    preset_name = table.Column<string>(type: "character varying(128)", maxLength: 128, nullable: false),
                    description = table.Column<string>(type: "text", nullable: true),
                    is_default = table.Column<bool>(type: "boolean", nullable: false, defaultValue: false),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_lineage_presets", x => x.id);
                    table.CheckConstraint("ck_lineage_presets_name_not_blank", "btrim(preset_name) <> ''");
                });

            migrationBuilder.CreateTable(
                name: "regimes",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    self_name = table.Column<string>(type: "character varying(128)", maxLength: 128, nullable: false),
                    status = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: false, defaultValue: "existing"),
                    predecessor_regime_id = table.Column<Guid>(type: "uuid", nullable: true),
                    origin_transition_type = table.Column<string>(type: "character varying(16)", maxLength: 16, nullable: true),
                    destroyed_by_regime_id = table.Column<Guid>(type: "uuid", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    updated_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    version = table.Column<int>(type: "integer", nullable: false, defaultValue: 0)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_regimes", x => x.id);
                    table.CheckConstraint("ck_regimes_destroyed_by_iff_destroyed", "(status = 'destroyed') = (destroyed_by_regime_id IS NOT NULL)");
                    table.CheckConstraint("ck_regimes_not_destroyed_by_self", "destroyed_by_regime_id <> id");
                    table.CheckConstraint("ck_regimes_not_own_predecessor", "predecessor_regime_id <> id");
                    table.CheckConstraint("ck_regimes_origin_transition_type", "origin_transition_type IS NULL OR origin_transition_type IN ('split', 'abdication')");
                    table.CheckConstraint("ck_regimes_predecessor_pair", "(predecessor_regime_id IS NULL) = (origin_transition_type IS NULL)");
                    table.CheckConstraint("ck_regimes_self_name_not_blank", "btrim(self_name) <> ''");
                    table.CheckConstraint("ck_regimes_status", "status IN ('existing', 'split', 'abdicated', 'destroyed')");
                    table.ForeignKey(
                        name: "fk_regimes_regimes_destroyed_by_regime_id",
                        column: x => x.destroyed_by_regime_id,
                        principalTable: "regimes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_regimes_regimes_predecessor_regime_id",
                        column: x => x.predecessor_regime_id,
                        principalTable: "regimes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "lineage_preset_members",
                columns: table => new
                {
                    preset_id = table.Column<Guid>(type: "uuid", nullable: false),
                    regime_id = table.Column<Guid>(type: "uuid", nullable: false),
                    sort_order = table.Column<int>(type: "integer", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_lineage_preset_members", x => new { x.preset_id, x.regime_id });
                    table.CheckConstraint("ck_lineage_preset_members_sort_order", "sort_order >= 0");
                    table.ForeignKey(
                        name: "fk_lineage_preset_members_lineage_presets_preset_id",
                        column: x => x.preset_id,
                        principalTable: "lineage_presets",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "fk_lineage_preset_members_regimes_regime_id",
                        column: x => x.regime_id,
                        principalTable: "regimes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "regime_aliases",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    regime_id = table.Column<Guid>(type: "uuid", nullable: false),
                    observer_regime_id = table.Column<Guid>(type: "uuid", nullable: true),
                    alias_name = table.Column<string>(type: "character varying(128)", maxLength: 128, nullable: false),
                    alias_type = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: false),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_regime_aliases", x => x.id);
                    table.CheckConstraint("ck_regime_aliases_alias_type", "alias_type IN ('contemporary', 'historiographic')");
                    table.CheckConstraint("ck_regime_aliases_name_not_blank", "btrim(alias_name) <> ''");
                    table.CheckConstraint("ck_regime_aliases_observer_not_self", "observer_regime_id <> regime_id");
                    table.ForeignKey(
                        name: "fk_regime_aliases_regimes_observer_regime_id",
                        column: x => x.observer_regime_id,
                        principalTable: "regimes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_regime_aliases_regimes_regime_id",
                        column: x => x.regime_id,
                        principalTable: "regimes",
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
                    relation_type = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: false),
                    valid_period = table.Column<NpgsqlRange<int>>(type: "int4range", nullable: false),
                    route = table.Column<MultiLineString>(type: "geometry(MultiLineString,4326)", nullable: true),
                    description = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_regime_relations", x => x.id);
                    table.CheckConstraint("ck_regime_relations_distinct_regimes", "regime_a_id <> regime_b_id");
                    table.CheckConstraint("ck_regime_relations_route_valid", "route IS NULL OR ST_IsValid(route)");
                    table.CheckConstraint("ck_regime_relations_type", "relation_type IN ('trade', 'tributary', 'marriage_alliance', 'alliance', 'hostility', 'other')");
                    table.CheckConstraint("ck_regime_relations_valid_period_bounded", "NOT isempty(valid_period) AND NOT lower_inf(valid_period) AND NOT upper_inf(valid_period)");
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

            migrationBuilder.CreateTable(
                name: "regime_territories",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    regime_id = table.Column<Guid>(type: "uuid", nullable: false),
                    valid_period = table.Column<NpgsqlRange<int>>(type: "int4range", nullable: false),
                    geom = table.Column<MultiPolygon>(type: "geometry(MultiPolygon,4326)", nullable: false),
                    is_disputed = table.Column<bool>(type: "boolean", nullable: false, defaultValue: false),
                    superseded_by = table.Column<Guid>(type: "uuid", nullable: true),
                    correction_reason = table.Column<string>(type: "text", nullable: true),
                    corrected_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    version = table.Column<int>(type: "integer", nullable: false, defaultValue: 0)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_regime_territories", x => x.id);
                    table.CheckConstraint("ck_regime_territories_correction_pair", "(superseded_by IS NULL) = (corrected_at IS NULL)");
                    table.CheckConstraint("ck_regime_territories_correction_reason", "superseded_by IS NULL OR (correction_reason IS NOT NULL AND btrim(correction_reason) <> '')");
                    table.CheckConstraint("ck_regime_territories_geom_valid", "ST_IsValid(geom)");
                    table.CheckConstraint("ck_regime_territories_not_self_superseded", "superseded_by <> id");
                    table.CheckConstraint("ck_regime_territories_valid_period_bounded", "NOT isempty(valid_period) AND NOT lower_inf(valid_period) AND NOT upper_inf(valid_period)");
                    table.ForeignKey(
                        name: "fk_regime_territories_regime_territories_superseded_by",
                        column: x => x.superseded_by,
                        principalTable: "regime_territories",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_regime_territories_regimes_regime_id",
                        column: x => x.regime_id,
                        principalTable: "regimes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "ix_lineage_preset_members_preset_id_sort_order",
                table: "lineage_preset_members",
                columns: new[] { "preset_id", "sort_order" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ix_lineage_preset_members_regime_id",
                table: "lineage_preset_members",
                column: "regime_id");

            migrationBuilder.CreateIndex(
                name: "ix_lineage_presets_preset_name",
                table: "lineage_presets",
                column: "preset_name",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ux_lineage_presets_single_default",
                table: "lineage_presets",
                column: "is_default",
                unique: true,
                filter: "is_default");

            migrationBuilder.CreateIndex(
                name: "ix_regime_aliases_alias_name",
                table: "regime_aliases",
                column: "alias_name");

            migrationBuilder.CreateIndex(
                name: "ix_regime_aliases_observer_regime_id",
                table: "regime_aliases",
                column: "observer_regime_id");

            migrationBuilder.CreateIndex(
                name: "ix_regime_aliases_regime_id_observer_regime_id_alias_name",
                table: "regime_aliases",
                columns: new[] { "regime_id", "observer_regime_id", "alias_name" },
                unique: true)
                .Annotation("Npgsql:NullsDistinct", false);

            migrationBuilder.CreateIndex(
                name: "ix_regime_relations_regime_a_id_regime_b_id",
                table: "regime_relations",
                columns: new[] { "regime_a_id", "regime_b_id" });

            migrationBuilder.CreateIndex(
                name: "ix_regime_relations_regime_b_id",
                table: "regime_relations",
                column: "regime_b_id");

            migrationBuilder.CreateIndex(
                name: "ix_regime_relations_valid_period",
                table: "regime_relations",
                column: "valid_period")
                .Annotation("Npgsql:IndexMethod", "gist");

            migrationBuilder.CreateIndex(
                name: "ix_regime_territories_geom",
                table: "regime_territories",
                column: "geom")
                .Annotation("Npgsql:IndexMethod", "gist");

            migrationBuilder.CreateIndex(
                name: "ix_regime_territories_regime_id",
                table: "regime_territories",
                column: "regime_id");

            migrationBuilder.CreateIndex(
                name: "ix_regime_territories_superseded_by",
                table: "regime_territories",
                column: "superseded_by",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ix_regime_territories_valid_period",
                table: "regime_territories",
                column: "valid_period")
                .Annotation("Npgsql:IndexMethod", "gist");

            migrationBuilder.CreateIndex(
                name: "ix_regimes_destroyed_by_regime_id",
                table: "regimes",
                column: "destroyed_by_regime_id");

            migrationBuilder.CreateIndex(
                name: "ix_regimes_predecessor_regime_id",
                table: "regimes",
                column: "predecessor_regime_id");

            migrationBuilder.CreateIndex(
                name: "ix_regimes_self_name",
                table: "regimes",
                column: "self_name");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "lineage_preset_members");

            migrationBuilder.DropTable(
                name: "regime_aliases");

            migrationBuilder.DropTable(
                name: "regime_relations");

            migrationBuilder.DropTable(
                name: "regime_territories");

            migrationBuilder.DropTable(
                name: "lineage_presets");

            migrationBuilder.DropTable(
                name: "regimes");
        }
    }
}
