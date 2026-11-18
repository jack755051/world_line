using System;
using Microsoft.EntityFrameworkCore.Migrations;
using NpgsqlTypes;

#nullable disable

namespace WorldLine.Api.Infrastructure.Migrations
{
    /// <summary>
    /// 詳細人物生平 B1（ARCHITECTURE §16.3-2、§16.4.1，2026-11-10，新增式）：新表 leader_record_citations，
    /// 任期（leader_records）逐筆接 sources。不改 leader_records 既有欄位與資料；leader_records.source 過渡期只當備註。
    /// grade 不加 CHECK（§16.9.1 T1：考證組確認後再加）；policy_version 只預留（T2 未決）。
    /// </summary>
    public partial class LeaderRecordCitations : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "leader_record_citations",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    record_id = table.Column<Guid>(type: "uuid", nullable: false),
                    source_id = table.Column<Guid>(type: "uuid", nullable: false),
                    locator = table.Column<string>(type: "text", nullable: false),
                    quote = table.Column<string>(type: "text", nullable: false),
                    quote_lang = table.Column<string>(type: "character varying(35)", maxLength: 35, nullable: true),
                    evidence_note = table.Column<string>(type: "text", nullable: true),
                    accessed_on = table.Column<DateOnly>(type: "date", nullable: false),
                    grade = table.Column<string>(type: "character varying(1)", maxLength: 1, nullable: true),
                    date_precision = table.Column<string>(type: "character varying(8)", maxLength: 8, nullable: true),
                    claim_span = table.Column<NpgsqlRange<int>>(type: "int4range", nullable: true),
                    policy_version = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: true),
                    retracted_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    retraction_reason = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_leader_record_citations", x => x.id);
                    table.CheckConstraint("ck_leader_record_citations_claim_span", "claim_span IS NULL OR (NOT isempty(claim_span) AND lower(claim_span) >= 0)");
                    table.CheckConstraint("ck_leader_record_citations_date_precision", "date_precision IS NULL OR date_precision IN ('day', 'month', 'year')");
                    table.CheckConstraint("ck_leader_record_citations_locator_not_blank", "btrim(locator) <> ''");
                    table.CheckConstraint("ck_leader_record_citations_quote_not_blank", "btrim(quote) <> ''");
                    table.CheckConstraint("ck_leader_record_citations_retraction_reason", "retracted_at IS NULL OR retraction_reason IS NOT NULL");
                    table.ForeignKey(
                        name: "fk_leader_record_citations_leader_records_record_id",
                        column: x => x.record_id,
                        principalTable: "leader_records",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_leader_record_citations_sources_source_id",
                        column: x => x.source_id,
                        principalTable: "sources",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "ix_leader_record_citations_record_id",
                table: "leader_record_citations",
                column: "record_id");

            migrationBuilder.CreateIndex(
                name: "ix_leader_record_citations_source_id",
                table: "leader_record_citations",
                column: "source_id");

            // I5：引用只能撤回、不能 DELETE；撤回後不可改回。
            migrationBuilder.Sql("""
                CREATE OR REPLACE FUNCTION fn_leader_record_citations_guard()
                RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    IF TG_OP = 'DELETE' THEN
                        RAISE EXCEPTION 'leader_record_citations I5: 不可刪除，請改用撤回（id: %）', OLD.id;
                    END IF;
                    IF OLD.retracted_at IS NOT NULL AND NEW.retracted_at IS NULL THEN
                        RAISE EXCEPTION 'leader_record_citations I5: retracted_at 不可撤銷（id: %）', OLD.id;
                    END IF;
                    RETURN NEW;
                END;
                $$;
                CREATE TRIGGER trg_leader_record_citations_guard
                BEFORE UPDATE OR DELETE ON leader_record_citations
                FOR EACH ROW EXECUTE FUNCTION fn_leader_record_citations_guard();
                """);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql("DROP TRIGGER IF EXISTS trg_leader_record_citations_guard ON leader_record_citations; DROP FUNCTION IF EXISTS fn_leader_record_citations_guard();");
            migrationBuilder.DropTable(
                name: "leader_record_citations");
        }
    }
}
