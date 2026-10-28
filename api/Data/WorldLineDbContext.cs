using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.ChangeTracking;
using WorldLine.Api.Domain;

namespace WorldLine.Api.Data;

/// <summary>
/// World Line 資料庫（PostgreSQL + PostGIS）。資料表與欄位一律 snake_case。
/// 憲法 I1–I4 盡量在 DB 層以 NOT NULL / CHECK / FK / UNIQUE / EXCLUDE 落實；
/// I5（修正保留原版本）由 superseded_by 版本鏈 + 觸發器（禁止刪除、限制更新、寫入 data_revisions）落實，
/// 見 Migrations/*_IntegrityAndHistory.cs。
/// </summary>
public class WorldLineDbContext(DbContextOptions<WorldLineDbContext> options) : DbContext(options)
{
    public DbSet<Regime> Regimes => Set<Regime>();
    public DbSet<RegimeAlias> RegimeAliases => Set<RegimeAlias>();
    public DbSet<RegimeTerritory> RegimeTerritories => Set<RegimeTerritory>();
    public DbSet<LineagePreset> LineagePresets => Set<LineagePreset>();
    public DbSet<LineagePresetMember> LineagePresetMembers => Set<LineagePresetMember>();
    public DbSet<RegimeRelation> RegimeRelations => Set<RegimeRelation>();
    public DbSet<HistoricalEvent> HistoricalEvents => Set<HistoricalEvent>();
    public DbSet<EventTag> EventTags => Set<EventTag>();
    public DbSet<HistoricalEventTagMap> HistoricalEventTagMaps => Set<HistoricalEventTagMap>();
    public DbSet<ObserverCategory> ObserverCategories => Set<ObserverCategory>();
    public DbSet<HistoricalEventPerspective> HistoricalEventPerspectives => Set<HistoricalEventPerspective>();
    public DbSet<HistoricalEventControversy> HistoricalEventControversies => Set<HistoricalEventControversy>();
    public DbSet<PlaceName> PlaceNames => Set<PlaceName>();
    public DbSet<ReignEra> ReignEras => Set<ReignEra>();
    public DbSet<RegimeControlRelation> RegimeControlRelations => Set<RegimeControlRelation>();
    public DbSet<Alliance> Alliances => Set<Alliance>();
    public DbSet<AllianceAlias> AllianceAliases => Set<AllianceAlias>();
    public DbSet<AllianceMembership> AllianceMemberships => Set<AllianceMembership>();

    /// <summary>
    /// 本次 SaveChanges 的修改原因（I5）。修改「有修訂紀錄的表」時必填，
    /// SaveChanges 會在同一交易內 `set_config('world_line.change_reason', ..., true)` 交給 DB 觸發器寫入 data_revisions。
    /// </summary>
    public string? ChangeReason { get; set; }

    /// <summary>DB 觸發器會要求修改原因的實體（對應 data_revisions 的表）。</summary>
    private static readonly HashSet<Type> RevisionedTypes =
    [
        typeof(Regime), typeof(RegimeAlias), typeof(RegimeRelation), typeof(HistoricalEvent),
        typeof(HistoricalEventPerspective), typeof(HistoricalEventControversy), typeof(PlaceName), typeof(ReignEra),
        typeof(RegimeControlRelation), typeof(Alliance), typeof(AllianceAlias), typeof(AllianceMembership),
    ];

    public override int SaveChanges(bool acceptAllChangesOnSuccess) =>
        SaveChangesAsync(acceptAllChangesOnSuccess).GetAwaiter().GetResult();

    public override async Task<int> SaveChangesAsync(bool acceptAllChangesOnSuccess, CancellationToken cancellationToken = default)
    {
        ChangeTracker.DetectChanges();
        var modified = ChangeTracker.Entries().Where(e => e.State == EntityState.Modified).ToList();

        foreach (var entry in modified)
        {
            BumpVersion(entry);
            if (entry.Entity is HistoricalEvent ev) ev.UpdatedAt = DateTimeOffset.UtcNow;
            if (entry.Entity is Alliance al) al.UpdatedAt = DateTimeOffset.UtcNow;
        }

        var needsReason = modified.Any(e => RevisionedTypes.Contains(e.Entity.GetType()));
        if (needsReason && string.IsNullOrWhiteSpace(ChangeReason))
        {
            throw new MissingChangeReasonException();
        }

        if (string.IsNullOrWhiteSpace(ChangeReason))
        {
            return await base.SaveChangesAsync(acceptAllChangesOnSuccess, cancellationToken);
        }

        // 修改原因用交易層級設定（SET LOCAL 語意），所以必須在交易內；外部已開交易就沿用
        var ownTransaction = Database.CurrentTransaction is null
            ? await Database.BeginTransactionAsync(cancellationToken)
            : null;
        try
        {
            await Database.ExecuteSqlInterpolatedAsync(
                $"SELECT set_config('world_line.change_reason', {ChangeReason}, true)", cancellationToken);
            var result = await base.SaveChangesAsync(acceptAllChangesOnSuccess, cancellationToken);
            if (ownTransaction is not null) await ownTransaction.CommitAsync(cancellationToken);
            return result;
        }
        finally
        {
            if (ownTransaction is not null) await ownTransaction.DisposeAsync();
        }
    }

    /// <summary>樂觀併發：Version 原值作為 WHERE 條件，新值 = 原值 + 1。</summary>
    private static void BumpVersion(EntityEntry entry)
    {
        var prop = entry.Metadata.FindProperty("Version");
        if (prop is null || prop.ClrType != typeof(int)) return;
        var p = entry.Property("Version");
        if (p.IsModified) return; // 呼叫端自行指定時不覆蓋
        p.CurrentValue = (int)p.OriginalValue! + 1;
    }

    /// <summary>
    /// I7：日期區間的精度檢查式。精度欄位必須是 year/month/day，且日期必須與精度對齊
    /// （year：起日 1/1、迄日 12/31；month：起日 1 號、迄日月底）。無終點時迄日精度必須為 null。
    /// wl_date_aligned() 定義於 migration M25Ww2DatesAndControl。
    /// </summary>
    internal static string PrecisionCheck(string period, string fromPrecision, string toPrecision, bool allowOpenEnd) =>
        $"{InList(fromPrecision, DatePrecision.All)} AND wl_date_aligned(lower({period}), {fromPrecision})"
        + (allowOpenEnd
            ? $" AND ((upper_inf({period}) AND {toPrecision} IS NULL) OR (NOT upper_inf({period}) AND {InList(toPrecision, DatePrecision.All)} AND wl_date_aligned(upper({period}), {toPrecision})))"
            : $" AND {InList(toPrecision, DatePrecision.All)} AND wl_date_aligned(upper({period}), {toPrecision})");

    private static string NullablePrecisionCheck(string period, string fromPrecision, string toPrecision) =>
        $"({period} IS NULL AND {fromPrecision} IS NULL AND {toPrecision} IS NULL) OR ({period} IS NOT NULL AND {PrecisionCheck(period, fromPrecision, toPrecision, false)})";

    /// <summary>日期區間的 DB 檢查式：非空、上下界皆有限（I1：不允許無時間區間或開放式區間）。</summary>
    private static string BoundedPeriod(string column) =>
        $"NOT isempty({column}) AND NOT lower_inf({column}) AND NOT upper_inf({column})";

    private static string InList(string column, IEnumerable<string> values) =>
        $"{column} IN ({string.Join(", ", values.Select(v => $"'{v}'"))})";

    protected override void OnModelCreating(ModelBuilder b)
    {
        b.HasPostgresExtension("postgis");
        b.HasPostgresExtension("btree_gist"); // I3 exclusion constraint 需要 uuid 的 = 運算子 GiST 支援

        b.Entity<Regime>(e =>
        {
            e.ToTable("regimes", t =>
            {
                t.HasCheckConstraint("ck_regimes_self_name_not_blank", "btrim(self_name) <> ''"); // I2
                t.HasCheckConstraint("ck_regimes_status", InList("status", RegimeStatus.All));
                t.HasCheckConstraint("ck_regimes_origin_transition_type",
                    $"origin_transition_type IS NULL OR {InList("origin_transition_type", [OriginTransitionType.Split, OriginTransitionType.Abdication])}");
                // 前身與產生方式必須同時有值（分裂/禪讓而來）或同時為 null（獨立建國）
                t.HasCheckConstraint("ck_regimes_predecessor_pair",
                    "(predecessor_regime_id IS NULL) = (origin_transition_type IS NULL)");
                // 被滅亡 ⇔ 有消滅方（憲法 §4 傳承關係鏈）
                t.HasCheckConstraint("ck_regimes_destroyed_by_iff_destroyed",
                    "(status = 'destroyed') = (destroyed_by_regime_id IS NOT NULL)");
                t.HasCheckConstraint("ck_regimes_not_own_predecessor", "predecessor_regime_id <> id");
                t.HasCheckConstraint("ck_regimes_not_destroyed_by_self", "destroyed_by_regime_id <> id");
                // 被併吞 ⇔ 有併吞方（憲法 §4 2026-10-28）
                t.HasCheckConstraint("ck_regimes_annexed_by_iff_annexed",
                    "(status = 'annexed') = (annexed_by_regime_id IS NOT NULL)");
                t.HasCheckConstraint("ck_regimes_not_annexed_by_self", "annexed_by_regime_id <> id");
                t.HasCheckConstraint("ck_regimes_existence_precision",
                    PrecisionCheck("existence_period", "existence_from_precision", "existence_to_precision", allowOpenEnd: true)); // I7
                // 存續區間：非空、有起點；只有仍存續（existing）可無終點
                t.HasCheckConstraint("ck_regimes_existence_period",
                    "NOT isempty(existence_period) AND NOT lower_inf(existence_period) AND (NOT upper_inf(existence_period) OR status = 'existing')");
            });
            e.HasKey(x => x.Id);
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.SelfName).HasMaxLength(128).IsRequired();
            e.Property(x => x.ExistencePeriod).HasColumnType("daterange").IsRequired();
            e.Property(x => x.ExistenceFromPrecision).HasMaxLength(8).IsRequired();
            e.Property(x => x.ExistenceToPrecision).HasMaxLength(8);
            e.HasIndex(x => x.ExistencePeriod).HasMethod("gist");
            e.Property(x => x.Status).HasMaxLength(32).IsRequired().HasDefaultValue(RegimeStatus.Existing);
            e.Property(x => x.OriginTransitionType).HasMaxLength(16);
            e.Property(x => x.CreatedAt).HasDefaultValueSql("now()");
            e.Property(x => x.UpdatedAt).HasDefaultValueSql("now()");
            e.Property(x => x.Version).HasDefaultValue(0).IsConcurrencyToken();
            e.HasOne(x => x.PredecessorRegime).WithMany().HasForeignKey(x => x.PredecessorRegimeId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne(x => x.DestroyedByRegime).WithMany().HasForeignKey(x => x.DestroyedByRegimeId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne(x => x.AnnexedByRegime).WithMany().HasForeignKey(x => x.AnnexedByRegimeId).OnDelete(DeleteBehavior.Restrict);
            e.HasIndex(x => x.SelfName);
        });

        b.Entity<RegimeAlias>(e =>
        {
            e.ToTable("regime_aliases", t =>
            {
                t.HasCheckConstraint("ck_regime_aliases_name_not_blank", "btrim(alias_name) <> ''");
                t.HasCheckConstraint("ck_regime_aliases_alias_type",
                    InList("alias_type", [AliasPerspective.Contemporary, AliasPerspective.Historiographic]));
                t.HasCheckConstraint("ck_regime_aliases_observer_not_self", "observer_regime_id <> regime_id");
            });
            e.HasKey(x => x.Id);
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.AliasName).HasMaxLength(128).IsRequired();
            e.Property(x => x.AliasType).HasMaxLength(32).IsRequired();
            e.Property(x => x.CreatedAt).HasDefaultValueSql("now()");
            // I4：代稱一定要追溯回存在的自稱本體（NOT NULL + FK，且本體不可被刪除）
            e.HasOne(x => x.Regime).WithMany(r => r.Aliases).HasForeignKey(x => x.RegimeId).IsRequired().OnDelete(DeleteBehavior.Restrict);
            e.HasOne(x => x.ObserverRegime).WithMany().HasForeignKey(x => x.ObserverRegimeId).OnDelete(DeleteBehavior.Restrict);
            e.HasIndex(x => new { x.RegimeId, x.ObserverRegimeId, x.AliasName }).IsUnique().AreNullsDistinct(false);
            e.HasIndex(x => x.AliasName);
        });

        b.Entity<RegimeTerritory>(e =>
        {
            e.ToTable("regime_territories", t =>
            {
                t.HasCheckConstraint("ck_regime_territories_valid_period_bounded", BoundedPeriod("valid_period")); // I1
                t.HasCheckConstraint("ck_regime_territories_precision",
                    PrecisionCheck("valid_period", "valid_from_precision", "valid_to_precision", allowOpenEnd: false)); // I7
                t.HasCheckConstraint("ck_regime_territories_geom_valid", "ST_IsValid(geom)");
                // I5：被取代的版本一定有修正時間與修正原因；現行版本則兩者皆無
                t.HasCheckConstraint("ck_regime_territories_correction_pair",
                    "(superseded_by IS NULL) = (corrected_at IS NULL)");
                t.HasCheckConstraint("ck_regime_territories_correction_reason",
                    "superseded_by IS NULL OR (correction_reason IS NOT NULL AND btrim(correction_reason) <> '')");
                t.HasCheckConstraint("ck_regime_territories_not_self_superseded", "superseded_by <> id");
            });
            e.HasKey(x => x.Id);
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.ValidPeriod).HasColumnType("daterange").IsRequired();
            e.Property(x => x.ValidFromPrecision).HasMaxLength(8).IsRequired();
            e.Property(x => x.ValidToPrecision).HasMaxLength(8).IsRequired();
            e.Property(x => x.Geom).HasColumnType("geometry(MultiPolygon,4326)").IsRequired();
            e.Property(x => x.IsDisputed).HasDefaultValue(false);
            e.Property(x => x.IsIllustrative).HasDefaultValue(false);
            e.Property(x => x.CreatedAt).HasDefaultValueSql("now()");
            e.Property(x => x.Version).HasDefaultValue(0).IsConcurrencyToken();
            e.HasOne(x => x.Regime).WithMany(r => r.Territories).HasForeignKey(x => x.RegimeId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne(x => x.SupersededByTerritory).WithOne().HasForeignKey<RegimeTerritory>(x => x.SupersededBy).OnDelete(DeleteBehavior.Restrict);
            // 版本鏈是線性的：每個新版本最多取代一個舊版本（UNIQUE，null 不計）
            e.HasIndex(x => x.SupersededBy).IsUnique();
            e.HasIndex(x => x.ValidPeriod).HasMethod("gist");
            e.HasIndex(x => x.Geom).HasMethod("gist");
        });

        b.Entity<LineagePreset>(e =>
        {
            e.ToTable("lineage_presets", t =>
                t.HasCheckConstraint("ck_lineage_presets_name_not_blank", "btrim(preset_name) <> ''"));
            e.HasKey(x => x.Id);
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.PresetName).HasMaxLength(128).IsRequired();
            e.Property(x => x.IsDefault).HasDefaultValue(false);
            e.Property(x => x.CreatedAt).HasDefaultValueSql("now()");
            e.HasIndex(x => x.PresetName).IsUnique();
            // 預設史觀主線全表最多一筆
            e.HasIndex(x => x.IsDefault).IsUnique().HasFilter("is_default").HasDatabaseName("ux_lineage_presets_single_default");
        });

        b.Entity<LineagePresetMember>(e =>
        {
            e.ToTable("lineage_preset_members", t =>
                t.HasCheckConstraint("ck_lineage_preset_members_sort_order", "sort_order >= 0"));
            e.HasKey(x => new { x.PresetId, x.RegimeId });
            e.HasOne(x => x.Preset).WithMany(p => p.Members).HasForeignKey(x => x.PresetId).OnDelete(DeleteBehavior.Cascade);
            e.HasOne(x => x.Regime).WithMany().HasForeignKey(x => x.RegimeId).OnDelete(DeleteBehavior.Restrict);
            e.HasIndex(x => new { x.PresetId, x.SortOrder }).IsUnique();
        });

        b.Entity<RegimeRelation>(e =>
        {
            e.ToTable("regime_relations", t =>
            {
                t.HasCheckConstraint("ck_regime_relations_distinct_regimes", "regime_a_id <> regime_b_id");
                t.HasCheckConstraint("ck_regime_relations_type", InList("relation_type",
                    [RelationType.Trade, RelationType.Tributary, RelationType.MarriageAlliance,
                     RelationType.Alliance, RelationType.Hostility, RelationType.Other]));
                t.HasCheckConstraint("ck_regime_relations_valid_period_bounded", BoundedPeriod("valid_period"));
                t.HasCheckConstraint("ck_regime_relations_precision",
                    PrecisionCheck("valid_period", "valid_from_precision", "valid_to_precision", allowOpenEnd: false)); // I7
                t.HasCheckConstraint("ck_regime_relations_route_valid", "route IS NULL OR ST_IsValid(route)");
            });
            e.HasKey(x => x.Id);
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.RelationType).HasMaxLength(32).IsRequired();
            e.Property(x => x.ValidPeriod).HasColumnType("daterange").IsRequired();
            e.Property(x => x.ValidFromPrecision).HasMaxLength(8).IsRequired();
            e.Property(x => x.ValidToPrecision).HasMaxLength(8).IsRequired();
            e.Property(x => x.Route).HasColumnType("geometry(MultiLineString,4326)");
            e.Property(x => x.CreatedAt).HasDefaultValueSql("now()");
            e.HasOne(x => x.RegimeA).WithMany().HasForeignKey(x => x.RegimeAId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne(x => x.RegimeB).WithMany().HasForeignKey(x => x.RegimeBId).OnDelete(DeleteBehavior.Restrict);
            e.HasIndex(x => x.ValidPeriod).HasMethod("gist");
            e.HasIndex(x => new { x.RegimeAId, x.RegimeBId });
            e.HasIndex(x => x.RegimeBId);
        });

        b.Entity<HistoricalEvent>(e =>
        {
            e.ToTable("historical_events", t =>
            {
                t.HasCheckConstraint("ck_historical_events_id_slug", "id ~ '^[a-z0-9][a-z0-9-]*$'");
                t.HasCheckConstraint("ck_historical_events_name_not_blank", "btrim(name) <> ''");
                t.HasCheckConstraint("ck_historical_events_decimal_order", "start_decimal <= end_decimal");
                t.HasCheckConstraint("ck_historical_events_not_own_parent", "parent_event_id <> id");
                t.HasCheckConstraint("ck_historical_events_time_zone", "time_zone IS NULL OR btrim(time_zone) <> ''");
                t.HasCheckConstraint("ck_historical_events_sections_object", "sections IS NULL OR jsonb_typeof(sections) = 'object'");
                t.HasCheckConstraint("ck_historical_events_geoms_valid",
                    "(origin_point IS NULL OR ST_IsValid(origin_point)) AND (influence_area IS NULL OR ST_IsValid(influence_area)) AND (routes IS NULL OR ST_IsValid(routes))");
            });
            e.HasKey(x => x.Id);
            e.Property(x => x.Id).HasMaxLength(64);
            e.Property(x => x.Name).HasMaxLength(100).IsRequired();
            e.Property(x => x.ParentEventId).HasMaxLength(64);
            e.Property(x => x.StartEdtf).HasMaxLength(32).IsRequired();
            e.Property(x => x.EndEdtf).HasMaxLength(32).IsRequired();
            e.Property(x => x.StartDecimal).HasPrecision(8, 3);
            e.Property(x => x.EndDecimal).HasPrecision(8, 3);
            e.Property(x => x.TimeZone).HasMaxLength(64);
            e.Property(x => x.OriginPoint).HasColumnType("geometry(Point,4326)");
            e.Property(x => x.InfluenceArea).HasColumnType("geometry(MultiPolygon,4326)");
            e.Property(x => x.Routes).HasColumnType("geometry(MultiLineString,4326)");
            e.Property(x => x.Sections).HasColumnType("jsonb");
            e.Property(x => x.CreatedAt).HasDefaultValueSql("now()");
            e.Property(x => x.UpdatedAt).HasDefaultValueSql("now()");
            e.Property(x => x.Version).HasDefaultValue(0).IsConcurrencyToken();
            e.HasOne(x => x.ParentEvent).WithMany().HasForeignKey(x => x.ParentEventId).OnDelete(DeleteBehavior.Restrict);
            e.HasIndex(x => new { x.StartDecimal, x.EndDecimal });
            e.HasIndex(x => x.OriginPoint).HasMethod("gist");
        });

        b.Entity<EventTag>(e =>
        {
            e.ToTable("event_tags", t => t.HasCheckConstraint("ck_event_tags_name", "tag_name ~ '^[a-z][a-z0-9_]*$'"));
            e.HasKey(x => x.Id);
            e.Property(x => x.TagName).HasMaxLength(32).IsRequired();
            e.HasIndex(x => x.TagName).IsUnique();
        });

        b.Entity<HistoricalEventTagMap>(e =>
        {
            e.ToTable("historical_event_tag_map");
            e.HasKey(x => new { x.EventId, x.TagId });
            e.HasOne(x => x.Event).WithMany(ev => ev.Tags).HasForeignKey(x => x.EventId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne(x => x.Tag).WithMany().HasForeignKey(x => x.TagId).OnDelete(DeleteBehavior.Restrict);
        });

        b.Entity<ObserverCategory>(e =>
        {
            e.ToTable("observer_categories", t => t.HasCheckConstraint("ck_observer_categories_name_not_blank", "btrim(category_name) <> ''"));
            e.HasKey(x => x.Id);
            e.Property(x => x.CategoryName).HasMaxLength(64).IsRequired();
            e.HasIndex(x => x.CategoryName).IsUnique();
        });

        b.Entity<HistoricalEventPerspective>(e =>
        {
            e.ToTable("historical_event_perspectives", t =>
            {
                // 觀察者恰好擇一：當事政權，或受控的非政權觀察者類別（不允許自由文字）
                t.HasCheckConstraint("ck_perspectives_exactly_one_observer", "num_nonnulls(regime_id, observer_category_id) = 1");
                t.HasCheckConstraint("ck_perspectives_text_not_blank", "btrim(local_name) <> '' AND btrim(narrative_summary) <> ''");
                t.HasCheckConstraint("ck_perspectives_sources_array", "primary_sources IS NULL OR jsonb_typeof(primary_sources) = 'array'");
            });
            e.HasKey(x => x.Id);
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.EventId).HasMaxLength(64).IsRequired();
            e.Property(x => x.LocalName).HasMaxLength(128).IsRequired();
            e.Property(x => x.NarrativeSummary).IsRequired();
            e.Property(x => x.PrimarySources).HasColumnType("jsonb");
            e.Property(x => x.ClaimedCasualties).HasColumnType("jsonb");
            e.Property(x => x.CreatedAt).HasDefaultValueSql("now()");
            e.HasOne(x => x.Event).WithMany(ev => ev.Perspectives).HasForeignKey(x => x.EventId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne(x => x.Regime).WithMany().HasForeignKey(x => x.RegimeId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne(x => x.ObserverCategory).WithMany().HasForeignKey(x => x.ObserverCategoryId).OnDelete(DeleteBehavior.Restrict);
        });

        b.Entity<HistoricalEventControversy>(e =>
        {
            e.ToTable("historical_event_controversies", t =>
            {
                t.HasCheckConstraint("ck_controversies_text_not_blank", "btrim(topic) <> '' AND btrim(neutral_description) <> ''");
                t.HasCheckConstraint("ck_controversies_viewpoints_array", "viewpoints IS NULL OR jsonb_typeof(viewpoints) = 'array'");
            });
            e.HasKey(x => x.Id);
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.EventId).HasMaxLength(64).IsRequired();
            e.Property(x => x.Topic).HasMaxLength(128).IsRequired();
            e.Property(x => x.NeutralDescription).IsRequired();
            e.Property(x => x.Viewpoints).HasColumnType("jsonb");
            e.Property(x => x.CreatedAt).HasDefaultValueSql("now()");
            e.HasOne(x => x.Event).WithMany(ev => ev.Controversies).HasForeignKey(x => x.EventId).OnDelete(DeleteBehavior.Restrict);
        });

        b.Entity<PlaceName>(e =>
        {
            e.ToTable("place_names", t =>
            {
                t.HasCheckConstraint("ck_place_names_name_not_blank", "btrim(historical_name) <> ''");
                t.HasCheckConstraint("ck_place_names_valid_period_bounded",
                    "valid_period IS NULL OR (" + BoundedPeriod("valid_period") + ")");
                t.HasCheckConstraint("ck_place_names_precision",
                    NullablePrecisionCheck("valid_period", "valid_from_precision", "valid_to_precision")); // I7
            });
            e.HasKey(x => x.Id);
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.HistoricalName).HasMaxLength(128).IsRequired();
            e.Property(x => x.ModernName).HasMaxLength(128);
            e.Property(x => x.ValidPeriod).HasColumnType("daterange");
            e.Property(x => x.ValidFromPrecision).HasMaxLength(8);
            e.Property(x => x.ValidToPrecision).HasMaxLength(8);
            e.Property(x => x.Geom).HasColumnType("geometry(Point,4326)");
            e.Property(x => x.CreatedAt).HasDefaultValueSql("now()");
            e.HasIndex(x => x.ValidPeriod).HasMethod("gist");
            e.HasIndex(x => x.Geom).HasMethod("gist");
        });

        b.Entity<ReignEra>(e =>
        {
            e.ToTable("reign_eras", t =>
            {
                t.HasCheckConstraint("ck_reign_eras_name_not_blank", "btrim(era_name) <> ''");
                t.HasCheckConstraint("ck_reign_eras_date_order", "end_date IS NULL OR start_date <= end_date");
                t.HasCheckConstraint("ck_reign_eras_precision",
                    $"{InList("start_precision", DatePrecision.All)} AND wl_date_aligned(start_date, start_precision) AND " +
                    $"((end_date IS NULL AND end_precision IS NULL) OR (end_date IS NOT NULL AND {InList("end_precision", DatePrecision.All)} AND wl_date_aligned(end_date + 1, end_precision)))"); // I7
            });
            e.HasKey(x => x.Id);
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.EraName).HasMaxLength(32).IsRequired();
            e.Property(x => x.MonarchName).HasMaxLength(64);
            e.Property(x => x.StartPrecision).HasMaxLength(8).IsRequired();
            e.Property(x => x.EndPrecision).HasMaxLength(8);
            e.Property(x => x.CreatedAt).HasDefaultValueSql("now()");
            e.HasOne(x => x.Regime).WithMany(r => r.ReignEras).HasForeignKey(x => x.RegimeId).OnDelete(DeleteBehavior.Restrict);
            e.HasIndex(x => new { x.RegimeId, x.EraName, x.StartDate }).IsUnique();
            e.HasIndex(x => new { x.StartDate, x.EndDate });
        });

        // ---- 二戰階段（2026-10-28）：控制關係、同盟陣營 ----

        b.Entity<RegimeControlRelation>(e =>
        {
            e.ToTable("regime_control_relations", t =>
            {
                t.HasCheckConstraint("ck_regime_control_relations_distinct", "controller_regime_id <> controlled_regime_id"); // I6
                t.HasCheckConstraint("ck_regime_control_relations_type", InList("control_type", ControlType.All));
                t.HasCheckConstraint("ck_regime_control_relations_valid_period_bounded", BoundedPeriod("valid_period")); // I6
                t.HasCheckConstraint("ck_regime_control_relations_precision",
                    PrecisionCheck("valid_period", "valid_from_precision", "valid_to_precision", allowOpenEnd: false)); // I7
                t.HasCheckConstraint("ck_regime_control_relations_area_valid", "area IS NULL OR ST_IsValid(area)");
            });
            e.HasKey(x => x.Id);
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.ControlType).HasMaxLength(16).IsRequired();
            e.Property(x => x.ValidPeriod).HasColumnType("daterange").IsRequired();
            e.Property(x => x.ValidFromPrecision).HasMaxLength(8).IsRequired();
            e.Property(x => x.ValidToPrecision).HasMaxLength(8).IsRequired();
            e.Property(x => x.Area).HasColumnType("geometry(MultiPolygon,4326)");
            e.Property(x => x.IsIllustrative).HasDefaultValue(false);
            e.Property(x => x.IsDisputed).HasDefaultValue(false);
            e.Property(x => x.CreatedAt).HasDefaultValueSql("now()");
            e.Property(x => x.Version).HasDefaultValue(0).IsConcurrencyToken();
            // I6：兩方都必須是存在的政權本體（NOT NULL + FK，本體不可刪除）
            e.HasOne(x => x.ControllerRegime).WithMany().HasForeignKey(x => x.ControllerRegimeId).IsRequired().OnDelete(DeleteBehavior.Restrict);
            e.HasOne(x => x.ControlledRegime).WithMany().HasForeignKey(x => x.ControlledRegimeId).IsRequired().OnDelete(DeleteBehavior.Restrict);
            e.HasIndex(x => x.ValidPeriod).HasMethod("gist");
            e.HasIndex(x => x.Area).HasMethod("gist");
            e.HasIndex(x => x.ControlledRegimeId);
            e.HasIndex(x => x.ControllerRegimeId);
        });

        b.Entity<Alliance>(e =>
        {
            e.ToTable("alliances", t =>
            {
                t.HasCheckConstraint("ck_alliances_self_name_not_blank", "btrim(self_name) <> ''");
                t.HasCheckConstraint("ck_alliances_existence_period",
                    "NOT isempty(existence_period) AND NOT lower_inf(existence_period)");
                t.HasCheckConstraint("ck_alliances_existence_precision",
                    PrecisionCheck("existence_period", "existence_from_precision", "existence_to_precision", allowOpenEnd: true)); // I7
            });
            e.HasKey(x => x.Id);
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.SelfName).HasMaxLength(128).IsRequired();
            e.Property(x => x.ExistencePeriod).HasColumnType("daterange").IsRequired();
            e.Property(x => x.ExistenceFromPrecision).HasMaxLength(8).IsRequired();
            e.Property(x => x.ExistenceToPrecision).HasMaxLength(8);
            e.Property(x => x.CreatedAt).HasDefaultValueSql("now()");
            e.Property(x => x.UpdatedAt).HasDefaultValueSql("now()");
            e.Property(x => x.Version).HasDefaultValue(0).IsConcurrencyToken();
            e.HasIndex(x => x.SelfName).IsUnique();
            e.HasIndex(x => x.ExistencePeriod).HasMethod("gist");
        });

        b.Entity<AllianceAlias>(e =>
        {
            e.ToTable("alliance_aliases", t =>
            {
                t.HasCheckConstraint("ck_alliance_aliases_name_not_blank", "btrim(alias_name) <> ''");
                t.HasCheckConstraint("ck_alliance_aliases_alias_type",
                    InList("alias_type", [AliasPerspective.Contemporary, AliasPerspective.Historiographic]));
            });
            e.HasKey(x => x.Id);
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.AliasName).HasMaxLength(128).IsRequired();
            e.Property(x => x.AliasType).HasMaxLength(32).IsRequired();
            e.Property(x => x.CreatedAt).HasDefaultValueSql("now()");
            e.HasOne(x => x.Alliance).WithMany(a => a.Aliases).HasForeignKey(x => x.AllianceId).IsRequired().OnDelete(DeleteBehavior.Restrict);
            e.HasOne(x => x.ObserverRegime).WithMany().HasForeignKey(x => x.ObserverRegimeId).OnDelete(DeleteBehavior.Restrict);
            e.HasIndex(x => new { x.AllianceId, x.ObserverRegimeId, x.AliasName }).IsUnique().AreNullsDistinct(false);
        });

        b.Entity<AllianceMembership>(e =>
        {
            e.ToTable("alliance_memberships", t =>
            {
                t.HasCheckConstraint("ck_alliance_memberships_role", InList("role", MembershipRole.All));
                t.HasCheckConstraint("ck_alliance_memberships_valid_period",
                    "NOT isempty(valid_period) AND NOT lower_inf(valid_period)");
                t.HasCheckConstraint("ck_alliance_memberships_precision",
                    PrecisionCheck("valid_period", "valid_from_precision", "valid_to_precision", allowOpenEnd: true)); // I7
            });
            e.HasKey(x => x.Id);
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.Role).HasMaxLength(16).IsRequired().HasDefaultValue(MembershipRole.Member);
            e.Property(x => x.ValidPeriod).HasColumnType("daterange").IsRequired();
            e.Property(x => x.ValidFromPrecision).HasMaxLength(8).IsRequired();
            e.Property(x => x.ValidToPrecision).HasMaxLength(8);
            e.Property(x => x.CreatedAt).HasDefaultValueSql("now()");
            e.Property(x => x.Version).HasDefaultValue(0).IsConcurrencyToken();
            e.HasOne(x => x.Alliance).WithMany(a => a.Memberships).HasForeignKey(x => x.AllianceId).IsRequired().OnDelete(DeleteBehavior.Restrict);
            e.HasOne(x => x.Regime).WithMany().HasForeignKey(x => x.RegimeId).IsRequired().OnDelete(DeleteBehavior.Restrict);
            e.HasIndex(x => x.ValidPeriod).HasMethod("gist");
            e.HasIndex(x => new { x.AllianceId, x.RegimeId });
        });
    }
}

/// <summary>修改有修訂紀錄的資料時未提供原因（I5）。API 層轉成 400 ProblemDetails。</summary>
public sealed class MissingChangeReasonException()
    : InvalidOperationException("I5：修改既有史料必須提供修改原因（changeReason）");
