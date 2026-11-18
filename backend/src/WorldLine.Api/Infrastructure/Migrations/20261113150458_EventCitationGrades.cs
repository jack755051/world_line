using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace WorldLine.Api.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class EventCitationGrades : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "event_citation_grades",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    event_id = table.Column<Guid>(type: "uuid", nullable: false),
                    source_id = table.Column<Guid>(type: "uuid", nullable: false),
                    locator = table.Column<string>(type: "text", nullable: false),
                    grade = table.Column<string>(type: "character varying(1)", maxLength: 1, nullable: false),
                    grade_basis = table.Column<string>(type: "text", nullable: false),
                    retracted_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    retraction_reason = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_event_citation_grades", x => x.id);
                    table.CheckConstraint("ck_event_citation_grades_basis", "btrim(grade_basis) <> ''");
                    table.CheckConstraint("ck_event_citation_grades_grade", "grade IN ('A', 'B', 'C')");
                    table.CheckConstraint("ck_event_citation_grades_retraction_reason", "retracted_at IS NULL OR retraction_reason IS NOT NULL");
                    table.ForeignKey(
                        name: "fk_event_citation_grades_event_citations_event_id_source_id_lo",
                        columns: x => new { x.event_id, x.source_id, x.locator },
                        principalTable: "event_citations",
                        principalColumns: new[] { "event_id", "source_id", "locator" },
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "ux_event_citation_grades_live",
                table: "event_citation_grades",
                columns: new[] { "event_id", "source_id", "locator" },
                unique: true,
                filter: "retracted_at IS NULL");
            // I5：不可刪除；只允許把 retracted_at／retraction_reason 從空填上（撤回），其餘欄位不可改。
            migrationBuilder.Sql("""
                CREATE OR REPLACE FUNCTION fn_event_citation_grades_guard() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'event_citation_grades I5: 不可刪除，請改用撤回'; END IF;
                    IF OLD.retracted_at IS NOT NULL THEN RAISE EXCEPTION 'event_citation_grades I5: 已撤回的列不可再改'; END IF;
                    IF NEW.retracted_at IS NULL OR (NEW.id, NEW.event_id, NEW.source_id, NEW.locator, NEW.grade, NEW.grade_basis, NEW.created_at)
                       IS DISTINCT FROM (OLD.id, OLD.event_id, OLD.source_id, OLD.locator, OLD.grade, OLD.grade_basis, OLD.created_at) THEN
                        RAISE EXCEPTION 'event_citation_grades I5: 只能撤回，不可修改；更正請撤回後另寫一列';
                    END IF;
                    RETURN NEW;
                END $$;
                CREATE TRIGGER trg_event_citation_grades_guard BEFORE UPDATE OR DELETE ON event_citation_grades
                    FOR EACH ROW EXECUTE FUNCTION fn_event_citation_grades_guard();
                """);
            migrationBuilder.Sql("""
                CREATE OR REPLACE VIEW v_record_confidence AS
                WITH ev AS (
                    -- 等級以「那一筆引文」為準（event_citation_grades），沒有才退回整冊的 sources.grade
                    SELECT e.id,
                           count(c.source_id) AS n_cit,
                           count(*) FILTER (WHERE coalesce(g.grade, s.grade) = 'A' AND s.source_kind <> 'dataset') AS n_a,
                           count(DISTINCT coalesce(s.family, s.id::text)) FILTER (WHERE coalesce(g.grade, s.grade) IN ('A','B') AND s.source_kind <> 'dataset') AS n_fam,
                           count(*) FILTER (WHERE c.source_id IS NOT NULL AND coalesce(g.grade, s.grade) IS NULL) AS n_ungraded
                    FROM historical_events e
                    LEFT JOIN event_citations c ON c.event_id = e.id
                    LEFT JOIN sources s ON s.id = c.source_id
                    LEFT JOIN event_citation_grades g ON g.event_id = c.event_id AND g.source_id = c.source_id AND g.locator = c.locator AND g.retracted_at IS NULL
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
                """);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql("""
                CREATE OR REPLACE VIEW v_record_confidence AS
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
                """);
            migrationBuilder.Sql("DROP TRIGGER IF EXISTS trg_event_citation_grades_guard ON event_citation_grades; DROP FUNCTION IF EXISTS fn_event_citation_grades_guard();");

            migrationBuilder.DropTable(
                name: "event_citation_grades");
        }
    }
}
