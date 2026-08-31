using System.Net;
using System.Net.Http.Json;

namespace WorldLine.Api.Tests.Integration;

/// <summary>task 2.15：task 2.4（政權查詢）＋ task 2.5（政權寫入）integration test。</summary>
[Collection(IntegrationTestCollection.Name)]
public class RegimesEndpointsTests(WorldLineApiFactory factory)
{
    [Fact]
    public async Task GetAll_回傳種子資料裡的政權()
    {
        var client = factory.AnonymousClient();

        var response = await client.GetAsync("/api/v1/regimes");
        var (statusCode, message, data) = await response.ReadEnvelopeAsync();

        Assert.Equal((int)HttpStatusCode.OK, statusCode);
        Assert.Equal("FETCH_SUCCESS", message);
        Assert.Contains(data.EnumerateArray(), r => r.GetProperty("selfName").GetString() == "魏");
    }

    [Fact]
    public async Task GetById_不存在的政權回404()
    {
        var client = factory.AnonymousClient();

        var response = await client.GetAsync($"/api/v1/regimes/{Guid.NewGuid()}");

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        var (_, message, _) = await response.ReadEnvelopeAsync();
        Assert.Equal("REGIME_NOT_FOUND", message);
    }

    [Fact]
    public async Task Create_缺X_API_Key回401()
    {
        var client = factory.AnonymousClient();

        var response = await client.PostAsJsonAsync("/api/v1/regimes", new { selfName = "測試政權" });

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    [Fact]
    public async Task Create_獨立建國_一律從active起步()
    {
        var client = factory.AuthorizedClient();

        var response = await client.PostAsJsonAsync("/api/v1/regimes", new { selfName = $"測試政權-{Guid.NewGuid():N}" });

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        var (_, message, data) = await response.ReadEnvelopeAsync();
        Assert.Equal("CREATE_SUCCESS", message);
        Assert.Equal("active", data.GetProperty("status").GetString());
    }

    [Fact]
    public async Task Create_predecessor已經conquered時擋下()
    {
        var client = factory.AuthorizedClient();
        var wuId = await client.FindRegimeIdBySelfNameAsync("吳"); // 種子資料：吳已經是 conquered

        var response = await client.PostAsJsonAsync("/api/v1/regimes", new
        {
            selfName = $"測試政權-{Guid.NewGuid():N}",
            predecessorRegimeId = wuId,
            originTransitionType = "succeeded",
        });

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        var (_, message, _) = await response.ReadEnvelopeAsync();
        Assert.Equal("PREDECESSOR_ALREADY_CONQUERED", message);
    }

    [Fact]
    public async Task Update_非法轉換擋下()
    {
        var client = factory.AuthorizedClient();
        var hanId = await client.FindRegimeIdBySelfNameAsync("漢"); // 種子資料：漢已經是 split，不能再轉回 active

        var response = await client.PatchAsJsonAsync($"/api/v1/regimes/{hanId}", new { status = "active" });

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        var (_, message, _) = await response.ReadEnvelopeAsync();
        Assert.Equal("INVALID_STATUS_TRANSITION", message);
    }

    [Fact]
    public async Task Update_合法轉成conquered_必須帶destroyedByRegimeId()
    {
        var client = factory.AuthorizedClient();
        var jinId = await client.FindRegimeIdBySelfNameAsync("晉");

        // 先建一個乾淨的測試政權（active），避免動到種子資料本身的狀態影響其他測試。
        var createResponse = await client.PostAsJsonAsync("/api/v1/regimes", new { selfName = $"測試政權-{Guid.NewGuid():N}" });
        var (_, _, created) = await createResponse.ReadEnvelopeAsync();
        var testRegimeId = created.GetProperty("id").GetGuid();

        var missingReasonResponse = await client.PatchAsJsonAsync($"/api/v1/regimes/{testRegimeId}", new { status = "conquered" });
        Assert.Equal(HttpStatusCode.BadRequest, missingReasonResponse.StatusCode);
        var (_, missingReasonMessage, _) = await missingReasonResponse.ReadEnvelopeAsync();
        Assert.Equal("DESTROYED_BY_REGIME_REQUIRED", missingReasonMessage);

        var successResponse = await client.PatchAsJsonAsync($"/api/v1/regimes/{testRegimeId}",
            new { status = "conquered", destroyedByRegimeId = jinId });
        Assert.Equal(HttpStatusCode.OK, successResponse.StatusCode);
        var (_, successMessage, data) = await successResponse.ReadEnvelopeAsync();
        Assert.Equal("UPDATE_SUCCESS", successMessage);
        Assert.Equal("conquered", data.GetProperty("status").GetString());
    }
}
