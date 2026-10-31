using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace WorldLine.Api.Infrastructure.Migrations
{
    /// <summary>事後追加事件參與方（方案 A，Tai 2026-10-31）：event_participants 加 added_at、addition_note（追加理由）。原有 I5 trigger（不可改、不可刪）不變。</summary>
    public partial class EventParticipantAppend : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<DateTimeOffset>(
                name: "added_at",
                table: "event_participants",
                type: "timestamp with time zone",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "addition_note",
                table: "event_participants",
                type: "jsonb",
                nullable: true);

            migrationBuilder.AddCheckConstraint(
                name: "ck_event_participants_addition",
                table: "event_participants",
                sql: "(added_at IS NULL) = (addition_note IS NULL) AND (addition_note IS NULL OR jsonb_typeof(addition_note) = 'object')");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            throw new NotSupportedException("EventParticipantAppend 不支援 Down（會刪除追加理由）；請改開新資料庫。");
        }
    }
}
