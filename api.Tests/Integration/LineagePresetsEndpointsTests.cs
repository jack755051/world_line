using System.Net;

namespace WorldLine.Api.Tests.Integration;

/// <summary>task 2.15：task 2.8（史觀主線 preset 查詢）integration test。</summary>
[Collection(IntegrationTestCollection.Name)]
public class LineagePresetsEndpointsTests(WorldLineApiFactory factory)
{
    [Fact]
    public async Task GetAll_回傳兩個preset_只有一個是預設()
    {
        var response = await factory.AnonymousClient().GetAsync("/api/v1/lineage-presets");
        var (_, _, data) = await response.ReadEnvelopeAsync();

        var presets = data.EnumerateArray().ToList();
        Assert.Equal(2, presets.Count);
        Assert.Single(presets, p => p.GetProperty("isDefault").GetBoolean());
    }

    [Fact]
    public async Task GetRegimes_不存在的preset回404()
    {
        var response = await factory.AnonymousClient().GetAsync($"/api/v1/lineage-presets/{Guid.NewGuid()}/regimes");

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        var (_, message, _) = await response.ReadEnvelopeAsync();
        Assert.Equal("LINEAGE_PRESET_NOT_FOUND", message);
    }

    [Fact]
    public async Task GetRegimes_預設史觀主線是漢魏晉三筆依序排列()
    {
        var listResponse = await factory.AnonymousClient().GetAsync("/api/v1/lineage-presets");
        var (_, _, presets) = await listResponse.ReadEnvelopeAsync();
        var defaultPresetId = presets.EnumerateArray()
            .Single(p => p.GetProperty("isDefault").GetBoolean())
            .GetProperty("id").GetGuid();

        var response = await factory.AnonymousClient().GetAsync($"/api/v1/lineage-presets/{defaultPresetId}/regimes");
        var (_, _, data) = await response.ReadEnvelopeAsync();

        var names = data.EnumerateArray().Select(r => r.GetProperty("selfName").GetString()).ToList();
        Assert.Equal(["漢", "魏", "晉"], names);
    }
}
