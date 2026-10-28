using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace WorldLine.Api.Infrastructure.Migrations
{
    /// <summary>
    /// Tai 2026-10-28 修正：事件不記時區欄位，只保留當地日期 occurred＋選填 time_note。
    /// 防護：若 local_time_zone 已有任何值就中止，不默默丟資料。
    /// </summary>
    public partial class DropEventLocalTimeZone : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql("""
                DO $$
                BEGIN
                  IF EXISTS (SELECT 1 FROM historical_events WHERE local_time_zone IS NOT NULL) THEN
                    RAISE EXCEPTION 'historical_events.local_time_zone 已有資料，拒絕刪除欄位；請先人工處理';
                  END IF;
                END $$;
                """);
            migrationBuilder.DropColumn(
                name: "local_time_zone",
                table: "historical_events");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "local_time_zone",
                table: "historical_events",
                type: "character varying(64)",
                maxLength: 64,
                nullable: true);
        }
    }
}
