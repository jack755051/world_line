using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace WorldLine.Api.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class SovereigntyDisputeKind : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "kind",
                table: "sovereignty_disputes",
                type: "character varying(16)",
                maxLength: 16,
                nullable: false,
                defaultValue: "contested");

            migrationBuilder.AddCheckConstraint(
                name: "ck_sovereignty_disputes_kind",
                table: "sovereignty_disputes",
                sql: "kind IN ('contested', 'layered')");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropCheckConstraint(
                name: "ck_sovereignty_disputes_kind",
                table: "sovereignty_disputes");

            migrationBuilder.DropColumn(
                name: "kind",
                table: "sovereignty_disputes");
        }
    }
}
