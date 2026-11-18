using System;
using Microsoft.EntityFrameworkCore.Migrations;
using NetTopologySuite.Geometries;
using NpgsqlTypes;

#nullable disable

namespace WorldLine.Api.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class CapitalRecords2 : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "capital_records",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    regime_id = table.Column<Guid>(type: "uuid", nullable: false),
                    city_name = table.Column<string>(type: "jsonb", nullable: false),
                    location = table.Column<Point>(type: "geometry(Point,4326)", nullable: false),
                    valid_period = table.Column<NpgsqlRange<DateOnly>>(type: "daterange", nullable: false),
                    source_ref = table.Column<string>(type: "text", nullable: true),
                    note = table.Column<string>(type: "text", nullable: true),
                    retracted_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    retraction_reason = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    version = table.Column<int>(type: "integer", nullable: false, defaultValue: 0)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_capital_records", x => x.id);
                    table.CheckConstraint("ck_capital_records_city_name_object", "jsonb_typeof(city_name) = 'object'");
                    table.CheckConstraint("ck_capital_records_retraction_reason", "retracted_at IS NULL OR retraction_reason IS NOT NULL");
                    table.CheckConstraint("ck_capital_records_start_bounded", "NOT lower_inf(valid_period) AND NOT isempty(valid_period)");
                    table.ForeignKey(
                        name: "fk_capital_records_regimes_regime_id",
                        column: x => x.regime_id,
                        principalTable: "regimes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "ix_capital_records_regime_id",
                table: "capital_records",
                column: "regime_id");

            migrationBuilder.CreateIndex(
                name: "ix_capital_records_valid_period",
                table: "capital_records",
                column: "valid_period")
                .Annotation("Npgsql:IndexMethod", "gist");

            // I5：只允許一次撤回（retracted_at 寫入後不可改回 null）
            migrationBuilder.Sql("""
                CREATE OR REPLACE FUNCTION fn_capital_records_no_unretract()
                RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    IF OLD.retracted_at IS NOT NULL AND NEW.retracted_at IS NULL THEN
                        RAISE EXCEPTION 'capital_records I5: retracted_at 不可撤銷（retracted_at: %）', OLD.retracted_at;
                    END IF;
                    RETURN NEW;
                END;
                $$;
                CREATE TRIGGER trg_capital_records_no_unretract
                BEFORE UPDATE ON capital_records
                FOR EACH ROW EXECUTE FUNCTION fn_capital_records_no_unretract();
                """);

            // EXCLUDE：同一政權的有效紀錄期間不可重疊（btree_gist 需已啟用）
            migrationBuilder.Sql("""
                ALTER TABLE capital_records
                    ADD CONSTRAINT excl_capital_records_no_overlap
                    EXCLUDE USING gist (regime_id WITH =, valid_period WITH &&)
                    WHERE (retracted_at IS NULL);
                """);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(name: "capital_records");
        }
    }
}
