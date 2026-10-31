using Microsoft.EntityFrameworkCore;

namespace WorldLine.Api.Infrastructure;

public static class DbSetup
{
    public const string ConnectionStringName = "WorldLine";

    public static void Configure(DbContextOptionsBuilder options, string connectionString) =>
        options
            .UseNpgsql(WithJitOff(connectionString), npgsql =>
            {
                npgsql.UseNetTopologySuite();
                npgsql.MigrationsHistoryTable("__ef_migrations_history");
            })
            .UseSnakeCaseNamingConvention();

    /// <summary>
    /// 關掉 PostgreSQL JIT（連線層 <c>-c jit=off</c>）。衝突端點的弧線查詢有上百個子計畫，
    /// JIT 編譯就要 8～9 秒，實際執行只要約 0.3 秒；這個資料量的查詢都不需要 JIT。
    /// 連線字串已自行指定 Options 時保留原值，只在沒有 jit 設定時補上。
    /// </summary>
    public static string WithJitOff(string connectionString)
    {
        var b = new Npgsql.NpgsqlConnectionStringBuilder(connectionString);
        if (b.Options is null || !b.Options.Contains("jit", StringComparison.OrdinalIgnoreCase))
            b.Options = string.IsNullOrWhiteSpace(b.Options) ? "-c jit=off" : b.Options + " -c jit=off";
        return b.ConnectionString;
    }
}
