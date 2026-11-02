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
    public DbSet<RegimeAlignment> RegimeAlignments => Set<RegimeAlignment>();
    public DbSet<RegimeAlignmentCitation> RegimeAlignmentCitations => Set<RegimeAlignmentCitation>();
    public DbSet<EventParticipant> EventParticipants => Set<EventParticipant>();
    public DbSet<EventCitation> EventCitations => Set<EventCitation>();
    public DbSet<ControlCoverageNote> ControlCoverageNotes => Set<ControlCoverageNote>();
    public DbSet<SovereigntyRecord> SovereigntyRecords => Set<SovereigntyRecord>();
    public DbSet<ConflictRecord> ConflictRecords => Set<ConflictRecord>();
    public DbSet<OccupationAttribution> OccupationAttributions => Set<OccupationAttribution>();
    public DbSet<CapitalRecord> CapitalRecords => Set<CapitalRecord>();

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

        // 陣營時間切片（憲法 §6「陣營」、PRD §6.3）。EXCLUDE（同政權有效切片不重疊）在 migration 以 SQL 建立。
        b.Entity<RegimeAlignment>(e =>
        {
            e.ToTable("regime_alignments", t =>
            {
                t.HasCheckConstraint("ck_regime_alignments_camp", InList("camp", Camps.All));
                // 起點＝條約簽署／參戰日，必須有界；迄日未知可無界（同 regime_relations）
                t.HasCheckConstraint("ck_regime_alignments_start_bounded", "NOT lower_inf(valid_period) AND NOT isempty(valid_period)");
                t.HasCheckConstraint("ck_regime_alignments_note_object", "note IS NULL OR jsonb_typeof(note) = 'object'");
                t.HasCheckConstraint("ck_regime_alignments_retraction_reason", "retracted_at IS NULL OR retraction_reason IS NOT NULL");
            });
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.Camp).HasMaxLength(16);
            e.Property(x => x.ValidPeriod).HasColumnType("daterange");
            e.Property(x => x.Note).HasColumnType("jsonb");
            e.Property(x => x.Version).HasDefaultValue(0);
            e.HasOne<Regime>().WithMany().HasForeignKey(x => x.RegimeId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne<HistoricalEvent>().WithMany().HasForeignKey(x => x.BasisEventId).OnDelete(DeleteBehavior.Restrict);
            e.HasMany(x => x.Citations).WithOne().HasForeignKey(c => c.RegimeAlignmentId).OnDelete(DeleteBehavior.Restrict);
            Timestamps(e, updated: false);
        });

        b.Entity<RegimeAlignmentCitation>(e =>
        {
            e.ToTable("regime_alignment_citations", t =>
                t.HasCheckConstraint("ck_rac_role", InList("role", CitationRoles.All)));
            e.HasKey(x => new { x.RegimeAlignmentId, x.SourceId, x.Locator });
            e.Property(x => x.Role).HasMaxLength(24).HasDefaultValue(CitationRoles.Primary);
            e.HasOne<Source>().WithMany().HasForeignKey(x => x.SourceId).OnDelete(DeleteBehavior.Restrict);
        });

        // 事件參與方與引用（PRD §6.3；2026-10-31 實作，AI 提案・待拍板）。I5 trigger 在 migration 以 SQL 建立。
        b.Entity<EventParticipant>(e =>
        {
            e.ToTable("event_participants", t =>
            {
                t.HasCheckConstraint("ck_event_participants_role", InList("role", EventParticipantRoles.All));
                // 事後追加（方案 A）：追加時間與理由必須同時有或同時沒有
                t.HasCheckConstraint("ck_event_participants_addition", "(added_at IS NULL) = (addition_note IS NULL) AND (addition_note IS NULL OR jsonb_typeof(addition_note) = 'object')");
            });
            e.HasKey(x => new { x.EventId, x.RegimeId, x.Role });
            e.Property(x => x.Role).HasMaxLength(16);
            e.Property(x => x.AdditionNote).HasColumnType("jsonb");
            e.HasOne<HistoricalEvent>().WithMany().HasForeignKey(x => x.EventId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne<Regime>().WithMany().HasForeignKey(x => x.RegimeId).OnDelete(DeleteBehavior.Restrict);
        });

        b.Entity<EventCitation>(e =>
        {
            e.ToTable("event_citations");
            e.HasKey(x => new { x.EventId, x.SourceId, x.Locator });
            e.HasOne<HistoricalEvent>().WithMany().HasForeignKey(x => x.EventId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne<Source>().WithMany().HasForeignKey(x => x.SourceId).OnDelete(DeleteBehavior.Restrict);
        });

        // 涵蓋備註（PRD §6.3 control_coverage_notes、§6.4 選項 C）
        b.Entity<ControlCoverageNote>(e =>
        {
            e.ToTable("control_coverage_notes", t =>
            {
                t.HasCheckConstraint("ck_control_coverage_notes_reason", InList("reason", CoverageReasons.All));
                t.HasCheckConstraint("ck_control_coverage_notes_period_bounded", "NOT lower_inf(valid_period) AND NOT upper_inf(valid_period) AND NOT isempty(valid_period)");
                t.HasCheckConstraint("ck_control_coverage_notes_note_object", "note IS NULL OR jsonb_typeof(note) = 'object'");
                t.HasCheckConstraint("ck_control_coverage_notes_retraction_reason", "retracted_at IS NULL OR retraction_reason IS NOT NULL");
            });
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.Geom).HasColumnType("geometry(MultiPolygon,4326)");
            e.Property(x => x.ValidPeriod).HasColumnType("daterange");
            e.Property(x => x.Reason).HasMaxLength(24);
            e.Property(x => x.Note).HasColumnType("jsonb");
            e.Property(x => x.Version).HasDefaultValue(0);
            e.HasOne<Theater>().WithMany().HasForeignKey(x => x.TheaterId).OnDelete(DeleteBehavior.Restrict);
            e.HasIndex(x => x.Geom).HasMethod("gist");
            e.HasIndex(x => x.ValidPeriod).HasMethod("gist");
            Timestamps(e, updated: false);
        });
        // 主權圖層（法理國界；2026-10-31 試驗，AI 提案・待拍板）。EXCLUDE 與 I5 trigger 在 migration 以 SQL 建立。
        b.Entity<SovereigntyRecord>(e =>
        {
            e.ToTable("sovereignty_records", t =>
            {
                t.HasCheckConstraint("ck_sovereignty_records_layer_status", InList("layer_status", SovereigntyLayerStatuses.All));
                t.HasCheckConstraint("ck_sovereignty_records_geometry_license", InList("geometry_license", CitationPolicy.PrimaryLicenseAllowlist.Order()));
                t.HasCheckConstraint("ck_sovereignty_records_attribution", "geometry_license NOT IN ('cc_by', 'cc_by_sa') OR attribution IS NOT NULL");
                t.HasCheckConstraint("ck_sovereignty_records_start_bounded", "NOT lower_inf(valid_period) AND NOT isempty(valid_period)");
                t.HasCheckConstraint("ck_sovereignty_records_provenance_object", "provenance IS NULL OR jsonb_typeof(provenance) = 'object'");
                t.HasCheckConstraint("ck_sovereignty_records_note_object", "note IS NULL OR jsonb_typeof(note) = 'object'");
                t.HasCheckConstraint("ck_sovereignty_records_retraction_reason", "retracted_at IS NULL OR retraction_reason IS NOT NULL");
                t.HasCheckConstraint("ck_sovereignty_records_ohm_pinned", "ohm_relation_id IS NULL OR (ohm_version IS NOT NULL AND ohm_fetched_at IS NOT NULL)");
            });
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.Geom).HasColumnType("geometry(MultiPolygon,4326)");
            e.Property(x => x.ValidPeriod).HasColumnType("daterange");
            e.Property(x => x.LayerStatus).HasMaxLength(16);
            e.Property(x => x.GeometryLicense).HasMaxLength(16);
            e.Property(x => x.Provenance).HasColumnType("jsonb");
            e.Property(x => x.Note).HasColumnType("jsonb");
            e.Property(x => x.Version).HasDefaultValue(0);
            e.HasOne<Regime>().WithMany().HasForeignKey(x => x.RegimeId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne<HistoricalEvent>().WithMany().HasForeignKey(x => x.StartEventId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne<HistoricalEvent>().WithMany().HasForeignKey(x => x.EndEventId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne<Source>().WithMany().HasForeignKey(x => x.GeometrySourceId).OnDelete(DeleteBehavior.Restrict);
            e.HasIndex(x => x.Geom).HasMethod("gist");
            e.HasIndex(x => x.ValidPeriod).HasMethod("gist");
            Timestamps(e, updated: false);
        });
        // 衝突圖示（交叉雙劍；2026-10-31 試驗，AI 提案・待拍板）。I5 trigger 在 migration 以 SQL 建立。
        b.Entity<ConflictRecord>(e =>
        {
            e.ToTable("conflict_records", t =>
            {
                t.HasCheckConstraint("ck_conflict_records_distinct_regimes", "regime_a_id <> regime_b_id");
                t.HasCheckConstraint("ck_conflict_records_start_bounded", "NOT lower_inf(valid_period) AND NOT isempty(valid_period)");
                t.HasCheckConstraint("ck_conflict_records_location_method_not_blank", "btrim(location_method) <> ''");
                t.HasCheckConstraint("ck_conflict_records_note_object", "note IS NULL OR jsonb_typeof(note) = 'object'");
                t.HasCheckConstraint("ck_conflict_records_retraction_reason", "retracted_at IS NULL OR retraction_reason IS NOT NULL");
            });
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.Location).HasColumnType("geometry(Point,4326)");
            e.Property(x => x.ValidPeriod).HasColumnType("daterange");
            e.Property(x => x.Note).HasColumnType("jsonb");
            e.Property(x => x.Version).HasDefaultValue(0);
            e.HasOne<Regime>().WithMany().HasForeignKey(x => x.RegimeAId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne<Regime>().WithMany().HasForeignKey(x => x.RegimeBId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne<HistoricalEvent>().WithMany().HasForeignKey(x => x.StartEventId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne<HistoricalEvent>().WithMany().HasForeignKey(x => x.EndEventId).OnDelete(DeleteBehavior.Restrict);
            e.HasIndex(x => x.ValidPeriod).HasMethod("gist");
            Timestamps(e, updated: false);
        });
        // 首都紀錄（capital_records；2026-11-02 試驗，AI 提案・待拍板）。EXCLUDE 與 I5 trigger 在 migration 以 SQL 建立。
        b.Entity<CapitalRecord>(e =>
        {
            e.ToTable("capital_records", t =>
            {
                t.HasCheckConstraint("ck_capital_records_city_name_object", "jsonb_typeof(city_name) = 'object'");
                t.HasCheckConstraint("ck_capital_records_start_bounded", "NOT lower_inf(valid_period) AND NOT isempty(valid_period)");
                t.HasCheckConstraint("ck_capital_records_retraction_reason", "retracted_at IS NULL OR retraction_reason IS NOT NULL");
            });
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.CityName).HasColumnType("jsonb");
            e.Property(x => x.Location).HasColumnType("geometry(Point,4326)");
            e.Property(x => x.ValidPeriod).HasColumnType("daterange");
            e.Property(x => x.Version).HasDefaultValue(0);
            e.HasOne<Regime>().WithMany().HasForeignKey(x => x.RegimeId).OnDelete(DeleteBehavior.Restrict);
            e.HasIndex(x => x.ValidPeriod).HasMethod("gist");
            Timestamps(e, updated: false);
        });
        // 佔領歸屬（主權圖層依佔領國上色；2026-10-31 試驗，AI 提案・待拍板）。EXCLUDE 與 I5 trigger 在 migration 以 SQL 建立。
        b.Entity<OccupationAttribution>(e =>
        {
            e.ToTable("occupation_attributions", t =>
            {
                t.HasCheckConstraint("ck_occupation_attributions_distinct_regimes", "occupied_regime_id <> occupier_regime_id");
                t.HasCheckConstraint("ck_occupation_attributions_control_kind", InList("control_kind", OccupationControlKinds.All));
                t.HasCheckConstraint("ck_occupation_attributions_start_bounded", "NOT lower_inf(valid_period) AND NOT isempty(valid_period)");
                t.HasCheckConstraint("ck_occupation_attributions_note_object", "note IS NULL OR jsonb_typeof(note) = 'object'");
                t.HasCheckConstraint("ck_occupation_attributions_retraction_reason", "retracted_at IS NULL OR retraction_reason IS NOT NULL");
            });
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.ValidPeriod).HasColumnType("daterange");
            e.Property(x => x.ControlKind).HasMaxLength(24);
            e.Property(x => x.Note).HasColumnType("jsonb");
            e.Property(x => x.Version).HasDefaultValue(0);
            e.HasOne<Regime>().WithMany().HasForeignKey(x => x.OccupiedRegimeId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne<Regime>().WithMany().HasForeignKey(x => x.OccupierRegimeId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne<HistoricalEvent>().WithMany().HasForeignKey(x => x.BasisEventId).OnDelete(DeleteBehavior.Restrict);
            e.HasIndex(x => x.ValidPeriod).HasMethod("gist");
            Timestamps(e, updated: false);
        });
    }
}
