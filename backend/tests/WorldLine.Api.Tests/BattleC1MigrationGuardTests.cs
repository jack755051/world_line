using Npgsql;

namespace WorldLine.Api.Tests;

/// <summary>
/// 戰役 C1 migration 在真實 PostGIS 上的驗證（ARCHITECTURE §19.1、I5）。
/// 跑在 PostGisFixture 的一次性 Testcontainers 容器（啟動時套用全部 migration，測試結束自動移除；不碰任何既有資料庫）。
/// Tai 2026-11-11 13:47 核准以暫時測試容器跑完整測試。
/// </summary>
[Collection(PostGisCollection.Name)]
public sealed class BattleC1MigrationGuardTests(PostGisFixture fx)
{
    private static readonly string[] Tables =
    [
        "battle_profiles", "battle_phases", "battle_map_features", "battle_units",
        "battle_profile_citations", "battle_phase_citations", "battle_map_feature_citations", "battle_unit_citations",
    ];

    private async Task<NpgsqlConnection> OpenAsync()
    {
        var c = new NpgsqlConnection(fx.ConnectionString);
        await c.OpenAsync();
        return c;
    }

    private static async Task<object?> ScalarAsync(NpgsqlConnection c, string sql)
    {
        await using var cmd = new NpgsqlCommand(sql, c);
        return await cmd.ExecuteScalarAsync();
    }

    private static async Task<Guid> PhaseAsync(NpgsqlConnection c)
    {
        var ev = (Guid)(await ScalarAsync(c,
            "INSERT INTO historical_events (event_kind, occurred, date_precision) VALUES ('battle', '[1940-05-26,1940-06-05)', 'day') RETURNING id"))!;
        // battle_phases.event_id 參照 battle_profiles（1:1 子表），先建 profile。
        await ScalarAsync(c, $"""
            INSERT INTO battle_profiles (event_id, slug, name, objective, objective_kind, control_change)
            VALUES ('{ev}', 'guard-test-{ev:N}', '{"{"}"zh-Hant":"測試"{"}"}', '{"{"}"zh-Hant":"測試"{"}"}', 'place', '{"{"}"zh-Hant":"測試"{"}"}')
            """);
        return (Guid)(await ScalarAsync(c, $"""
            INSERT INTO battle_phases (event_id, seq, name, period, start_precision, end_precision)
            VALUES ('{ev}', 1, '{"{"}"zh-Hant":"測試階段"{"}"}', '[1940-05-26,1940-05-28)', 'day', 'day') RETURNING id
            """))!;
    }

    [Fact]
    public async Task BattleC1_migration_is_applied_with_all_tables_and_guard_triggers()
    {
        await using var c = await OpenAsync();
        Assert.Equal(1L, await ScalarAsync(c,
            "SELECT count(*) FROM __ef_migrations_history h WHERE h::text LIKE '%20261111053803_BattleC1%'"));
        foreach (var t in Tables)
        {
            Assert.Equal(1L, await ScalarAsync(c, $"SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name = '{t}'"));
            Assert.Equal(1L, await ScalarAsync(c, $"SELECT count(*) FROM pg_trigger WHERE tgname = 'trg_{t}_guard' AND NOT tgisinternal AND tgenabled <> 'D'"));
        }
    }

    [Fact]
    public async Task Delete_on_battle_phases_is_blocked_by_I5_trigger()
    {
        await using var c = await OpenAsync();
        var phase = await PhaseAsync(c);
        var ex = await Assert.ThrowsAsync<PostgresException>(() => ScalarAsync(c, $"DELETE FROM battle_phases WHERE id = '{phase}'"));
        Assert.Contains("I5", ex.MessageText);
        Assert.Equal(1L, await ScalarAsync(c, $"SELECT count(*) FROM battle_phases WHERE id = '{phase}'"));
    }

    [Fact]
    public async Task Retraction_cannot_be_undone()
    {
        await using var c = await OpenAsync();
        var phase = await PhaseAsync(c);
        await ScalarAsync(c, $"UPDATE battle_phases SET retracted_at = now(), retraction_reason = 'test' WHERE id = '{phase}'");
        var ex = await Assert.ThrowsAsync<PostgresException>(() =>
            ScalarAsync(c, $"UPDATE battle_phases SET retracted_at = NULL, retraction_reason = NULL WHERE id = '{phase}'"));
        Assert.Contains("I5", ex.MessageText);
    }
}
