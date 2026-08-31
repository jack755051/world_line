using System.Net;
using System.Net.Http.Json;

namespace WorldLine.Api.Tests.Integration;

/// <summary>task 2.15：task 2.9a（政權代稱 CRUD）integration test。</summary>
[Collection(IntegrationTestCollection.Name)]
public class RegimeAliasesEndpointsTests(WorldLineApiFactory factory)
{
    [Fact]
    public async Task GetByRegime_不存在的政權回404()
    {
        var response = await factory.AnonymousClient().GetAsync($"/api/v1/regimes/{Guid.NewGuid()}/aliases");

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        var (_, message, _) = await response.ReadEnvelopeAsync();
        Assert.Equal("REGIME_NOT_FOUND", message);
    }

    [Fact]
    public async Task Create_aliasType不是受控值時擋下()
    {
        var client = factory.AuthorizedClient();
        var wuId = await client.FindRegimeIdBySelfNameAsync("吳");

        var response = await client.PostAsJsonAsync($"/api/v1/regimes/{wuId}/aliases", new
        {
            aliasName = "測試代稱",
            aliasType = "not-a-real-type",
        });

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        var (_, message, _) = await response.ReadEnvelopeAsync();
        Assert.Equal("INVALID_ALIAS_TYPE", message);
    }

    [Fact]
    public async Task Create成功後GetByRegime查得到()
    {
        var client = factory.AuthorizedClient();
        var wuId = await client.FindRegimeIdBySelfNameAsync("吳");

        var createResponse = await client.PostAsJsonAsync($"/api/v1/regimes/{wuId}/aliases", new { aliasName = "測試代稱" });
        Assert.Equal(HttpStatusCode.Created, createResponse.StatusCode);

        var getResponse = await client.GetAsync($"/api/v1/regimes/{wuId}/aliases");
        var (_, _, data) = await getResponse.ReadEnvelopeAsync();
        Assert.Contains(data.EnumerateArray(), a => a.GetProperty("aliasName").GetString() == "測試代稱");
    }
}
