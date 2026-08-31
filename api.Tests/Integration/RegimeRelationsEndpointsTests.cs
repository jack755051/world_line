using System.Net;
using System.Net.Http.Json;

namespace WorldLine.Api.Tests.Integration;

/// <summary>task 2.15：task 2.9（政權持續性關係 CRUD）integration test。</summary>
[Collection(IntegrationTestCollection.Name)]
public class RegimeRelationsEndpointsTests(WorldLineApiFactory factory)
{
    [Fact]
    public async Task GetByRegimeAndYear_缺year回400()
    {
        var client = factory.AnonymousClient();
        var wuId = await client.FindRegimeIdBySelfNameAsync("吳");

        var response = await client.GetAsync($"/api/v1/regimes/{wuId}/relations");

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Fact]
    public async Task Create_關係另一端不能是同一個政權()
    {
        var client = factory.AuthorizedClient();
        var wuId = await client.FindRegimeIdBySelfNameAsync("吳");

        var response = await client.PostAsJsonAsync($"/api/v1/regimes/{wuId}/relations", new
        {
            otherRegimeId = wuId,
            relationType = "alliance",
            startYear = 210,
            endYear = 220,
        });

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        var (_, message, _) = await response.ReadEnvelopeAsync();
        Assert.Equal("RELATION_SAME_REGIME", message);
    }

    [Fact]
    public async Task Create成功後GetByRegimeAndYear查得到()
    {
        var client = factory.AuthorizedClient();
        var wuId = await client.FindRegimeIdBySelfNameAsync("吳");
        var shuId = await client.FindRegimeIdBySelfNameAsync("蜀漢");

        var createResponse = await client.PostAsJsonAsync($"/api/v1/regimes/{wuId}/relations", new
        {
            otherRegimeId = shuId,
            relationType = "alliance",
            startYear = 600,
            endYear = 610,
            description = "測試同盟",
        });
        Assert.Equal(HttpStatusCode.Created, createResponse.StatusCode);

        var getResponse = await client.GetAsync($"/api/v1/regimes/{wuId}/relations?year=605");
        var (_, _, data) = await getResponse.ReadEnvelopeAsync();
        Assert.Contains(data.EnumerateArray(), r => r.GetProperty("relationType").GetString() == "alliance");
    }
}
