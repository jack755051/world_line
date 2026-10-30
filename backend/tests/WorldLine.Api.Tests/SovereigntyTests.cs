using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Nodes;
using Npgsql;

namespace WorldLine.Api.Tests;

/// <summary>
/// 主權圖層（法理國界，sovereignty_records；2026-10-31 試驗 feature/borders-1938-1940，AI 提案・待拍板）：
/// 與控制區分開；依政權回傳（前端依政權上色），陣營只作補充；起訖事件沒有引用即「待查證」；幾何授權與 OHM 版本釘選。
/// </summary>
[Collection(PostGisCollection.Name)]
public sealed class SovereigntyTests(PostGisFixture fx)
{
    private static JsonObject Body(Guid regime, Guid source, string start, string? end, JsonObject? geometry = null,
        string license = "cc0", string? attribution = null, Guid? startEvent = null, Guid? endEvent = null,
        string status = "de_jure", long? relation = 2704712, int? version = 208)
    {
        var b = new JsonObject
        {
            ["regimeId"] = regime.ToString(),
            ["geometry"] = geometry ?? ApiTestKit.Square(10, 48, 2),
            ["validPeriod"] = new JsonObject { ["start"] = start, ["end"] = end },
            ["layerStatus"] = status,
            ["geometrySourceId"] = source.ToString(),
            ["geometryLocator"] = relation is null ? "n/a" : $"relation/{relation} v{version}",
            ["geometryLicense"] = license,
            ["attribution"] = attribution,
            ["startEventId"] = startEvent?.ToString(),
            ["endEventId"] = endEvent?.ToString(),
            ["provenance"] = new JsonObject { ["memberWayLicenses"] = new JsonObject { ["CC-BY 4.0"] = 25 } },
        };
        if (relation is not null)
        {
            b["ohmRelationId"] = relation;
            b["ohmVersion"] = version;
            b["ohmFetchedAt"] = "2026-10-30T19:22:26Z";
        }
        return b;
    }

    private static Task<HttpResponseMessage> Post(ApiTestKit k, JsonObject body) =>
        k.W.PostAsync("/api/v1/sovereignty-records", new StringContent(body.ToJsonString(), System.Text.Encoding.UTF8, "application/json"));

    private static async Task<Guid> Event(ApiTestKit k, string start, params object[] citations)
    {
        var res = await k.W.PostAsJsonAsync("/api/v1/events", new
        {
            eventKind = "treaty",
            occurred = new { start, end = DateOnly.Parse(start).AddDays(1).ToString("yyyy-MM-dd") },
            datePrecision = "day",
            summary = new Dictionary<string, string> { ["zh-Hant"] = "疆界變動", ["en"] = "Border change" },
            citations,
        });
        return await k.Id(res);
    }

    private static async Task<JsonElement?> FeatureOn(ApiTestKit k, string date, Guid record)
    {
        var data = (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/sovereignty?date={date}"), HttpStatusCode.OK)).GetProperty("data");
        Assert.Equal(date, data.GetProperty("date").GetString());
        foreach (var f in data.GetProperty("featureCollection").GetProperty("features").EnumerateArray())
            if (f.GetProperty("properties").GetProperty("recordId").GetGuid() == record) return f;
        return null;
    }

    [Fact]
    public async Task Record_is_returned_only_inside_its_half_open_period_with_regime_slug_and_pinned_provenance()
    {
        var k = new ApiTestKit(fx);
        var reich = await k.Regime("reich");
        var ohm = await k.Source(kind: "dataset", license: "cc0", title: "OpenHistoricalMap");
        var id = await k.Id(await Post(k, Body(reich, ohm, "1938-03-13", "1938-11-21")));

        Assert.Null(await FeatureOn(k, "1938-03-12", id));
        Assert.Null(await FeatureOn(k, "1938-11-21", id)); // 半開區間
        var f = (await FeatureOn(k, "1938-10-15", id))!.Value;
        var p = f.GetProperty("properties");
        Assert.Equal($"reich-{k.Tag}", p.GetProperty("regimeSlug").GetString());
        Assert.Equal("de_jure", p.GetProperty("layerStatus").GetString());
        var g = p.GetProperty("geometry");
        Assert.Equal(2704712, g.GetProperty("ohmRelationId").GetInt64());
        Assert.Equal(208, g.GetProperty("ohmVersion").GetInt32());
        Assert.Equal("cc0", g.GetProperty("geometryLicense").GetString());
        Assert.Equal(25, g.GetProperty("flags").GetProperty("memberWayLicenses").GetProperty("CC-BY 4.0").GetInt32());
        Assert.Equal("MultiPolygon", f.GetProperty("geometry").GetProperty("type").GetString());
        Assert.Equal(JsonValueKind.Null, p.GetProperty("startEvent").ValueKind);
    }

    [Fact] // 「待查證」：事件沒有合格引用 → pending；有引用 → verified
    public async Task Events_without_citations_are_pending_verification()
    {
        var k = new ApiTestKit(fx);
        var hu = await k.Regime("hungary");
        var ohm = await k.Source(kind: "dataset", license: "cc0", title: "OpenHistoricalMap");
        var dgfp = await k.Source(kind: "official_record", license: "us_federal_pd", title: "DGFP D IV");
        var award = await Event(k, "1938-11-02", new { sourceId = dgfp, locator = "Doc. 99, pp. 118–126", evidenceNote = "仲裁文本" });
        var unsourced = await Event(k, "1939-03-14");
        var id = await k.Id(await Post(k, Body(hu, ohm, "1938-11-02", "1939-03-14", startEvent: award, endEvent: unsourced)));

        var p = (await FeatureOn(k, "1938-12-01", id))!.Value.GetProperty("properties");
        Assert.Equal("verified", p.GetProperty("startEvent").GetProperty("verification").GetString());
        Assert.Equal("Doc. 99, pp. 118–126", p.GetProperty("startEvent").GetProperty("citations")[0].GetProperty("locator").GetString());
        Assert.Equal("pending", p.GetProperty("endEvent").GetProperty("verification").GetString());
        Assert.Equal(0, p.GetProperty("endEvent").GetProperty("citations").GetArrayLength());
    }

    [Fact] // 政權優先於陣營：陣營只作補充（有切片才帶），不影響回傳的要素
    public async Task Camp_is_only_a_supplement()
    {
        var k = new ApiTestKit(fx);
        var it = await k.Regime("italy");
        var ohm = await k.Source(kind: "dataset", license: "cc0", title: "OpenHistoricalMap");
        var frus = await k.Source(kind: "official_record", title: "FRUS 1939 I");
        var id = await k.Id(await Post(k, Body(it, ohm, "1929-06-07", "1940-06-24")));
        Assert.Equal(JsonValueKind.Null, (await FeatureOn(k, "1939-01-01", id))!.Value.GetProperty("properties").GetProperty("regimeAlignment").ValueKind);

        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/regimes/{it}/alignments", new
        {
            camp = "axis", validPeriod = new { start = "1939-05-22" },
            citations = new[] { new { sourceId = frus, locator = "p. 1", role = "primary", evidenceNote = "鋼鐵條約" } },
        }), HttpStatusCode.Created);
        var p = (await FeatureOn(k, "1939-10-15", id))!.Value.GetProperty("properties");
        Assert.Equal("axis", p.GetProperty("regimeAlignment").GetProperty("camp").GetString());
        Assert.Equal($"italy-{k.Tag}", p.GetProperty("regimeSlug").GetString());
    }

    [Fact]
    public async Task Same_regime_periods_cannot_overlap_and_retraction_allows_reentry()
    {
        var k = new ApiTestKit(fx);
        var pl = await k.Regime("poland");
        var ohm = await k.Source(kind: "dataset", license: "cc0", title: "OpenHistoricalMap");
        var a = await k.Id(await Post(k, Body(pl, ohm, "1924-06-22", "1938-11-01")));
        await ApiTestKit.Expect(await Post(k, Body(pl, ohm, "1938-10-01", "1939-10-06")), HttpStatusCode.Conflict, "CONFLICTING_OFFICIAL_VERSION");
        await k.Id(await Post(k, Body(pl, ohm, "1938-11-01", "1939-10-06"))); // 相接不重疊

        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/sovereignty-records/{a}/retraction", new { reason = "幾何換版" }), HttpStatusCode.OK);
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/sovereignty-records/{a}/retraction", new { reason = "again" }), HttpStatusCode.Conflict);
        Assert.Null(await FeatureOn(k, "1938-01-01", a));
        await k.Id(await Post(k, Body(pl, ohm, "1924-06-22", "1938-11-01", version: 215)));
    }

    [Fact] // 授權：幾何來源授權須在允許清單；cc_by 必須署名；OHM 關係必須釘版本
    public async Task Licence_and_pinning_rules()
    {
        var k = new ApiTestKit(fx);
        var es = await k.Regime("spain");
        var ohm = await k.Source(kind: "dataset", license: "cc0", title: "OpenHistoricalMap");
        var nc = await k.Source(kind: "dataset", license: null, title: "CShapes (CC BY-NC-SA)");
        await ApiTestKit.Expect(await Post(k, Body(es, nc, "1939-04-01", "1956-04-07")), HttpStatusCode.BadRequest, "SOURCE_NOT_QUALIFIED");
        await ApiTestKit.Expect(await Post(k, Body(es, ohm, "1939-04-01", "1956-04-07", license: "cc_by")), HttpStatusCode.BadRequest, "VALIDATION_FAILED");
        await ApiTestKit.Expect(await Post(k, Body(es, ohm, "1939-04-01", "1956-04-07", license: "cc_by_nc")), HttpStatusCode.BadRequest, "VALIDATION_FAILED");
        var noVersion = Body(es, ohm, "1939-04-01", "1956-04-07");
        noVersion.Remove("ohmVersion");
        await ApiTestKit.Expect(await Post(k, noVersion), HttpStatusCode.BadRequest, "VALIDATION_FAILED");
        await k.Id(await Post(k, Body(es, ohm, "1939-04-01", "1956-04-07", license: "cc_by", attribution: "© Instituto Geográfico Nacional (CNIG), CC BY 4.0")));
    }

    [Fact]
    public async Task Date_is_required_and_start_must_be_bounded()
    {
        var k = new ApiTestKit(fx);
        await ApiTestKit.Expect(await k.R.GetAsync("/api/v1/sovereignty"), HttpStatusCode.BadRequest, "VALIDATION_FAILED");
        var ch = await k.Regime("swiss");
        var ohm = await k.Source(kind: "dataset", license: "cc0", title: "OpenHistoricalMap");
        await ApiTestKit.Expect(await Post(k, Body(ch, ohm, null!, "1967-10-03")), HttpStatusCode.BadRequest, "PERIOD_REQUIRED");
        await k.Id(await Post(k, Body(ch, ohm, "1874-09-23", null))); // 迄日未知可無界
    }

    [Fact] // I5：不可刪除；只允許一次寫入撤回，其他欄位不可改
    public async Task I5_guards_on_sovereignty_records()
    {
        var k = new ApiTestKit(fx);
        var dk = await k.Regime("denmark");
        var ohm = await k.Source(kind: "dataset", license: "cc0", title: "OpenHistoricalMap");
        var id = await k.Id(await Post(k, Body(dk, ohm, "1932-01-30", "1944-06-17")));
        await using var c = new NpgsqlConnection(fx.ConnectionString);
        await c.OpenAsync();
        async Task Exec(string sql) { await using var cmd = new NpgsqlCommand(sql, c); await cmd.ExecuteNonQueryAsync(); }
        var ex = await Assert.ThrowsAsync<PostgresException>(() => Exec($"DELETE FROM sovereignty_records WHERE id = '{id}'"));
        Assert.Equal(PostgresErrorCodes.RestrictViolation, ex.SqlState);
        ex = await Assert.ThrowsAsync<PostgresException>(() => Exec($"UPDATE sovereignty_records SET geometry_locator = 'x' WHERE id = '{id}'"));
        Assert.Equal(PostgresErrorCodes.RestrictViolation, ex.SqlState);
        ex = await Assert.ThrowsAsync<PostgresException>(() => Exec(
            $"INSERT INTO sovereignty_records (regime_id, geom, valid_period, layer_status, geometry_source_id, geometry_locator, geometry_license) " +
            $"SELECT regime_id, geom, daterange('1940-01-01','1941-01-01'), layer_status, geometry_source_id, 'y', geometry_license FROM sovereignty_records WHERE id = '{id}'"));
        Assert.Equal(PostgresErrorCodes.ExclusionViolation, ex.SqlState);
    }
}
