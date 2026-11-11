using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace WorldLine.Api.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class BattleEventKindOperation : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropCheckConstraint(
                name: "ck_historical_events_kind",
                table: "historical_events");

            migrationBuilder.AddCheckConstraint(
                name: "ck_historical_events_kind",
                table: "historical_events",
                sql: "event_kind IN ('war', 'campaign', 'battle', 'treaty', 'armistice', 'surrender', 'political', 'atrocity', 'operation')");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropCheckConstraint(
                name: "ck_historical_events_kind",
                table: "historical_events");

            migrationBuilder.AddCheckConstraint(
                name: "ck_historical_events_kind",
                table: "historical_events",
                sql: "event_kind IN ('war', 'campaign', 'battle', 'treaty', 'armistice', 'surrender', 'political', 'atrocity')");
        }
    }
}
