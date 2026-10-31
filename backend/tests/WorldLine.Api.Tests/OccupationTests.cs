using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Nodes;
using Npgsql;

namespace WorldLine.Api.Tests;

/// <summary>
/// 佔領歸屬（occupation_attributions；2026-10-31 Tai：主權圖層的佔領區用佔領國顏色、依控制程度分深淺）：
/// 依被佔領政權＋期間；依據事件沒有引用＝待查證；同政權期間不可重疊；I5 只新增、只撤回一次。
/// </summary>
[Collection(PostGisCollection.Name)]
public sealed class OccupationTests(PostGisFixture fx)
{
    private static async Task<Guid> Record(ApiTestKit k, Guid regime, Guid source, string start, string end) =>
        await k.Id(await k.W.PostAsync("/api/v1/sovereignty-records", new StringContent(new JsonObject
        {
            ["regimeId"] = regime.ToString(),
            ["geometry"] = ApiTestKit.Square(5, 52, 1),
            ["validPeriod"] = new JsonObject { ["start"] = start, ["end"] = end },
            ["layerStatus"] = "not_sovereign",
            ["geometrySourceId"] = source.ToString(),
            ["geometryLocator"] = "relation/2883430 v24",
            ["geometryLicense"] = "cc0",
            ["ohmRelationId"] = 2883430,
            ["ohmVersion"] = 24,
            ["ohmFetchedAt"] = "2026-10-30T19:22:26Z",
        }.ToJsonString(), System.Text.Encoding.UTF8, "application/json")));

    private static async Task<Guid> Event(ApiTestKit k, string start, params object[] citations) =>
        await k.Id(await k.W.PostAsJsonAsync("/api/v1/events", new
        {
            eventKind = "political",
            occurred = new { start, end = DateOnly.Parse(start).AddDays(1).ToString("yyyy-MM-dd") },
            datePrecision = "day",
            summary = new Dictionary<string, string> { ["zh-Hant"] = "設立帝國專員轄區", ["en"] = "Reichskommissariat set up" },
            citations,
        }));

    private static Task<HttpResponseMessage> Attribute(ApiTestKit k, Guid occupied, Guid occupier, string kind, string start, string? end,
        Guid? basis = null, bool? co = null) =>
        k.W.PostAsJsonAsync("/api/v1/occupation-attributions", new
        {
            occupiedRegimeId = occupied, occupierRegimeId = occupier, controlKind = kind,
            validPeriod = new { start, end }, basisEventId = basis, coOccupied = co,
            note = new Dictionary<string, string> { ["zh-Hant"] = "測試", ["en"] = "test" },
        });

    private static async Task<JsonElement> Props(ApiTestKit k, string date, Guid record)
    {
        var data = (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/sovereignty?date={date}"), HttpStatusCode.OK)).GetProperty("data");
        foreach (var f in data.GetProperty("featureCollection").GetProperty("features").EnumerateArray())
            if (f.GetProperty("properties").GetProperty("recordId").GetGuid() == record) return f.GetProperty("properties");
        throw new Xunit.Sdk.XunitException("feature not found");
    }

    [Fact]
    public async Task Sovereignty_feature_carries_occupier_kind_and_verification_only_inside_the_attribution_period()
    {
        var k = new ApiTestKit(fx);
        var rk = await k.Regime("rk-nl");
        var reich = await k.Regime("reich");
        var ohm = await k.Source(kind: "dataset", license: "cc0", title: "OpenHistoricalMap");
        var dgfp = await k.Source(kind: "official_record", title: "DGFP D IX");
        var rec = await Record(k, rk, ohm, "1940-05-15", "1945-05-05");
        var ev = await Event(k, "1940-05-18", new { sourceId = dgfp, locator = "No. 274", evidenceNote = "Führer decree" });
        var a = await ApiTestKit.Expect(await Attribute(k, rk, reich, "civil_administration", "1940-05-29", "1945-05-05", ev), HttpStatusCode.Created);
        Assert.Equal("civil_administration", a.GetProperty("data").GetProperty("controlKind").GetString());

        Assert.Equal(JsonValueKind.Null, (await Props(k, "1940-05-20", rec)).GetProperty("occupation").ValueKind);
        var o = (await Props(k, "1942-11-01", rec)).GetProperty("occupation");
        Assert.Equal(reich, o.GetProperty("occupierRegimeId").GetGuid());
        Assert.Equal($"reich-{k.Tag}", o.GetProperty("occupierSlug").GetString());
        Assert.Equal("civil_administration", o.GetProperty("controlKind").GetString());
        Assert.Equal("verified", o.GetProperty("verification").GetString());
        Assert.Equal("No. 274", o.GetProperty("basisEvent").GetProperty("citations")[0].GetProperty("locator").GetString());
        Assert.False(o.GetProperty("coOccupied").GetBoolean());
    }

    [Fact]
    public async Task Without_cited_basis_event_the_attribution_is_pending_and_co_occupation_is_flagged()
    {
        var k = new ApiTestKit(fx);
        var gr = await k.Regime("hellenic-state");
        var it = await k.Regime("italia");
        var ohm = await k.Source(kind: "dataset", license: "cc0", title: "OpenHistoricalMap");
        var rec = await Record(k, gr, ohm, "1941-04-30", "1943-07-01");
        var uncited = await Event(k, "1941-04-30");
        await ApiTestKit.Expect(await Attribute(k, gr, it, "military_administration", "1941-04-30", "1943-07-01", uncited, co: true), HttpStatusCode.Created);
        var o = (await Props(k, "1942-01-01", rec)).GetProperty("occupation");
        Assert.Equal("pending", o.GetProperty("verification").GetString());
        Assert.True(o.GetProperty("coOccupied").GetBoolean());

        var gr2 = await k.Regime("no-event");
        var rec2 = await Record(k, gr2, ohm, "1941-04-30", "1943-07-01");
        await ApiTestKit.Expect(await Attribute(k, gr2, it, "annexed", "1941-04-30", null), HttpStatusCode.Created);
        var o2 = (await Props(k, "1942-01-01", rec2)).GetProperty("occupation");
        Assert.Equal("pending", o2.GetProperty("verification").GetString());
        Assert.Equal(JsonValueKind.Null, o2.GetProperty("basisEvent").ValueKind);
    }

    [Fact]
    public async Task Validation_overlap_and_retraction_rules()
    {
        var k = new ApiTestKit(fx);
        var occ = await k.Regime("occ");
        var de = await k.Regime("de");
        await ApiTestKit.Expect(await Attribute(k, occ, de, "protectorate", "1940-01-01", null), HttpStatusCode.BadRequest);
        await ApiTestKit.Expect(await Attribute(k, occ, occ, "annexed", "1940-01-01", null), HttpStatusCode.BadRequest);
        await ApiTestKit.Expect(await Attribute(k, occ, Guid.NewGuid(), "annexed", "1940-01-01", null), HttpStatusCode.BadRequest);
        var id = await k.Id(await Attribute(k, occ, de, "military_administration", "1940-01-01", "1941-01-01"));
        await ApiTestKit.Expect(await Attribute(k, occ, de, "civil_administration", "1940-06-01", "1942-01-01"), HttpStatusCode.Conflict);
        // 分段（半開區間相接）可以
        await ApiTestKit.Expect(await Attribute(k, occ, de, "civil_administration", "1941-01-01", "1942-01-01"), HttpStatusCode.Created);

        var r = await k.W.PostAsJsonAsync($"/api/v1/occupation-attributions/{id}/retraction", new { reason = "改分段" });
        await ApiTestKit.Expect(r, HttpStatusCode.OK);
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/occupation-attributions/{id}/retraction", new { reason = "again" }), HttpStatusCode.Conflict);
        // 撤回後同期間可重新新增
        await ApiTestKit.Expect(await Attribute(k, occ, de, "annexed", "1940-01-01", "1941-01-01"), HttpStatusCode.Created);

        await using var c = new NpgsqlConnection(fx.ConnectionString);
        await c.OpenAsync();
        await using (var cmd = new NpgsqlCommand($"UPDATE occupation_attributions SET control_kind = 'annexed' WHERE id = '{id}'", c))
            Assert.Equal("23001", (await Assert.ThrowsAsync<PostgresException>(() => cmd.ExecuteNonQueryAsync())).SqlState);
        await using (var cmd = new NpgsqlCommand($"DELETE FROM occupation_attributions WHERE id = '{id}'", c))
            await Assert.ThrowsAsync<PostgresException>(() => cmd.ExecuteNonQueryAsync());
    }
}
