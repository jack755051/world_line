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

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.ApplyConfigurationsFromAssembly(typeof(WorldLineDbContext).Assembly);
    }
}
