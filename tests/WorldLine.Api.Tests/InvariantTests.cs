namespace WorldLine.Api.Tests;

/// <summary>憲法 §5 不可變約束 I1–I5 與 §4 狀態機在資料庫層的落實。</summary>
public class InvariantTests
{
    [Fact]
    public async Task I2_regime_requires_non_blank_self_name()
    {
        await using var db = await TestDb.OpenAsync();
        Assert.Equal(SqlState.NotNull, await db.ExpectErrorAsync("INSERT INTO regimes (self_name, existence_period) VALUES (NULL, '[618,907]')"));
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync("INSERT INTO regimes (self_name, existence_period) VALUES ('   ', '[618,907]')"));
        Assert.NotEqual(Guid.Empty, await db.InsertRegimeAsync("唐"));
    }

    [Fact]
    public async Task I4_alias_must_point_to_existing_regime()
    {
        await using var db = await TestDb.OpenAsync();
        Assert.Equal(SqlState.ForeignKey, await db.ExpectErrorAsync(
            $"INSERT INTO regime_aliases (regime_id, alias_name, alias_type) VALUES ('{Guid.NewGuid()}', '大食', 'contemporary')"));
        Assert.Equal(SqlState.NotNull, await db.ExpectErrorAsync(
            "INSERT INTO regime_aliases (regime_id, alias_name, alias_type) VALUES (NULL, '大食', 'contemporary')"));

        var arab = await db.InsertRegimeAsync("阿拉伯帝國");
        var tang = await db.InsertRegimeAsync("唐");
        await db.ExecAsync($"INSERT INTO regime_aliases (regime_id, observer_regime_id, alias_name, alias_type) VALUES ('{arab}', '{tang}', '大食', 'contemporary')");
        Assert.Equal(SqlState.Restrict, await db.ExpectErrorAsync($"DELETE FROM regimes WHERE id = '{arab}'"));
    }

    [Fact]
    public async Task I1_territory_requires_bounded_period()
    {
        await using var db = await TestDb.OpenAsync();
        var tang = await db.InsertRegimeAsync("唐");
        Assert.Equal(SqlState.NotNull, await db.ExpectErrorAsync(
            $"INSERT INTO regime_territories (regime_id, valid_period, geom) VALUES ('{tang}', NULL, {TestDb.Square(100)})"));
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync(
            $"INSERT INTO regime_territories (regime_id, valid_period, geom) VALUES ('{tang}', 'empty', {TestDb.Square(100)})"));
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync(
            $"INSERT INTO regime_territories (regime_id, valid_period, geom) VALUES ('{tang}', '[618,)', {TestDb.Square(100)})"));
        await db.ExecAsync($"INSERT INTO regime_territories (regime_id, valid_period, geom) VALUES ('{tang}', '[618,907]', {TestDb.Square(100)})");
    }

    [Fact]
    public async Task I3_no_two_official_overlapping_territories_unless_disputed()
    {
        await using var db = await TestDb.OpenAsync();
        var tang = await db.InsertRegimeAsync("唐");
        await db.ExecAsync($"INSERT INTO regime_territories (regime_id, valid_period, geom) VALUES ('{tang}', '[618,700]', {TestDb.Square(100)})");
        // 相鄰不重疊：允許
        await db.ExecAsync($"INSERT INTO regime_territories (regime_id, valid_period, geom) VALUES ('{tang}', '[701,907]', {TestDb.Square(101)})");
        // 標記爭議並存：允許
        await db.ExecAsync($"INSERT INTO regime_territories (regime_id, valid_period, geom, is_disputed) VALUES ('{tang}', '[650,680]', {TestDb.Square(102)}, true)");
        await db.ExecAsync("SET CONSTRAINTS ex_regime_territories_official_no_overlap IMMEDIATE");
        await db.ExecAsync("SET CONSTRAINTS ex_regime_territories_official_no_overlap DEFERRED");

        // 兩筆正式版本時間重疊：拒絕（約束為 DEFERRABLE，於 IMMEDIATE 檢查時報錯）
        Assert.Equal(SqlState.Exclusion, await db.ExpectErrorAsync(
            $"INSERT INTO regime_territories (regime_id, valid_period, geom) VALUES ('{tang}', '[690,710]', {TestDb.Square(103)}); " +
            "SET CONSTRAINTS ex_regime_territories_official_no_overlap IMMEDIATE"));
    }

    [Fact]
    public async Task I5_territory_correction_keeps_original_version()
    {
        await using var db = await TestDb.OpenAsync();
        var tang = await db.InsertRegimeAsync("唐");
        var v1 = await db.ScalarAsync<Guid>($"INSERT INTO regime_territories (regime_id, valid_period, geom) VALUES ('{tang}', '[618,907]', {TestDb.Square(100)}) RETURNING id");

        // 不可覆蓋、不可刪除
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync($"UPDATE regime_territories SET geom = {TestDb.Square(105)} WHERE id = '{v1}'"));
        Assert.Equal(SqlState.Restrict, await db.ExpectErrorAsync($"DELETE FROM regime_territories WHERE id = '{v1}'"));
        // 標記被取代時必須附原因
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync(
            $"UPDATE regime_territories SET superseded_by = '{v1}', corrected_at = now() WHERE id = '{v1}'"));

        // 正確修正流程：新增新版本 → 舊版本指向新版本並附原因與時間（同一交易內，I3 延遲檢查）
        var v2 = await db.ScalarAsync<Guid>($"INSERT INTO regime_territories (regime_id, valid_period, geom) VALUES ('{tang}', '[618,907]', {TestDb.Square(105)}) RETURNING id");
        await db.ExecAsync($"UPDATE regime_territories SET superseded_by = '{v2}', correction_reason = '依新考據修正西界', corrected_at = now() WHERE id = '{v1}'");
        await db.ExecAsync("SET CONSTRAINTS ALL IMMEDIATE");

        Assert.Equal(2L, await db.ScalarAsync<long>($"SELECT count(*) FROM regime_territories WHERE regime_id = '{tang}'"));
        // 已被取代的版本不可再修改
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync(
            $"UPDATE regime_territories SET correction_reason = 'x' WHERE id = '{v1}'"));
    }

    [Fact]
    public async Task I5_regime_update_requires_reason_and_is_recorded()
    {
        await using var db = await TestDb.OpenAsync();
        var id = await db.InsertRegimeAsync("曹魏");
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync($"UPDATE regimes SET self_name = '魏' WHERE id = '{id}'"));

        await db.ExecAsync("SELECT set_config('world_line.change_reason', '改用自稱「魏」', true)");
        await db.ExecAsync($"UPDATE regimes SET self_name = '魏' WHERE id = '{id}'");
        Assert.Equal(1L, await db.ScalarAsync<long>(
            $"SELECT count(*) FROM data_revisions WHERE table_name = 'regimes' AND row_id = '{id}' AND old_row->>'self_name' = '曹魏' AND new_row->>'self_name' = '魏'"));
    }

    [Fact]
    public async Task StateMachine_destroyed_requires_destroyer_and_transitions_are_guarded()
    {
        await using var db = await TestDb.OpenAsync();
        var wei = await db.InsertRegimeAsync("魏");
        var shu = await db.InsertRegimeAsync("蜀漢");
        await db.ExecAsync("SELECT set_config('world_line.change_reason', '測試', true)");

        // 被滅亡必須記錄消滅方
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync($"UPDATE regimes SET status = 'destroyed' WHERE id = '{shu}'"));
        await db.ExecAsync($"UPDATE regimes SET status = 'destroyed', destroyed_by_regime_id = '{wei}' WHERE id = '{shu}'");
        // 終止狀態之間不可互轉（禪讓與滅亡不可合併）
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync($"UPDATE regimes SET status = 'abdicated', destroyed_by_regime_id = NULL WHERE id = '{shu}'"));
        // 前身與產生方式須成對
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync($"INSERT INTO regimes (self_name, existence_period, predecessor_regime_id) VALUES ('西晉', '[266,316]', '{wei}')"));
        await db.ExecAsync($"INSERT INTO regimes (self_name, existence_period, predecessor_regime_id, origin_transition_type) VALUES ('西晉', '[266,316]', '{wei}', 'abdication')");
    }
}
