using System;
using Microsoft.EntityFrameworkCore.Migrations;
using NpgsqlTypes;

#nullable disable

namespace WorldLine.Api.Infrastructure.Migrations
{
    /// <inheritdoc />
    /// <summary>
    /// B3 分段生平（ARCHITECTURE §16.2–16.4，2026-11-11；Tai 同意，只寫檔、本回合不套用）：新增 6 表（段落／經歷／角色＋各自 citation）、
    /// I5 trigger（禁 DELETE／TRUNCATE、撤回不可撤銷）、sources.source_kind 加 encyclopedia／official_website。
    /// person_roles.role_kind CHECK 含 cabinet_minister（對草案 P1 的必要擴充）。leader_records／leader_bio_gaps 不動。
    /// </summary>
    public partial class BioParagraphsPositionsRoles : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropCheckConstraint(
                name: "ck_sources_source_kind",
                table: "sources");

            migrationBuilder.CreateTable(
                name: "leader_bio_paragraphs",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    bio_id = table.Column<Guid>(type: "uuid", nullable: false),
                    ord = table.Column<int>(type: "integer", nullable: false),
                    period = table.Column<NpgsqlRange<DateOnly>>(type: "daterange", nullable: true),
                    period_start_precision = table.Column<string>(type: "character varying(8)", maxLength: 8, nullable: true),
                    period_end_precision = table.Column<string>(type: "character varying(8)", maxLength: 8, nullable: true),
                    heading = table.Column<string>(type: "jsonb", nullable: true),
                    body = table.Column<string>(type: "jsonb", nullable: false),
                    related_record_ids = table.Column<Guid[]>(type: "uuid[]", nullable: true),
                    superseded_by = table.Column<Guid>(type: "uuid", nullable: true),
                    retracted_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    retraction_reason = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    version = table.Column<int>(type: "integer", nullable: false, defaultValue: 0)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_leader_bio_paragraphs", x => x.id);
                    table.CheckConstraint("ck_leader_bio_paragraphs_body_object", "jsonb_typeof(body) = 'object'");
                    table.CheckConstraint("ck_leader_bio_paragraphs_end_precision", "period_end_precision IS NULL OR period_end_precision IN ('day', 'month', 'year')");
                    table.CheckConstraint("ck_leader_bio_paragraphs_heading_object", "heading IS NULL OR jsonb_typeof(heading) = 'object'");
                    table.CheckConstraint("ck_leader_bio_paragraphs_ord", "ord > 0");
                    table.CheckConstraint("ck_leader_bio_paragraphs_period", "period IS NULL OR (NOT isempty(period) AND NOT lower_inf(period))");
                    table.CheckConstraint("ck_leader_bio_paragraphs_retraction_reason", "retracted_at IS NULL OR retraction_reason IS NOT NULL");
                    table.CheckConstraint("ck_leader_bio_paragraphs_start_precision", "period_start_precision IS NULL OR period_start_precision IN ('day', 'month', 'year')");
                    table.ForeignKey(
                        name: "fk_leader_bio_paragraphs_leader_bio_paragraphs_superseded_by",
                        column: x => x.superseded_by,
                        principalTable: "leader_bio_paragraphs",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_leader_bio_paragraphs_leader_bios_bio_id",
                        column: x => x.bio_id,
                        principalTable: "leader_bios",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "person_positions",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    bio_id = table.Column<Guid>(type: "uuid", nullable: false),
                    seed_key = table.Column<string>(type: "text", nullable: false),
                    regime_id = table.Column<Guid>(type: "uuid", nullable: true),
                    organization = table.Column<string>(type: "jsonb", nullable: true),
                    title = table.Column<string>(type: "jsonb", nullable: false),
                    position_kind = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: false),
                    period = table.Column<NpgsqlRange<DateOnly>>(type: "daterange", nullable: false),
                    start_precision = table.Column<string>(type: "character varying(8)", maxLength: 8, nullable: true),
                    end_precision = table.Column<string>(type: "character varying(8)", maxLength: 8, nullable: true),
                    note = table.Column<string>(type: "text", nullable: true),
                    superseded_by = table.Column<Guid>(type: "uuid", nullable: true),
                    retracted_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    retraction_reason = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    version = table.Column<int>(type: "integer", nullable: false, defaultValue: 0)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_person_positions", x => x.id);
                    table.CheckConstraint("ck_person_positions_end_precision", "end_precision IS NULL OR (end_precision IN ('day', 'month', 'year') AND NOT upper_inf(period))");
                    table.CheckConstraint("ck_person_positions_organization_object", "organization IS NULL OR jsonb_typeof(organization) = 'object'");
                    table.CheckConstraint("ck_person_positions_period", "NOT isempty(period) AND NOT lower_inf(period)");
                    table.CheckConstraint("ck_person_positions_position_kind", "position_kind IN ('minister', 'legislator', 'diplomat', 'military_command', 'military_education', 'judicial', 'police', 'other')");
                    table.CheckConstraint("ck_person_positions_retraction_reason", "retracted_at IS NULL OR retraction_reason IS NOT NULL");
                    table.CheckConstraint("ck_person_positions_seed_key_not_blank", "btrim(seed_key) <> ''");
                    table.CheckConstraint("ck_person_positions_start_precision", "start_precision IS NULL OR start_precision IN ('day', 'month', 'year')");
                    table.CheckConstraint("ck_person_positions_title_object", "jsonb_typeof(title) = 'object'");
                    table.ForeignKey(
                        name: "fk_person_positions_leader_bios_bio_id",
                        column: x => x.bio_id,
                        principalTable: "leader_bios",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_person_positions_person_positions_superseded_by",
                        column: x => x.superseded_by,
                        principalTable: "person_positions",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_person_positions_regimes_regime_id",
                        column: x => x.regime_id,
                        principalTable: "regimes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "person_roles",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    bio_id = table.Column<Guid>(type: "uuid", nullable: false),
                    seed_key = table.Column<string>(type: "text", nullable: false),
                    regime_id = table.Column<Guid>(type: "uuid", nullable: true),
                    organization = table.Column<string>(type: "jsonb", nullable: true),
                    title = table.Column<string>(type: "jsonb", nullable: false),
                    role_kind = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: false),
                    period = table.Column<NpgsqlRange<DateOnly>>(type: "daterange", nullable: false),
                    start_precision = table.Column<string>(type: "character varying(8)", maxLength: 8, nullable: true),
                    end_precision = table.Column<string>(type: "character varying(8)", maxLength: 8, nullable: true),
                    acting = table.Column<bool>(type: "boolean", nullable: false, defaultValue: false),
                    t14_rule = table.Column<string>(type: "character varying(8)", maxLength: 8, nullable: true),
                    note = table.Column<string>(type: "text", nullable: true),
                    superseded_by = table.Column<Guid>(type: "uuid", nullable: true),
                    retracted_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    retraction_reason = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    version = table.Column<int>(type: "integer", nullable: false, defaultValue: 0)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_person_roles", x => x.id);
                    table.CheckConstraint("ck_person_roles_end_precision", "end_precision IS NULL OR (end_precision IN ('day', 'month', 'year') AND NOT upper_inf(period))");
                    table.CheckConstraint("ck_person_roles_organization_object", "organization IS NULL OR jsonb_typeof(organization) = 'object'");
                    table.CheckConstraint("ck_person_roles_period", "NOT isempty(period) AND NOT lower_inf(period)");
                    table.CheckConstraint("ck_person_roles_retraction_reason", "retracted_at IS NULL OR retraction_reason IS NOT NULL");
                    table.CheckConstraint("ck_person_roles_role_kind", "role_kind IN ('head_of_state', 'head_of_government', 'de_facto_leader', 'cabinet_minister')");
                    table.CheckConstraint("ck_person_roles_seed_key_not_blank", "btrim(seed_key) <> ''");
                    table.CheckConstraint("ck_person_roles_start_precision", "start_precision IS NULL OR start_precision IN ('day', 'month', 'year')");
                    table.CheckConstraint("ck_person_roles_t14_rule", "t14_rule IS NULL OR t14_rule ~ '^R[0-9]$'");
                    table.CheckConstraint("ck_person_roles_title_object", "jsonb_typeof(title) = 'object'");
                    table.ForeignKey(
                        name: "fk_person_roles_leader_bios_bio_id",
                        column: x => x.bio_id,
                        principalTable: "leader_bios",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_person_roles_person_roles_superseded_by",
                        column: x => x.superseded_by,
                        principalTable: "person_roles",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_person_roles_regimes_regime_id",
                        column: x => x.regime_id,
                        principalTable: "regimes",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "leader_bio_paragraph_citations",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    paragraph_id = table.Column<Guid>(type: "uuid", nullable: false),
                    source_id = table.Column<Guid>(type: "uuid", nullable: false),
                    locator = table.Column<string>(type: "text", nullable: false),
                    quote = table.Column<string>(type: "text", nullable: false),
                    quote_lang = table.Column<string>(type: "character varying(35)", maxLength: 35, nullable: true),
                    evidence_note = table.Column<string>(type: "text", nullable: true),
                    accessed_on = table.Column<DateOnly>(type: "date", nullable: false),
                    grade = table.Column<string>(type: "character varying(1)", maxLength: 1, nullable: true),
                    date_precision = table.Column<string>(type: "character varying(8)", maxLength: 8, nullable: true),
                    claim_span = table.Column<NpgsqlRange<int>>(type: "int4range", nullable: true),
                    policy_version = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: true),
                    retracted_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    retraction_reason = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_leader_bio_paragraph_citations", x => x.id);
                    table.CheckConstraint("ck_leader_bio_paragraph_citations_claim_span", "claim_span IS NULL OR (NOT isempty(claim_span) AND lower(claim_span) >= 0)");
                    table.CheckConstraint("ck_leader_bio_paragraph_citations_date_precision", "date_precision IS NULL OR date_precision IN ('day', 'month', 'year')");
                    table.CheckConstraint("ck_leader_bio_paragraph_citations_grade", "grade IS NULL OR grade IN ('A', 'B')");
                    table.CheckConstraint("ck_leader_bio_paragraph_citations_locator_not_blank", "btrim(locator) <> ''");
                    table.CheckConstraint("ck_leader_bio_paragraph_citations_quote_not_blank", "btrim(quote) <> ''");
                    table.CheckConstraint("ck_leader_bio_paragraph_citations_retraction_reason", "retracted_at IS NULL OR retraction_reason IS NOT NULL");
                    table.ForeignKey(
                        name: "fk_leader_bio_paragraph_citations_leader_bio_paragraphs_paragr",
                        column: x => x.paragraph_id,
                        principalTable: "leader_bio_paragraphs",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_leader_bio_paragraph_citations_sources_source_id",
                        column: x => x.source_id,
                        principalTable: "sources",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "person_position_citations",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    position_id = table.Column<Guid>(type: "uuid", nullable: false),
                    source_id = table.Column<Guid>(type: "uuid", nullable: false),
                    locator = table.Column<string>(type: "text", nullable: false),
                    quote = table.Column<string>(type: "text", nullable: false),
                    quote_lang = table.Column<string>(type: "character varying(35)", maxLength: 35, nullable: true),
                    evidence_note = table.Column<string>(type: "text", nullable: true),
                    accessed_on = table.Column<DateOnly>(type: "date", nullable: false),
                    grade = table.Column<string>(type: "character varying(1)", maxLength: 1, nullable: true),
                    date_precision = table.Column<string>(type: "character varying(8)", maxLength: 8, nullable: true),
                    claim_span = table.Column<NpgsqlRange<int>>(type: "int4range", nullable: true),
                    policy_version = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: true),
                    retracted_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    retraction_reason = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_person_position_citations", x => x.id);
                    table.CheckConstraint("ck_person_position_citations_claim_span", "claim_span IS NULL OR (NOT isempty(claim_span) AND lower(claim_span) >= 0)");
                    table.CheckConstraint("ck_person_position_citations_date_precision", "date_precision IS NULL OR date_precision IN ('day', 'month', 'year')");
                    table.CheckConstraint("ck_person_position_citations_grade", "grade IS NULL OR grade IN ('A', 'B')");
                    table.CheckConstraint("ck_person_position_citations_locator_not_blank", "btrim(locator) <> ''");
                    table.CheckConstraint("ck_person_position_citations_quote_not_blank", "btrim(quote) <> ''");
                    table.CheckConstraint("ck_person_position_citations_retraction_reason", "retracted_at IS NULL OR retraction_reason IS NOT NULL");
                    table.ForeignKey(
                        name: "fk_person_position_citations_person_positions_position_id",
                        column: x => x.position_id,
                        principalTable: "person_positions",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_person_position_citations_sources_source_id",
                        column: x => x.source_id,
                        principalTable: "sources",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "person_role_citations",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                    role_id = table.Column<Guid>(type: "uuid", nullable: false),
                    source_id = table.Column<Guid>(type: "uuid", nullable: false),
                    locator = table.Column<string>(type: "text", nullable: false),
                    quote = table.Column<string>(type: "text", nullable: false),
                    quote_lang = table.Column<string>(type: "character varying(35)", maxLength: 35, nullable: true),
                    evidence_note = table.Column<string>(type: "text", nullable: true),
                    accessed_on = table.Column<DateOnly>(type: "date", nullable: false),
                    grade = table.Column<string>(type: "character varying(1)", maxLength: 1, nullable: true),
                    date_precision = table.Column<string>(type: "character varying(8)", maxLength: 8, nullable: true),
                    claim_span = table.Column<NpgsqlRange<int>>(type: "int4range", nullable: true),
                    policy_version = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: true),
                    retracted_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    retraction_reason = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_person_role_citations", x => x.id);
                    table.CheckConstraint("ck_person_role_citations_claim_span", "claim_span IS NULL OR (NOT isempty(claim_span) AND lower(claim_span) >= 0)");
                    table.CheckConstraint("ck_person_role_citations_date_precision", "date_precision IS NULL OR date_precision IN ('day', 'month', 'year')");
                    table.CheckConstraint("ck_person_role_citations_grade", "grade IS NULL OR grade IN ('A', 'B')");
                    table.CheckConstraint("ck_person_role_citations_locator_not_blank", "btrim(locator) <> ''");
                    table.CheckConstraint("ck_person_role_citations_quote_not_blank", "btrim(quote) <> ''");
                    table.CheckConstraint("ck_person_role_citations_retraction_reason", "retracted_at IS NULL OR retraction_reason IS NOT NULL");
                    table.ForeignKey(
                        name: "fk_person_role_citations_person_roles_role_id",
                        column: x => x.role_id,
                        principalTable: "person_roles",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_person_role_citations_sources_source_id",
                        column: x => x.source_id,
                        principalTable: "sources",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.AddCheckConstraint(
                name: "ck_sources_source_kind",
                table: "sources",
                sql: "source_kind IN ('map', 'atlas_map', 'treaty', 'official_record', 'trial_record', 'peer_reviewed', 'official_history', 'dataset', 'encyclopedia', 'official_website')");

            migrationBuilder.CreateIndex(
                name: "ix_leader_bio_paragraph_citations_paragraph_id",
                table: "leader_bio_paragraph_citations",
                column: "paragraph_id");

            migrationBuilder.CreateIndex(
                name: "ix_leader_bio_paragraph_citations_source_id",
                table: "leader_bio_paragraph_citations",
                column: "source_id");

            migrationBuilder.CreateIndex(
                name: "ix_leader_bio_paragraphs_bio_id_ord",
                table: "leader_bio_paragraphs",
                columns: new[] { "bio_id", "ord" },
                unique: true,
                filter: "retracted_at IS NULL");

            migrationBuilder.CreateIndex(
                name: "ix_leader_bio_paragraphs_period",
                table: "leader_bio_paragraphs",
                column: "period")
                .Annotation("Npgsql:IndexMethod", "gist");

            migrationBuilder.CreateIndex(
                name: "ix_leader_bio_paragraphs_superseded_by",
                table: "leader_bio_paragraphs",
                column: "superseded_by",
                filter: "superseded_by IS NOT NULL");

            migrationBuilder.CreateIndex(
                name: "ix_person_position_citations_position_id",
                table: "person_position_citations",
                column: "position_id");

            migrationBuilder.CreateIndex(
                name: "ix_person_position_citations_source_id",
                table: "person_position_citations",
                column: "source_id");

            migrationBuilder.CreateIndex(
                name: "ix_person_positions_bio_id_seed_key",
                table: "person_positions",
                columns: new[] { "bio_id", "seed_key" },
                unique: true,
                filter: "retracted_at IS NULL");

            migrationBuilder.CreateIndex(
                name: "ix_person_positions_regime_id",
                table: "person_positions",
                column: "regime_id",
                filter: "regime_id IS NOT NULL");

            migrationBuilder.CreateIndex(
                name: "ix_person_positions_superseded_by",
                table: "person_positions",
                column: "superseded_by");

            migrationBuilder.CreateIndex(
                name: "ix_person_role_citations_role_id",
                table: "person_role_citations",
                column: "role_id");

            migrationBuilder.CreateIndex(
                name: "ix_person_role_citations_source_id",
                table: "person_role_citations",
                column: "source_id");

            migrationBuilder.CreateIndex(
                name: "ix_person_roles_bio_id_seed_key",
                table: "person_roles",
                columns: new[] { "bio_id", "seed_key" },
                unique: true,
                filter: "retracted_at IS NULL");

            migrationBuilder.CreateIndex(
                name: "ix_person_roles_regime_id",
                table: "person_roles",
                column: "regime_id",
                filter: "regime_id IS NOT NULL");

            migrationBuilder.CreateIndex(
                name: "ix_person_roles_superseded_by",
                table: "person_roles",
                column: "superseded_by");

            migrationBuilder.Sql("""
                CREATE OR REPLACE FUNCTION fn_leader_bio_paragraphs_guard()
                RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    IF TG_OP IN ('DELETE', 'TRUNCATE') THEN
                        RAISE EXCEPTION 'leader_bio_paragraphs I5: 不可刪除，請改用撤回';
                    END IF;
                    IF OLD.retracted_at IS NOT NULL AND NEW.retracted_at IS NULL THEN
                        RAISE EXCEPTION 'leader_bio_paragraphs I5: retracted_at 不可撤銷（id: %）', OLD.id;
                    END IF;
                    RETURN NEW;
                END;
                $$;
                CREATE TRIGGER trg_leader_bio_paragraphs_guard
                BEFORE UPDATE OR DELETE ON leader_bio_paragraphs
                FOR EACH ROW EXECUTE FUNCTION fn_leader_bio_paragraphs_guard();
                CREATE TRIGGER trg_leader_bio_paragraphs_no_truncate
                BEFORE TRUNCATE ON leader_bio_paragraphs
                FOR EACH STATEMENT EXECUTE FUNCTION fn_leader_bio_paragraphs_guard();
                """);

            migrationBuilder.Sql("""
                CREATE OR REPLACE FUNCTION fn_leader_bio_paragraph_citations_guard()
                RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    IF TG_OP IN ('DELETE', 'TRUNCATE') THEN
                        RAISE EXCEPTION 'leader_bio_paragraph_citations I5: 不可刪除，請改用撤回';
                    END IF;
                    IF OLD.retracted_at IS NOT NULL AND NEW.retracted_at IS NULL THEN
                        RAISE EXCEPTION 'leader_bio_paragraph_citations I5: retracted_at 不可撤銷（id: %）', OLD.id;
                    END IF;
                    RETURN NEW;
                END;
                $$;
                CREATE TRIGGER trg_leader_bio_paragraph_citations_guard
                BEFORE UPDATE OR DELETE ON leader_bio_paragraph_citations
                FOR EACH ROW EXECUTE FUNCTION fn_leader_bio_paragraph_citations_guard();
                CREATE TRIGGER trg_leader_bio_paragraph_citations_no_truncate
                BEFORE TRUNCATE ON leader_bio_paragraph_citations
                FOR EACH STATEMENT EXECUTE FUNCTION fn_leader_bio_paragraph_citations_guard();
                """);

            migrationBuilder.Sql("""
                CREATE OR REPLACE FUNCTION fn_person_positions_guard()
                RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    IF TG_OP IN ('DELETE', 'TRUNCATE') THEN
                        RAISE EXCEPTION 'person_positions I5: 不可刪除，請改用撤回';
                    END IF;
                    IF OLD.retracted_at IS NOT NULL AND NEW.retracted_at IS NULL THEN
                        RAISE EXCEPTION 'person_positions I5: retracted_at 不可撤銷（id: %）', OLD.id;
                    END IF;
                    RETURN NEW;
                END;
                $$;
                CREATE TRIGGER trg_person_positions_guard
                BEFORE UPDATE OR DELETE ON person_positions
                FOR EACH ROW EXECUTE FUNCTION fn_person_positions_guard();
                CREATE TRIGGER trg_person_positions_no_truncate
                BEFORE TRUNCATE ON person_positions
                FOR EACH STATEMENT EXECUTE FUNCTION fn_person_positions_guard();
                """);

            migrationBuilder.Sql("""
                CREATE OR REPLACE FUNCTION fn_person_position_citations_guard()
                RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    IF TG_OP IN ('DELETE', 'TRUNCATE') THEN
                        RAISE EXCEPTION 'person_position_citations I5: 不可刪除，請改用撤回';
                    END IF;
                    IF OLD.retracted_at IS NOT NULL AND NEW.retracted_at IS NULL THEN
                        RAISE EXCEPTION 'person_position_citations I5: retracted_at 不可撤銷（id: %）', OLD.id;
                    END IF;
                    RETURN NEW;
                END;
                $$;
                CREATE TRIGGER trg_person_position_citations_guard
                BEFORE UPDATE OR DELETE ON person_position_citations
                FOR EACH ROW EXECUTE FUNCTION fn_person_position_citations_guard();
                CREATE TRIGGER trg_person_position_citations_no_truncate
                BEFORE TRUNCATE ON person_position_citations
                FOR EACH STATEMENT EXECUTE FUNCTION fn_person_position_citations_guard();
                """);

            migrationBuilder.Sql("""
                CREATE OR REPLACE FUNCTION fn_person_roles_guard()
                RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    IF TG_OP IN ('DELETE', 'TRUNCATE') THEN
                        RAISE EXCEPTION 'person_roles I5: 不可刪除，請改用撤回';
                    END IF;
                    IF OLD.retracted_at IS NOT NULL AND NEW.retracted_at IS NULL THEN
                        RAISE EXCEPTION 'person_roles I5: retracted_at 不可撤銷（id: %）', OLD.id;
                    END IF;
                    RETURN NEW;
                END;
                $$;
                CREATE TRIGGER trg_person_roles_guard
                BEFORE UPDATE OR DELETE ON person_roles
                FOR EACH ROW EXECUTE FUNCTION fn_person_roles_guard();
                CREATE TRIGGER trg_person_roles_no_truncate
                BEFORE TRUNCATE ON person_roles
                FOR EACH STATEMENT EXECUTE FUNCTION fn_person_roles_guard();
                """);

            migrationBuilder.Sql("""
                CREATE OR REPLACE FUNCTION fn_person_role_citations_guard()
                RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    IF TG_OP IN ('DELETE', 'TRUNCATE') THEN
                        RAISE EXCEPTION 'person_role_citations I5: 不可刪除，請改用撤回';
                    END IF;
                    IF OLD.retracted_at IS NOT NULL AND NEW.retracted_at IS NULL THEN
                        RAISE EXCEPTION 'person_role_citations I5: retracted_at 不可撤銷（id: %）', OLD.id;
                    END IF;
                    RETURN NEW;
                END;
                $$;
                CREATE TRIGGER trg_person_role_citations_guard
                BEFORE UPDATE OR DELETE ON person_role_citations
                FOR EACH ROW EXECUTE FUNCTION fn_person_role_citations_guard();
                CREATE TRIGGER trg_person_role_citations_no_truncate
                BEFORE TRUNCATE ON person_role_citations
                FOR EACH STATEMENT EXECUTE FUNCTION fn_person_role_citations_guard();
                """);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql("DROP TRIGGER IF EXISTS trg_leader_bio_paragraphs_no_truncate ON leader_bio_paragraphs; DROP TRIGGER IF EXISTS trg_leader_bio_paragraphs_guard ON leader_bio_paragraphs; DROP FUNCTION IF EXISTS fn_leader_bio_paragraphs_guard(); DROP TRIGGER IF EXISTS trg_leader_bio_paragraph_citations_no_truncate ON leader_bio_paragraph_citations; DROP TRIGGER IF EXISTS trg_leader_bio_paragraph_citations_guard ON leader_bio_paragraph_citations; DROP FUNCTION IF EXISTS fn_leader_bio_paragraph_citations_guard(); DROP TRIGGER IF EXISTS trg_person_positions_no_truncate ON person_positions; DROP TRIGGER IF EXISTS trg_person_positions_guard ON person_positions; DROP FUNCTION IF EXISTS fn_person_positions_guard(); DROP TRIGGER IF EXISTS trg_person_position_citations_no_truncate ON person_position_citations; DROP TRIGGER IF EXISTS trg_person_position_citations_guard ON person_position_citations; DROP FUNCTION IF EXISTS fn_person_position_citations_guard(); DROP TRIGGER IF EXISTS trg_person_roles_no_truncate ON person_roles; DROP TRIGGER IF EXISTS trg_person_roles_guard ON person_roles; DROP FUNCTION IF EXISTS fn_person_roles_guard(); DROP TRIGGER IF EXISTS trg_person_role_citations_no_truncate ON person_role_citations; DROP TRIGGER IF EXISTS trg_person_role_citations_guard ON person_role_citations; DROP FUNCTION IF EXISTS fn_person_role_citations_guard();");
            migrationBuilder.DropTable(
                name: "leader_bio_paragraph_citations");

            migrationBuilder.DropTable(
                name: "person_position_citations");

            migrationBuilder.DropTable(
                name: "person_role_citations");

            migrationBuilder.DropTable(
                name: "leader_bio_paragraphs");

            migrationBuilder.DropTable(
                name: "person_positions");

            migrationBuilder.DropTable(
                name: "person_roles");

            migrationBuilder.DropCheckConstraint(
                name: "ck_sources_source_kind",
                table: "sources");

            migrationBuilder.AddCheckConstraint(
                name: "ck_sources_source_kind",
                table: "sources",
                sql: "source_kind IN ('map', 'atlas_map', 'treaty', 'official_record', 'trial_record', 'peer_reviewed', 'official_history', 'dataset')");
        }
    }
}
