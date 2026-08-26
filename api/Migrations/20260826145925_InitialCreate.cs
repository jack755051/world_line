using System;
using Microsoft.EntityFrameworkCore.Migrations;
using NetTopologySuite.Geometries;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;
using NpgsqlTypes;

#nullable disable

namespace WorldLine.Api.Migrations
{
    /// <inheritdoc />
    public partial class InitialCreate : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AlterDatabase()
                .Annotation("Npgsql:PostgresExtension:postgis", ",,");

            migrationBuilder.CreateTable(
                name: "event_tags",
                columns: table => new
                {
                    id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    tag_name = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_event_tags", x => x.id);
                });

            migrationBuilder.CreateTable(
                name: "historical_events",
                columns: table => new
                {
                    id = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: false),
                    name = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                    parent_event_id = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: true),
                    start_edtf = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: false),
                    end_edtf = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: false),
                    start_decimal = table.Column<decimal>(type: "numeric(8,3)", nullable: false),
                    end_decimal = table.Column<decimal>(type: "numeric(8,3)", nullable: false),
                    origin_point = table.Column<Point>(type: "geometry(Point,4326)", nullable: true),
                    influence_area = table.Column<MultiPolygon>(type: "geometry(MultiPolygon,4326)", nullable: true),
                    routes = table.Column<MultiLineString>(type: "geometry(MultiLineString,4326)", nullable: true),
                    sections = table.Column<string>(type: "jsonb", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    updated_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_historical_events", x => x.id);
                    table.ForeignKey(
                        name: "fk_historical_events_historical_events_parent_event_id",
                        column: x => x.parent_event_id,
                        principalTable: "historical_events",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "lineage_presets",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    preset_name = table.Column<string>(type: "character varying(128)", maxLength: 128, nullable: false),
                    description = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_lineage_presets", x => x.id);
                });

            migrationBuilder.CreateTable(
                name: "observer_categories",
                columns: table => new
                {
                    id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    category_name = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_observer_categories", x => x.id);
                });

            migrationBuilder.CreateTable(
                name: "place_names",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    historical_name = table.Column<string>(type: "character varying(128)", maxLength: 128, nullable: false),
                    modern_name = table.Column<string>(type: "character varying(128)", maxLength: 128, nullable: true),
                    valid_period = table.Column<NpgsqlRange<int>>(type: "int4range", nullable: true),
                    geom = table.Column<Point>(type: "geometry(Point,4326)", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_place_names", x => x.id);
                });

            migrationBuilder.CreateTable(
                name: "regimes",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    self_name = table.Column<string>(type: "character varying(128)", maxLength: 128, nullable: false),
                    status = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: false),
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
                name: "historical_event_controversies",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    event_id = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: true),
                    topic = table.Column<string>(type: "character varying(128)", maxLength: 128, nullable: false),
                    neutral_description = table.Column<string>(type: "text", nullable: false),
                    viewpoints = table.Column<string>(type: "jsonb", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_historical_event_controversies", x => x.id);
                    table.ForeignKey(
                        name: "fk_historical_event_controversies_historical_events_event_id",
                        column: x => x.event_id,
                        principalTable: "historical_events",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "historical_event_tag_map",
                columns: table => new
                {
                    event_id = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: false),
                    tag_id = table.Column<int>(type: "integer", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_historical_event_tag_map", x => new { x.event_id, x.tag_id });
                    table.ForeignKey(
                        name: "fk_historical_event_tag_map_event_tags_tag_id",
                        column: x => x.tag_id,
                        principalTable: "event_tags",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "fk_historical_event_tag_map_historical_events_event_id",
                        column: x => x.event_id,
                        principalTable: "historical_events",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "historical_event_perspectives",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    event_id = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: true),
                    regime_id = table.Column<Guid>(type: "uuid", nullable: true),
                    observer_category_id = table.Column<int>(type: "integer", nullable: true),
                    local_name = table.Column<string>(type: "character varying(128)", maxLength: 128, nullable: false),
                    narrative_summary = table.Column<string>(type: "text", nullable: false),
                    official_justification = table.Column<string>(type: "text", nullable: true),
                    primary_sources = table.Column<string>(type: "jsonb", nullable: true),
                    claimed_casualties = table.Column<string>(type: "jsonb", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_historical_event_perspectives", x => x.id);
                    table.ForeignKey(
                        name: "fk_historical_event_perspectives_historical_events_event_id",
                        column: x => x.event_id,
                        principalTable: "historical_events",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "fk_historical_event_perspectives_observer_categories_observer_",
                        column: x => x.observer_category_id,
                        principalTable: "observer_categories",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_historical_event_perspectives_regimes_regime_id",
                        column: x => x.regime_id,
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
                    alias_type = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_regime_aliases", x => x.id);
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

            migrationBuilder.CreateTable(
                name: "reign_eras",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    regime_id = table.Column<Guid>(type: "uuid", nullable: false),
                    era_name = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: false),
                    start_year = table.Column<int>(type: "integer", nullable: false),
                    end_year = table.Column<int>(type: "integer", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_reign_eras", x => x.id);
                    table.ForeignKey(
                        name: "fk_reign_eras_regimes_regime_id",
                        column: x => x.regime_id,
                        principalTable: "regimes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "ix_event_tags_tag_name",
                table: "event_tags",
                column: "tag_name",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ix_historical_event_controversies_event_id",
                table: "historical_event_controversies",
                column: "event_id");

            migrationBuilder.CreateIndex(
                name: "ix_historical_event_perspectives_event_id",
                table: "historical_event_perspectives",
                column: "event_id");

            migrationBuilder.CreateIndex(
                name: "ix_historical_event_perspectives_observer_category_id",
                table: "historical_event_perspectives",
                column: "observer_category_id");

            migrationBuilder.CreateIndex(
                name: "ix_historical_event_perspectives_regime_id",
                table: "historical_event_perspectives",
                column: "regime_id");

            migrationBuilder.CreateIndex(
                name: "ix_historical_event_tag_map_tag_id",
                table: "historical_event_tag_map",
                column: "tag_id");

            migrationBuilder.CreateIndex(
                name: "ix_historical_events_parent_event_id",
                table: "historical_events",
                column: "parent_event_id");

            migrationBuilder.CreateIndex(
                name: "ix_lineage_preset_members_regime_id",
                table: "lineage_preset_members",
                column: "regime_id");

            migrationBuilder.CreateIndex(
                name: "ix_observer_categories_category_name",
                table: "observer_categories",
                column: "category_name",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ix_regime_aliases_observer_regime_id",
                table: "regime_aliases",
                column: "observer_regime_id");

            migrationBuilder.CreateIndex(
                name: "ix_regime_aliases_regime_id",
                table: "regime_aliases",
                column: "regime_id");

            migrationBuilder.CreateIndex(
                name: "ix_regime_relations_regime_a_id",
                table: "regime_relations",
                column: "regime_a_id");

            migrationBuilder.CreateIndex(
                name: "ix_regime_relations_regime_b_id",
                table: "regime_relations",
                column: "regime_b_id");

            migrationBuilder.CreateIndex(
                name: "ix_regime_territories_regime_id",
                table: "regime_territories",
                column: "regime_id");

            migrationBuilder.CreateIndex(
                name: "ix_regime_territories_superseded_by",
                table: "regime_territories",
                column: "superseded_by");

            migrationBuilder.CreateIndex(
                name: "ix_regimes_destroyed_by_regime_id",
                table: "regimes",
                column: "destroyed_by_regime_id");

            migrationBuilder.CreateIndex(
                name: "ix_regimes_predecessor_regime_id",
                table: "regimes",
                column: "predecessor_regime_id");

            migrationBuilder.CreateIndex(
                name: "ix_reign_eras_regime_id",
                table: "reign_eras",
                column: "regime_id");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "historical_event_controversies");

            migrationBuilder.DropTable(
                name: "historical_event_perspectives");

            migrationBuilder.DropTable(
                name: "historical_event_tag_map");

            migrationBuilder.DropTable(
                name: "lineage_preset_members");

            migrationBuilder.DropTable(
                name: "place_names");

            migrationBuilder.DropTable(
                name: "regime_aliases");

            migrationBuilder.DropTable(
                name: "regime_relations");

            migrationBuilder.DropTable(
                name: "regime_territories");

            migrationBuilder.DropTable(
                name: "reign_eras");

            migrationBuilder.DropTable(
                name: "observer_categories");

            migrationBuilder.DropTable(
                name: "event_tags");

            migrationBuilder.DropTable(
                name: "historical_events");

            migrationBuilder.DropTable(
                name: "lineage_presets");

            migrationBuilder.DropTable(
                name: "regimes");
        }
    }
}
