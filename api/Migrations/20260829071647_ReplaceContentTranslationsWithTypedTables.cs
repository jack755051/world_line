using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace WorldLine.Api.Migrations
{
    /// <inheritdoc />
    public partial class ReplaceContentTranslationsWithTypedTables : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "content_translations");

            migrationBuilder.CreateTable(
                name: "historical_event_controversy_translations",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    controversy_id = table.Column<Guid>(type: "uuid", nullable: false),
                    locale = table.Column<string>(type: "character varying(5)", maxLength: 5, nullable: false),
                    topic = table.Column<string>(type: "character varying(128)", maxLength: 128, nullable: false),
                    neutral_description = table.Column<string>(type: "text", nullable: false),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_historical_event_controversy_translations", x => x.id);
                    table.ForeignKey(
                        name: "fk_historical_event_controversy_translations_historical_event_",
                        column: x => x.controversy_id,
                        principalTable: "historical_event_controversies",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "historical_event_translations",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    event_id = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: false),
                    locale = table.Column<string>(type: "character varying(5)", maxLength: 5, nullable: false),
                    name = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_historical_event_translations", x => x.id);
                    table.ForeignKey(
                        name: "fk_historical_event_translations_historical_events_event_id",
                        column: x => x.event_id,
                        principalTable: "historical_events",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "lineage_preset_translations",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    lineage_preset_id = table.Column<Guid>(type: "uuid", nullable: false),
                    locale = table.Column<string>(type: "character varying(5)", maxLength: 5, nullable: false),
                    preset_name = table.Column<string>(type: "character varying(128)", maxLength: 128, nullable: false),
                    description = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_lineage_preset_translations", x => x.id);
                    table.ForeignKey(
                        name: "fk_lineage_preset_translations_lineage_presets_lineage_preset_",
                        column: x => x.lineage_preset_id,
                        principalTable: "lineage_presets",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "regime_alias_translations",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    regime_alias_id = table.Column<Guid>(type: "uuid", nullable: false),
                    locale = table.Column<string>(type: "character varying(5)", maxLength: 5, nullable: false),
                    alias_name = table.Column<string>(type: "character varying(128)", maxLength: 128, nullable: false),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_regime_alias_translations", x => x.id);
                    table.ForeignKey(
                        name: "fk_regime_alias_translations_regime_aliases_regime_alias_id",
                        column: x => x.regime_alias_id,
                        principalTable: "regime_aliases",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "regime_translations",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    regime_id = table.Column<Guid>(type: "uuid", nullable: false),
                    locale = table.Column<string>(type: "character varying(5)", maxLength: 5, nullable: false),
                    self_name = table.Column<string>(type: "character varying(128)", maxLength: 128, nullable: false),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_regime_translations", x => x.id);
                    table.ForeignKey(
                        name: "fk_regime_translations_regimes_regime_id",
                        column: x => x.regime_id,
                        principalTable: "regimes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "ix_historical_event_controversy_translations_controversy_id_lo",
                table: "historical_event_controversy_translations",
                columns: new[] { "controversy_id", "locale" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ix_historical_event_translations_event_id_locale",
                table: "historical_event_translations",
                columns: new[] { "event_id", "locale" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ix_lineage_preset_translations_lineage_preset_id_locale",
                table: "lineage_preset_translations",
                columns: new[] { "lineage_preset_id", "locale" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ix_regime_alias_translations_regime_alias_id_locale",
                table: "regime_alias_translations",
                columns: new[] { "regime_alias_id", "locale" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ix_regime_translations_regime_id_locale",
                table: "regime_translations",
                columns: new[] { "regime_id", "locale" },
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "historical_event_controversy_translations");

            migrationBuilder.DropTable(
                name: "historical_event_translations");

            migrationBuilder.DropTable(
                name: "lineage_preset_translations");

            migrationBuilder.DropTable(
                name: "regime_alias_translations");

            migrationBuilder.DropTable(
                name: "regime_translations");

            migrationBuilder.CreateTable(
                name: "content_translations",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    entity_id = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: false),
                    entity_type = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: false),
                    field_name = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: false),
                    locale = table.Column<string>(type: "character varying(5)", maxLength: 5, nullable: false),
                    translated_text = table.Column<string>(type: "text", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_content_translations", x => x.id);
                });

            migrationBuilder.CreateIndex(
                name: "ix_content_translations_entity_type_entity_id_field_name_locale",
                table: "content_translations",
                columns: new[] { "entity_type", "entity_id", "field_name", "locale" },
                unique: true);
        }
    }
}
