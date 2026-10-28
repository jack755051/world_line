using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using WorldLine.Api.Domain;

namespace WorldLine.Api.Infrastructure;

/// <summary>PRD §6.3 M0 最小 schema。DB 層約束照 PRD；I5 trigger 在獨立 migration（手寫 SQL）。</summary>
public sealed class WorldLineDbContext(DbContextOptions<WorldLineDbContext> options) : DbContext(options)
{
    public DbSet<Source> Sources => Set<Source>();
    public DbSet<Regime> Regimes => Set<Regime>();
    public DbSet<RegimeName> RegimeNames => Set<RegimeName>();
    public DbSet<Theater> Theaters => Set<Theater>();
    public DbSet<ControlSnapshot> ControlSnapshots => Set<ControlSnapshot>();
    public DbSet<ControlRecord> ControlRecords => Set<ControlRecord>();
    public DbSet<ControlRecordVersion> ControlRecordVersions => Set<ControlRecordVersion>();
    public DbSet<ControlRecordCitation> ControlRecordCitations => Set<ControlRecordCitation>();
    public DbSet<ReferenceLand> ReferenceLand => Set<ReferenceLand>();
    public DbSet<RegimeRelation> RegimeRelations => Set<RegimeRelation>();
    public DbSet<HistoricalEvent> HistoricalEvents => Set<HistoricalEvent>();

    private static string InList(string column, IEnumerable<string> values) =>
        $"{column} IN ({string.Join(", ", values.Select(v => $"'{v}'"))})";

    private static void Timestamps<T>(EntityTypeBuilder<T> e, bool updated) where T : class
    {
        e.Property<DateTimeOffset>("CreatedAt").HasDefaultValueSql("now()");
        if (updated) e.Property<DateTimeOffset>("UpdatedAt").HasDefaultValueSql("now()");
    }

    protected override void OnModelCreating(ModelBuilder b)
    {
        b.HasPostgresExtension("postgis");
        b.HasPostgresExtension("btree_gist");

        b.Entity<Source>(e =>
        {
            e.ToTable("sources", t =>
            {
                t.HasCheckConstraint("ck_sources_source_kind", InList("source_kind", SourceKinds.All));
                t.HasCheckConstraint("ck_sources_publisher_not_blank", "btrim(publisher) <> ''");
            });
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.SourceKind).HasMaxLength(32);
            e.Property(x => x.LicenseCode).HasMaxLength(32);
            e.Property(x => x.Version).HasDefaultValue(0).IsConcurrencyToken();
            Timestamps(e, updated: true);
        });

        b.Entity<Regime>(e =>
        {
            e.ToTable("regimes");
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.Slug).HasMaxLength(80);
            e.HasIndex(x => x.Slug).IsUnique();
            e.Property(x => x.WikidataQid).HasMaxLength(20);
            e.Property(x => x.Version).HasDefaultValue(0).IsConcurrencyToken();
            e.HasMany(x => x.Names).WithOne().HasForeignKey(n => n.RegimeId).OnDelete(DeleteBehavior.Restrict);
            Timestamps(e, updated: true);
        });

        b.Entity<RegimeName>(e =>
        {
            e.ToTable("regime_names", t =>
            {
                t.HasCheckConstraint("ck_regime_names_name_kind", InList("name_kind", NameKinds.All));
                // AI 提案（PRD §6.3）：代稱必須標視角
                t.HasCheckConstraint("ck_regime_names_exonym_observer", "name_kind = 'self' OR observer_regime_id IS NOT NULL");
                t.HasCheckConstraint("ck_regime_names_display_object", "jsonb_typeof(display) = 'object'");
            });
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.NameKind).HasMaxLength(8);
            e.Property(x => x.OriginalLang).HasMaxLength(16);
            e.Property(x => x.Display).HasColumnType("jsonb");
            e.Property(x => x.ValidPeriod).HasColumnType("daterange");
            e.Property(x => x.IsPrimary).HasDefaultValue(false);
            e.Property(x => x.Version).HasDefaultValue(0);
            e.HasOne<Regime>().WithMany().HasForeignKey(x => x.ObserverRegimeId).OnDelete(DeleteBehavior.Restrict);
            Timestamps(e, updated: false);
        });

        b.Entity<Theater>(e =>
        {
            e.ToTable("theaters");
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.Code).HasMaxLength(40);
            e.HasIndex(x => x.Code).IsUnique();
            e.Property(x => x.Name).HasColumnType("jsonb");
            e.Property(x => x.Extent).HasColumnType("geometry(MultiPolygon,4326)");
            Timestamps(e, updated: false);
        });

        b.Entity<ControlSnapshot>(e =>
        {
            e.ToTable("control_snapshots", t =>
            {
                t.HasCheckConstraint("ck_control_snapshots_attestation", InList("attestation", Attestations.All));
                t.HasCheckConstraint("ck_control_snapshots_interval_period", "(attestation = 'interval') = (attested_period IS NOT NULL)");
            });
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.AsOfNote).HasColumnType("jsonb");
            e.Property(x => x.Title).HasColumnType("jsonb");
            e.Property(x => x.Attestation).HasMaxLength(8).HasDefaultValue(Attestations.Point);
            e.Property(x => x.AttestedPeriod).HasColumnType("daterange");
            e.HasIndex(x => new { x.TheaterId, x.AsOf }).IsUnique();
            e.HasOne<Theater>().WithMany().HasForeignKey(x => x.TheaterId).OnDelete(DeleteBehavior.Restrict);
            Timestamps(e, updated: false);
        });

        b.Entity<ControlRecord>(e =>
        {
            e.ToTable("control_records");
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.HasOne<Regime>().WithMany().HasForeignKey(x => x.ControllerRegimeId).OnDelete(DeleteBehavior.Restrict);
            e.HasMany(x => x.Versions).WithOne().HasForeignKey(v => v.ControlRecordId).OnDelete(DeleteBehavior.Restrict);
            Timestamps(e, updated: false);
        });

        b.Entity<ControlRecordVersion>(e =>
        {
            e.ToTable("control_record_versions", t =>
            {
                t.HasCheckConstraint("ck_crv_control_type", InList("control_type", ControlTypes.All));
                // I1：疆域資料兩端必須有界
                t.HasCheckConstraint("ck_crv_valid_period_bounded", "NOT lower_inf(valid_period) AND NOT upper_inf(valid_period)");
                t.HasCheckConstraint("ck_crv_geom_valid", "ST_IsValid(geom)");
            });
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.ControlType).HasMaxLength(24);
            e.Property(x => x.ValidPeriod).HasColumnType("daterange");
            e.Property(x => x.StartUncertainty).HasColumnType("daterange");
            e.Property(x => x.EndUncertainty).HasColumnType("daterange");
            e.Property(x => x.Geom).HasColumnType("geometry(MultiPolygon,4326)");
            e.Property(x => x.IsDisputed).HasDefaultValue(false);
            e.Property(x => x.IsRetraction).HasDefaultValue(false);
            e.HasOne<ControlSnapshot>().WithMany().HasForeignKey(x => x.SnapshotId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne<Regime>().WithMany().HasForeignKey(x => x.PatronRegimeId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne<ControlRecordVersion>().WithMany().HasForeignKey(x => x.SupersededBy).OnDelete(DeleteBehavior.Restrict);
            e.HasMany(x => x.Citations).WithOne().HasForeignKey(c => c.ControlRecordVersionId).OnDelete(DeleteBehavior.Restrict);
            e.HasIndex(x => x.ValidPeriod).HasMethod("gist").HasFilter("superseded_by IS NULL").HasDatabaseName("ix_crv_current_period");
            e.HasIndex(x => x.Geom).HasMethod("gist").HasFilter("superseded_by IS NULL").HasDatabaseName("ix_crv_current_geom");
            Timestamps(e, updated: false);
        });

        b.Entity<ControlRecordCitation>(e =>
        {
            e.ToTable("control_record_citations", t =>
                t.HasCheckConstraint("ck_crc_role", InList("role", CitationRoles.All)));
            e.HasKey(x => new { x.ControlRecordVersionId, x.SourceId, x.Locator });
            e.Property(x => x.Role).HasMaxLength(24).HasDefaultValue(CitationRoles.Primary);
            e.HasOne<Source>().WithMany().HasForeignKey(x => x.SourceId).OnDelete(DeleteBehavior.Restrict);
        });

        b.Entity<ReferenceLand>(e =>
        {
            e.ToTable("reference_land");
            e.Property(x => x.Geom).HasColumnType("geometry(MultiPolygon,4326)");
            e.HasIndex(x => x.Geom).HasMethod("gist").HasDatabaseName("ix_reference_land_geom");
            e.HasOne<Source>().WithMany().HasForeignKey(x => x.SourceId).OnDelete(DeleteBehavior.Restrict);
        });

        b.Entity<RegimeRelation>(e =>
        {
            e.ToTable("regime_relations", t =>
            {
                t.HasCheckConstraint("ck_regime_relations_type", InList("relation_type", RelationTypes.All));
                t.HasCheckConstraint("ck_regime_relations_distinct", "regime_a_id <> regime_b_id");
                t.HasCheckConstraint("ck_regime_relations_start_bounded", "NOT lower_inf(valid_period)");
                t.HasCheckConstraint("ck_regime_relations_note_object", "note IS NULL OR jsonb_typeof(note) = 'object'");
            });
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.RelationType).HasMaxLength(24);
            e.Property(x => x.ValidPeriod).HasColumnType("daterange");
            e.Property(x => x.StartUncertainty).HasColumnType("daterange");
            e.Property(x => x.EndUncertainty).HasColumnType("daterange");
            e.Property(x => x.Note).HasColumnType("jsonb");
            e.Property(x => x.Version).HasDefaultValue(0);
            e.HasOne<Regime>().WithMany().HasForeignKey(x => x.RegimeAId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne<Regime>().WithMany().HasForeignKey(x => x.RegimeBId).OnDelete(DeleteBehavior.Restrict);
            e.HasIndex(x => x.ValidPeriod).HasMethod("gist").HasDatabaseName("ix_regime_relations_period");
            Timestamps(e, updated: false);
        });

        b.Entity<HistoricalEvent>(e =>
        {
            e.ToTable("historical_events", t =>
            {
                t.HasCheckConstraint("ck_historical_events_kind", InList("event_kind", EventKinds.All));
                t.HasCheckConstraint("ck_historical_events_precision", InList("date_precision", DatePrecisions.All));
                t.HasCheckConstraint("ck_historical_events_occurred_bounded", "NOT lower_inf(occurred) AND NOT upper_inf(occurred)");
                t.HasCheckConstraint("ck_historical_events_time_note_object", "time_note IS NULL OR jsonb_typeof(time_note) = 'object'");
            });
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.EventKind).HasMaxLength(16);
            e.Property(x => x.Summary).HasColumnType("jsonb");
            e.Property(x => x.Occurred).HasColumnType("daterange");
            e.Property(x => x.DatePrecision).HasMaxLength(8);
            e.Property(x => x.TimeNote).HasColumnType("jsonb");
            e.Property(x => x.Location).HasColumnType("geometry(Geometry,4326)");
            e.Property(x => x.Version).HasDefaultValue(0).IsConcurrencyToken();
            e.HasOne<HistoricalEvent>().WithMany().HasForeignKey(x => x.ParentEventId).OnDelete(DeleteBehavior.Restrict);
            e.HasIndex(x => x.Occurred).HasMethod("gist").HasDatabaseName("ix_events_occurred");
            Timestamps(e, updated: true);
        });
    }
}
