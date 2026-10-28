using Microsoft.EntityFrameworkCore;
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

    /// <summary>年份區間的 DB 檢查式：非空、上下界皆有限（I1：不允許無時間區間或開放式區間）。</summary>
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
            });
            e.HasKey(x => x.Id);
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.SelfName).HasMaxLength(128).IsRequired();
            e.Property(x => x.Status).HasMaxLength(32).IsRequired().HasDefaultValue(RegimeStatus.Existing);
            e.Property(x => x.OriginTransitionType).HasMaxLength(16);
            e.Property(x => x.CreatedAt).HasDefaultValueSql("now()");
            e.Property(x => x.UpdatedAt).HasDefaultValueSql("now()");
            e.Property(x => x.Version).HasDefaultValue(0).IsConcurrencyToken();
            e.HasOne(x => x.PredecessorRegime).WithMany().HasForeignKey(x => x.PredecessorRegimeId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne(x => x.DestroyedByRegime).WithMany().HasForeignKey(x => x.DestroyedByRegimeId).OnDelete(DeleteBehavior.Restrict);
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
            e.Property(x => x.ValidPeriod).HasColumnType("int4range").IsRequired();
            e.Property(x => x.Geom).HasColumnType("geometry(MultiPolygon,4326)").IsRequired();
            e.Property(x => x.IsDisputed).HasDefaultValue(false);
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
                t.HasCheckConstraint("ck_regime_relations_route_valid", "route IS NULL OR ST_IsValid(route)");
            });
            e.HasKey(x => x.Id);
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.RelationType).HasMaxLength(32).IsRequired();
            e.Property(x => x.ValidPeriod).HasColumnType("int4range").IsRequired();
            e.Property(x => x.Route).HasColumnType("geometry(MultiLineString,4326)");
            e.Property(x => x.CreatedAt).HasDefaultValueSql("now()");
            e.HasOne(x => x.RegimeA).WithMany().HasForeignKey(x => x.RegimeAId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne(x => x.RegimeB).WithMany().HasForeignKey(x => x.RegimeBId).OnDelete(DeleteBehavior.Restrict);
            e.HasIndex(x => x.ValidPeriod).HasMethod("gist");
            e.HasIndex(x => new { x.RegimeAId, x.RegimeBId });
            e.HasIndex(x => x.RegimeBId);
        });
    }
}
