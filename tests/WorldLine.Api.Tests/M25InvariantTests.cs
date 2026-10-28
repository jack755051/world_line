namespace WorldLine.Api.Tests;

/// <summary>
/// M2.5（憲法 2026-10-28：二戰為第一階段）在資料庫層的約束：I6 控制關係、I7 日期精度、被併吞、同盟陣營、
/// 以及年份 → 日期的遷移換算（交易內執行後回滾）。
/// </summary>
public class M25InvariantTests
{
    private const string RegimeCols = "self_name, existence_period, existence_from_precision, existence_to_precision";
    private const string ControlCols = "controller_regime_id, controlled_regime_id, control_type, valid_period, valid_from_precision, valid_to_precision";

    [Fact]
    public async Task I7_bounds_must_align_with_declared_precision()
    {
        await using var db = await TestDb.OpenAsync();
        // 只知年 → 起日必須是 1/1
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync($"INSERT INTO regimes ({RegimeCols}) VALUES ('甲', '[1868-03-01,)', 'year', NULL)"));
        await db.ExecAsync($"INSERT INTO regimes ({RegimeCols}) VALUES ('甲', '[1868-03-01,)', 'month', NULL)");
        // 迄日精度 month 要求迄日是月底（排他上界為下月 1 日）
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync($"INSERT INTO regimes ({RegimeCols}) VALUES ('乙', '[1932-03-01,1945-08-18]', 'day', 'month')"));
        await db.ExecAsync($"INSERT INTO regimes ({RegimeCols}) VALUES ('乙', '[1932-03-01,1945-08-31]', 'day', 'month')");
        await db.ExecAsync($"INSERT INTO regimes ({RegimeCols}) VALUES ('丙', '[1932-03-01,1945-08-18]', 'day', 'day')");
        // 開放終點不可宣稱終點精度；精度只接受 year/month/day
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync($"INSERT INTO regimes ({RegimeCols}) VALUES ('丁', '[1912-01-01,)', 'year', 'year')"));
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync($"INSERT INTO regimes ({RegimeCols}) VALUES ('戊', '[1912-01-01,)', 'decade', NULL)"));
        // 年號：昭和元年只有 7 天，不能宣稱只知年
        var japan = await db.InsertRegimeAsync("日本");
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync(
            $"INSERT INTO reign_eras (regime_id, era_name, start_date, start_precision, end_date, end_precision) VALUES ('{japan}', '昭和', '1926-12-25', 'year', '1989-01-07', 'day')"));
        await db.ExecAsync(
            $"INSERT INTO reign_eras (regime_id, era_name, start_date, start_precision, end_date, end_precision) VALUES ('{japan}', '昭和', '1926-12-25', 'day', '1989-01-07', 'day')");
    }

    [Fact]
    public async Task Annexed_is_a_terminal_transition_that_requires_the_annexing_regime()
    {
        await using var db = await TestDb.OpenAsync();
        var austria = await db.InsertRegimeAsync("奧地利");
        var germany = await db.InsertRegimeAsync("德意志國");
        await db.ExecAsync("SELECT set_config('world_line.change_reason', '測試', true)");

        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync($"UPDATE regimes SET status = 'annexed' WHERE id = '{austria}'"));
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync($"UPDATE regimes SET status = 'annexed', annexed_by_regime_id = '{austria}' WHERE id = '{austria}'"));
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync($"UPDATE regimes SET annexed_by_regime_id = '{germany}' WHERE id = '{austria}'"));
        await db.ExecAsync($"UPDATE regimes SET status = 'annexed', annexed_by_regime_id = '{germany}' WHERE id = '{austria}'");
        // 被併吞 ≠ 被滅亡：終止狀態之間不可互轉
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync(
            $"UPDATE regimes SET status = 'destroyed', annexed_by_regime_id = NULL, destroyed_by_regime_id = '{germany}' WHERE id = '{austria}'"));
    }

    [Fact]
    public async Task I6_control_relation_needs_two_existing_regimes_and_a_bounded_period()
    {
        await using var db = await TestDb.OpenAsync();
        var japan = await db.InsertRegimeAsync("日本");
        var manchukuo = await db.InsertRegimeAsync("滿洲國");
        const string p = "'[1932-03-01,1945-08-18]', 'day', 'day'";

        Assert.Equal(SqlState.ForeignKey, await db.ExpectErrorAsync($"INSERT INTO regime_control_relations ({ControlCols}) VALUES ('{japan}', '{Guid.NewGuid()}', 'puppet', {p})"));
        Assert.Equal(SqlState.NotNull, await db.ExpectErrorAsync($"INSERT INTO regime_control_relations ({ControlCols}) VALUES (NULL, '{manchukuo}', 'puppet', {p})"));
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync($"INSERT INTO regime_control_relations ({ControlCols}) VALUES ('{japan}', '{japan}', 'puppet', {p})"));
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync($"INSERT INTO regime_control_relations ({ControlCols}) VALUES ('{japan}', '{manchukuo}', 'alliance', {p})"));
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync($"INSERT INTO regime_control_relations ({ControlCols}) VALUES ('{japan}', '{manchukuo}', 'puppet', '[1932-03-01,)', 'day', 'day')"));
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync($"INSERT INTO regime_control_relations ({ControlCols}) VALUES ('{japan}', '{manchukuo}', 'puppet', '[1932-03-01,1945-08-18]', 'year', 'day')"));

        var id = await db.ScalarAsync<Guid>($"INSERT INTO regime_control_relations ({ControlCols}) VALUES ('{japan}', '{manchukuo}', 'puppet', {p}) RETURNING id");
        // 同控制方／被控制方／類型的非爭議期間不可重疊；不同類型或標記爭議可以並存
        Assert.Equal(SqlState.Exclusion, await db.ExpectErrorAsync(
            $"INSERT INTO regime_control_relations ({ControlCols}) VALUES ('{japan}', '{manchukuo}', 'puppet', '[1940-01-01,1941-12-31]', 'year', 'year')"));
        await db.ExecAsync($"INSERT INTO regime_control_relations ({ControlCols}, is_disputed) VALUES ('{japan}', '{manchukuo}', 'puppet', '[1940-01-01,1941-12-31]', 'year', 'year', true)");
        await db.ExecAsync($"INSERT INTO regime_control_relations ({ControlCols}) VALUES ('{japan}', '{manchukuo}', 'protectorate', '[1940-01-01,1941-12-31]', 'year', 'year')");

        // I5：不可刪除；修改要原因並留紀錄
        Assert.Equal(SqlState.Restrict, await db.ExpectErrorAsync($"DELETE FROM regime_control_relations WHERE id = '{id}'"));
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync($"UPDATE regime_control_relations SET description = '補註' WHERE id = '{id}'"));
        await db.ExecAsync("SELECT set_config('world_line.change_reason', '補充說明', true)");
        await db.ExecAsync($"UPDATE regime_control_relations SET description = '補註' WHERE id = '{id}'");
        Assert.Equal(1L, await db.ScalarAsync<long>($"SELECT count(*) FROM data_revisions WHERE table_name = 'regime_control_relations' AND row_id = '{id}'"));
    }

    [Fact]
    public async Task Alliance_membership_periods_cannot_overlap_and_rows_cannot_be_deleted()
    {
        await using var db = await TestDb.OpenAsync();
        var italy = await db.InsertRegimeAsync("義大利");
        var axis = await db.ScalarAsync<Guid>(
            $"INSERT INTO alliances (self_name, existence_period, existence_from_precision, existence_to_precision) VALUES ('測試陣營-{Guid.NewGuid():N}', '[1936-10-25,1945-09-02]', 'day', 'day') RETURNING id");
        const string cols = "alliance_id, regime_id, role, valid_period, valid_from_precision, valid_to_precision";

        await db.ExecAsync($"INSERT INTO alliance_memberships ({cols}) VALUES ('{axis}', '{italy}', 'member', '[1936-10-25,1943-09-08]', 'day', 'day')");
        Assert.Equal(SqlState.Exclusion, await db.ExpectErrorAsync(
            $"INSERT INTO alliance_memberships ({cols}) VALUES ('{axis}', '{italy}', 'member', '[1943-01-01,1943-12-31]', 'year', 'year')"));
        // 退出後再加入：不重疊的新紀錄
        await db.ExecAsync($"INSERT INTO alliance_memberships ({cols}) VALUES ('{axis}', '{italy}', 'associate', '[1943-09-23,1945-04-25]', 'day', 'day')");
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync(
            $"INSERT INTO alliance_memberships ({cols}) VALUES ('{axis}', '{italy}', 'enemy', '[1946-01-01,)', 'year', NULL)"));

        Assert.Equal(SqlState.Restrict, await db.ExpectErrorAsync($"DELETE FROM alliance_memberships WHERE alliance_id = '{axis}'"));
        Assert.Equal(SqlState.Restrict, await db.ExpectErrorAsync($"DELETE FROM alliances WHERE id = '{axis}'"));
    }

    [Fact]
    public async Task Year_to_date_migration_helpers_use_astronomical_years()
    {
        await using var db = await TestDb.OpenAsync();
        // PostgreSQL 沒有 0 年：天文紀年 0 = 西元前 1 年，-201 = 西元前 202 年
        Assert.Equal("0618-01-01", await db.ScalarAsync<string>("SELECT wl_astro_jan1(618)::text"));
        Assert.Equal("0001-01-01 BC", await db.ScalarAsync<string>("SELECT wl_astro_jan1(0)::text"));
        Assert.Equal("0202-01-01 BC", await db.ScalarAsync<string>("SELECT wl_astro_jan1(-201)::text"));
        // 示範 seed 的長安（西元前 202 年起）以 daterange 保存
        Assert.Equal("0202-01-01 BC", await db.ScalarAsync<string>("SELECT lower(valid_period)::text FROM place_names WHERE historical_name = '長安' LIMIT 1"));
        // 年精度的年號：迄年 → 該年 12/31
        Assert.Equal("0756-12-31", await db.ScalarAsync<string>("SELECT end_date::text FROM reign_eras WHERE era_name = '天寶' LIMIT 1"));
    }
}
