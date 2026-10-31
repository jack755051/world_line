using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace WorldLine.Api.Tests;

/// <summary>
/// 衝突圖示（交叉雙劍；2026-10-31 試驗 feature/borders-1938-1940，AI 提案・待拍板）：
/// 每個衝突都對應有日期的開戰事件；顯示期間由事件推得 [開戰日, 停戰或投降日 + 1)；
/// 起訖事件沿用主權卡的事件結構（沒有引用＝待查證）；撤回走 I5。
/// </summary>
[Collection(PostGisCollection.Name)]
public sealed class ConflictTests(PostGisFixture fx)
{
    private static object Point(double x, double y) => new { type = "Point", coordinates = new[] { x, y } };

    private static async Task<Guid> Event(ApiTestKit k, string kind, string start, params object[] citations)
    {
        var res = await k.W.PostAsJsonAsync("/api/v1/events", new
        {
            eventKind = kind,
            occurred = new { start, end = DateOnly.Parse(start).AddDays(1).ToString("yyyy-MM-dd") },
            datePrecision = "day",
            summary = new Dictionary<string, string> { ["zh-Hant"] = $"{kind} {start}", ["en"] = $"{kind} {start}" },
            citations,
        });
        return await k.Id(res);
    }

    private static Task<HttpResponseMessage> Post(ApiTestKit k, Guid a, Guid b, Guid? start, Guid? end, object? location = null, string method = "共同邊界中點") =>
        k.W.PostAsJsonAsync("/api/v1/conflict-records", new
        {
            regimeAId = a, regimeBId = b, startEventId = start, endEventId = end,
            location = location ?? Point(18.5, 51.5), locationMethod = method,
        });

    private static async Task<JsonElement?> FeatureOn(ApiTestKit k, string date, Guid id)
    {
        var data = (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/conflicts?date={date}"), HttpStatusCode.OK)).GetProperty("data");
        Assert.Equal(date, data.GetProperty("date").GetString());
        Assert.Equal("FeatureCollection", data.GetProperty("featureCollection").GetProperty("type").GetString());
        foreach (var f in data.GetProperty("featureCollection").GetProperty("features").EnumerateArray())
            if (f.GetProperty("properties").GetProperty("recordId").GetGuid() == id) return f;
        return null;
    }

    [Fact]
    public async Task Shown_from_start_event_date_through_end_event_date_inclusive_with_point_and_event_refs()
    {
        var k = new ApiTestKit(fx);
        var de = await k.Regime("reich");
        var pl = await k.Regime("polska");
        var frus = await k.Source(kind: "official_record", title: "FRUS 1939 I");
        var start = await Event(k, "war", "1939-09-01", new { sourceId = frus, locator = "Doc. 403, pp. 402–403", evidenceNote = "state of war" });
        var end = await Event(k, "surrender", "1939-10-06");
        var id = await k.Id(await Post(k, de, pl, start, end));

        Assert.Null(await FeatureOn(k, "1939-08-31", id));
        Assert.Null(await FeatureOn(k, "1939-10-07", id));
        Assert.NotNull(await FeatureOn(k, "1939-10-06", id)); // 結束日當天仍顯示
        var f = (await FeatureOn(k, "1939-09-15", id))!.Value;
        Assert.Equal("Feature", f.GetProperty("type").GetString());
        Assert.Equal("Point", f.GetProperty("geometry").GetProperty("type").GetString());
        var p = f.GetProperty("properties");
        Assert.Equal($"reich-{k.Tag}", p.GetProperty("regimeASlug").GetString());
        Assert.Equal($"polska-{k.Tag}", p.GetProperty("regimeBSlug").GetString());
        Assert.Equal("1939-09-01", p.GetProperty("validPeriod").GetProperty("start").GetString());
        Assert.Equal("1939-10-07", p.GetProperty("validPeriod").GetProperty("end").GetString());
        Assert.Equal("verified", p.GetProperty("startEvent").GetProperty("verification").GetString());
        Assert.Equal("Doc. 403, pp. 402–403", p.GetProperty("startEvent").GetProperty("citations")[0].GetProperty("locator").GetString());
        // 結束事件沒有引用：待查證，citations 為空陣列（與起始事件同一形狀）
        Assert.Equal("pending", p.GetProperty("endEvent").GetProperty("verification").GetString());
        Assert.Equal(0, p.GetProperty("endEvent").GetProperty("citations").GetArrayLength());
        Assert.Equal("共同邊界中點", p.GetProperty("locationMethod").GetString());
    }

    private static async Task<Guid> Territory(ApiTestKit k, Guid regime, Guid source, double x, double y, string status = "de_jure") =>
        await k.Id(await k.W.PostAsync("/api/v1/sovereignty-records", new StringContent(new JsonObject
        {
            ["regimeId"] = regime.ToString(),
            ["geometry"] = ApiTestKit.Square(x, y, 1),
            ["validPeriod"] = new JsonObject { ["start"] = "1941-01-01", ["end"] = "1944-01-01" },
            ["layerStatus"] = status,
            ["geometrySourceId"] = source.ToString(),
            ["geometryLocator"] = "relation/1 v1",
            ["geometryLicense"] = "cc0",
            ["ohmRelationId"] = 1,
            ["ohmVersion"] = 1,
            ["ohmFetchedAt"] = "2026-10-30T19:22:26Z",
        }.ToJsonString(), System.Text.Encoding.UTF8, "application/json")));

    [Fact]
    public async Task Far_apart_belligerents_get_a_dashed_arc_between_their_territories_adjacent_ones_do_not()
    {
        var k = new ApiTestKit(fx);
        var ohm = await k.Source(kind: "dataset", license: "cc0", title: "OpenHistoricalMap");
        var de = await k.Regime("reich");
        var nb = await k.Regime("nachbar");
        var us = await k.Regime("usa");
        var occ = await k.Regime("besetzt");
        var far = await k.Regime("jenseits");
        var none = await k.Regime("ohne-gebiet");
        await Territory(k, de, ohm, 5, 52);
        await Territory(k, nb, ohm, 6, 52);          // 與 de 共邊
        await Territory(k, us, ohm, -100, 37);      // 遠方
        await Territory(k, occ, ohm, 5, 40, "not_sovereign");
        await Territory(k, far, ohm, 6, 40);         // 只與 de 佔領的 occ 共邊
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync("/api/v1/occupation-attributions", new
        {
            occupiedRegimeId = occ, occupierRegimeId = de, controlKind = "military_administration",
            validPeriod = new { start = "1941-01-01", end = "1944-01-01" }, coOccupied = false,
            note = new Dictionary<string, string> { ["zh-Hant"] = "測試", ["en"] = "test" },
        }), HttpStatusCode.Created);
        var start = await Event(k, "war", "1941-12-11");
        var cNb = await k.Id(await Post(k, de, nb, start, null));
        var cUs = await k.Id(await Post(k, de, us, start, null, Point(-38, 55), "兩國沒有共同邊界"));
        var cFar = await k.Id(await Post(k, de, far, start, null));
        var cNone = await k.Id(await Post(k, de, none, start, null));

        var pNb = (await FeatureOn(k, "1942-12-01", cNb))!.Value.GetProperty("properties");
        Assert.True(pNb.GetProperty("adjacent").GetBoolean());
        Assert.Equal(JsonValueKind.Null, pNb.GetProperty("arc").ValueKind);

        var pUs = (await FeatureOn(k, "1942-12-01", cUs))!.Value.GetProperty("properties");
        Assert.False(pUs.GetProperty("adjacent").GetBoolean());
        var arc = pUs.GetProperty("arc");
        var from = arc.GetProperty("from").EnumerateArray().Select(v => v.GetDouble()).ToArray();
        var to = arc.GetProperty("to").EnumerateArray().Select(v => v.GetDouble()).ToArray();
        Assert.InRange(from[0], 5, 6); Assert.InRange(from[1], 52, 53);     // de 領土內
        Assert.InRange(to[0], -100, -99); Assert.InRange(to[1], 37, 38);    // us 領土內

        // 經由佔領區相接也算相鄰
        var pFar = (await FeatureOn(k, "1942-12-01", cFar))!.Value.GetProperty("properties");
        Assert.True(pFar.GetProperty("adjacent").GetBoolean());
        Assert.Equal(JsonValueKind.Null, pFar.GetProperty("arc").ValueKind);

        Assert.Equal(JsonValueKind.Null, arc.GetProperty("eventEnd").ValueKind); // 「兩國沒有共同邊界」的位置不是事件地點

        // 事件地點在一方領土內（珍珠港在美國夏威夷）→ 該方端點＝事件地點
        var jp = await k.Regime("nippon");
        await Territory(k, jp, ohm, 140, 36);
        var cPearl = await k.Id(await Post(k, jp, us, start, null, Point(-99.5, 37.5), "開戰地點：測試（在美國領土內）"));
        var aPearl = (await FeatureOn(k, "1942-12-01", cPearl))!.Value.GetProperty("properties").GetProperty("arc");
        Assert.Equal("to", aPearl.GetProperty("eventEnd").GetString());
        Assert.Equal(new[] { -99.5, 37.5 }, aPearl.GetProperty("to").EnumerateArray().Select(v => v.GetDouble()).ToArray());
        // 另一端＝日本領土（140–141E、36–37N）中離事件地點最近的點；-99.5 往東走（換日線）比往西近，所以取東緣 141E
        Assert.Equal(141, aPearl.GetProperty("from")[0].GetDouble(), 3);
        Assert.Equal(37, aPearl.GetProperty("from")[1].GetDouble(), 3);

        // 事件地點不在任何一方（哥打巴魯在尚未建置的英屬馬來亞）→ 離事件地點較遠的一方（宗主國 de）改用事件地點
        var cKota = await k.Id(await Post(k, jp, de, start, null, Point(102.24, 6.13), "開戰地點：哥打巴魯"));
        var aKota = (await FeatureOn(k, "1942-12-01", cKota))!.Value.GetProperty("properties").GetProperty("arc");
        Assert.Equal("to", aKota.GetProperty("eventEnd").GetString());
        Assert.Equal(new[] { 102.24, 6.13 }, aKota.GetProperty("to").EnumerateArray().Select(v => v.GetDouble()).ToArray());

        // 一方當日沒有主權紀錄：不畫弧
        var pNone = (await FeatureOn(k, "1942-12-01", cNone))!.Value.GetProperty("properties");
        Assert.False(pNone.GetProperty("adjacent").GetBoolean());
        Assert.Equal(JsonValueKind.Null, pNone.GetProperty("arc").ValueKind);
    }

    [Fact]
    public async Task Event_retraction_refuses_while_referenced_then_hides_event_from_regime_list()
    {
        var k = new ApiTestKit(fx);
        var jp = await k.Regime("nippon");
        var uk = await k.Regime("britannia");
        var old = await k.Id(await k.W.PostAsJsonAsync("/api/v1/events", new
        {
            eventKind = "war", occurred = new { start = "1941-12-08", end = "1941-12-09" }, datePrecision = "day",
            summary = new Dictionary<string, string> { ["zh-Hant"] = "日英開戰", ["en"] = "war" },
            participants = new[] { new { regimeId = jp, role = "belligerent" }, new { regimeId = uk, role = "belligerent" } },
        }));
        var cf = await k.Id(await Post(k, jp, uk, old, null, Point(102.24, 6.13), "開戰地點：哥打巴魯"));
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/events/{old}/retraction", new { reason = "補出處" }), HttpStatusCode.Conflict); // 衝突仍引用
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/conflict-records/{cf}/retraction", new { reason = "改指向新事件" }), HttpStatusCode.OK);
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/events/{old}/retraction", new { reason = "" }), HttpStatusCode.BadRequest);
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/events/{old}/retraction", new { reason = "補出處" }), HttpStatusCode.OK);
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/events/{old}/retraction", new { reason = "again" }), HttpStatusCode.Conflict);
        await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/events/{old}"), HttpStatusCode.NotFound);
        var list = (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/regimes/{uk}/events"), HttpStatusCode.OK)).GetProperty("data");
        Assert.DoesNotContain(list.EnumerateArray(), e => e.GetProperty("id").GetGuid() == old);
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/events/{Guid.CreateVersion7()}/retraction", new { reason = "x" }), HttpStatusCode.NotFound);
    }

    [Fact]
    public async Task Without_end_event_the_conflict_stays_open()
    {
        var k = new ApiTestKit(fx);
        var it = await k.Regime("italia");
        var gr = await k.Regime("hellas");
        var start = await Event(k, "war", "1940-10-28");
        var id = await k.Id(await Post(k, it, gr, start, null, Point(20.6, 40.2)));
        var p = (await FeatureOn(k, "1941-01-15", id))!.Value.GetProperty("properties");
        Assert.Equal(JsonValueKind.Null, p.GetProperty("validPeriod").GetProperty("end").ValueKind);
        Assert.Equal(JsonValueKind.Null, p.GetProperty("endEvent").ValueKind);
        Assert.Equal("pending", p.GetProperty("startEvent").GetProperty("verification").GetString());
    }

    [Fact]
    public async Task Validation_start_event_required_order_distinct_regimes_and_point_location()
    {
        var k = new ApiTestKit(fx);
        var a = await k.Regime("a");
        var b = await k.Regime("b");
        var start = await Event(k, "war", "1940-05-10");
        var earlier = await Event(k, "surrender", "1940-05-01");
        await ApiTestKit.Expect(await Post(k, a, b, null, null), HttpStatusCode.BadRequest);
        await ApiTestKit.Expect(await Post(k, a, b, Guid.NewGuid(), null), HttpStatusCode.BadRequest);
        await ApiTestKit.Expect(await Post(k, a, a, start, null), HttpStatusCode.BadRequest);
        await ApiTestKit.Expect(await Post(k, a, b, start, earlier), HttpStatusCode.BadRequest);
        await ApiTestKit.Expect(await Post(k, a, b, start, null, ApiTestKit.Square(1, 1)), HttpStatusCode.BadRequest);
        await ApiTestKit.Expect(await Post(k, a, b, start, null, method: " "), HttpStatusCode.BadRequest);
        await ApiTestKit.Expect(await k.R.GetAsync("/api/v1/conflicts"), HttpStatusCode.BadRequest);
    }

    [Fact]
    public async Task Retraction_hides_the_conflict_and_can_happen_only_once()
    {
        var k = new ApiTestKit(fx);
        var a = await k.Regime("nl-a");
        var b = await k.Regime("nl-b");
        var start = await Event(k, "war", "1940-05-10");
        var end = await Event(k, "surrender", "1940-05-14");
        var id = await k.Id(await Post(k, a, b, start, end));
        Assert.NotNull(await FeatureOn(k, "1940-05-12", id));
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/conflict-records/{id}/retraction", new { reason = "測試" }), HttpStatusCode.OK);
        Assert.Null(await FeatureOn(k, "1940-05-12", id));
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/conflict-records/{id}/retraction", new { reason = "再一次" }), HttpStatusCode.Conflict);
    }
}
