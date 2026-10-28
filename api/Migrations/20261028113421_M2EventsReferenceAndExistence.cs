using System;
using Microsoft.EntityFrameworkCore.Migrations;
using NetTopologySuite.Geometries;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;
using NpgsqlTypes;

#nullable disable

namespace WorldLine.Api.Migrations
{
    /// <inheritdoc />
    public partial class M2EventsReferenceAndExistence : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<NpgsqlRange<int>>(
                name: "existence_period",
                table: "regimes",
                type: "int4range",
                nullable: false,
                defaultValue: new NpgsqlTypes.NpgsqlRange<int>(0, false, 0, false));

            migrationBuilder.AddColumn<bool>(
                name: "is_illustrative",
                table: "regime_territories",
                type: "boolean",
                nullable: false,
                defaultValue: false);

            migrationBuilder.AddColumn<string>(
                name: "source",
                table: "regime_territories",
                type: "text",
                nullable: true);

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
                    table.CheckConstraint("ck_event_tags_name", "tag_name ~ '^[a-z][a-z0-9_]*$'");
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
                    start_decimal = table.Column<decimal>(type: "numeric(8,3)", precision: 8, scale: 3, nullable: false),
                    end_decimal = table.Column<decimal>(type: "numeric(8,3)", precision: 8, scale: 3, nullable: false),
                    origin_point = table.Column<Point>(type: "geometry(Point,4326)", nullable: true),
                    influence_area = table.Column<MultiPolygon>(type: "geometry(MultiPolygon,4326)", nullable: true),
                    routes = table.Column<MultiLineString>(type: "geometry(MultiLineString,4326)", nullable: true),
                    sections = table.Column<string>(type: "jsonb", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    updated_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    version = table.Column<int>(type: "integer", nullable: false, defaultValue: 0)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_historical_events", x => x.id);
                    table.CheckConstraint("ck_historical_events_decimal_order", "start_decimal <= end_decimal");
                    table.CheckConstraint("ck_historical_events_geoms_valid", "(origin_point IS NULL OR ST_IsValid(origin_point)) AND (influence_area IS NULL OR ST_IsValid(influence_area)) AND (routes IS NULL OR ST_IsValid(routes))");
                    table.CheckConstraint("ck_historical_events_id_slug", "id ~ '^[a-z0-9][a-z0-9-]*$'");
                    table.CheckConstraint("ck_historical_events_name_not_blank", "btrim(name) <> ''");
                    table.CheckConstraint("ck_historical_events_not_own_parent", "parent_event_id <> id");
                    table.CheckConstraint("ck_historical_events_sections_object", "sections IS NULL OR jsonb_typeof(sections) = 'object'");
                    table.ForeignKey(
                        name: "fk_historical_events_historical_events_parent_event_id",
                        column: x => x.parent_event_id,
                        principalTable: "historical_events",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
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
                    table.CheckConstraint("ck_observer_categories_name_not_blank", "btrim(category_name) <> ''");
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
                    table.CheckConstraint("ck_place_names_name_not_blank", "btrim(historical_name) <> ''");
                    table.CheckConstraint("ck_place_names_valid_period_bounded", "valid_period IS NULL OR (NOT isempty(valid_period) AND NOT lower_inf(valid_period) AND NOT upper_inf(valid_period))");
                });

            migrationBuilder.CreateTable(
                name: "reign_eras",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    regime_id = table.Column<Guid>(type: "uuid", nullable: false),
                    era_name = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: false),
                    monarch_name = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: true),
                    start_year = table.Column<int>(type: "integer", nullable: false),
                    end_year = table.Column<int>(type: "integer", nullable: false),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_reign_eras", x => x.id);
                    table.CheckConstraint("ck_reign_eras_name_not_blank", "btrim(era_name) <> ''");
                    table.CheckConstraint("ck_reign_eras_year_order", "start_year <= end_year");
                    table.ForeignKey(
                        name: "fk_reign_eras_regimes_regime_id",
                        column: x => x.regime_id,
                        principalTable: "regimes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "historical_event_controversies",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    event_id = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: false),
                    topic = table.Column<string>(type: "character varying(128)", maxLength: 128, nullable: false),
                    neutral_description = table.Column<string>(type: "text", nullable: false),
                    viewpoints = table.Column<string>(type: "jsonb", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_historical_event_controversies", x => x.id);
                    table.CheckConstraint("ck_controversies_text_not_blank", "btrim(topic) <> '' AND btrim(neutral_description) <> ''");
                    table.CheckConstraint("ck_controversies_viewpoints_array", "viewpoints IS NULL OR jsonb_typeof(viewpoints) = 'array'");
                    table.ForeignKey(
                        name: "fk_historical_event_controversies_historical_events_event_id",
                        column: x => x.event_id,
                        principalTable: "historical_events",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "historical_event_tag_map",
                columns: table => new
                {
                    event_id = table.Column<string>(type: "character varying(64)", nullable: false),
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
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_historical_event_tag_map_historical_events_event_id",
                        column: x => x.event_id,
                        principalTable: "historical_events",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "historical_event_perspectives",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    event_id = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: false),
                    regime_id = table.Column<Guid>(type: "uuid", nullable: true),
                    observer_category_id = table.Column<int>(type: "integer", nullable: true),
                    local_name = table.Column<string>(type: "character varying(128)", maxLength: 128, nullable: false),
                    narrative_summary = table.Column<string>(type: "text", nullable: false),
                    official_justification = table.Column<string>(type: "text", nullable: true),
                    primary_sources = table.Column<string>(type: "jsonb", nullable: true),
                    claimed_casualties = table.Column<string>(type: "jsonb", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_historical_event_perspectives", x => x.id);
                    table.CheckConstraint("ck_perspectives_exactly_one_observer", "num_nonnulls(regime_id, observer_category_id) = 1");
                    table.CheckConstraint("ck_perspectives_sources_array", "primary_sources IS NULL OR jsonb_typeof(primary_sources) = 'array'");
                    table.CheckConstraint("ck_perspectives_text_not_blank", "btrim(local_name) <> '' AND btrim(narrative_summary) <> ''");
                    table.ForeignKey(
                        name: "fk_historical_event_perspectives_historical_events_event_id",
                        column: x => x.event_id,
                        principalTable: "historical_events",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
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

            migrationBuilder.CreateIndex(
                name: "ix_regimes_existence_period",
                table: "regimes",
                column: "existence_period")
                .Annotation("Npgsql:IndexMethod", "gist");

            migrationBuilder.AddCheckConstraint(
                name: "ck_regimes_existence_period",
                table: "regimes",
                sql: "NOT isempty(existence_period) AND NOT lower_inf(existence_period) AND (NOT upper_inf(existence_period) OR status = 'existing')");

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
                name: "ix_historical_events_origin_point",
                table: "historical_events",
                column: "origin_point")
                .Annotation("Npgsql:IndexMethod", "gist");

            migrationBuilder.CreateIndex(
                name: "ix_historical_events_parent_event_id",
                table: "historical_events",
                column: "parent_event_id");

            migrationBuilder.CreateIndex(
                name: "ix_historical_events_start_decimal_end_decimal",
                table: "historical_events",
                columns: new[] { "start_decimal", "end_decimal" });

            migrationBuilder.CreateIndex(
                name: "ix_observer_categories_category_name",
                table: "observer_categories",
                column: "category_name",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ix_place_names_geom",
                table: "place_names",
                column: "geom")
                .Annotation("Npgsql:IndexMethod", "gist");

            migrationBuilder.CreateIndex(
                name: "ix_place_names_valid_period",
                table: "place_names",
                column: "valid_period")
                .Annotation("Npgsql:IndexMethod", "gist");

            migrationBuilder.CreateIndex(
                name: "ix_reign_eras_regime_id_era_name_start_year",
                table: "reign_eras",
                columns: new[] { "regime_id", "era_name", "start_year" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ix_reign_eras_start_year_end_year",
                table: "reign_eras",
                columns: new[] { "start_year", "end_year" });
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
                name: "place_names");

            migrationBuilder.DropTable(
                name: "reign_eras");

            migrationBuilder.DropTable(
                name: "observer_categories");

            migrationBuilder.DropTable(
                name: "event_tags");

            migrationBuilder.DropTable(
                name: "historical_events");

            migrationBuilder.DropIndex(
                name: "ix_regimes_existence_period",
                table: "regimes");

            migrationBuilder.DropCheckConstraint(
                name: "ck_regimes_existence_period",
                table: "regimes");

            migrationBuilder.DropColumn(
                name: "existence_period",
                table: "regimes");

            migrationBuilder.DropColumn(
                name: "is_illustrative",
                table: "regime_territories");

            migrationBuilder.DropColumn(
                name: "source",
                table: "regime_territories");
        }
    }
}
