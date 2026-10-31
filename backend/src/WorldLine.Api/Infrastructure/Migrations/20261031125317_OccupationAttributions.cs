using System;
using Microsoft.EntityFrameworkCore.Migrations;
using NpgsqlTypes;

#nullable disable

namespace WorldLine.Api.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class OccupationAttributions : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "occupation_attributions",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    occupied_regime_id = table.Column<Guid>(type: "uuid", nullable: false),
                    occupier_regime_id = table.Column<Guid>(type: "uuid", nullable: false),
                    control_kind = table.Column<string>(type: "character varying(24)", maxLength: 24, nullable: false),
                    valid_period = table.Column<NpgsqlRange<DateOnly>>(type: "daterange", nullable: false),
                    basis_event_id = table.Column<Guid>(type: "uuid", nullable: true),
                    co_occupied = table.Column<bool>(type: "boolean", nullable: false),
                    note = table.Column<string>(type: "jsonb", nullable: true),
                    retracted_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    retraction_reason = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    version = table.Column<int>(type: "integer", nullable: false, defaultValue: 0)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_occupation_attributions", x => x.id);
                    table.CheckConstraint("ck_occupation_attributions_control_kind", "control_kind IN ('annexed', 'civil_administration', 'military_administration')");
                    table.CheckConstraint("ck_occupation_attributions_distinct_regimes", "occupied_regime_id <> occupier_regime_id");
                    table.CheckConstraint("ck_occupation_attributions_note_object", "note IS NULL OR jsonb_typeof(note) = 'object'");
                    table.CheckConstraint("ck_occupation_attributions_retraction_reason", "retracted_at IS NULL OR retraction_reason IS NOT NULL");
                    table.CheckConstraint("ck_occupation_attributions_start_bounded", "NOT lower_inf(valid_period) AND NOT isempty(valid_period)");
                    table.ForeignKey(
                        name: "fk_occupation_attributions_historical_events_basis_event_id",
                        column: x => x.basis_event_id,
                        principalTable: "historical_events",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_occupation_attributions_regimes_occupied_regime_id",
                        column: x => x.occupied_regime_id,
                        principalTable: "regimes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_occupation_attributions_regimes_occupier_regime_id",
                        column: x => x.occupier_regime_id,
                        principalTable: "regimes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "ix_occupation_attributions_basis_event_id",
                table: "occupation_attributions",
                column: "basis_event_id");

            migrationBuilder.CreateIndex(
                name: "ix_occupation_attributions_occupied_regime_id",
                table: "occupation_attributions",
                column: "occupied_regime_id");

            migrationBuilder.CreateIndex(
                name: "ix_occupation_attributions_occupier_regime_id",
                table: "occupation_attributions",
                column: "occupier_regime_id");

            migrationBuilder.CreateIndex(
                name: "ix_occupation_attributions_valid_period",
                table: "occupation_attributions",
                column: "valid_period")
                .Annotation("Npgsql:IndexMethod", "gist");

            // 同一被佔領政權的有效歸屬期間不可重疊；I5：不可刪除，只允許「一次」寫入撤回，其他欄位不可改；修正＝撤回後新增
            migrationBuilder.Sql("""
                ALTER TABLE occupation_attributions ADD CONSTRAINT ex_occupation_attributions_no_overlap
                  EXCLUDE USING gist (occupied_regime_id WITH =, valid_period WITH &&) WHERE (retracted_at IS NULL);

                CREATE FUNCTION wl_occupation_guard_update() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                  IF OLD.retracted_at IS NOT NULL THEN
                    RAISE EXCEPTION 'I5：佔領歸屬 % 已撤回，不可再修改', OLD.id
                      USING ERRCODE = 'restrict_violation';
                  END IF;
                  IF (to_jsonb(NEW) - 'retracted_at' - 'retraction_reason')
                     IS DISTINCT FROM (to_jsonb(OLD) - 'retracted_at' - 'retraction_reason') THEN
                    RAISE EXCEPTION 'I5：佔領歸屬 % 只允許寫入撤回（retracted_at／retraction_reason）；修正請撤回後新增', OLD.id
                      USING ERRCODE = 'restrict_violation';
                  END IF;
                  RETURN NEW;
                END $$;

                CREATE TRIGGER trg_occupation_attributions_guard_update BEFORE UPDATE ON occupation_attributions
                  FOR EACH ROW EXECUTE FUNCTION wl_occupation_guard_update();
                CREATE TRIGGER trg_occupation_attributions_forbid_delete BEFORE DELETE ON occupation_attributions
                  FOR EACH ROW EXECUTE FUNCTION wl_forbid_delete();
                CREATE TRIGGER trg_occupation_attributions_forbid_truncate BEFORE TRUNCATE ON occupation_attributions
                  FOR EACH STATEMENT EXECUTE FUNCTION wl_forbid_delete();
                """);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            throw new NotSupportedException("OccupationAttributions 不支援 Down（會刪除史料）；請改開新資料庫。");
        }
    }
}
