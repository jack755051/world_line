using System.Net;
using System.Net.Http.Json;
using System.Text.Json.Nodes;
using Npgsql;

namespace WorldLine.Api.Tests;

/// <summary>疆界圖磚第 2 層（ARCHITECTURE.md §9 步驟 2）：boundary_periods view 與第 1 層 API 的日期規則一致。</summary>
[Collection(PostGisCollection.Name)]
public sealed class BoundaryPeriodsTests(PostGisFixture fx)
{
    private static JsonObject Body(Guid regime, Guid source, string start, string? end, string status = "de_jure") => new()
    {
        ["regimeId"] = regime.ToString(),
        ["geometry"] = ApiTestKit.Square(10, 48, 2),
        ["validPeriod"] = new JsonObject { ["start"] = start, ["end"] = end },
        ["layerStatus"] = status,
        ["geometrySourceId"] = source.ToString(),
        ["geometryLocator"] = "n/a",
        ["geometryLicense"] = "cc0",
    };

    private static async Task<Guid> Post(ApiTestKit k, JsonObject body) =>
        await k.Id(await k.W.PostAsync("/api/v1/sovereignty-records", new StringContent(body.ToJsonString(), System.Text.Encoding.UTF8, "application/json")));

    private static int Day(string d) => DateOnly.Parse(d).DayNumber - new DateOnly(1900, 1, 1).DayNumber;

    /// <summary>前端 sovereignty-style.ts regimeColor 的後備色盤雜湊（8 色）。</summary>
    private static int ColorIdx(string slug)
    {
        uint h = 0;
        foreach (var ch in slug) h = unchecked(h * 31 + ch);
        return (int)(h % 8);
    }

    [Fact]
    public async Task Boundary_periods_match_sovereignty_records_and_api_dates()
    {
        var k = new ApiTestKit(fx);
        var regime = await k.Regime("bp-regime");
        var src = await k.Source(kind: "dataset", license: "cc0", title: "OpenHistoricalMap");
        var closed = await Post(k, Body(regime, src, "1899-12-25", "1920-06-04"));
        var open = await Post(k, Body(regime, src, "1920-06-04", null, "not_sovereign"));
        var retracted = await Post(k, Body(await k.Regime("bp-gone"), src, "1910-01-01", "1911-01-01"));
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/sovereignty-records/{retracted}/retraction", new { reason = "測試" }), HttpStatusCode.OK);

        await using var c = new NpgsqlConnection(fx.ConnectionString);
        await c.OpenAsync();
        await using var cmd = new NpgsqlCommand(
            "SELECT record_id, regime_slug, start_day, end_day, color_idx, disputed, control_type, ST_Area(geom) FROM boundary_periods WHERE record_id = ANY(@ids) ORDER BY start_day", c);
        cmd.Parameters.AddWithValue("ids", new[] { closed, open, retracted });
        var rows = new List<(Guid Id, string Slug, int Start, int End, int Color, bool Disputed, string Type, double Area)>();
        await using (var rd = await cmd.ExecuteReaderAsync())
            while (await rd.ReadAsync())
                rows.Add((rd.GetGuid(0), rd.GetString(1), rd.GetInt32(2), rd.GetInt32(3), rd.GetInt32(4), rd.GetBoolean(5), rd.GetString(6), rd.GetDouble(7)));

        Assert.Equal(2, rows.Count); // 撤回的不在 view 裡
        Assert.Equal((closed, -7, Day("1920-06-04")), (rows[0].Id, rows[0].Start, rows[0].End)); // 1900-01-01 之前為負數
        Assert.Equal((open, Day("1920-06-04"), int.MaxValue), (rows[1].Id, rows[1].Start, rows[1].End)); // 仍持續者用最大值
        Assert.Equal(("de_jure", "not_sovereign"), (rows[0].Type, rows[1].Type));
        Assert.All(rows, r => Assert.False(r.Disputed));
        Assert.All(rows, r => Assert.Equal(ColorIdx(r.Slug), r.Color));
        Assert.All(rows, r => Assert.Equal(4, r.Area, 6));

        // 與第 1 層 API 一致：start_day <= d AND end_day > d（半開區間，迄日當天已換段）
        foreach (var (date, expected) in new[] { ("1899-12-24", (Guid?)null), ("1899-12-25", closed), ("1920-06-03", closed), ("1920-06-04", open), ("2026-01-01", open) })
        {
            var d = Day(date);
            var inView = rows.Where(r => r.Start <= d && r.End > d).Select(r => (Guid?)r.Id).SingleOrDefault();
            Assert.Equal(expected, inView);
            var api = (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/sovereignty?date={date}"), HttpStatusCode.OK))
                .GetProperty("data").GetProperty("featureCollection").GetProperty("features").EnumerateArray()
                .Select(f => f.GetProperty("properties").GetProperty("recordId").GetGuid())
                .Where(id => id == closed || id == open).Select(id => (Guid?)id).SingleOrDefault();
            Assert.Equal(expected, api);
        }
    }

    [Theory] // SQL 雜湊與前端演算法一致（含超過 32 位元時的截斷）
    [InlineData("deutsches-reich")]
    [InlineData("kingdom-of-the-netherlands")]
    [InlineData("a")]
    [InlineData("british-raj-protectorate-of-the-straits-settlements-long-slug")]
    public async Task Color_idx_function_matches_frontend_hash(string slug)
    {
        await using var c = new NpgsqlConnection(fx.ConnectionString);
        await c.OpenAsync();
        await using var cmd = new NpgsqlCommand("SELECT wl_color_idx(@s)", c);
        cmd.Parameters.AddWithValue("s", slug);
        Assert.Equal(ColorIdx(slug), (int)(await cmd.ExecuteScalarAsync())!);
    }
}
