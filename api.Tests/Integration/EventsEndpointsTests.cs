using System.Net;
using System.Net.Http.Json;

namespace WorldLine.Api.Tests.Integration;

/// <summary>task 2.15：task 2.10（事件骨幹 CRUD）＋ task 2.11（事件標籤）integration test。</summary>
[Collection(IntegrationTestCollection.Name)]
public class EventsEndpointsTests(WorldLineApiFactory factory)
{
    [Fact]
    public async Task GetByYear_缺year回400()
    {
        var response = await factory.AnonymousClient().GetAsync("/api/v1/events");

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Fact]
    public async Task GetByYear_year208回赤壁之戰()
    {
        var response = await factory.AnonymousClient().GetAsync("/api/v1/events?year=208");
        var (_, _, data) = await response.ReadEnvelopeAsync();

        Assert.Contains(data.EnumerateArray(), e => e.GetProperty("id").GetString() == "event-chibi-208");
    }

    [Fact]
    public async Task GetById_赤壁之戰含戰爭tag()
    {
        var response = await factory.AnonymousClient().GetAsync("/api/v1/events/event-chibi-208");
        var (_, _, data) = await response.ReadEnvelopeAsync();

        Assert.Contains(data.GetProperty("tags").EnumerateArray(), t => t.GetProperty("tagName").GetString() == "戰爭");
    }

    [Fact]
    public async Task GetById_不存在回404()
    {
        var response = await factory.AnonymousClient().GetAsync("/api/v1/events/event-does-not-exist");

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        var (_, message, _) = await response.ReadEnvelopeAsync();
        Assert.Equal("EVENT_NOT_FOUND", message);
    }

    [Fact]
    public async Task Create_錯誤EDTF格式回400()
    {
        var client = factory.AuthorizedClient();
        var id = $"event-test-{Guid.NewGuid():N}";

        var response = await client.PostAsJsonAsync("/api/v1/events", new
        {
            id,
            name = "測試事件",
            startEdtf = "not-a-date",
            endEdtf = "not-a-date",
        });

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        var (_, message, _) = await response.ReadEnvelopeAsync();
        Assert.Equal("INVALID_EDTF", message);
    }

    [Fact]
    public async Task Create_結束早於開始回400()
    {
        var client = factory.AuthorizedClient();
        var id = $"event-test-{Guid.NewGuid():N}";

        var response = await client.PostAsJsonAsync("/api/v1/events", new
        {
            id,
            name = "測試事件",
            startEdtf = "0300",
            endEdtf = "0290",
        });

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        var (_, message, _) = await response.ReadEnvelopeAsync();
        Assert.Equal("EVENT_END_BEFORE_START", message);
    }

    [Fact]
    public async Task Create_重複id回409()
    {
        var client = factory.AuthorizedClient();

        var response = await client.PostAsJsonAsync("/api/v1/events", new
        {
            id = "event-chibi-208", // 種子資料已存在
            name = "測試事件",
            startEdtf = "0300",
            endEdtf = "0300",
        });

        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
        var (_, message, _) = await response.ReadEnvelopeAsync();
        Assert.Equal("EVENT_ID_ALREADY_EXISTS", message);
    }

    [Fact]
    public async Task Create_帶不存在的tagId回400()
    {
        var client = factory.AuthorizedClient();
        var id = $"event-test-{Guid.NewGuid():N}";

        var response = await client.PostAsJsonAsync("/api/v1/events", new
        {
            id,
            name = "測試事件",
            startEdtf = "0300",
            endEdtf = "0300",
            tagIds = new[] { 999999 },
        });

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        var (_, message, _) = await response.ReadEnvelopeAsync();
        Assert.Equal("EVENT_TAG_NOT_FOUND", message);
    }

    [Fact]
    public async Task Create成功_回應含指定的tags()
    {
        var client = factory.AuthorizedClient();
        var id = $"event-test-{Guid.NewGuid():N}";

        var response = await client.PostAsJsonAsync("/api/v1/events", new
        {
            id,
            name = "測試事件",
            startEdtf = "0300",
            endEdtf = "0300",
            tagIds = new[] { 1 }, // 戰爭
        });

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        var (_, message, data) = await response.ReadEnvelopeAsync();
        Assert.Equal("CREATE_SUCCESS", message);
        Assert.Contains(data.GetProperty("tags").EnumerateArray(), t => t.GetProperty("tagName").GetString() == "戰爭");
    }
}
