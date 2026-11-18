using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace WorldLine.Api.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class SourceRulesFields : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "family",
                table: "sources",
                type: "character varying(64)",
                maxLength: 64,
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "grade",
                table: "sources",
                type: "character varying(1)",
                maxLength: 1,
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "grade_basis",
                table: "sources",
                type: "text",
                nullable: true);

            migrationBuilder.AddColumn<Guid>(
                name: "source_id",
                table: "regimes",
                type: "uuid",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "source_locator",
                table: "regimes",
                type: "text",
                nullable: true);

            migrationBuilder.AddColumn<Guid>(
                name: "source_id",
                table: "capital_records",
                type: "uuid",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "source_locator",
                table: "capital_records",
                type: "text",
                nullable: true);

            migrationBuilder.AddCheckConstraint(
                name: "ck_sources_grade",
                table: "sources",
                sql: "grade IS NULL OR grade IN ('A', 'B', 'C', 'X')");

            migrationBuilder.AddCheckConstraint(
                name: "ck_sources_grade_basis",
                table: "sources",
                sql: "grade IS NULL OR grade_basis IS NOT NULL");

            migrationBuilder.CreateIndex(
                name: "ix_regimes_source_id",
                table: "regimes",
                column: "source_id");

            migrationBuilder.CreateIndex(
                name: "ix_capital_records_source_id",
                table: "capital_records",
                column: "source_id");

            migrationBuilder.AddForeignKey(
                name: "fk_capital_records_sources_source_id",
                table: "capital_records",
                column: "source_id",
                principalTable: "sources",
                principalColumn: "id",
                onDelete: ReferentialAction.Restrict);

            migrationBuilder.AddForeignKey(
                name: "fk_regimes_sources_source_id",
                table: "regimes",
                column: "source_id",
                principalTable: "sources",
                principalColumn: "id",
                onDelete: ReferentialAction.Restrict);
            // 可信程度是「由出處推導」的檢視，不是存進各表的欄位：多數資料表禁止 UPDATE（I5），
            // 所以不回頭改既有列；補上來源等級或引文後，這裡的結果自動跟著變。規則：docs/source-rules.md §5。
            migrationBuilder.Sql("""
                CREATE VIEW v_record_confidence AS
                WITH ev AS (
                    SELECT e.id,
                           count(c.source_id) AS n_cit,
                           count(*) FILTER (WHERE s.grade = 'A' AND s.source_kind <> 'dataset') AS n_a,
                           count(DISTINCT coalesce(s.family, s.id::text)) FILTER (WHERE s.grade IN ('A','B') AND s.source_kind <> 'dataset') AS n_fam,
                           count(*) FILTER (WHERE c.source_id IS NOT NULL AND s.grade IS NULL) AS n_ungraded
                    FROM historical_events e
                    LEFT JOIN event_citations c ON c.event_id = e.id
                    LEFT JOIN sources s ON s.id = c.source_id
                    WHERE e.retracted_at IS NULL
                    GROUP BY e.id
                ), evc AS (
                    SELECT id,
                           CASE WHEN n_cit = 0 THEN 'unsourced' WHEN n_a >= 1 OR n_fam >= 2 THEN 'verified' ELSE 'needs_check' END AS confidence,
                           CASE WHEN n_cit = 0 THEN 'no_citation' WHEN n_a >= 1 THEN 'one_a' WHEN n_fam >= 2 THEN 'two_b_families'
                                WHEN n_fam = 1 THEN 'single_b' WHEN n_ungraded > 0 THEN 'ungraded_source' ELSE 'below_b' END AS basis
                    FROM ev
                ), lr AS (
                    SELECT r.id,
                           count(*) FILTER (WHERE c.grade = 'A') AS n_a,
                           count(DISTINCT coalesce(s.family, s.id::text)) FILTER (WHERE c.grade IN ('A','B')) AS n_fam
                    FROM leader_records r
                    LEFT JOIN leader_record_citations c ON c.record_id = r.id AND c.retracted_at IS NULL
                    LEFT JOIN sources s ON s.id = c.source_id
                    WHERE r.retracted_at IS NULL
                    GROUP BY r.id
                )
                SELECT 'event'::text AS record_kind, id AS record_id, confidence, basis FROM evc
                UNION ALL
                SELECT 'sovereignty', v.id,
                       CASE WHEN x.confidence = 'verified' THEN 'verified' ELSE 'needs_check' END,
                       CASE WHEN x.id IS NULL THEN 'dataset_only' WHEN x.confidence = 'verified' THEN 'start_event_' || x.basis ELSE 'start_event_' || x.basis END
                FROM sovereignty_records v LEFT JOIN evc x ON x.id = v.start_event_id
                WHERE v.retracted_at IS NULL
                UNION ALL
                SELECT 'capital', k.id,
                       CASE WHEN s.grade = 'A' THEN 'verified'
                            WHEN s.id IS NULL AND (k.source_ref IS NULL OR btrim(k.source_ref) = '' OR k.source_ref LIKE '待查證%') THEN 'unsourced'
                            ELSE 'needs_check' END,
                       CASE WHEN s.grade = 'A' THEN 'one_a' WHEN s.grade = 'B' THEN 'single_b' WHEN s.id IS NOT NULL THEN 'ungraded_source'
                            WHEN k.source_ref IS NULL OR btrim(k.source_ref) = '' OR k.source_ref LIKE '待查證%' THEN 'no_source' ELSE 'free_text' END
                FROM capital_records k LEFT JOIN sources s ON s.id = k.source_id
                WHERE k.retracted_at IS NULL
                UNION ALL
                SELECT 'regime', g.id,
                       CASE WHEN s.grade = 'A' THEN 'verified' ELSE 'needs_check' END,
                       CASE WHEN s.grade = 'A' THEN 'one_a' WHEN s.grade = 'B' THEN 'single_b' WHEN s.id IS NOT NULL THEN 'ungraded_source' ELSE 'dataset_only' END
                FROM regimes g LEFT JOIN sources s ON s.id = g.source_id
                WHERE g.retracted_at IS NULL
                UNION ALL
                SELECT 'leader_record', id,
                       CASE WHEN n_a >= 1 OR n_fam >= 2 THEN 'verified' ELSE 'needs_check' END,
                       CASE WHEN n_a >= 1 THEN 'one_a' WHEN n_fam >= 2 THEN 'two_b_families' WHEN n_fam = 1 THEN 'single_b' ELSE 'free_text' END
                FROM lr;
                COMMENT ON VIEW v_record_confidence IS '各類紀錄的可信程度（verified／needs_check／unsourced），由出處即時推導；規則見 docs/source-rules.md';
                """);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql("DROP VIEW IF EXISTS v_record_confidence;");

            migrationBuilder.DropForeignKey(
                name: "fk_capital_records_sources_source_id",
                table: "capital_records");

            migrationBuilder.DropForeignKey(
                name: "fk_regimes_sources_source_id",
                table: "regimes");

            migrationBuilder.DropCheckConstraint(
                name: "ck_sources_grade",
                table: "sources");

            migrationBuilder.DropCheckConstraint(
                name: "ck_sources_grade_basis",
                table: "sources");

            migrationBuilder.DropIndex(
                name: "ix_regimes_source_id",
                table: "regimes");

            migrationBuilder.DropIndex(
                name: "ix_capital_records_source_id",
                table: "capital_records");

            migrationBuilder.DropColumn(
                name: "family",
                table: "sources");

            migrationBuilder.DropColumn(
                name: "grade",
                table: "sources");

            migrationBuilder.DropColumn(
                name: "grade_basis",
                table: "sources");

            migrationBuilder.DropColumn(
                name: "source_id",
                table: "regimes");

            migrationBuilder.DropColumn(
                name: "source_locator",
                table: "regimes");

            migrationBuilder.DropColumn(
                name: "source_id",
                table: "capital_records");

            migrationBuilder.DropColumn(
                name: "source_locator",
                table: "capital_records");
        }
    }
}
