using System;
using Microsoft.EntityFrameworkCore.Migrations;
using NpgsqlTypes;

#nullable disable

namespace WorldLine.Api.Infrastructure.Migrations
{
    /// <summary>陣營時間切片（憲法 §6「陣營」、PRD §6.3 regime_alignments＋regime_alignment_citations）。</summary>
    public partial class RegimeAlignments : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "regime_alignments",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    regime_id = table.Column<Guid>(type: "uuid", nullable: false),
                    camp = table.Column<string>(type: "character varying(16)", maxLength: 16, nullable: false),
                    valid_period = table.Column<NpgsqlRange<DateOnly>>(type: "daterange", nullable: false),
                    basis_event_id = table.Column<Guid>(type: "uuid", nullable: true),
                    note = table.Column<string>(type: "jsonb", nullable: true),
                    retracted_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    retraction_reason = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    version = table.Column<int>(type: "integer", nullable: false, defaultValue: 0)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_regime_alignments", x => x.id);
                    table.CheckConstraint("ck_regime_alignments_camp", "camp IN ('axis', 'allies', 'co_belligerent', 'neutral')");
                    table.CheckConstraint("ck_regime_alignments_note_object", "note IS NULL OR jsonb_typeof(note) = 'object'");
                    table.CheckConstraint("ck_regime_alignments_retraction_reason", "retracted_at IS NULL OR retraction_reason IS NOT NULL");
                    table.CheckConstraint("ck_regime_alignments_start_bounded", "NOT lower_inf(valid_period) AND NOT isempty(valid_period)");
                    table.ForeignKey(
                        name: "fk_regime_alignments_historical_events_basis_event_id",
                        column: x => x.basis_event_id,
                        principalTable: "historical_events",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_regime_alignments_regimes_regime_id",
                        column: x => x.regime_id,
                        principalTable: "regimes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "regime_alignment_citations",
                columns: table => new
                {
                    regime_alignment_id = table.Column<Guid>(type: "uuid", nullable: false),
                    source_id = table.Column<Guid>(type: "uuid", nullable: false),
                    locator = table.Column<string>(type: "text", nullable: false),
                    role = table.Column<string>(type: "character varying(24)", maxLength: 24, nullable: false, defaultValue: "primary"),
                    evidence_note = table.Column<string>(type: "text", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_regime_alignment_citations", x => new { x.regime_alignment_id, x.source_id, x.locator });
                    table.CheckConstraint("ck_rac_role", "role IN ('primary', 'auxiliary_geometry', 'date_check')");
                    table.ForeignKey(
                        name: "fk_regime_alignment_citations_regime_alignments_regime_alignme",
                        column: x => x.regime_alignment_id,
                        principalTable: "regime_alignments",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_regime_alignment_citations_sources_source_id",
                        column: x => x.source_id,
                        principalTable: "sources",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "ix_regime_alignment_citations_source_id",
                table: "regime_alignment_citations",
                column: "source_id");

            migrationBuilder.CreateIndex(
                name: "ix_regime_alignments_basis_event_id",
                table: "regime_alignments",
                column: "basis_event_id");

            migrationBuilder.CreateIndex(
                name: "ix_regime_alignments_regime_id",
                table: "regime_alignments",
                column: "regime_id");

            // PRD §6.3：同一政權的有效切片不可重疊（撤回的不算）
            migrationBuilder.Sql("""
                ALTER TABLE regime_alignments
                  ADD CONSTRAINT ex_regime_alignments_no_overlap
                  EXCLUDE USING gist (regime_id WITH =, valid_period WITH &&) WHERE (retracted_at IS NULL);
                """);

            // I5：不可刪除；切片只允許「一次」寫入撤回（retracted_at＋retraction_reason），其他欄位不可改；引用寫入後不可改
            migrationBuilder.Sql("""
                CREATE FUNCTION wl_alignment_guard_update() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                  IF OLD.retracted_at IS NOT NULL THEN
                    RAISE EXCEPTION 'I5：陣營切片 % 已撤回，不可再修改', OLD.id
                      USING ERRCODE = 'restrict_violation';
                  END IF;
                  IF (to_jsonb(NEW) - 'retracted_at' - 'retraction_reason')
                     IS DISTINCT FROM (to_jsonb(OLD) - 'retracted_at' - 'retraction_reason') THEN
                    RAISE EXCEPTION 'I5：陣營切片 % 只允許寫入撤回（retracted_at／retraction_reason）；修正請撤回後新增', OLD.id
                      USING ERRCODE = 'restrict_violation';
                  END IF;
                  RETURN NEW;
                END $$;

                CREATE TRIGGER trg_regime_alignments_guard_update BEFORE UPDATE ON regime_alignments
                  FOR EACH ROW EXECUTE FUNCTION wl_alignment_guard_update();
                CREATE TRIGGER trg_rac_forbid_update BEFORE UPDATE ON regime_alignment_citations
                  FOR EACH ROW EXECUTE FUNCTION wl_forbid_update();
                """);
            foreach (var t in new[] { "regime_alignments", "regime_alignment_citations" })
            {
                migrationBuilder.Sql($"""
                    CREATE TRIGGER trg_{t}_forbid_delete BEFORE DELETE ON {t}
                      FOR EACH ROW EXECUTE FUNCTION wl_forbid_delete();
                    CREATE TRIGGER trg_{t}_forbid_truncate BEFORE TRUNCATE ON {t}
                      FOR EACH STATEMENT EXECUTE FUNCTION wl_forbid_delete();
                    """);
            }
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            throw new NotSupportedException("RegimeAlignments 不支援 Down（會刪除史料）；請改開新資料庫。");
        }
    }
}
