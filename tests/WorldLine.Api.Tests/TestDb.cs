using Npgsql;

namespace WorldLine.Api.Tests;

/// <summary>
/// 整合測試用連線：讀環境變數 WORLDLINE_TEST_DB（未設定則跳過整合測試）。
/// 每個測試都在交易內執行並於結束時 ROLLBACK，不會在資料庫留下任何資料。
/// </summary>
public sealed class TestDb : IAsyncDisposable
{
    public const string EnvVar = "WORLDLINE_TEST_DB";

    public NpgsqlConnection Connection { get; }
    public NpgsqlTransaction Transaction { get; }

    private TestDb(NpgsqlConnection connection, NpgsqlTransaction transaction)
    {
        Connection = connection;
        Transaction = transaction;
    }

    public static string? ConnectionString => Environment.GetEnvironmentVariable(EnvVar);

    public static async Task<TestDb> OpenAsync()
    {
        Assert.SkipWhen(string.IsNullOrWhiteSpace(ConnectionString), $"未設定 {EnvVar}，略過資料庫整合測試");
        var conn = new NpgsqlConnection(ConnectionString);
        await conn.OpenAsync();
        var tx = await conn.BeginTransactionAsync();
        return new TestDb(conn, tx);
    }

    public async Task ExecAsync(string sql)
    {
        await using var cmd = new NpgsqlCommand(sql, Connection, Transaction);
        await cmd.ExecuteNonQueryAsync();
    }

    public async Task<T> ScalarAsync<T>(string sql)
    {
        await using var cmd = new NpgsqlCommand(sql, Connection, Transaction);
        var result = await cmd.ExecuteScalarAsync();
        return (T)result!;
    }

    /// <summary>在 savepoint 內執行，預期失敗並回傳 SQLSTATE；交易本身不中斷。</summary>
    public async Task<string> ExpectErrorAsync(string sql)
    {
        await ExecAsync("SAVEPOINT expect_error");
        try
        {
            await ExecAsync(sql);
        }
        catch (PostgresException ex)
        {
            await ExecAsync("ROLLBACK TO SAVEPOINT expect_error");
            return ex.SqlState;
        }
        await ExecAsync("RELEASE SAVEPOINT expect_error");
        Assert.Fail($"預期 SQL 會失敗，但執行成功：{sql}");
        return "";
    }

    public Task<Guid> InsertRegimeAsync(string selfName) =>
        ScalarAsync<Guid>($"INSERT INTO regimes (self_name) VALUES ('{selfName}') RETURNING id");

    public static string Square(int x) =>
        $"ST_Multi(ST_GeomFromText('POLYGON(({x} 30,{x + 10} 30,{x + 10} 40,{x} 40,{x} 30))', 4326))";

    public async ValueTask DisposeAsync()
    {
        await Transaction.RollbackAsync();
        await Connection.DisposeAsync();
    }
}

public static class SqlState
{
    public const string NotNull = "23502";
    public const string ForeignKey = "23503";
    public const string Check = "23514";
    public const string Exclusion = "23P01";
    public const string Restrict = "23001";
}
