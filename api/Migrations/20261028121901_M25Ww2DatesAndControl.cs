using System;
using Microsoft.EntityFrameworkCore.Migrations;
using NetTopologySuite.Geometries;
using NpgsqlTypes;

#nullable disable

namespace WorldLine.Api.Migrations
{
    /// <summary>
    /// M2.5（憲法 2026-10-28：二戰為第一階段）：
    /// - I7：int4range（年）→ daterange（日），原地轉型不刪資料；各區間加 from/to 精度（year/month/day），CHECK 以 wl_date_aligned 驗證對齊。
    /// - reign_eras 起訖年 → 起訖日＋精度（昭和元年只有 7 天）。
    /// - §4：regimes 新增終止狀態 annexed（被併吞）與 annexed_by_regime_id。
    /// - §4 選項 A／I6：regime_control_relations（控制方 → 被控制方、類型、日期區間、可選範圍）。
    /// - §6 Q8：alliances / alliance_aliases / alliance_memberships（加入／退出日）。
    /// - §9 Q11：historical_events.time_zone / time_note。
    /// I5 觸發器與排除約束見下一個遷移 M25IntegrityTriggers。
    /// </summary>
    public partial class M25Ww2DatesAndControl : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            // ---- 共用函式（後面的 CHECK 會用到，必須最先建立）----
            migrationBuilder.Sql(@"
CREATE OR REPLACE FUNCTION wl_date_aligned(d date, p text) RETURNS boolean
LANGUAGE sql IMMUTABLE AS $$
  SELECT CASE p
    WHEN 'year'  THEN extract(month FROM d) = 1 AND extract(day FROM d) = 1
    WHEN 'month' THEN extract(day FROM d) = 1
    WHEN 'day'   THEN true
    ELSE false
  END
$$;
COMMENT ON FUNCTION wl_date_aligned(date, text) IS 'I7：日期是否對齊精度（year→1/1、month→1 日、day→任意）。區間終點以 upper()（排他）檢查';

CREATE OR REPLACE FUNCTION wl_astro_jan1(y integer) RETURNS date
LANGUAGE sql IMMUTABLE AS $$
  SELECT make_date(CASE WHEN y <= 0 THEN y - 1 ELSE y END, 1, 1)
$$;
COMMENT ON FUNCTION wl_astro_jan1(integer) IS 'M2.5 遷移用：天文紀年年份（0 = 西元前 1 年）→ 該年 1 月 1 日（PostgreSQL 無 0 年）';");

            migrationBuilder.DropIndex(
                name: "ix_reign_eras_regime_id_era_name_start_year",
                table: "reign_eras");

            migrationBuilder.DropIndex(
                name: "ix_reign_eras_start_year_end_year",
                table: "reign_eras");

            migrationBuilder.DropCheckConstraint(
                name: "ck_reign_eras_year_order",
                table: "reign_eras");

            migrationBuilder.DropCheckConstraint(
                name: "ck_regimes_status",
                table: "regimes");

            // ---- 年份區間 → 日期區間（原地轉型，不刪資料）：int4range [a, b+1) → daterange [a-01-01, (b+1)-01-01) ----
            // ALTER COLUMN TYPE 會重寫表但不觸發列級觸發器；GiST 索引與 I3 排除約束會自動重建。
            foreach (var (table, column) in new[]
                     {
                         ("regimes", "existence_period"), ("regime_territories", "valid_period"),
                         ("regime_relations", "valid_period"), ("place_names", "valid_period"),
                     })
            {
                migrationBuilder.Sql($@"
ALTER TABLE {table} ALTER COLUMN {column} TYPE daterange USING
  CASE WHEN {column} IS NULL THEN NULL
       ELSE daterange(wl_astro_jan1(lower({column})),
                      CASE WHEN upper_inf({column}) THEN NULL ELSE wl_astro_jan1(upper({column})) END,
                      '[)') END;");
            }

            // ---- 精度欄位：既有資料全部只知年 → 'year'。以「加欄位帶預設值」回填，不必 UPDATE（不觸發 I5 修訂）----
            migrationBuilder.Sql(@"
ALTER TABLE regimes ADD COLUMN existence_from_precision character varying(8) NOT NULL DEFAULT 'year';
ALTER TABLE regimes ALTER COLUMN existence_from_precision DROP DEFAULT;
ALTER TABLE regimes ADD COLUMN existence_to_precision character varying(8) DEFAULT 'year';
ALTER TABLE regimes ALTER COLUMN existence_to_precision DROP DEFAULT;

ALTER TABLE regime_territories ADD COLUMN valid_from_precision character varying(8) NOT NULL DEFAULT 'year';
ALTER TABLE regime_territories ALTER COLUMN valid_from_precision DROP DEFAULT;
ALTER TABLE regime_territories ADD COLUMN valid_to_precision character varying(8) NOT NULL DEFAULT 'year';
ALTER TABLE regime_territories ALTER COLUMN valid_to_precision DROP DEFAULT;

ALTER TABLE regime_relations ADD COLUMN valid_from_precision character varying(8) NOT NULL DEFAULT 'year';
ALTER TABLE regime_relations ALTER COLUMN valid_from_precision DROP DEFAULT;
ALTER TABLE regime_relations ADD COLUMN valid_to_precision character varying(8) NOT NULL DEFAULT 'year';
ALTER TABLE regime_relations ALTER COLUMN valid_to_precision DROP DEFAULT;

ALTER TABLE place_names ADD COLUMN valid_from_precision character varying(8) DEFAULT 'year';
ALTER TABLE place_names ALTER COLUMN valid_from_precision DROP DEFAULT;
ALTER TABLE place_names ADD COLUMN valid_to_precision character varying(8) DEFAULT 'year';
ALTER TABLE place_names ALTER COLUMN valid_to_precision DROP DEFAULT;");

            // 開放終點（仍存續）與無期間的地名不該有精度：少數列需要 UPDATE，依 I5 附修改原因（寫入 data_revisions）
            migrationBuilder.Sql(@"
SELECT set_config('world_line.change_reason', 'M2.5 遷移：年份區間改為日期區間並補精度（開放終點不設終點精度）', true);
UPDATE regimes SET existence_to_precision = NULL WHERE upper_inf(existence_period);
UPDATE place_names SET valid_from_precision = NULL, valid_to_precision = NULL WHERE valid_period IS NULL;");

            // ---- 年號：起訖年 → 起訖日（起 = 起年 1/1，訖 = 訖年 12/31），保留原值 ----
            migrationBuilder.Sql(@"
ALTER TABLE reign_eras RENAME COLUMN start_year TO start_date;
ALTER TABLE reign_eras ALTER COLUMN start_date TYPE date USING wl_astro_jan1(start_date);
ALTER TABLE reign_eras RENAME COLUMN end_year TO end_date;
ALTER TABLE reign_eras ALTER COLUMN end_date TYPE date USING (wl_astro_jan1(end_date + 1) - 1);
ALTER TABLE reign_eras ALTER COLUMN end_date DROP NOT NULL;
ALTER TABLE reign_eras ADD COLUMN start_precision character varying(8) NOT NULL DEFAULT 'year';
ALTER TABLE reign_eras ALTER COLUMN start_precision DROP DEFAULT;
ALTER TABLE reign_eras ADD COLUMN end_precision character varying(8) DEFAULT 'year';
ALTER TABLE reign_eras ALTER COLUMN end_precision DROP DEFAULT;");

            migrationBuilder.AddColumn<Guid>(
                name: "annexed_by_regime_id",
                table: "regimes",
                type: "uuid",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "time_note",
                table: "historical_events",
                type: "text",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "time_zone",
                table: "historical_events",
                type: "character varying(64)",
                maxLength: 64,
                nullable: true);

            migrationBuilder.CreateTable(
                name: "alliances",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    self_name = table.Column<string>(type: "character varying(128)", maxLength: 128, nullable: false),
                    description = table.Column<string>(type: "text", nullable: true),
                    existence_period = table.Column<NpgsqlRange<DateOnly>>(type: "daterange", nullable: false),
                    existence_from_precision = table.Column<string>(type: "character varying(8)", maxLength: 8, nullable: false),
                    existence_to_precision = table.Column<string>(type: "character varying(8)", maxLength: 8, nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    updated_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    version = table.Column<int>(type: "integer", nullable: false, defaultValue: 0)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_alliances", x => x.id);
                    table.CheckConstraint("ck_alliances_existence_period", "NOT isempty(existence_period) AND NOT lower_inf(existence_period)");
                    table.CheckConstraint("ck_alliances_existence_precision", "existence_from_precision IN ('year', 'month', 'day') AND wl_date_aligned(lower(existence_period), existence_from_precision) AND ((upper_inf(existence_period) AND existence_to_precision IS NULL) OR (NOT upper_inf(existence_period) AND existence_to_precision IN ('year', 'month', 'day') AND wl_date_aligned(upper(existence_period), existence_to_precision)))");
                    table.CheckConstraint("ck_alliances_self_name_not_blank", "btrim(self_name) <> ''");
                });

            migrationBuilder.CreateTable(
                name: "regime_control_relations",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    controller_regime_id = table.Column<Guid>(type: "uuid", nullable: false),
                    controlled_regime_id = table.Column<Guid>(type: "uuid", nullable: false),
                    control_type = table.Column<string>(type: "character varying(16)", maxLength: 16, nullable: false),
                    valid_period = table.Column<NpgsqlRange<DateOnly>>(type: "daterange", nullable: false),
                    valid_from_precision = table.Column<string>(type: "character varying(8)", maxLength: 8, nullable: false),
                    valid_to_precision = table.Column<string>(type: "character varying(8)", maxLength: 8, nullable: false),
                    area = table.Column<MultiPolygon>(type: "geometry(MultiPolygon,4326)", nullable: true),
                    is_illustrative = table.Column<bool>(type: "boolean", nullable: false, defaultValue: false),
                    is_disputed = table.Column<bool>(type: "boolean", nullable: false, defaultValue: false),
                    description = table.Column<string>(type: "text", nullable: true),
                    source = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    version = table.Column<int>(type: "integer", nullable: false, defaultValue: 0)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_regime_control_relations", x => x.id);
                    table.CheckConstraint("ck_regime_control_relations_area_valid", "area IS NULL OR ST_IsValid(area)");
                    table.CheckConstraint("ck_regime_control_relations_distinct", "controller_regime_id <> controlled_regime_id");
                    table.CheckConstraint("ck_regime_control_relations_precision", "valid_from_precision IN ('year', 'month', 'day') AND wl_date_aligned(lower(valid_period), valid_from_precision) AND valid_to_precision IN ('year', 'month', 'day') AND wl_date_aligned(upper(valid_period), valid_to_precision)");
                    table.CheckConstraint("ck_regime_control_relations_type", "control_type IN ('occupation', 'puppet', 'protectorate', 'colony', 'mandate')");
                    table.CheckConstraint("ck_regime_control_relations_valid_period_bounded", "NOT isempty(valid_period) AND NOT lower_inf(valid_period) AND NOT upper_inf(valid_period)");
                    table.ForeignKey(
                        name: "fk_regime_control_relations_regimes_controlled_regime_id",
                        column: x => x.controlled_regime_id,
                        principalTable: "regimes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_regime_control_relations_regimes_controller_regime_id",
                        column: x => x.controller_regime_id,
                        principalTable: "regimes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "alliance_aliases",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    alliance_id = table.Column<Guid>(type: "uuid", nullable: false),
                    observer_regime_id = table.Column<Guid>(type: "uuid", nullable: true),
                    alias_name = table.Column<string>(type: "character varying(128)", maxLength: 128, nullable: false),
                    alias_type = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: false),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_alliance_aliases", x => x.id);
                    table.CheckConstraint("ck_alliance_aliases_alias_type", "alias_type IN ('contemporary', 'historiographic')");
                    table.CheckConstraint("ck_alliance_aliases_name_not_blank", "btrim(alias_name) <> ''");
                    table.ForeignKey(
                        name: "fk_alliance_aliases_alliances_alliance_id",
                        column: x => x.alliance_id,
                        principalTable: "alliances",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_alliance_aliases_regimes_observer_regime_id",
                        column: x => x.observer_regime_id,
                        principalTable: "regimes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "alliance_memberships",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    alliance_id = table.Column<Guid>(type: "uuid", nullable: false),
                    regime_id = table.Column<Guid>(type: "uuid", nullable: false),
                    role = table.Column<string>(type: "character varying(16)", maxLength: 16, nullable: false, defaultValue: "member"),
                    valid_period = table.Column<NpgsqlRange<DateOnly>>(type: "daterange", nullable: false),
                    valid_from_precision = table.Column<string>(type: "character varying(8)", maxLength: 8, nullable: false),
                    valid_to_precision = table.Column<string>(type: "character varying(8)", maxLength: 8, nullable: true),
                    note = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    version = table.Column<int>(type: "integer", nullable: false, defaultValue: 0)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_alliance_memberships", x => x.id);
                    table.CheckConstraint("ck_alliance_memberships_precision", "valid_from_precision IN ('year', 'month', 'day') AND wl_date_aligned(lower(valid_period), valid_from_precision) AND ((upper_inf(valid_period) AND valid_to_precision IS NULL) OR (NOT upper_inf(valid_period) AND valid_to_precision IN ('year', 'month', 'day') AND wl_date_aligned(upper(valid_period), valid_to_precision)))");
                    table.CheckConstraint("ck_alliance_memberships_role", "role IN ('member', 'co_belligerent', 'associate')");
                    table.CheckConstraint("ck_alliance_memberships_valid_period", "NOT isempty(valid_period) AND NOT lower_inf(valid_period)");
                    table.ForeignKey(
                        name: "fk_alliance_memberships_alliances_alliance_id",
                        column: x => x.alliance_id,
                        principalTable: "alliances",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_alliance_memberships_regimes_regime_id",
                        column: x => x.regime_id,
                        principalTable: "regimes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "ix_reign_eras_regime_id_era_name_start_date",
                table: "reign_eras",
                columns: new[] { "regime_id", "era_name", "start_date" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ix_reign_eras_start_date_end_date",
                table: "reign_eras",
                columns: new[] { "start_date", "end_date" });

            migrationBuilder.AddCheckConstraint(
                name: "ck_reign_eras_date_order",
                table: "reign_eras",
                sql: "end_date IS NULL OR start_date <= end_date");

            migrationBuilder.AddCheckConstraint(
                name: "ck_reign_eras_precision",
                table: "reign_eras",
                sql: "start_precision IN ('year', 'month', 'day') AND wl_date_aligned(start_date, start_precision) AND ((end_date IS NULL AND end_precision IS NULL) OR (end_date IS NOT NULL AND end_precision IN ('year', 'month', 'day') AND wl_date_aligned(end_date + 1, end_precision)))");

            migrationBuilder.CreateIndex(
                name: "ix_regimes_annexed_by_regime_id",
                table: "regimes",
                column: "annexed_by_regime_id");

            migrationBuilder.AddCheckConstraint(
                name: "ck_regimes_annexed_by_iff_annexed",
                table: "regimes",
                sql: "(status = 'annexed') = (annexed_by_regime_id IS NOT NULL)");

            migrationBuilder.AddCheckConstraint(
                name: "ck_regimes_existence_precision",
                table: "regimes",
                sql: "existence_from_precision IN ('year', 'month', 'day') AND wl_date_aligned(lower(existence_period), existence_from_precision) AND ((upper_inf(existence_period) AND existence_to_precision IS NULL) OR (NOT upper_inf(existence_period) AND existence_to_precision IN ('year', 'month', 'day') AND wl_date_aligned(upper(existence_period), existence_to_precision)))");

            migrationBuilder.AddCheckConstraint(
                name: "ck_regimes_not_annexed_by_self",
                table: "regimes",
                sql: "annexed_by_regime_id <> id");

            migrationBuilder.AddCheckConstraint(
                name: "ck_regimes_status",
                table: "regimes",
                sql: "status IN ('existing', 'split', 'abdicated', 'destroyed', 'annexed')");

            migrationBuilder.AddCheckConstraint(
                name: "ck_regime_territories_precision",
                table: "regime_territories",
                sql: "valid_from_precision IN ('year', 'month', 'day') AND wl_date_aligned(lower(valid_period), valid_from_precision) AND valid_to_precision IN ('year', 'month', 'day') AND wl_date_aligned(upper(valid_period), valid_to_precision)");

            migrationBuilder.AddCheckConstraint(
                name: "ck_regime_relations_precision",
                table: "regime_relations",
                sql: "valid_from_precision IN ('year', 'month', 'day') AND wl_date_aligned(lower(valid_period), valid_from_precision) AND valid_to_precision IN ('year', 'month', 'day') AND wl_date_aligned(upper(valid_period), valid_to_precision)");

            migrationBuilder.AddCheckConstraint(
                name: "ck_place_names_precision",
                table: "place_names",
                sql: "(valid_period IS NULL AND valid_from_precision IS NULL AND valid_to_precision IS NULL) OR (valid_period IS NOT NULL AND valid_from_precision IN ('year', 'month', 'day') AND wl_date_aligned(lower(valid_period), valid_from_precision) AND valid_to_precision IN ('year', 'month', 'day') AND wl_date_aligned(upper(valid_period), valid_to_precision))");

            migrationBuilder.AddCheckConstraint(
                name: "ck_historical_events_time_zone",
                table: "historical_events",
                sql: "time_zone IS NULL OR btrim(time_zone) <> ''");

            migrationBuilder.CreateIndex(
                name: "ix_alliance_aliases_alliance_id_observer_regime_id_alias_name",
                table: "alliance_aliases",
                columns: new[] { "alliance_id", "observer_regime_id", "alias_name" },
                unique: true)
                .Annotation("Npgsql:NullsDistinct", false);

            migrationBuilder.CreateIndex(
                name: "ix_alliance_aliases_observer_regime_id",
                table: "alliance_aliases",
                column: "observer_regime_id");

            migrationBuilder.CreateIndex(
                name: "ix_alliance_memberships_alliance_id_regime_id",
                table: "alliance_memberships",
                columns: new[] { "alliance_id", "regime_id" });

            migrationBuilder.CreateIndex(
                name: "ix_alliance_memberships_regime_id",
                table: "alliance_memberships",
                column: "regime_id");

            migrationBuilder.CreateIndex(
                name: "ix_alliance_memberships_valid_period",
                table: "alliance_memberships",
                column: "valid_period")
                .Annotation("Npgsql:IndexMethod", "gist");

            migrationBuilder.CreateIndex(
                name: "ix_alliances_existence_period",
                table: "alliances",
                column: "existence_period")
                .Annotation("Npgsql:IndexMethod", "gist");

            migrationBuilder.CreateIndex(
                name: "ix_alliances_self_name",
                table: "alliances",
                column: "self_name",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ix_regime_control_relations_area",
                table: "regime_control_relations",
                column: "area")
                .Annotation("Npgsql:IndexMethod", "gist");

            migrationBuilder.CreateIndex(
                name: "ix_regime_control_relations_controlled_regime_id",
                table: "regime_control_relations",
                column: "controlled_regime_id");

            migrationBuilder.CreateIndex(
                name: "ix_regime_control_relations_controller_regime_id",
                table: "regime_control_relations",
                column: "controller_regime_id");

            migrationBuilder.CreateIndex(
                name: "ix_regime_control_relations_valid_period",
                table: "regime_control_relations",
                column: "valid_period")
                .Annotation("Npgsql:IndexMethod", "gist");

            migrationBuilder.AddForeignKey(
                name: "fk_regimes_regimes_annexed_by_regime_id",
                table: "regimes",
                column: "annexed_by_regime_id",
                principalTable: "regimes",
                principalColumn: "id",
                onDelete: ReferentialAction.Restrict);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            // 不提供自動回退：日期區間轉回年份會丟失日／月精度，且新表（控制關係、陣營）只能刪除——違反「不刪資料」(I5)。
            // 需要回退時請以資料庫備份還原。
            throw new NotSupportedException("M2.5（日期區間、控制關係、同盟陣營）不提供自動回退；請以備份還原。");
        }
    }
}
