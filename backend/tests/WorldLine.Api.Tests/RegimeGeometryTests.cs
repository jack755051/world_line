using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace WorldLine.Api.Tests;

/// <summary>
/// ARCHITECTURE.md §9「介面」GET /regimes/{id}/geometry?date=：tiles 模式點選政權時取被選政權的完整幾何
/// （它自己的主權紀錄＋當天由它佔領的政權紀錄），每筆與 GET /sovereignty 同日回傳的那筆相同。
/// </summary>
[Collection(PostGisCollection.Name)]
public sealed class RegimeGeometryTests(PostGisFixture fx)
{
    private static async Task<Guid> Record(ApiTestKit k, Guid regime, Guid source, double lng, string start, string end, string status = "de_jure") =>
        await k.Id(await k.W.PostAsync("/api/v1/sovereignty-records", new StringContent(new JsonObject
        {
            ["regimeId"] = regime.ToString(),
            ["geometry"] = ApiTestKit.Square(lng, 52, 1),
            ["validPeriod"] = new JsonObject { ["start"] = start, ["end"] = end },
            ["layerStatus"] = status,
            ["geometrySourceId"] = source.ToString(),
            ["geometryLocator"] = "n/a",
            ["geometryLicense"] = "cc0",
        }.ToJsonString(), System.Text.Encoding.UTF8, "application/json")));

    private static async Task<JsonElement[]> Features(HttpResponseMessage r) =>
        (await ApiTestKit.Expect(r, HttpStatusCode.OK)).GetProperty("data").GetProperty("featureCollection").GetProperty("features").EnumerateArray().ToArray();

    [Fact]
    public async Task Returns_own_records_plus_regimes_it_occupies_identical_to_sovereignty()
    {
        var k = new ApiTestKit(fx);
        var reich = await k.Regime("geo-reich");
        var occupied = await k.Regime("geo-occupied");
        var other = await k.Regime("geo-other");
        var src = await k.Source(kind: "dataset", license: "cc0", title: "OpenHistoricalMap");
        var own = await Record(k, reich, src, 10, "1939-01-01", "1946-01-01");
        var occ = await Record(k, occupied, src, 5, "1939-01-01", "1946-01-01", "not_sovereign");
        var unrelated = await Record(k, other, src, 20, "1939-01-01", "1946-01-01");
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync("/api/v1/occupation-attributions", new
        {
            occupiedRegimeId = occupied, occupierRegimeId = reich, controlKind = "civil_administration",
            validPeriod = new { start = "1940-05-29", end = "1945-05-05" },
            note = new Dictionary<string, string> { ["zh-Hant"] = "測試", ["en"] = "test" },
        }), HttpStatusCode.Created);

        // 佔領期間前：只有自己的紀錄
        var before = await Features(await k.R.GetAsync($"/api/v1/regimes/{reich}/geometry?date=1940-05-20"));
        Assert.Equal([own], before.Select(f => f.GetProperty("properties").GetProperty("recordId").GetGuid()));

        // 佔領期間：自己＋被它佔領的；不含無關政權；每筆與 /sovereignty 同日同縮放的那筆完全相同
        var during = await Features(await k.R.GetAsync($"/api/v1/regimes/{reich}/geometry?date=1942-11-01&zoom=4"));
        var ids = during.Select(f => f.GetProperty("properties").GetProperty("recordId").GetGuid()).ToHashSet();
        Assert.True(ids.SetEquals([own, occ]));
        Assert.DoesNotContain(unrelated, ids);
        var all = (await Features(await k.R.GetAsync("/api/v1/sovereignty?date=1942-11-01&zoom=4")))
            .ToDictionary(f => f.GetProperty("properties").GetProperty("recordId").GetGuid(), f => f.GetRawText());
        foreach (var f in during) Assert.Equal(all[f.GetProperty("properties").GetProperty("recordId").GetGuid()], f.GetRawText());

        // 查不到的政權 404；date 必填 400
        await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/regimes/{Guid.NewGuid()}/geometry?date=1942-11-01"), HttpStatusCode.NotFound);
        await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/regimes/{reich}/geometry"), HttpStatusCode.BadRequest);
    }
}
