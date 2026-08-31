using System.Net;
using System.Net.Http.Json;

namespace WorldLine.Api.Tests.Integration;

/// <summary>task 2.15：task 2.6（疆域查詢）＋ task 2.7（疆域寫入/修正）integration test。</summary>
[Collection(IntegrationTestCollection.Name)]
public class TerritoriesEndpointsTests(WorldLineApiFactory factory)
{
    [Fact]
    public async Task GetByYear_缺year回400()
    {
        var response = await factory.AnonymousClient().GetAsync("/api/v1/territories");

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        var (_, message, _) = await response.ReadEnvelopeAsync();
        Assert.Equal("YEAR_REQUIRED", message);
    }

    [Fact]
    public async Task GetByYear_year225回三國三方疆域()
    {
        var response = await factory.AnonymousClient().GetAsync("/api/v1/territories?year=225");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var (_, _, data) = await response.ReadEnvelopeAsync();
        Assert.Equal("FeatureCollection", data.GetProperty("type").GetString());
        Assert.Equal(3, data.GetProperty("features").GetArrayLength()); // 魏/蜀漢/吳
    }

    [Fact]
    public async Task Create與Correct_I5版本鏈完整流程()
    {
        var client = factory.AuthorizedClient();
        var wuId = await client.FindRegimeIdBySelfNameAsync("吳");

        var createResponse = await client.PostAsJsonAsync($"/api/v1/regimes/{wuId}/territories", new
        {
            startYear = 500,
            endYear = 510,
            geom = new
            {
                type = "MultiPolygon",
                coordinates = new[] { new[] { new[] { new[] { 130.0, 20.0 }, new[] { 130.0, 21.0 }, new[] { 131.0, 21.0 }, new[] { 131.0, 20.0 }, new[] { 130.0, 20.0 } } } },
            },
        });
        Assert.Equal(HttpStatusCode.Created, createResponse.StatusCode);
        var (_, createMessage, created) = await createResponse.ReadEnvelopeAsync();
        Assert.Equal("CREATE_SUCCESS", createMessage);
        var territoryId = created.GetProperty("properties").GetProperty("id").GetGuid();

        // 修正：endYear 沒有晚於 startYear -> 400
        var invalidCorrect = await client.PatchAsJsonAsync($"/api/v1/territories/{territoryId}/correct", new
        {
            startYear = 510,
            endYear = 500,
            geom = new { type = "MultiPolygon", coordinates = new[] { new[] { new[] { new[] { 130.0, 20.0 }, new[] { 130.0, 21.0 }, new[] { 131.0, 21.0 }, new[] { 131.0, 20.0 }, new[] { 130.0, 20.0 } } } } },
            correctionReason = "測試",
        });
        Assert.Equal(HttpStatusCode.BadRequest, invalidCorrect.StatusCode);
        var (_, invalidMessage, _) = await invalidCorrect.ReadEnvelopeAsync();
        Assert.Equal("TERRITORY_END_BEFORE_START", invalidMessage);

        // 合法修正：新版本取代舊版本
        var correctResponse = await client.PatchAsJsonAsync($"/api/v1/territories/{territoryId}/correct", new
        {
            startYear = 501,
            endYear = 509,
            geom = new { type = "MultiPolygon", coordinates = new[] { new[] { new[] { new[] { 130.0, 20.0 }, new[] { 130.0, 22.0 }, new[] { 132.0, 22.0 }, new[] { 132.0, 20.0 }, new[] { 130.0, 20.0 } } } } },
            correctionReason = "測試修正邊界",
        });
        Assert.Equal(HttpStatusCode.OK, correctResponse.StatusCode);
        var (_, correctMessage, corrected) = await correctResponse.ReadEnvelopeAsync();
        Assert.Equal("UPDATE_SUCCESS", correctMessage);
        Assert.Equal(501, corrected.GetProperty("properties").GetProperty("startYear").GetInt32());

        // 2026-08-31 修正：對已經被修正過的舊版本（territoryId，鏈上第 1 筆）再修正一次
        // 應該成功——沿著 SupersededBy 追到鏈上真正最新的那一筆（第 2 筆，剛剛修正出來
        // 的版本）套用這次修正，鏈延伸成 3 筆，不會分岔也不會被拒絕。
        var secondCorrectResponse = await client.PatchAsJsonAsync($"/api/v1/territories/{territoryId}/correct", new
        {
            startYear = 502,
            endYear = 508,
            geom = new { type = "MultiPolygon", coordinates = new[] { new[] { new[] { new[] { 130.0, 20.0 }, new[] { 130.0, 23.0 }, new[] { 133.0, 23.0 }, new[] { 133.0, 20.0 }, new[] { 130.0, 20.0 } } } } },
            correctionReason = "再修一次邊界",
        });
        Assert.Equal(HttpStatusCode.OK, secondCorrectResponse.StatusCode);
        var (_, secondMessage, secondCorrected) = await secondCorrectResponse.ReadEnvelopeAsync();
        Assert.Equal("UPDATE_SUCCESS", secondMessage);
        Assert.Equal(502, secondCorrected.GetProperty("properties").GetProperty("startYear").GetInt32());

        // GET 只看得到鏈上最新（第 3 筆），第 1/2 筆都已被取代，不會重複出現。
        var wuTerritories = await client.GetAsync($"/api/v1/regimes/{wuId}/territories");
        var (_, _, wuData) = await wuTerritories.ReadEnvelopeAsync();
        var wuIds = wuData.GetProperty("features").EnumerateArray()
            .Select(f => f.GetProperty("properties").GetProperty("id").GetGuid())
            .ToList();
        Assert.Contains(secondCorrected.GetProperty("properties").GetProperty("id").GetGuid(), wuIds);
        Assert.DoesNotContain(territoryId, wuIds);
    }
}
