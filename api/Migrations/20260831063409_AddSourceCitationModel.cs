using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace WorldLine.Api.Migrations
{
    /// <inheritdoc />
    public partial class AddSourceCitationModel : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "sources",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    title = table.Column<string>(type: "character varying(256)", maxLength: 256, nullable: false),
                    author_or_publisher = table.Column<string>(type: "character varying(256)", maxLength: 256, nullable: true),
                    version_or_published_at = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: true),
                    locator = table.Column<string>(type: "character varying(512)", maxLength: 512, nullable: true),
                    license = table.Column<string>(type: "character varying(256)", maxLength: 256, nullable: true),
                    accessed_at = table.Column<DateOnly>(type: "date", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_sources", x => x.id);
                });

            migrationBuilder.CreateTable(
                name: "historical_event_citations",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    historical_event_id = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: false),
                    source_id = table.Column<Guid>(type: "uuid", nullable: false),
                    evidence_note = table.Column<string>(type: "text", nullable: false),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_historical_event_citations", x => x.id);
                    table.ForeignKey(
                        name: "fk_historical_event_citations_historical_events_historical_eve",
                        column: x => x.historical_event_id,
                        principalTable: "historical_events",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "fk_historical_event_citations_sources_source_id",
                        column: x => x.source_id,
                        principalTable: "sources",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "regime_citations",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    regime_id = table.Column<Guid>(type: "uuid", nullable: false),
                    source_id = table.Column<Guid>(type: "uuid", nullable: false),
                    evidence_note = table.Column<string>(type: "text", nullable: false),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_regime_citations", x => x.id);
                    table.ForeignKey(
                        name: "fk_regime_citations_regimes_regime_id",
                        column: x => x.regime_id,
                        principalTable: "regimes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "fk_regime_citations_sources_source_id",
                        column: x => x.source_id,
                        principalTable: "sources",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "regime_relation_citations",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    regime_relation_id = table.Column<Guid>(type: "uuid", nullable: false),
                    source_id = table.Column<Guid>(type: "uuid", nullable: false),
                    evidence_note = table.Column<string>(type: "text", nullable: false),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_regime_relation_citations", x => x.id);
                    table.ForeignKey(
                        name: "fk_regime_relation_citations_regime_relations_regime_relation_",
                        column: x => x.regime_relation_id,
                        principalTable: "regime_relations",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "fk_regime_relation_citations_sources_source_id",
                        column: x => x.source_id,
                        principalTable: "sources",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "regime_territory_citations",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    regime_territory_id = table.Column<Guid>(type: "uuid", nullable: false),
                    source_id = table.Column<Guid>(type: "uuid", nullable: false),
                    evidence_note = table.Column<string>(type: "text", nullable: false),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_regime_territory_citations", x => x.id);
                    table.ForeignKey(
                        name: "fk_regime_territory_citations_regime_territories_regime_territ",
                        column: x => x.regime_territory_id,
                        principalTable: "regime_territories",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "fk_regime_territory_citations_sources_source_id",
                        column: x => x.source_id,
                        principalTable: "sources",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "reign_era_citations",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    reign_era_id = table.Column<Guid>(type: "uuid", nullable: false),
                    source_id = table.Column<Guid>(type: "uuid", nullable: false),
                    evidence_note = table.Column<string>(type: "text", nullable: false),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_reign_era_citations", x => x.id);
                    table.ForeignKey(
                        name: "fk_reign_era_citations_reign_eras_reign_era_id",
                        column: x => x.reign_era_id,
                        principalTable: "reign_eras",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "fk_reign_era_citations_sources_source_id",
                        column: x => x.source_id,
                        principalTable: "sources",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "ix_historical_event_citations_historical_event_id",
                table: "historical_event_citations",
                column: "historical_event_id");

            migrationBuilder.CreateIndex(
                name: "ix_historical_event_citations_source_id",
                table: "historical_event_citations",
                column: "source_id");

            migrationBuilder.CreateIndex(
                name: "ix_regime_citations_regime_id",
                table: "regime_citations",
                column: "regime_id");

            migrationBuilder.CreateIndex(
                name: "ix_regime_citations_source_id",
                table: "regime_citations",
                column: "source_id");

            migrationBuilder.CreateIndex(
                name: "ix_regime_relation_citations_regime_relation_id",
                table: "regime_relation_citations",
                column: "regime_relation_id");

            migrationBuilder.CreateIndex(
                name: "ix_regime_relation_citations_source_id",
                table: "regime_relation_citations",
                column: "source_id");

            migrationBuilder.CreateIndex(
                name: "ix_regime_territory_citations_regime_territory_id",
                table: "regime_territory_citations",
                column: "regime_territory_id");

            migrationBuilder.CreateIndex(
                name: "ix_regime_territory_citations_source_id",
                table: "regime_territory_citations",
                column: "source_id");

            migrationBuilder.CreateIndex(
                name: "ix_reign_era_citations_reign_era_id",
                table: "reign_era_citations",
                column: "reign_era_id");

            migrationBuilder.CreateIndex(
                name: "ix_reign_era_citations_source_id",
                table: "reign_era_citations",
                column: "source_id");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "historical_event_citations");

            migrationBuilder.DropTable(
                name: "regime_citations");

            migrationBuilder.DropTable(
                name: "regime_relation_citations");

            migrationBuilder.DropTable(
                name: "regime_territory_citations");

            migrationBuilder.DropTable(
                name: "reign_era_citations");

            migrationBuilder.DropTable(
                name: "sources");
        }
    }
}
