using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using WorldLine.Api.Domain;

namespace WorldLine.Api.Infrastructure;

/// <summary>B3 分段生平六張表的 EF 設定（ARCHITECTURE §16.2–16.4，2026-11-11）。I5 trigger 在 migration 以 SQL 建立。</summary>
internal static class BioDetailModel
{
    private static string InList(string column, IEnumerable<string> values) =>
        $"{column} IN ({string.Join(", ", values.Select(v => $"'{v}'"))})";

    private const string Retraction = "retracted_at IS NULL OR retraction_reason IS NOT NULL";
    private const string Active = "retracted_at IS NULL";

    public static void Configure(ModelBuilder b)
    {
        b.Entity<LeaderBioParagraph>(e =>
        {
            e.ToTable("leader_bio_paragraphs", t =>
            {
                t.HasCheckConstraint("ck_leader_bio_paragraphs_ord", "ord > 0");
                t.HasCheckConstraint("ck_leader_bio_paragraphs_period", "period IS NULL OR (NOT isempty(period) AND NOT lower_inf(period))");
                t.HasCheckConstraint("ck_leader_bio_paragraphs_start_precision", "period_start_precision IS NULL OR " + InList("period_start_precision", DatePrecisions.All));
                t.HasCheckConstraint("ck_leader_bio_paragraphs_end_precision", "period_end_precision IS NULL OR " + InList("period_end_precision", DatePrecisions.All));
                t.HasCheckConstraint("ck_leader_bio_paragraphs_heading_object", "heading IS NULL OR jsonb_typeof(heading) = 'object'");
                t.HasCheckConstraint("ck_leader_bio_paragraphs_body_object", "jsonb_typeof(body) = 'object'");
                t.HasCheckConstraint("ck_leader_bio_paragraphs_retraction_reason", Retraction);
            });
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.Period).HasColumnType("daterange");
            e.Property(x => x.PeriodStartPrecision).HasMaxLength(8);
            e.Property(x => x.PeriodEndPrecision).HasMaxLength(8);
            e.Property(x => x.Heading).HasColumnType("jsonb");
            e.Property(x => x.Body).HasColumnType("jsonb");
            e.Property(x => x.RelatedRecordIds).HasColumnType("uuid[]");
            e.Property(x => x.Version).HasDefaultValue(0);
            e.HasOne<LeaderBio>().WithMany().HasForeignKey(x => x.BioId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne<LeaderBioParagraph>().WithMany().HasForeignKey(x => x.SupersededBy).OnDelete(DeleteBehavior.Restrict);
            e.HasIndex(x => new { x.BioId, x.Ord }).IsUnique().HasFilter(Active);
            e.HasIndex(x => x.SupersededBy).HasFilter("superseded_by IS NOT NULL");
            e.HasIndex(x => x.Period).HasMethod("gist");
            Created(e);
        });
        Citation<LeaderBioParagraphCitation>(b, "leader_bio_paragraph_citations", e =>
        {
            e.HasOne<LeaderBioParagraph>().WithMany().HasForeignKey(x => x.ParagraphId).OnDelete(DeleteBehavior.Restrict);
            e.HasIndex(x => x.ParagraphId);
        });

        b.Entity<PersonPosition>(e =>
        {
            e.ToTable("person_positions", t =>
            {
                t.HasCheckConstraint("ck_person_positions_seed_key_not_blank", "btrim(seed_key) <> ''");
                t.HasCheckConstraint("ck_person_positions_position_kind", InList("position_kind", PersonPositionKinds.All));
                t.HasCheckConstraint("ck_person_positions_period", "NOT isempty(period) AND NOT lower_inf(period)");
                t.HasCheckConstraint("ck_person_positions_start_precision", "start_precision IS NULL OR " + InList("start_precision", DatePrecisions.All));
                t.HasCheckConstraint("ck_person_positions_end_precision", "end_precision IS NULL OR (" + InList("end_precision", DatePrecisions.All) + " AND NOT upper_inf(period))");
                t.HasCheckConstraint("ck_person_positions_title_object", "jsonb_typeof(title) = 'object'");
                t.HasCheckConstraint("ck_person_positions_organization_object", "organization IS NULL OR jsonb_typeof(organization) = 'object'");
                t.HasCheckConstraint("ck_person_positions_retraction_reason", Retraction);
            });
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.PositionKind).HasMaxLength(32);
            e.Property(x => x.Period).HasColumnType("daterange");
            e.Property(x => x.StartPrecision).HasMaxLength(8);
            e.Property(x => x.EndPrecision).HasMaxLength(8);
            e.Property(x => x.Organization).HasColumnType("jsonb");
            e.Property(x => x.Title).HasColumnType("jsonb");
            e.Property(x => x.Version).HasDefaultValue(0);
            e.HasOne<LeaderBio>().WithMany().HasForeignKey(x => x.BioId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne<Regime>().WithMany().HasForeignKey(x => x.RegimeId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne<PersonPosition>().WithMany().HasForeignKey(x => x.SupersededBy).OnDelete(DeleteBehavior.Restrict);
            e.HasIndex(x => new { x.BioId, x.SeedKey }).IsUnique().HasFilter(Active);
            e.HasIndex(x => x.RegimeId).HasFilter("regime_id IS NOT NULL");
            Created(e);
        });
        Citation<PersonPositionCitation>(b, "person_position_citations", e =>
        {
            e.HasOne<PersonPosition>().WithMany().HasForeignKey(x => x.PositionId).OnDelete(DeleteBehavior.Restrict);
            e.HasIndex(x => x.PositionId);
        });

        b.Entity<PersonRole>(e =>
        {
            e.ToTable("person_roles", t =>
            {
                t.HasCheckConstraint("ck_person_roles_seed_key_not_blank", "btrim(seed_key) <> ''");
                t.HasCheckConstraint("ck_person_roles_role_kind", InList("role_kind", PersonRoleKinds.All));
                t.HasCheckConstraint("ck_person_roles_period", "NOT isempty(period) AND NOT lower_inf(period)");
                t.HasCheckConstraint("ck_person_roles_start_precision", "start_precision IS NULL OR " + InList("start_precision", DatePrecisions.All));
                t.HasCheckConstraint("ck_person_roles_end_precision", "end_precision IS NULL OR (" + InList("end_precision", DatePrecisions.All) + " AND NOT upper_inf(period))");
                t.HasCheckConstraint("ck_person_roles_t14_rule", "t14_rule IS NULL OR t14_rule ~ '^R[0-9]$'");
                t.HasCheckConstraint("ck_person_roles_title_object", "jsonb_typeof(title) = 'object'");
                t.HasCheckConstraint("ck_person_roles_organization_object", "organization IS NULL OR jsonb_typeof(organization) = 'object'");
                t.HasCheckConstraint("ck_person_roles_retraction_reason", Retraction);
            });
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.RoleKind).HasMaxLength(32);
            e.Property(x => x.Period).HasColumnType("daterange");
            e.Property(x => x.StartPrecision).HasMaxLength(8);
            e.Property(x => x.EndPrecision).HasMaxLength(8);
            e.Property(x => x.T14Rule).HasMaxLength(8);
            e.Property(x => x.Organization).HasColumnType("jsonb");
            e.Property(x => x.Title).HasColumnType("jsonb");
            e.Property(x => x.Acting).HasDefaultValue(false);
            e.Property(x => x.Version).HasDefaultValue(0);
            e.HasOne<LeaderBio>().WithMany().HasForeignKey(x => x.BioId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne<Regime>().WithMany().HasForeignKey(x => x.RegimeId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne<PersonRole>().WithMany().HasForeignKey(x => x.SupersededBy).OnDelete(DeleteBehavior.Restrict);
            e.HasIndex(x => new { x.BioId, x.SeedKey }).IsUnique().HasFilter(Active);
            e.HasIndex(x => x.RegimeId).HasFilter("regime_id IS NOT NULL");
            Created(e);
        });
        Citation<PersonRoleCitation>(b, "person_role_citations", e =>
        {
            e.HasOne<PersonRole>().WithMany().HasForeignKey(x => x.RoleId).OnDelete(DeleteBehavior.Restrict);
            e.HasIndex(x => x.RoleId);
        });
    }

    private static void Created<T>(EntityTypeBuilder<T> e) where T : class =>
        e.Property<DateTimeOffset>("CreatedAt").HasDefaultValueSql("now()");

    private static void Citation<T>(ModelBuilder b, string table, Action<EntityTypeBuilder<T>> extra) where T : BioDetailCitationBase
    {
        b.Entity<T>(e =>
        {
            e.ToTable(table, t =>
            {
                t.HasCheckConstraint($"ck_{table}_locator_not_blank", "btrim(locator) <> ''");
                t.HasCheckConstraint($"ck_{table}_quote_not_blank", "btrim(quote) <> ''");
                t.HasCheckConstraint($"ck_{table}_grade", "grade IS NULL OR " + InList("grade", BioSourcePolicy.AllowedGrades.Order()));
                t.HasCheckConstraint($"ck_{table}_date_precision", "date_precision IS NULL OR " + InList("date_precision", DatePrecisions.All));
                t.HasCheckConstraint($"ck_{table}_claim_span", "claim_span IS NULL OR (NOT isempty(claim_span) AND lower(claim_span) >= 0)");
                t.HasCheckConstraint($"ck_{table}_retraction_reason", Retraction);
            });
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.QuoteLang).HasMaxLength(35);
            e.Property(x => x.Grade).HasMaxLength(1);
            e.Property(x => x.DatePrecision).HasMaxLength(8);
            e.Property(x => x.ClaimSpan).HasColumnType("int4range");
            e.Property(x => x.PolicyVersion).HasMaxLength(32);
            e.HasOne<Source>().WithMany().HasForeignKey(x => x.SourceId).OnDelete(DeleteBehavior.Restrict);
            e.HasIndex(x => x.SourceId);
            extra(e);
            Created(e);
        });
    }
}
