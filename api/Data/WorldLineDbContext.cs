using Microsoft.EntityFrameworkCore;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Data;

public class WorldLineDbContext(DbContextOptions<WorldLineDbContext> options) : DbContext(options)
{
    public DbSet<Regime> Regimes => Set<Regime>();
    public DbSet<RegimeAlias> RegimeAliases => Set<RegimeAlias>();
    public DbSet<RegimeTerritory> RegimeTerritories => Set<RegimeTerritory>();
    public DbSet<ReignEra> ReignEras => Set<ReignEra>();
    public DbSet<PlaceName> PlaceNames => Set<PlaceName>();

    public DbSet<LineagePreset> LineagePresets => Set<LineagePreset>();
    public DbSet<LineagePresetMember> LineagePresetMembers => Set<LineagePresetMember>();
    public DbSet<RegimeRelation> RegimeRelations => Set<RegimeRelation>();
    public DbSet<RegimeTransitionEvent> RegimeTransitionEvents => Set<RegimeTransitionEvent>();

    public DbSet<HistoricalEvent> HistoricalEvents => Set<HistoricalEvent>();
    public DbSet<EventTag> EventTags => Set<EventTag>();
    public DbSet<HistoricalEventTagMap> HistoricalEventTagMaps => Set<HistoricalEventTagMap>();
    public DbSet<ObserverCategory> ObserverCategories => Set<ObserverCategory>();
    public DbSet<HistoricalEventPerspective> HistoricalEventPerspectives => Set<HistoricalEventPerspective>();
    public DbSet<HistoricalEventControversy> HistoricalEventControversies => Set<HistoricalEventControversy>();

    // 憲法 R4：中英雙語內容支援（task 2.16，2026-08-29 從通用表改回型別化表，換取真外鍵/
    // 級聯刪除——見 PRD §6「多語言內容設計」修訂記錄）。
    public DbSet<RegimeTranslation> RegimeTranslations => Set<RegimeTranslation>();
    public DbSet<RegimeAliasTranslation> RegimeAliasTranslations => Set<RegimeAliasTranslation>();
    public DbSet<HistoricalEventTranslation> HistoricalEventTranslations => Set<HistoricalEventTranslation>();
    public DbSet<LineagePresetTranslation> LineagePresetTranslations => Set<LineagePresetTranslation>();
    public DbSet<HistoricalEventControversyTranslation> HistoricalEventControversyTranslations => Set<HistoricalEventControversyTranslation>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        // Required so a GiST index can cover a plain (non-range/geometry) column like regime_id
        // alongside an int4range column — see RegimeTerritoryConfiguration's composite GiST index
        // (PRD §5: "int4range 時間區間索引（GiST 複合索引）").
        modelBuilder.HasPostgresExtension("btree_gist");

        modelBuilder.ApplyConfigurationsFromAssembly(typeof(WorldLineDbContext).Assembly);
    }
}
