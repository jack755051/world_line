using Microsoft.EntityFrameworkCore.Design;

namespace WorldLine.Api.Infrastructure;

/// <summary>
/// 供 <c>dotnet ef migrations add</c> 使用。產生 migration 不需要連線；
/// 套用時用 <c>WORLDLINE_DESIGN_CONNECTION</c>（未設定則用不存在的本機 DB，避免誤連到舊環境的 appdb）。
/// </summary>
public sealed class DesignTimeDbContextFactory : IDesignTimeDbContextFactory<WorldLineDbContext>
{
    public WorldLineDbContext CreateDbContext(string[] args)
    {
        var cs = Environment.GetEnvironmentVariable("WORLDLINE_DESIGN_CONNECTION")
                 ?? "Host=127.0.0.1;Port=5433;Database=appdb_ww2_design;Username=unused;Password=unused";
        var builder = new Microsoft.EntityFrameworkCore.DbContextOptionsBuilder<WorldLineDbContext>();
        DbSetup.Configure(builder, cs);
        return new WorldLineDbContext(builder.Options);
    }
}
