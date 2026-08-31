using System.Net;

namespace WorldLine.Api.Tests.Integration;

/// <summary>task 2.15：task 2.9b（地名雙軌查詢）integration test。</summary>
[Collection(IntegrationTestCollection.Name)]
public class PlaceNamesEndpointsTests(WorldLineApiFactory factory)
{
    [Fact]
    public async Task GetByYear_缺year回400()
    {
        var response = await factory.AnonymousClient().GetAsync("/api/v1/place-names");

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        var (_, message, _) = await response.ReadEnvelopeAsync();
        Assert.Equal("YEAR_REQUIRED", message);
    }

    [Fact]
    public async Task GetByYear_year100只回雒陽()
    {
        var response = await factory.AnonymousClient().GetAsync("/api/v1/place-names?year=100");
        var (_, _, data) = await response.ReadEnvelopeAsync();

        var names = data.EnumerateArray().Select(p => p.GetProperty("historicalName").GetString()).ToList();
        Assert.Equal(["雒陽"], names);
    }

    [Fact]
    public async Task GetById_不存在回404()
    {
        var response = await factory.AnonymousClient().GetAsync($"/api/v1/place-names/{Guid.NewGuid()}");

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        var (_, message, _) = await response.ReadEnvelopeAsync();
        Assert.Equal("PLACE_NAME_NOT_FOUND", message);
    }

    [Fact]
    public async Task GetById_成功時含modernName雙軌欄位()
    {
        var listResponse = await factory.AnonymousClient().GetAsync("/api/v1/place-names?year=100");
        var (_, _, list) = await listResponse.ReadEnvelopeAsync();
        var id = list.EnumerateArray().Single().GetProperty("id").GetGuid();

        var response = await factory.AnonymousClient().GetAsync($"/api/v1/place-names/{id}");
        var (_, _, data) = await response.ReadEnvelopeAsync();

        Assert.Equal("雒陽", data.GetProperty("historicalName").GetString());
        Assert.Equal("洛陽", data.GetProperty("modernName").GetString());
    }
}
