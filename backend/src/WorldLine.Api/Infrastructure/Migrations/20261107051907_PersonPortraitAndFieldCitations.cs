using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace WorldLine.Api.Infrastructure.Migrations
{
    /// <summary>
    /// 人物 P1（2026-11-07，新增式）：leader_bios 加卒日精度、Wikidata Q 號、照片授權欄位、superseded_by；
    /// 新表 leader_bio_field_citations（生平逐欄位引用，接既有 sources）。不刪不改既有欄位與資料。
    /// </summary>
    public partial class PersonPortraitAndFieldCitations : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "death_date_precision",
                table: "leader_bios",
                type: "character varying(8)",
                maxLength: 8,
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "portrait_attribution",
                table: "leader_bios",
                type: "text",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "portrait_author",
                table: "leader_bios",
                type: "text",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "portrait_license_code",
                table: "leader_bios",
                type: "character varying(32)",
                maxLength: 32,
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "portrait_license_url",
                table: "leader_bios",
                type: "text",
                nullable: true);

            migrationBuilder.AddColumn<DateOnly>(
                name: "portrait_retrieved_on",
                table: "leader_bios",
                type: "date",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "portrait_source_url",
                table: "leader_bios",
                type: "text",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "portrait_url",
                table: "leader_bios",
                type: "text",
                nullable: true);

            migrationBuilder.AddColumn<Guid>(
                name: "superseded_by",
                table: "leader_bios",
                type: "uuid",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "wikidata_qid",
                table: "leader_bios",
                type: "character varying(16)",
                maxLength: 16,
                nullable: true);

            migrationBuilder.CreateTable(
                name: "leader_bio_field_citations",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    bio_id = table.Column<Guid>(type: "uuid", nullable: false),
                    field = table.Column<string>(type: "character varying(16)", maxLength: 16, nullable: false),
                    source_id = table.Column<Guid>(type: "uuid", nullable: false),
                    locator = table.Column<string>(type: "text", nullable: false),
                    evidence_note = table.Column<string>(type: "text", nullable: true),
                    accessed_on = table.Column<DateOnly>(type: "date", nullable: false),
                    retracted_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    retraction_reason = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_leader_bio_field_citations", x => x.id);
                    table.CheckConstraint("ck_leader_bio_field_citations_field", "field IN ('name', 'nameZh', 'birthDate', 'deathDate', 'birthPlace', 'party', 'summary', 'portrait')");
                    table.CheckConstraint("ck_leader_bio_field_citations_locator_not_blank", "btrim(locator) <> ''");
                    table.CheckConstraint("ck_leader_bio_field_citations_retraction_reason", "retracted_at IS NULL OR retraction_reason IS NOT NULL");
                    table.ForeignKey(
                        name: "fk_leader_bio_field_citations_leader_bios_bio_id",
                        column: x => x.bio_id,
                        principalTable: "leader_bios",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_leader_bio_field_citations_sources_source_id",
                        column: x => x.source_id,
                        principalTable: "sources",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "ix_leader_bios_superseded_by",
                table: "leader_bios",
                column: "superseded_by");

            migrationBuilder.CreateIndex(
                name: "ix_leader_bios_wikidata_qid",
                table: "leader_bios",
                column: "wikidata_qid",
                filter: "wikidata_qid IS NOT NULL AND retracted_at IS NULL");

            migrationBuilder.AddCheckConstraint(
                name: "ck_leader_bios_death_date_precision",
                table: "leader_bios",
                sql: "death_date_precision IS NULL OR death_date_precision IN ('day', 'month', 'year')");

            migrationBuilder.AddCheckConstraint(
                name: "ck_leader_bios_portrait_complete",
                table: "leader_bios",
                sql: "portrait_url IS NULL OR (portrait_source_url IS NOT NULL AND portrait_license_code IS NOT NULL AND portrait_attribution IS NOT NULL AND portrait_retrieved_on IS NOT NULL)");

            migrationBuilder.AddCheckConstraint(
                name: "ck_leader_bios_portrait_license",
                table: "leader_bios",
                sql: "portrait_license_code IS NULL OR portrait_license_code IN ('cc_by', 'cc_by_sa', 'cc0', 'pd_expired', 'us_federal_pd')");

            migrationBuilder.AddCheckConstraint(
                name: "ck_leader_bios_wikidata_qid",
                table: "leader_bios",
                sql: "wikidata_qid IS NULL OR wikidata_qid ~ '^Q[1-9][0-9]*$'");

            migrationBuilder.CreateIndex(
                name: "ix_leader_bio_field_citations_bio_id",
                table: "leader_bio_field_citations",
                column: "bio_id");

            migrationBuilder.CreateIndex(
                name: "ix_leader_bio_field_citations_source_id",
                table: "leader_bio_field_citations",
                column: "source_id");

            migrationBuilder.AddForeignKey(
                name: "fk_leader_bios_leader_bios_superseded_by",
                table: "leader_bios",
                column: "superseded_by",
                principalTable: "leader_bios",
                principalColumn: "id",
                onDelete: ReferentialAction.Restrict);

            // I5：引用只能撤回、不能 DELETE；撤回後不可改回。
            migrationBuilder.Sql("""
                CREATE OR REPLACE FUNCTION fn_leader_bio_field_citations_guard()
                RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    IF TG_OP = 'DELETE' THEN
                        RAISE EXCEPTION 'leader_bio_field_citations I5: 不可刪除，請改用撤回（id: %）', OLD.id;
                    END IF;
                    IF OLD.retracted_at IS NOT NULL AND NEW.retracted_at IS NULL THEN
                        RAISE EXCEPTION 'leader_bio_field_citations I5: retracted_at 不可撤銷（id: %）', OLD.id;
                    END IF;
                    RETURN NEW;
                END;
                $$;
                CREATE TRIGGER trg_leader_bio_field_citations_guard
                BEFORE UPDATE OR DELETE ON leader_bio_field_citations
                FOR EACH ROW EXECUTE FUNCTION fn_leader_bio_field_citations_guard();
                """);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql("DROP TRIGGER IF EXISTS trg_leader_bio_field_citations_guard ON leader_bio_field_citations; DROP FUNCTION IF EXISTS fn_leader_bio_field_citations_guard();");
            migrationBuilder.DropForeignKey(
                name: "fk_leader_bios_leader_bios_superseded_by",
                table: "leader_bios");

            migrationBuilder.DropTable(
                name: "leader_bio_field_citations");

            migrationBuilder.DropIndex(
                name: "ix_leader_bios_superseded_by",
                table: "leader_bios");

            migrationBuilder.DropIndex(
                name: "ix_leader_bios_wikidata_qid",
                table: "leader_bios");

            migrationBuilder.DropCheckConstraint(
                name: "ck_leader_bios_death_date_precision",
                table: "leader_bios");

            migrationBuilder.DropCheckConstraint(
                name: "ck_leader_bios_portrait_complete",
                table: "leader_bios");

            migrationBuilder.DropCheckConstraint(
                name: "ck_leader_bios_portrait_license",
                table: "leader_bios");

            migrationBuilder.DropCheckConstraint(
                name: "ck_leader_bios_wikidata_qid",
                table: "leader_bios");

            migrationBuilder.DropColumn(
                name: "death_date_precision",
                table: "leader_bios");

            migrationBuilder.DropColumn(
                name: "portrait_attribution",
                table: "leader_bios");

            migrationBuilder.DropColumn(
                name: "portrait_author",
                table: "leader_bios");

            migrationBuilder.DropColumn(
                name: "portrait_license_code",
                table: "leader_bios");

            migrationBuilder.DropColumn(
                name: "portrait_license_url",
                table: "leader_bios");

            migrationBuilder.DropColumn(
                name: "portrait_retrieved_on",
                table: "leader_bios");

            migrationBuilder.DropColumn(
                name: "portrait_source_url",
                table: "leader_bios");

            migrationBuilder.DropColumn(
                name: "portrait_url",
                table: "leader_bios");

            migrationBuilder.DropColumn(
                name: "superseded_by",
                table: "leader_bios");

            migrationBuilder.DropColumn(
                name: "wikidata_qid",
                table: "leader_bios");
        }
    }
}
