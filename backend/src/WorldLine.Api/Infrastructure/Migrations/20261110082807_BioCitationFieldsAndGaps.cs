using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace WorldLine.Api.Infrastructure.Migrations
{
    /// <summary>
    /// 詳細人物生平 B1 其餘項目（ARCHITECTURE §16.4.1、§16.4.2、§16.6，2026-11-10，新增式；Tai 16:20 核准「只寫檔、不套用」）：
    /// - leader_bio_field_citations 補 quote、quote_lang、grade、date_precision、policy_version（全可空；舊列不動）。
    ///   field CHECK 值域加 deathPlace（先 DROP 再以超集重建，既有資料全部仍合法）。
    /// - grade CHECK 只收 A／B：leader_bio_field_citations 與 leader_record_citations（後者已套用 5442、目前 0 列）。
    /// - quote ≤ 25 字不加 DB 約束，只在 BioSourcePolicy 檢查（主管裁定）。
    /// - leader_bios.death_place（jsonb 雙語物件）。
    /// - 新表 leader_bio_gaps＋I5 trigger（禁 DELETE；retracted_at、resolved_at 設了不可清除）。
    /// Down 只供開發／測試：若已有 deathPlace 引用或 death_place 資料，Down 會失敗或丟失該欄，正式環境不執行 Down。
    /// </summary>
    public partial class BioCitationFieldsAndGaps : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropCheckConstraint(
                name: "ck_leader_bio_field_citations_field",
                table: "leader_bio_field_citations");

            migrationBuilder.AddColumn<string>(
                name: "death_place",
                table: "leader_bios",
                type: "jsonb",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "date_precision",
                table: "leader_bio_field_citations",
                type: "character varying(8)",
                maxLength: 8,
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "grade",
                table: "leader_bio_field_citations",
                type: "character varying(1)",
                maxLength: 1,
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "policy_version",
                table: "leader_bio_field_citations",
                type: "character varying(32)",
                maxLength: 32,
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "quote",
                table: "leader_bio_field_citations",
                type: "text",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "quote_lang",
                table: "leader_bio_field_citations",
                type: "character varying(35)",
                maxLength: 35,
                nullable: true);

            migrationBuilder.CreateTable(
                name: "leader_bio_gaps",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    bio_id = table.Column<Guid>(type: "uuid", nullable: false),
                    target = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: false),
                    gap_kind = table.Column<string>(type: "character varying(24)", maxLength: 24, nullable: false),
                    note = table.Column<string>(type: "text", nullable: true),
                    candidate_citations = table.Column<string>(type: "jsonb", nullable: true),
                    checked_on = table.Column<DateOnly>(type: "date", nullable: false),
                    resolved_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    resolved_by_citation_id = table.Column<Guid>(type: "uuid", nullable: true),
                    retracted_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    retraction_reason = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_leader_bio_gaps", x => x.id);
                    table.CheckConstraint("ck_leader_bio_gaps_candidate_citations_array", "candidate_citations IS NULL OR jsonb_typeof(candidate_citations) = 'array'");
                    table.CheckConstraint("ck_leader_bio_gaps_field_target", "target NOT LIKE 'field:%' OR substr(target, 7) IN ('name', 'nameZh', 'birthDate', 'deathDate', 'birthPlace', 'deathPlace', 'party', 'summary', 'portrait')");
                    table.CheckConstraint("ck_leader_bio_gaps_gap_kind", "gap_kind IN ('conflict', 'not_found', 'identity_uncertain')");
                    table.CheckConstraint("ck_leader_bio_gaps_resolved_by", "resolved_by_citation_id IS NULL OR resolved_at IS NOT NULL");
                    table.CheckConstraint("ck_leader_bio_gaps_retraction_reason", "retracted_at IS NULL OR retraction_reason IS NOT NULL");
                    table.CheckConstraint("ck_leader_bio_gaps_target", "target ~ '^(field|position|paragraph):[^[:space:]].*$|^identity$'");
                    table.ForeignKey(
                        name: "fk_leader_bio_gaps_leader_bios_bio_id",
                        column: x => x.bio_id,
                        principalTable: "leader_bios",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.AddCheckConstraint(
                name: "ck_leader_record_citations_grade",
                table: "leader_record_citations",
                sql: "grade IS NULL OR grade IN ('A', 'B')");

            migrationBuilder.AddCheckConstraint(
                name: "ck_leader_bios_death_place_object",
                table: "leader_bios",
                sql: "death_place IS NULL OR jsonb_typeof(death_place) = 'object'");

            migrationBuilder.AddCheckConstraint(
                name: "ck_leader_bio_field_citations_date_precision",
                table: "leader_bio_field_citations",
                sql: "date_precision IS NULL OR date_precision IN ('day', 'month', 'year')");

            migrationBuilder.AddCheckConstraint(
                name: "ck_leader_bio_field_citations_field",
                table: "leader_bio_field_citations",
                sql: "field IN ('name', 'nameZh', 'birthDate', 'deathDate', 'birthPlace', 'deathPlace', 'party', 'summary', 'portrait')");

            migrationBuilder.AddCheckConstraint(
                name: "ck_leader_bio_field_citations_grade",
                table: "leader_bio_field_citations",
                sql: "grade IS NULL OR grade IN ('A', 'B')");

            migrationBuilder.AddCheckConstraint(
                name: "ck_leader_bio_field_citations_quote_not_blank",
                table: "leader_bio_field_citations",
                sql: "quote IS NULL OR btrim(quote) <> ''");

            migrationBuilder.CreateIndex(
                name: "ix_leader_bio_gaps_bio_id_target_gap_kind",
                table: "leader_bio_gaps",
                columns: new[] { "bio_id", "target", "gap_kind" },
                unique: true,
                filter: "resolved_at IS NULL AND retracted_at IS NULL");

            // I5：缺口紀錄只能撤回或標為已解決，不能 DELETE；撤回、解決都不可撤銷。
            migrationBuilder.Sql("""
                CREATE OR REPLACE FUNCTION fn_leader_bio_gaps_guard()
                RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    IF TG_OP = 'DELETE' THEN
                        RAISE EXCEPTION 'leader_bio_gaps I5: 不可刪除，請改用撤回或標為已解決（id: %）', OLD.id;
                    END IF;
                    IF OLD.retracted_at IS NOT NULL AND NEW.retracted_at IS NULL THEN
                        RAISE EXCEPTION 'leader_bio_gaps I5: retracted_at 不可撤銷（id: %）', OLD.id;
                    END IF;
                    IF OLD.resolved_at IS NOT NULL AND NEW.resolved_at IS NULL THEN
                        RAISE EXCEPTION 'leader_bio_gaps I5: resolved_at 不可撤銷（id: %）', OLD.id;
                    END IF;
                    RETURN NEW;
                END;
                $$;
                CREATE TRIGGER trg_leader_bio_gaps_guard
                BEFORE UPDATE OR DELETE ON leader_bio_gaps
                FOR EACH ROW EXECUTE FUNCTION fn_leader_bio_gaps_guard();
                """);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql("DROP TRIGGER IF EXISTS trg_leader_bio_gaps_guard ON leader_bio_gaps; DROP FUNCTION IF EXISTS fn_leader_bio_gaps_guard();");
            migrationBuilder.DropTable(
                name: "leader_bio_gaps");

            migrationBuilder.DropCheckConstraint(
                name: "ck_leader_record_citations_grade",
                table: "leader_record_citations");

            migrationBuilder.DropCheckConstraint(
                name: "ck_leader_bios_death_place_object",
                table: "leader_bios");

            migrationBuilder.DropCheckConstraint(
                name: "ck_leader_bio_field_citations_date_precision",
                table: "leader_bio_field_citations");

            migrationBuilder.DropCheckConstraint(
                name: "ck_leader_bio_field_citations_field",
                table: "leader_bio_field_citations");

            migrationBuilder.DropCheckConstraint(
                name: "ck_leader_bio_field_citations_grade",
                table: "leader_bio_field_citations");

            migrationBuilder.DropCheckConstraint(
                name: "ck_leader_bio_field_citations_quote_not_blank",
                table: "leader_bio_field_citations");

            migrationBuilder.DropColumn(
                name: "death_place",
                table: "leader_bios");

            migrationBuilder.DropColumn(
                name: "date_precision",
                table: "leader_bio_field_citations");

            migrationBuilder.DropColumn(
                name: "grade",
                table: "leader_bio_field_citations");

            migrationBuilder.DropColumn(
                name: "policy_version",
                table: "leader_bio_field_citations");

            migrationBuilder.DropColumn(
                name: "quote",
                table: "leader_bio_field_citations");

            migrationBuilder.DropColumn(
                name: "quote_lang",
                table: "leader_bio_field_citations");

            migrationBuilder.AddCheckConstraint(
                name: "ck_leader_bio_field_citations_field",
                table: "leader_bio_field_citations",
                sql: "field IN ('name', 'nameZh', 'birthDate', 'deathDate', 'birthPlace', 'party', 'summary', 'portrait')");
        }
    }
}
