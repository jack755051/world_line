using System;
using Microsoft.EntityFrameworkCore.Migrations;
using NpgsqlTypes;

#nullable disable

namespace WorldLine.Api.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class LeaderRecords : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "leader_records",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    regime_id = table.Column<Guid>(type: "uuid", nullable: false),
                    name = table.Column<string>(type: "text", nullable: false),
                    name_zh = table.Column<string>(type: "text", nullable: true),
                    role = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: false),
                    title = table.Column<string>(type: "text", nullable: true),
                    valid_period = table.Column<NpgsqlRange<DateOnly>>(type: "daterange", nullable: false),
                    source = table.Column<string>(type: "text", nullable: false),
                    source_url = table.Column<string>(type: "text", nullable: true),
                    verified = table.Column<bool>(type: "boolean", nullable: false, defaultValue: false),
                    retracted_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    retraction_reason = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    version = table.Column<int>(type: "integer", nullable: false, defaultValue: 0)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_leader_records", x => x.id);
                    table.CheckConstraint("ck_leader_records_name_not_blank", "btrim(name) <> ''");
                    table.CheckConstraint("ck_leader_records_retraction_reason", "retracted_at IS NULL OR retraction_reason IS NOT NULL");
                    table.CheckConstraint("ck_leader_records_role", "role IN ('head_of_state', 'head_of_government')");
                    table.CheckConstraint("ck_leader_records_source_not_blank", "btrim(source) <> ''");
                    table.CheckConstraint("ck_leader_records_start_bounded", "NOT lower_inf(valid_period) AND NOT isempty(valid_period)");
                    table.ForeignKey(
                        name: "fk_leader_records_regimes_regime_id",
                        column: x => x.regime_id,
                        principalTable: "regimes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "ix_leader_records_regime_id",
                table: "leader_records",
                column: "regime_id");

            migrationBuilder.CreateIndex(
                name: "ix_leader_records_valid_period",
                table: "leader_records",
                column: "valid_period")
                .Annotation("Npgsql:IndexMethod", "gist");

            // I5：只允許一次撤回（retracted_at 寫入後不可改回 null）
            migrationBuilder.Sql("""
                CREATE OR REPLACE FUNCTION fn_leader_records_no_unretract()
                RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    IF OLD.retracted_at IS NOT NULL AND NEW.retracted_at IS NULL THEN
                        RAISE EXCEPTION 'leader_records I5: retracted_at 不可撤銷（retracted_at: %）', OLD.retracted_at;
                    END IF;
                    RETURN NEW;
                END;
                $$;
                CREATE TRIGGER trg_leader_records_no_unretract
                BEFORE UPDATE ON leader_records
                FOR EACH ROW EXECUTE FUNCTION fn_leader_records_no_unretract();
                """);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "leader_records");
        }
    }
}
