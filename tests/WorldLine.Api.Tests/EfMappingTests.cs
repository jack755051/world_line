using Microsoft.EntityFrameworkCore;
using NetTopologySuite.Geometries;
using NpgsqlTypes;
using WorldLine.Api.Data;
using WorldLine.Api.Domain;

namespace WorldLine.Api.Tests;

/// <summary>EF Core + Npgsql + NetTopologySuite 對應可正常寫入／查詢（交易內執行後回滾）。</summary>
public class EfMappingTests
{
    [Fact]
    public async Task Can_save_and_query_regime_territory_by_date()
    {
        await TestDatabase.EnsureReadyAsync();
        var options = new DbContextOptionsBuilder<WorldLineDbContext>();
        DbSetup.Configure(options, TestDb.ConnectionString!);
        await using var ctx = new WorldLineDbContext(options.Options);
        await using var tx = await ctx.Database.BeginTransactionAsync();

        var gf = new GeometryFactory(new PrecisionModel(), 4326);
        var square = gf.CreateMultiPolygon([gf.CreatePolygon([
            new(100, 30), new(110, 30), new(110, 40), new(100, 40), new(100, 30)])]);

        var period = new NpgsqlRange<DateOnly>(new DateOnly(618, 1, 1), true, new DateOnly(907, 12, 31), true);
        var tang = new Regime
        {
            SelfName = "唐", ExistencePeriod = period,
            ExistenceFromPrecision = DatePrecision.Year, ExistenceToPrecision = DatePrecision.Year,
        };
        tang.Territories.Add(new RegimeTerritory
        {
            ValidPeriod = period, ValidFromPrecision = DatePrecision.Year, ValidToPrecision = DatePrecision.Year, Geom = square,
        });
        ctx.Regimes.Add(tang);
        await ctx.SaveChangesAsync();

        var found = await ctx.RegimeTerritories
            .Where(t => t.SupersededBy == null && t.ValidPeriod.Contains(new DateOnly(700, 6, 1)))
            .Select(t => new { t.Regime.SelfName, t.Geom })
            .ToListAsync();

        Assert.Contains(found, f => f.SelfName == "唐" && f.Geom.Area > 0);
        await tx.RollbackAsync();
    }
}
