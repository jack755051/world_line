using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace WorldLine.Api.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class SovereigntyDisputes : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "sovereignty_disputes",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    slug = table.Column<string>(type: "character varying(80)", maxLength: 80, nullable: false),
                    summary = table.Column<string>(type: "jsonb", nullable: false),
                    retracted_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    retraction_reason = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_sovereignty_disputes", x => x.id);
                    table.CheckConstraint("ck_sovereignty_disputes_retraction_reason", "retracted_at IS NULL OR retraction_reason IS NOT NULL");
                    table.CheckConstraint("ck_sovereignty_disputes_slug", "slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'");
                    table.CheckConstraint("ck_sovereignty_disputes_summary_object", "jsonb_typeof(summary) = 'object'");
                });

            migrationBuilder.CreateTable(
                name: "sovereignty_dispute_claims",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    dispute_id = table.Column<Guid>(type: "uuid", nullable: false),
                    claimant_regime_id = table.Column<Guid>(type: "uuid", nullable: false),
                    record_id = table.Column<Guid>(type: "uuid", nullable: true),
                    position = table.Column<string>(type: "jsonb", nullable: false),
                    effective = table.Column<bool>(type: "boolean", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_sovereignty_dispute_claims", x => x.id);
                    table.CheckConstraint("ck_sovereignty_dispute_claims_position_object", "jsonb_typeof(position) = 'object'");
                    table.ForeignKey(
                        name: "fk_sovereignty_dispute_claims_regimes_claimant_regime_id",
                        column: x => x.claimant_regime_id,
                        principalTable: "regimes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_sovereignty_dispute_claims_sovereignty_disputes_dispute_id",
                        column: x => x.dispute_id,
                        principalTable: "sovereignty_disputes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_sovereignty_dispute_claims_sovereignty_records_record_id",
                        column: x => x.record_id,
                        principalTable: "sovereignty_records",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "ix_sovereignty_dispute_claims_claimant_regime_id",
                table: "sovereignty_dispute_claims",
                column: "claimant_regime_id");

            migrationBuilder.CreateIndex(
                name: "ix_sovereignty_dispute_claims_record_id",
                table: "sovereignty_dispute_claims",
                column: "record_id");

            migrationBuilder.CreateIndex(
                name: "ux_sovereignty_dispute_claims_record",
                table: "sovereignty_dispute_claims",
                columns: new[] { "dispute_id", "record_id" },
                unique: true,
                filter: "record_id IS NOT NULL");

            migrationBuilder.CreateIndex(
                name: "ux_sovereignty_disputes_slug_live",
                table: "sovereignty_disputes",
                column: "slug",
                unique: true,
                filter: "retracted_at IS NULL");

            // I5：爭議只能撤回，不可修改或刪除；主張列完全不可改（跟著爭議一起撤回）。
            migrationBuilder.Sql("""
                CREATE OR REPLACE FUNCTION fn_sovereignty_disputes_guard() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'sovereignty_disputes I5: 不可刪除，請改用撤回'; END IF;
                    IF OLD.retracted_at IS NOT NULL THEN RAISE EXCEPTION 'sovereignty_disputes I5: 已撤回的列不可再改'; END IF;
                    IF NEW.retracted_at IS NULL OR (to_jsonb(NEW) - 'retracted_at' - 'retraction_reason') IS DISTINCT FROM (to_jsonb(OLD) - 'retracted_at' - 'retraction_reason') THEN
                        RAISE EXCEPTION 'sovereignty_disputes I5: 只能撤回，不可修改；更正請撤回後另寫一筆';
                    END IF;
                    RETURN NEW;
                END $$;
                CREATE TRIGGER trg_sovereignty_disputes_guard BEFORE UPDATE OR DELETE ON sovereignty_disputes
                    FOR EACH ROW EXECUTE FUNCTION fn_sovereignty_disputes_guard();
                CREATE OR REPLACE FUNCTION fn_sovereignty_dispute_claims_guard() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    RAISE EXCEPTION 'sovereignty_dispute_claims I5: 不可修改或刪除；更正請撤回整筆爭議後重寫';
                END $$;
                CREATE TRIGGER trg_sovereignty_dispute_claims_guard BEFORE UPDATE OR DELETE ON sovereignty_dispute_claims
                    FOR EACH ROW EXECUTE FUNCTION fn_sovereignty_dispute_claims_guard();
                """);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql("""
                DROP TRIGGER IF EXISTS trg_sovereignty_dispute_claims_guard ON sovereignty_dispute_claims;
                DROP FUNCTION IF EXISTS fn_sovereignty_dispute_claims_guard();
                DROP TRIGGER IF EXISTS trg_sovereignty_disputes_guard ON sovereignty_disputes;
                DROP FUNCTION IF EXISTS fn_sovereignty_disputes_guard();
                """);
            migrationBuilder.DropTable(
                name: "sovereignty_dispute_claims");

            migrationBuilder.DropTable(
                name: "sovereignty_disputes");
        }
    }
}
