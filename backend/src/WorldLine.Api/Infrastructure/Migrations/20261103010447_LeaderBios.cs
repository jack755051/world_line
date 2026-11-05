using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace WorldLine.Api.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class LeaderBios : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<Guid>(
                name: "person_id",
                table: "leader_records",
                type: "uuid",
                nullable: true);

            migrationBuilder.CreateTable(
                name: "leader_bios",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    name = table.Column<string>(type: "text", nullable: false),
                    name_zh = table.Column<string>(type: "text", nullable: true),
                    birth_date = table.Column<DateOnly>(type: "date", nullable: true),
                    birth_date_precision = table.Column<string>(type: "character varying(8)", maxLength: 8, nullable: true),
                    death_date = table.Column<DateOnly>(type: "date", nullable: true),
                    birth_place = table.Column<string>(type: "jsonb", nullable: true),
                    party = table.Column<string>(type: "jsonb", nullable: true),
                    summary = table.Column<string>(type: "jsonb", nullable: true),
                    field_sources = table.Column<string>(type: "jsonb", nullable: true),
                    is_test = table.Column<bool>(type: "boolean", nullable: false, defaultValue: false),
                    retracted_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    retraction_reason = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    version = table.Column<int>(type: "integer", nullable: false, defaultValue: 0)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_leader_bios", x => x.id);
                    table.CheckConstraint("ck_leader_bios_birth_date_precision", "birth_date_precision IS NULL OR birth_date_precision IN ('day', 'month', 'year')");
                    table.CheckConstraint("ck_leader_bios_birth_place_object", "birth_place IS NULL OR jsonb_typeof(birth_place) = 'object'");
                    table.CheckConstraint("ck_leader_bios_field_sources_object", "field_sources IS NULL OR jsonb_typeof(field_sources) = 'object'");
                    table.CheckConstraint("ck_leader_bios_name_not_blank", "btrim(name) <> ''");
                    table.CheckConstraint("ck_leader_bios_party_object", "party IS NULL OR jsonb_typeof(party) = 'object'");
                    table.CheckConstraint("ck_leader_bios_retraction_reason", "retracted_at IS NULL OR retraction_reason IS NOT NULL");
                    table.CheckConstraint("ck_leader_bios_summary_object", "summary IS NULL OR jsonb_typeof(summary) = 'object'");
                });

            migrationBuilder.CreateIndex(
                name: "ix_leader_records_person_id",
                table: "leader_records",
                column: "person_id",
                filter: "person_id IS NOT NULL");

            migrationBuilder.AddForeignKey(
                name: "fk_leader_records_leader_bios_person_id",
                table: "leader_records",
                column: "person_id",
                principalTable: "leader_bios",
                principalColumn: "id",
                onDelete: ReferentialAction.Restrict);

            // I5：只允許一次撤回（retracted_at 寫入後不可改回 null）
            migrationBuilder.Sql("""
                CREATE OR REPLACE FUNCTION fn_leader_bios_no_unretract()
                RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    IF OLD.retracted_at IS NOT NULL AND NEW.retracted_at IS NULL THEN
                        RAISE EXCEPTION 'leader_bios I5: retracted_at 不可撤銷（retracted_at: %）', OLD.retracted_at;
                    END IF;
                    RETURN NEW;
                END;
                $$;
                CREATE TRIGGER trg_leader_bios_no_unretract
                BEFORE UPDATE ON leader_bios
                FOR EACH ROW EXECUTE FUNCTION fn_leader_bios_no_unretract();
                """);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "fk_leader_records_leader_bios_person_id",
                table: "leader_records");

            migrationBuilder.DropTable(
                name: "leader_bios");

            migrationBuilder.DropIndex(
                name: "ix_leader_records_person_id",
                table: "leader_records");

            migrationBuilder.DropColumn(
                name: "person_id",
                table: "leader_records");
        }
    }
}
