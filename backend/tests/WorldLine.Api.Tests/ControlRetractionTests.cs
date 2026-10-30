using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Nodes;
using Npgsql;

namespace WorldLine.Api.Tests;

/// <summary>
/// 控制紀錄與涵蓋備註的撤回（PRD §7 POST /control-records/{id}/retraction；I5「撤回也是一個版本」）。
/// 2026-10-31 實作（AI 提案・待拍板），用於「快照延伸到下一張快照」（Tai 2026-10-31）：已寫入的單日紀錄撤回後新增延伸版本。
/// </summary>
[Collection(PostGisCollection.Name)]
public sealed class ControlRetractionTests(PostGisFixture fx)
{
    private static object Gap(JsonObject geometry, string start, string end) => new
    {
        geometry, validPeriod = new { start, end }, reason = "not_yet_digitized",
        note = new Dictionary<string, string> { ["zh-Hant"] = "測試", ["en"] = "test" },
    };

    private static object Retraction(string reason) => new { reason };

    private static async Task<(HashSet<Guid> records, HashSet<Guid> gaps)> On(ApiTestKit k, string date)
    {
        var data = (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/control?date={date}"), HttpStatusCode.OK)).GetProperty("data");
        return (
            data.GetProperty("featureCollection").GetProperty("features").EnumerateArray()
                .Select(f => f.GetProperty("properties").GetProperty("controlRecordId").GetGuid()).ToHashSet(),
            data.GetProperty("coverageNotes").EnumerateArray().Select(n => n.GetProperty("id").GetGuid()).ToHashSet());
    }

    [Fact]
    public async Task Retracted_control_record_disappears_and_frees_the_slot_for_a_replacement()
    {
        var k = new ApiTestKit(fx);
        var reich = await k.Regime("de");
        var map = await k.Source();
        var snap = await k.Snapshot(await k.Theater("we"), "1940-06-04");
        var body = ApiTestKit.ControlBody(reich, snap, map, "1940-06-04", "1940-06-05", ApiTestKit.Square(-120, 50, 1));
        var cr = await k.Id(await k.PostControl(body), "controlRecordId");
        Assert.Contains(cr, (await On(k, "1940-06-04")).records);

        // 原因必填；未知 id → 404
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/control-records/{cr}/retraction", Retraction(" ")), HttpStatusCode.BadRequest);
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/control-records/{Guid.NewGuid()}/retraction", Retraction("x")), HttpStatusCode.NotFound);
        // 沒有 API key 不可撤回
        Assert.Equal(HttpStatusCode.Unauthorized,
            (await k.R.PostAsJsonAsync($"/api/v1/control-records/{cr}/retraction", Retraction("x"))).StatusCode);

        // 撤回前：同控制方、同期間、同幾何 → 409（I3）
        var extended = ApiTestKit.ControlBody(reich, snap, map, "1940-06-04", "1940-06-12", ApiTestKit.Square(-120, 50, 1));
        await ApiTestKit.Expect(await k.PostControl(extended), HttpStatusCode.Conflict, "CONFLICTING_OFFICIAL_VERSION");

        var res = (await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/control-records/{cr}/retraction", Retraction("快照延伸")), HttpStatusCode.OK)).GetProperty("data");
        Assert.Equal(cr, res.GetProperty("id").GetGuid());
        Assert.DoesNotContain(cr, (await On(k, "1940-06-04")).records);
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/control-records/{cr}/retraction", Retraction("again")), HttpStatusCode.Conflict, "CONFLICTING_OFFICIAL_VERSION");

        // 撤回後可新增延伸版本
        var cr2 = await k.Id(await k.PostControl(extended), "controlRecordId");
        Assert.Contains(cr2, (await On(k, "1940-06-08")).records);
        Assert.DoesNotContain(cr2, (await On(k, "1940-06-12")).records);

        // 歷程保留：原版本被撤回版本取代，撤回版本帶原因與引用
        await using var c = new NpgsqlConnection(fx.ConnectionString);
        await c.OpenAsync();
        await using var cmd = new NpgsqlCommand(
            "SELECT count(*) FILTER (WHERE superseded_by IS NOT NULL AND NOT is_retraction), " +
            "count(*) FILTER (WHERE is_retraction AND superseded_by IS NULL AND revision_reason = '快照延伸'), " +
            "(SELECT count(*) FROM control_record_citations cc JOIN control_record_versions v2 ON v2.id = cc.control_record_version_id WHERE v2.control_record_id = @id AND v2.is_retraction) " +
            "FROM control_record_versions WHERE control_record_id = @id", c);
        cmd.Parameters.AddWithValue("id", cr);
        await using var rd = await cmd.ExecuteReaderAsync();
        Assert.True(await rd.ReadAsync());
        Assert.Equal(1L, rd.GetInt64(0));
        Assert.Equal(1L, rd.GetInt64(1));
        Assert.True(rd.GetInt64(2) >= 1);
    }

    [Fact]
    public async Task Retracted_coverage_note_disappears_once()
    {
        var k = new ApiTestKit(fx);
        var gap = await k.Id(await k.W.PostAsJsonAsync("/api/v1/control-coverage-notes", Gap(ApiTestKit.Square(-125, 55, 1), "1940-06-04", "1940-06-05")));
        Assert.Contains(gap, (await On(k, "1940-06-04")).gaps);

        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/control-coverage-notes/{gap}/retraction", Retraction("")), HttpStatusCode.BadRequest);
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/control-coverage-notes/{Guid.NewGuid()}/retraction", Retraction("x")), HttpStatusCode.NotFound);
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/control-coverage-notes/{gap}/retraction", Retraction("快照延伸")), HttpStatusCode.OK);
        Assert.DoesNotContain(gap, (await On(k, "1940-06-04")).gaps);
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/control-coverage-notes/{gap}/retraction", Retraction("again")), HttpStatusCode.Conflict, "CONFLICTING_OFFICIAL_VERSION");

        var gap2 = await k.Id(await k.W.PostAsJsonAsync("/api/v1/control-coverage-notes", Gap(ApiTestKit.Square(-125, 55, 1), "1940-06-04", "1940-06-12")));
        Assert.Contains(gap2, (await On(k, "1940-06-11")).gaps);
    }
}
