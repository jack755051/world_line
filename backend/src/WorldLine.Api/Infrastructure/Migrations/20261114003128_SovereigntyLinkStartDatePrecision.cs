using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace WorldLine.Api.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class SovereigntyLinkStartDatePrecision : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "start_date_precision",
                table: "sovereignty_record_links",
                type: "character varying(8)",
                maxLength: 8,
                nullable: true);

            migrationBuilder.AddCheckConstraint(
                name: "ck_sovereignty_record_links_start_date_precision",
                table: "sovereignty_record_links",
                sql: "start_date_precision IS NULL OR start_date_precision IN ('day', 'month', 'year')");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropCheckConstraint(
                name: "ck_sovereignty_record_links_start_date_precision",
                table: "sovereignty_record_links");

            migrationBuilder.DropColumn(
                name: "start_date_precision",
                table: "sovereignty_record_links");
        }
    }
}
