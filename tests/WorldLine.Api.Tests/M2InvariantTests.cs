using Microsoft.EntityFrameworkCore;
using WorldLine.Api.Data;
using WorldLine.Api.Domain;

namespace WorldLine.Api.Tests;

/// <summary>M2 新增表格與欄位在資料庫層的約束（交易內執行後回滾）。</summary>
public class M2InvariantTests
{
    [Fact]
    public async Task Regime_existence_period_required_and_open_end_only_while_existing()
    {
        await using var db = await TestDb.OpenAsync();
        Assert.Equal(SqlState.NotNull, await db.ExpectErrorAsync("INSERT INTO regimes (self_name) VALUES ('無年代')"));
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync("INSERT INTO regimes (self_name, existence_period) VALUES ('空區間', 'empty')"));
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync("INSERT INTO regimes (self_name, existence_period) VALUES ('無起點', '(,300]')"));
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync("INSERT INTO regimes (self_name, existence_period, status) VALUES ('已分裂', '[25,)', 'split')"));
        await db.ExecAsync("INSERT INTO regimes (self_name, existence_period) VALUES ('仍存續', '[750,)')");
    }

    [Fact]
    public async Task Perspective_needs_exactly_one_observer()
    {
        await using var db = await TestDb.OpenAsync();
        var tang = await db.InsertRegimeAsync("唐");
        await db.ExecAsync("INSERT INTO historical_events (id, name, start_edtf, end_edtf, start_decimal, end_decimal) VALUES ('t-evt', '測試事件', '0751', '0751', 751, 751.997)");
        var cat = await db.ScalarAsync<int>("SELECT id FROM observer_categories ORDER BY id LIMIT 1");
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync(
            "INSERT INTO historical_event_perspectives (event_id, local_name, narrative_summary) VALUES ('t-evt', '甲', '乙')"));
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync(
            $"INSERT INTO historical_event_perspectives (event_id, regime_id, observer_category_id, local_name, narrative_summary) VALUES ('t-evt', '{tang}', {cat}, '甲', '乙')"));
        await db.ExecAsync($"INSERT INTO historical_event_perspectives (event_id, regime_id, local_name, narrative_summary) VALUES ('t-evt', '{tang}', '怛羅斯之役', '唐軍敗績')");
    }

    [Fact]
    public async Task Event_slug_and_decimal_order_checked_and_rows_cannot_be_deleted()
    {
        await using var db = await TestDb.OpenAsync();
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync(
            "INSERT INTO historical_events (id, name, start_edtf, end_edtf, start_decimal, end_decimal) VALUES ('Bad Slug', 'x', '0751', '0751', 751, 751.997)"));
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync(
            "INSERT INTO historical_events (id, name, start_edtf, end_edtf, start_decimal, end_decimal) VALUES ('rev', 'x', '0752', '0751', 752, 751)"));
        await db.ExecAsync("INSERT INTO historical_events (id, name, start_edtf, end_edtf, start_decimal, end_decimal) VALUES ('t-del', 'x', '0751', '0751', 751, 751.997)");
        Assert.Equal(SqlState.Restrict, await db.ExpectErrorAsync("DELETE FROM historical_events WHERE id = 't-del'"));
        Assert.Equal(SqlState.Restrict, await db.ExpectErrorAsync("DELETE FROM reign_eras"));
        Assert.Equal(SqlState.Restrict, await db.ExpectErrorAsync("DELETE FROM place_names"));
    }

    [Fact]
    public async Task Event_update_requires_reason_and_revision_uses_slug_row_id()
    {
        await using var db = await TestDb.OpenAsync();
        await db.ExecAsync("INSERT INTO historical_events (id, name, start_edtf, end_edtf, start_decimal, end_decimal) VALUES ('t-rev', '舊名', '0751', '0751', 751, 751.997)");
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync("UPDATE historical_events SET name = '新名' WHERE id = 't-rev'"));
        await db.ExecAsync("SELECT set_config('world_line.change_reason', '測試更名', true)");
        await db.ExecAsync("UPDATE historical_events SET name = '新名' WHERE id = 't-rev'");
        Assert.Equal(1L, await db.ScalarAsync<long>(
            "SELECT count(*) FROM data_revisions WHERE table_name = 'historical_events' AND row_id = 't-rev' AND new_row->>'name' = '新名'"));
    }

    [Fact]
    public async Task Territory_illustrative_flag_and_source_cannot_be_overwritten()
    {
        await using var db = await TestDb.OpenAsync();
        var tang = await db.InsertRegimeAsync("唐");
        var t = await db.ScalarAsync<Guid>($"INSERT INTO regime_territories (regime_id, valid_period, geom, is_illustrative, source) VALUES ('{tang}', '[618,907]', {TestDb.Square(100)}, true, '示意') RETURNING id");
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync($"UPDATE regime_territories SET is_illustrative = false WHERE id = '{t}'"));
        Assert.Equal(SqlState.Check, await db.ExpectErrorAsync($"UPDATE regime_territories SET source = '考據' WHERE id = '{t}'"));
    }
}

/// <summary>EF 端 I5 行為：修改需原因、version 自動遞增、修訂紀錄寫入（交易內執行後回滾）。</summary>
public class EfRevisionTests
{
    [Fact]
    public async Task Modify_without_reason_throws_and_with_reason_bumps_version()
    {
        await TestDatabase.EnsureReadyAsync();
        await using var ctx = TestDatabase.CreateContext();
        await using var tx = await ctx.Database.BeginTransactionAsync();

        var r = new Regime { SelfName = "測試國", ExistencePeriod = Api.Ranges.Closed(100, 200) };
        ctx.Regimes.Add(r);
        await ctx.SaveChangesAsync();
        Assert.Equal(0, r.Version);

        r.SelfName = "測試國二";
        await Assert.ThrowsAsync<MissingChangeReasonException>(() => ctx.SaveChangesAsync());

        ctx.ChangeReason = "測試改名";
        await ctx.SaveChangesAsync();
        Assert.Equal(1, r.Version);

        var revisions = await ctx.Database
            .SqlQuery<long>($"SELECT count(*) AS \"Value\" FROM data_revisions WHERE table_name = 'regimes' AND row_id = {r.Id.ToString()} AND change_reason = '測試改名'")
            .SingleAsync();
        Assert.Equal(1L, revisions);
        await tx.RollbackAsync();
    }
}
