using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Npgsql;

namespace WorldLine.Api.Tests;

/// <summary>
/// 陣營時間切片（憲法 §6「陣營」、PRD §6.3 regime_alignments）：
/// 每段都要有來源、起日必填、同政權不可重疊、/control 依日期帶出控制方陣營（沒有就是 null＝陣營未建置）。
/// 測試資料只寫進 Testcontainers 的測試資料庫。
/// </summary>
[Collection(PostGisCollection.Name)]
public sealed class RegimeAlignmentTests(PostGisFixture fx)
{
    private static object Cite(Guid source, string role = "primary", string locator = "Doc. 2643-PS, p. 355") =>
        new { sourceId = source, role, locator, evidenceNote = "條約簽署日" };

    private static object Body(string camp, string? start, string? end, params object[] citations) =>
        new { camp, validPeriod = new { start, end }, citations };

    private static Task<HttpResponseMessage> Post(ApiTestKit k, Guid regime, object body) =>
        k.W.PostAsJsonAsync($"/api/v1/regimes/{regime}/alignments", body);

    private static async Task<(ApiTestKit k, Guid regime, Guid source)> Setup(PostGisFixture fx)
    {
        var k = new ApiTestKit(fx);
        var regime = await k.Regime("reich");
        var source = await k.Source(kind: "trial_record", license: "us_federal_pd", title: "NCA V");
        return (k, regime, source);
    }

    [Fact]
    public async Task Alignment_with_primary_citation_is_created_and_listed()
    {
        var (k, regime, source) = await Setup(fx);
        var data = (await ApiTestKit.Expect(await Post(k, regime, Body("axis", "1940-09-27", null, Cite(source))), HttpStatusCode.Created))
            .GetProperty("data");
        Assert.Equal("axis", data.GetProperty("camp").GetString());
        Assert.Equal("1940-09-27", data.GetProperty("validPeriod").GetProperty("start").GetString());
        Assert.Equal(JsonValueKind.Null, data.GetProperty("validPeriod").GetProperty("end").ValueKind);
        var cite = data.GetProperty("citations").EnumerateArray().Single();
        Assert.Equal("NCA V", cite.GetProperty("sourceTitle").GetString());
        Assert.Equal("Doc. 2643-PS, p. 355", cite.GetProperty("locator").GetString());

        var list = (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/regimes/{regime}/alignments"), HttpStatusCode.OK)).GetProperty("data");
        Assert.Equal(1, list.GetArrayLength());
    }

    [Fact]
    public async Task Alignment_without_citation_is_rejected()
    {
        var (k, regime, _) = await Setup(fx);
        await ApiTestKit.Expect(await Post(k, regime, Body("axis", "1940-09-27", null)), HttpStatusCode.BadRequest, "CITATION_REQUIRED");
    }

    [Fact]
    public async Task Alignment_with_only_date_check_citation_is_rejected()
    {
        var (k, regime, source) = await Setup(fx);
        await ApiTestKit.Expect(await Post(k, regime, Body("axis", "1940-09-27", null, Cite(source, role: "date_check"))),
            HttpStatusCode.BadRequest, "CITATION_REQUIRED");
    }

    [Fact]
    public async Task Primary_citation_without_usage_rights_is_rejected()
    {
        var (k, regime, _) = await Setup(fx);
        var unlicensed = await k.Source(kind: "peer_reviewed", license: null, title: "paper");
        await ApiTestKit.Expect(await Post(k, regime, Body("axis", "1940-09-27", null, Cite(unlicensed))),
            HttpStatusCode.BadRequest, "SOURCE_NOT_QUALIFIED");
    }

    [Fact]
    public async Task Citation_without_locator_is_rejected()
    {
        var (k, regime, source) = await Setup(fx);
        await ApiTestKit.Expect(await Post(k, regime, Body("axis", "1940-09-27", null, Cite(source, locator: " "))),
            HttpStatusCode.BadRequest, "SOURCE_NOT_QUALIFIED");
    }

    [Fact]
    public async Task Start_date_is_required()
    {
        var (k, regime, source) = await Setup(fx);
        await ApiTestKit.Expect(await Post(k, regime, Body("axis", null, "1943-09-08", Cite(source))), HttpStatusCode.BadRequest, "PERIOD_REQUIRED");
    }

    [Fact]
    public async Task Unknown_camp_is_rejected()
    {
        var (k, regime, source) = await Setup(fx);
        await ApiTestKit.Expect(await Post(k, regime, Body("fascist", "1940-09-27", null, Cite(source))), HttpStatusCode.BadRequest, "VALIDATION_FAILED");
    }

    [Fact]
    public async Task Unknown_regime_returns_404()
    {
        var (k, _, source) = await Setup(fx);
        await ApiTestKit.Expect(await Post(k, Guid.NewGuid(), Body("axis", "1940-09-27", null, Cite(source))), HttpStatusCode.NotFound);
    }

    [Fact] // 陣營隨時間改變（例：義大利 1943）→ 分段；相接可以，重疊不行
    public async Task Same_regime_segments_may_touch_but_not_overlap()
    {
        var (k, regime, source) = await Setup(fx);
        await ApiTestKit.Expect(await Post(k, regime, Body("axis", "1940-09-27", "1943-09-08", Cite(source))), HttpStatusCode.Created);
        await ApiTestKit.Expect(await Post(k, regime, Body("co_belligerent", "1943-10-13", null, Cite(source, locator: "p. 2"))), HttpStatusCode.Created);
        await ApiTestKit.Expect(await Post(k, regime, Body("allies", "1943-09-07", "1943-10-13", Cite(source, locator: "p. 3"))),
            HttpStatusCode.Conflict, "CONFLICTING_OFFICIAL_VERSION");
        await ApiTestKit.Expect(await Post(k, regime, Body("neutral", "1943-09-08", "1943-10-13", Cite(source, locator: "p. 4"))), HttpStatusCode.Created);
    }

    [Fact] // GET /control：依日期帶出控制方陣營；日期在切片之前 → null（前端顯示「陣營未建置」）
    public async Task Control_features_carry_controller_alignment_on_that_date()
    {
        var (k, regime, source) = await Setup(fx);
        var map = await k.Source();
        var theater = await k.Theater("west");
        var snap = await k.Snapshot(theater, "1940-07-15");
        var cr = await k.Id(await k.PostControl(ApiTestKit.ControlBody(regime, snap, map, "1940-07-15", "1942-11-11", ApiTestKit.Square(30, 30, 1))), "controlRecordId");
        await ApiTestKit.Expect(await Post(k, regime, Body("axis", "1940-09-27", null, Cite(source))), HttpStatusCode.Created);

        async Task<JsonElement> Props(string date) =>
            (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/control?date={date}"), HttpStatusCode.OK))
                .GetProperty("data").GetProperty("featureCollection").GetProperty("features").EnumerateArray()
                .Single(f => f.GetProperty("properties").GetProperty("controlRecordId").GetGuid() == cr).GetProperty("properties");

        Assert.Equal(JsonValueKind.Null, (await Props("1940-08-15")).GetProperty("controllerAlignment").ValueKind);
        var al = (await Props("1940-10-01")).GetProperty("controllerAlignment");
        Assert.Equal("axis", al.GetProperty("camp").GetString());
        Assert.Equal("NCA V", al.GetProperty("citations")[0].GetProperty("sourceTitle").GetString());
    }

    [Fact] // DB 兜底：EXCLUDE 不重疊、I5 不可刪除、只允許寫入撤回
    public async Task Schema_guards_exclusion_delete_and_update()
    {
        var (_, regime, _) = await Setup(fx);
        await using var c = new NpgsqlConnection(fx.ConnectionString);
        await c.OpenAsync();
        async Task<object?> Exec(string sql) { await using var cmd = new NpgsqlCommand(sql, c); return await cmd.ExecuteScalarAsync(); }

        var id = (Guid)(await Exec($"INSERT INTO regime_alignments (regime_id, camp, valid_period) VALUES ('{regime}', 'axis', daterange('1940-09-27', NULL)) RETURNING id"))!;
        var ex = await Assert.ThrowsAsync<PostgresException>(() =>
            Exec($"INSERT INTO regime_alignments (regime_id, camp, valid_period) VALUES ('{regime}', 'allies', daterange('1943-01-01','1944-01-01'))"));
        Assert.Equal(PostgresErrorCodes.ExclusionViolation, ex.SqlState);

        ex = await Assert.ThrowsAsync<PostgresException>(() => Exec($"INSERT INTO regime_alignments (regime_id, camp, valid_period) VALUES ('{regime}', 'axis', daterange(NULL, '1939-01-01'))"));
        Assert.Equal(PostgresErrorCodes.CheckViolation, ex.SqlState);

        ex = await Assert.ThrowsAsync<PostgresException>(() => Exec($"DELETE FROM regime_alignments WHERE id = '{id}'"));
        Assert.Equal(PostgresErrorCodes.RestrictViolation, ex.SqlState);

        ex = await Assert.ThrowsAsync<PostgresException>(() => Exec($"UPDATE regime_alignments SET camp = 'allies' WHERE id = '{id}'"));
        Assert.Equal(PostgresErrorCodes.RestrictViolation, ex.SqlState);

        // 撤回後，同期間可以再建一筆（EXCLUDE 只看有效切片）
        await Exec($"UPDATE regime_alignments SET retracted_at = now(), retraction_reason = '測試撤回' WHERE id = '{id}'");
        await Exec($"INSERT INTO regime_alignments (regime_id, camp, valid_period) VALUES ('{regime}', 'allies', daterange('1943-01-01','1944-01-01'))");
        ex = await Assert.ThrowsAsync<PostgresException>(() => Exec($"UPDATE regime_alignments SET retraction_reason = 'x' WHERE id = '{id}'"));
        Assert.Equal(PostgresErrorCodes.RestrictViolation, ex.SqlState);
    }
}
