using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;

namespace WorldLine.Api.Data;

/// <summary>
/// 給 `dotnet ef` 使用。連線字串取自環境變數 WORLDLINE_DB；未設定時只用於產生 migration（不會連線）。
/// </summary>
public class DesignTimeDbContextFactory : IDesignTimeDbContextFactory<WorldLineDbContext>
{
    public WorldLineDbContext CreateDbContext(string[] args)
    {
        var cs = Environment.GetEnvironmentVariable("WORLDLINE_DB")
                 ?? "Host=localhost;Port=5432;Database=worldline_design_time";
        var options = new DbContextOptionsBuilder<WorldLineDbContext>();
        DbSetup.Configure(options, cs);
        return new WorldLineDbContext(options.Options);
    }
}

public static class DbSetup
{
    public static void Configure(DbContextOptionsBuilder options, string connectionString) =>
        options
            .UseNpgsql(connectionString, npgsql => npgsql.UseNetTopologySuite())
            .UseSnakeCaseNamingConvention();
}
