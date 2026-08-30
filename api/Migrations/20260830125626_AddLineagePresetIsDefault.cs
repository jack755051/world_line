using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace WorldLine.Api.Migrations
{
    /// <inheritdoc />
    public partial class AddLineagePresetIsDefault : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<bool>(
                name: "is_default",
                table: "lineage_presets",
                type: "boolean",
                nullable: false,
                defaultValue: false);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "is_default",
                table: "lineage_presets");
        }
    }
}
