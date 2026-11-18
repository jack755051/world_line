using System.Net;
using System.Net.Http.Json;

namespace WorldLine.Api.Tests;

/// <summary>
/// 首都紀錄（capital_records；2026-11-02 試驗，AI 提案・待拍板）：
/// 每筆記政權在某期間的首都；EXCLUDE 約束阻止同一政權的重疊期間；撤回走 I5。
/// </summary>
[Collection(PostGisCollection.Name)]
public sealed class CapitalTests(PostGisFixture fx)
{
    private static object Point(double lon, double lat) => new { type = "Point", coordinates = new[] { lon, lat } };

    private async Task<System.Guid> CreateCapital(
        ApiTestKit k, System.Guid regimeId,
        string cityZh, string cityEn,
        double lon, double lat,
        string start, string? end = null,
        string? sourceRef = null) =>
        await k.Id(await k.W.PostAsJsonAsync("/api/v1/capital-records", new
        {
            regimeId,
            cityName = new Dictionary<string, string> { ["zh-Hant"] = cityZh, ["en"] = cityEn },
            location = Point(lon, lat),
            validStart = start,
            validEnd = end,
            sourceRef = sourceRef ?? "待查證",
        }));

    private static async Task<System.Collections.Generic.List<System.Text.Json.JsonElement>> FeaturesOn(
        ApiTestKit k, string date) =>
        (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/capitals?date={date}"), HttpStatusCode.OK))
            .GetProperty("data").GetProperty("features")
            .EnumerateArray().ToList();

    [Fact]
    public async Task Capital_shown_within_valid_period_and_hidden_outside()
    {
        var k = new ApiTestKit(fx);
        var de = await k.Regime("berlin-test");

        var id = await CreateCapital(k, de, "柏林", "Berlin", 13.4, 52.5, "1933-01-30", "1945-05-08",
            "Encyclopædia Britannica: Berlin");

        // 期間內可見
        var features = await FeaturesOn(k, "1939-09-01");
        Assert.Contains(features, f => f.GetProperty("recordId").GetGuid() == id);

        // 期間前看不到
        var before = await FeaturesOn(k, "1933-01-29");
        Assert.DoesNotContain(before, f => f.GetProperty("recordId").GetGuid() == id);

        // 期間後看不到（半開 [start, end)）
        var after = await FeaturesOn(k, "1945-05-08");
        Assert.DoesNotContain(after, f => f.GetProperty("recordId").GetGuid() == id);
    }

    [Fact]
    public async Task Capital_feature_has_correct_properties()
    {
        var k = new ApiTestKit(fx);
        var fr = await k.Regime("paris-test");

        var id = await CreateCapital(k, fr, "巴黎", "Paris", 2.35, 48.85, "1900-01-01", null,
            "Encyclopædia Britannica: Paris");

        var features = await FeaturesOn(k, "1942-01-01");
        var f = features.First(x => x.GetProperty("recordId").GetGuid() == id);

        Assert.Equal("Paris", f.GetProperty("cityName").GetProperty("en").GetString());
        Assert.Equal("巴黎", f.GetProperty("cityName").GetProperty("zh-Hant").GetString());
        Assert.Equal("Point", f.GetProperty("location").GetProperty("type").GetString());
        Assert.Equal("Encyclopædia Britannica: Paris", f.GetProperty("sourceRef").GetString());

        // ValidPeriod：start 有值，end 為 null（開放區間）
        Assert.Equal("1900-01-01", f.GetProperty("validPeriod").GetProperty("start").GetString());
        Assert.Equal(System.Text.Json.JsonValueKind.Null, f.GetProperty("validPeriod").GetProperty("end").ValueKind);
    }

    [Fact]
    public async Task Overlap_rejected_with_409()
    {
        var k = new ApiTestKit(fx);
        var jp = await k.Regime("tokyo-test");

        // 第一筆成功
        await CreateCapital(k, jp, "東京", "Tokyo", 139.7, 35.7, "1900-01-01", "1950-01-01");

        // 重疊期間 → 409
        var res = await k.W.PostAsJsonAsync("/api/v1/capital-records", new
        {
            regimeId = jp,
            cityName = new Dictionary<string, string> { ["zh-Hant"] = "東京", ["en"] = "Tokyo" },
            location = Point(139.7, 35.7),
            validStart = "1920-01-01",
            validEnd = "1940-01-01",
            sourceRef = "待查證",
        });
        Assert.Equal(HttpStatusCode.Conflict, res.StatusCode);
    }

    [Fact]
    public async Task Retract_marks_capital_as_inactive()
    {
        var k = new ApiTestKit(fx);
        var it = await k.Regime("rome-test");

        var id = await CreateCapital(k, it, "羅馬", "Rome", 12.5, 41.9, "1900-01-01", null);

        // 撤回前可見
        var features = await FeaturesOn(k, "1935-01-01");
        Assert.Contains(features, f => f.GetProperty("recordId").GetGuid() == id);

        // 撤回
        var retract = await k.W.PostAsJsonAsync($"/api/v1/capital-records/{id}/retraction",
            new { reason = "測試撤回" });
        await ApiTestKit.Expect(retract, HttpStatusCode.OK);

        // 撤回後不可見
        var after = await FeaturesOn(k, "1935-01-01");
        Assert.DoesNotContain(after, f => f.GetProperty("recordId").GetGuid() == id);
    }

    [Fact]
    public async Task Missing_required_fields_return_400()
    {
        var k = new ApiTestKit(fx);
        // 缺少 regimeId
        var r1 = await k.W.PostAsJsonAsync("/api/v1/capital-records", new
        {
            cityName = new Dictionary<string, string> { ["en"] = "London" },
            location = Point(-0.1, 51.5),
            validStart = "1900-01-01",
        });
        Assert.Equal(HttpStatusCode.BadRequest, r1.StatusCode);

        // 缺少 location
        var regime = await k.Regime("london-test");
        var r2 = await k.W.PostAsJsonAsync("/api/v1/capital-records", new
        {
            regimeId = regime,
            cityName = new Dictionary<string, string> { ["en"] = "London" },
            validStart = "1900-01-01",
        });
        Assert.Equal(HttpStatusCode.BadRequest, r2.StatusCode);
    }
}
