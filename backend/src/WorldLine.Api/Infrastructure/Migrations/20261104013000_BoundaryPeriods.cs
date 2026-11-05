using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace WorldLine.Api.Infrastructure.Migrations
{
    /// <summary>
    /// 疆界圖磚第 2 層（ARCHITECTURE.md §9 遷移步驟 2）：<c>boundary_periods</c> view，每段「不變幾何」一筆，供圖磚建置（tools/tiles）匯出。
    /// - 一筆有效主權紀錄＝一段不變幾何（主權紀錄不可改幾何，疆界變動即分段）。
    /// - 日期存成整數日：從 1900-01-01 起算的天數（更早為負數）；<c>end_day</c> 不含當日，仍持續者用 int 最大值 2147483647。
    ///   與第 1 層 API 的 <c>valid_period @&gt; d</c> 等價：<c>start_day &lt;= d AND end_day &gt; d</c>。
    /// - <c>color_idx</c>：與前端 <c>regimeColor</c> 後備色盤（8 色）相同的 slug 雜湊（h = h × 31 + 字元碼，取 32 位元，mod 8）；
    ///   有手動指定色的政權由前端依 <c>regime_slug</c> 覆寫。
    /// - <c>disputed</c>：主權紀錄目前沒有爭議欄位，一律 false。<c>control_type</c>＝<c>layer_status</c>（de_jure／not_sovereign）。
    /// 只是 view，不改既有資料表。
    /// </summary>
    [DbContext(typeof(WorldLineDbContext))]
    [Migration("20261104013000_BoundaryPeriods")]
    public partial class BoundaryPeriods : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql("""
                CREATE OR REPLACE FUNCTION wl_color_idx(slug text) RETURNS integer
                LANGUAGE plpgsql IMMUTABLE STRICT PARALLEL SAFE AS $$
                DECLARE h bigint := 0; c text;
                BEGIN
                  FOREACH c IN ARRAY regexp_split_to_array(slug, '') LOOP
                    h := (h * 31 + ascii(c)) % 4294967296;
                  END LOOP;
                  RETURN (h % 8)::integer;
                END $$;

                CREATE VIEW boundary_periods AS
                SELECT r.id AS record_id,
                       r.regime_id,
                       g.slug AS regime_slug,
                       (lower(r.valid_period) - DATE '1900-01-01') AS start_day,
                       COALESCE(upper(r.valid_period) - DATE '1900-01-01', 2147483647) AS end_day,
                       r.geom,
                       wl_color_idx(g.slug) AS color_idx,
                       false AS disputed,
                       r.layer_status::text AS control_type
                FROM sovereignty_records r
                JOIN regimes g ON g.id = r.regime_id
                WHERE r.retracted_at IS NULL;
                """);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql("DROP VIEW IF EXISTS boundary_periods; DROP FUNCTION IF EXISTS wl_color_idx(text);");
        }
    }
}
