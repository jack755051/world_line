using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace WorldLine.Api.Infrastructure.Migrations
{
    /// <summary>
    /// leader_bio_gaps.target CHECK 加 role:&lt;seed_key&gt;（B3：缺 period.start 的角色候選改記缺漏；Tai 2026-11-11 決定）。
    /// 只換 ck_leader_bio_gaps_target；尚未套用到任何資料庫。
    /// </summary>
    public partial class GapTargetAllowsRole : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropCheckConstraint(
                name: "ck_leader_bio_gaps_target",
                table: "leader_bio_gaps");

            migrationBuilder.AddCheckConstraint(
                name: "ck_leader_bio_gaps_target",
                table: "leader_bio_gaps",
                sql: "target ~ '^(field|position|paragraph|role):[^[:space:]].*$|^identity$'");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropCheckConstraint(
                name: "ck_leader_bio_gaps_target",
                table: "leader_bio_gaps");

            migrationBuilder.AddCheckConstraint(
                name: "ck_leader_bio_gaps_target",
                table: "leader_bio_gaps",
                sql: "target ~ '^(field|position|paragraph):[^[:space:]].*$|^identity$'");
        }
    }
}
