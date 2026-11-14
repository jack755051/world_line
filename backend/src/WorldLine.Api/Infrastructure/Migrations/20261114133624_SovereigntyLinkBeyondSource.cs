using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace WorldLine.Api.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class SovereigntyLinkBeyondSource : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropCheckConstraint(
                name: "ck_sovereignty_record_links_kind",
                table: "sovereignty_record_links");

            migrationBuilder.AddCheckConstraint(
                name: "ck_sovereignty_record_links_kind",
                table: "sovereignty_record_links",
                sql: "kind IN ('baseline', 'continuation', 'minor_revision', 'change', 'new', 'beyond_source')");

            // 可信程度檢視：beyond_source 的紀錄不沿用前一筆（recursion 只追 continuation），原因碼 beyond_source。
            migrationBuilder.Sql("""
                CREATE OR REPLACE VIEW v_record_confidence AS
                WITH RECURSIVE ev AS (
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
                ), sv AS (
                    -- 每筆主權紀錄自己的起始事件（原欄位，或事後在 sovereignty_record_links 補上的）與來歷
                    SELECT v.id, coalesce(v.start_event_id, l.start_event_id) AS ev, l.kind, l.continues_record_id AS prev
                    FROM sovereignty_records v
                    LEFT JOIN sovereignty_record_links l ON l.record_id = v.id AND l.retracted_at IS NULL
                    WHERE v.retracted_at IS NULL
                ), chain AS (
                    -- 「接續前一筆、形狀相同」的紀錄沒有自己的事件時，往前追到有事件或不是接續的那一筆
                    -- kind = 'beyond_source'（形狀沿用前一筆，但前一筆的出處撐不到這一段）不往前追：要有自己的出處才算已查證
                    SELECT id, id AS root_id, ev, kind, prev, 0 AS depth FROM sv
                    UNION ALL
                    SELECT c.id, p.id, p.ev, p.kind, p.prev, c.depth + 1
                    FROM chain c JOIN sv p ON p.id = c.prev
                    WHERE c.ev IS NULL AND c.kind = 'continuation' AND c.depth < 60
                ), root AS (
                    SELECT DISTINCT ON (id) id, root_id, ev, kind FROM chain ORDER BY id, depth DESC
                ), rc AS (
                    -- 主權紀錄本身的引文（地圖集圖版、劃界條約等）：門檻同事件
                    SELECT c.record_id,
                           count(*) FILTER (WHERE c.grade = 'A' AND s.source_kind <> 'dataset') AS n_a,
                           count(DISTINCT coalesce(s.family, s.id::text)) FILTER (WHERE c.grade IN ('A','B') AND s.source_kind <> 'dataset') AS n_fam
                    FROM sovereignty_record_citations c JOIN sources s ON s.id = c.source_id
                    WHERE c.retracted_at IS NULL
                    GROUP BY c.record_id
                )
                SELECT 'event'::text AS record_kind, id AS record_id, confidence, basis FROM evc
                UNION ALL
                SELECT 'sovereignty', r.id,
                       CASE WHEN x.confidence = 'verified' OR q.n_a >= 1 OR q.n_fam >= 2 THEN 'verified' ELSE 'needs_check' END,
                       CASE WHEN x.confidence = 'verified' THEN 'start_event_' || x.basis
                            WHEN q.n_a >= 1 THEN 'record_citation_one_a'
                            WHEN q.n_fam >= 2 THEN 'record_citation_two_b_families'
                            WHEN r.ev IS NOT NULL THEN 'start_event_' || coalesce(x.basis, 'missing')
                            WHEN q.n_fam = 1 THEN 'record_citation_single_b'
                            WHEN r.kind = 'baseline' THEN 'baseline'
                            WHEN r.kind = 'new' THEN 'new_no_event'
                            WHEN r.kind = 'change' THEN 'change_no_event'
                            WHEN r.kind = 'minor_revision' THEN 'minor_revision_no_event'
                            WHEN r.kind = 'beyond_source' THEN 'beyond_source'
                            ELSE 'dataset_only' END
                FROM root r LEFT JOIN evc x ON x.id = r.ev
                LEFT JOIN LATERAL (SELECT max(n_a) AS n_a, max(n_fam) AS n_fam FROM rc WHERE rc.record_id IN (r.id, r.root_id)) q ON true
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
            migrationBuilder.DropCheckConstraint(
                name: "ck_sovereignty_record_links_kind",
                table: "sovereignty_record_links");

            migrationBuilder.AddCheckConstraint(
                name: "ck_sovereignty_record_links_kind",
                table: "sovereignty_record_links",
                sql: "kind IN ('baseline', 'continuation', 'minor_revision', 'change', 'new')");

            migrationBuilder.Sql("""
                CREATE OR REPLACE VIEW v_record_confidence AS
                WITH RECURSIVE ev AS (
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
                ), sv AS (
                    -- 每筆主權紀錄自己的起始事件（原欄位，或事後在 sovereignty_record_links 補上的）與來歷
                    SELECT v.id, coalesce(v.start_event_id, l.start_event_id) AS ev, l.kind, l.continues_record_id AS prev
                    FROM sovereignty_records v
                    LEFT JOIN sovereignty_record_links l ON l.record_id = v.id AND l.retracted_at IS NULL
                    WHERE v.retracted_at IS NULL
                ), chain AS (
                    -- 「接續前一筆、形狀相同」的紀錄沒有自己的事件時，往前追到有事件或不是接續的那一筆
                    SELECT id, id AS root_id, ev, kind, prev, 0 AS depth FROM sv
                    UNION ALL
                    SELECT c.id, p.id, p.ev, p.kind, p.prev, c.depth + 1
                    FROM chain c JOIN sv p ON p.id = c.prev
                    WHERE c.ev IS NULL AND c.kind = 'continuation' AND c.depth < 60
                ), root AS (
                    SELECT DISTINCT ON (id) id, root_id, ev, kind FROM chain ORDER BY id, depth DESC
                ), rc AS (
                    -- 主權紀錄本身的引文（地圖集圖版、劃界條約等）：門檻同事件
                    SELECT c.record_id,
                           count(*) FILTER (WHERE c.grade = 'A' AND s.source_kind <> 'dataset') AS n_a,
                           count(DISTINCT coalesce(s.family, s.id::text)) FILTER (WHERE c.grade IN ('A','B') AND s.source_kind <> 'dataset') AS n_fam
                    FROM sovereignty_record_citations c JOIN sources s ON s.id = c.source_id
                    WHERE c.retracted_at IS NULL
                    GROUP BY c.record_id
                )
                SELECT 'event'::text AS record_kind, id AS record_id, confidence, basis FROM evc
                UNION ALL
                SELECT 'sovereignty', r.id,
                       CASE WHEN x.confidence = 'verified' OR q.n_a >= 1 OR q.n_fam >= 2 THEN 'verified' ELSE 'needs_check' END,
                       CASE WHEN x.confidence = 'verified' THEN 'start_event_' || x.basis
                            WHEN q.n_a >= 1 THEN 'record_citation_one_a'
                            WHEN q.n_fam >= 2 THEN 'record_citation_two_b_families'
                            WHEN r.ev IS NOT NULL THEN 'start_event_' || coalesce(x.basis, 'missing')
                            WHEN q.n_fam = 1 THEN 'record_citation_single_b'
                            WHEN r.kind = 'baseline' THEN 'baseline'
                            WHEN r.kind = 'new' THEN 'new_no_event'
                            WHEN r.kind = 'change' THEN 'change_no_event'
                            WHEN r.kind = 'minor_revision' THEN 'minor_revision_no_event'
                            ELSE 'dataset_only' END
                FROM root r LEFT JOIN evc x ON x.id = r.ev
                LEFT JOIN LATERAL (SELECT max(n_a) AS n_a, max(n_fam) AS n_fam FROM rc WHERE rc.record_id IN (r.id, r.root_id)) q ON true
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
    }
}
