using Microsoft.EntityFrameworkCore;
using Npgsql;
using WorldLine.Api.Data;
using WorldLine.Api.Seed;

namespace WorldLine.Api.Tests;

/// <summary>
/// 專用測試資料庫的準備（整個測試行程只做一次）：
/// 1. 確認 WORLDLINE_TEST_DB 的資料庫名稱含 "test"（防呆：絕不對 appdb 寫入測試資料）；
/// 2. 不存在就 CREATE DATABASE（連到同主機的 postgres 維護庫）；不會 DROP 任何東西；
/// 3. 套用所有 EF migration；4. 跑示範 seed（可重複執行，只補缺的）。
/// </summary>
public static class TestDatabase
{
    private static readonly Lazy<Task> Ready = new(InitializeAsync);

    public static async Task EnsureReadyAsync()
    {
        Assert.SkipWhen(string.IsNullOrWhiteSpace(TestDb.ConnectionString), $"未設定 {TestDb.EnvVar}，略過資料庫整合測試");
        await Ready.Value;
    }

    public static WorldLineDbContext CreateContext()
    {
        var options = new DbContextOptionsBuilder<WorldLineDbContext>();
        DbSetup.Configure(options, TestDb.ConnectionString!);
        return new WorldLineDbContext(options.Options);
    }

    private static async Task InitializeAsync()
    {
        var builder = new NpgsqlConnectionStringBuilder(TestDb.ConnectionString);
        var database = builder.Database ?? "";
        if (!database.Contains("test", StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException(
                $"{TestDb.EnvVar} 必須指向專用測試資料庫（名稱需含 test），目前是「{database}」。I5 禁止刪除，測試資料無法清除。");

        var admin = new NpgsqlConnectionStringBuilder(builder.ConnectionString) { Database = "postgres", Pooling = false };
        await using (var conn = new NpgsqlConnection(admin.ConnectionString))
        {
            await conn.OpenAsync();
            await using var exists = new NpgsqlCommand("SELECT 1 FROM pg_database WHERE datname = @n", conn);
            exists.Parameters.AddWithValue("n", database);
            if (await exists.ExecuteScalarAsync() is null)
            {
                await using var create = new NpgsqlCommand($"CREATE DATABASE \"{database.Replace("\"", "\"\"")}\"", conn);
                await create.ExecuteNonQueryAsync();
            }
        }

        await using var ctx = CreateContext();
        await ctx.Database.MigrateAsync();
        await DemoSeeder.RunAsync(ctx);
        NpgsqlConnection.ClearAllPools(); // migration 新增了型別（postgis 等），讓後續連線重新載入型別對應
    }
}
