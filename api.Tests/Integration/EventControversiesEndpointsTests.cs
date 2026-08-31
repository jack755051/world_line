using System.Net;
using System.Net.Http.Json;

namespace WorldLine.Api.Tests.Integration;

/// <summary>task 2.15：task 2.13（事件爭議點）integration test。</summary>
[Collection(IntegrationTestCollection.Name)]
public class EventControversiesEndpointsTests(WorldLineApiFactory factory)
{
    [Fact]
    public async Task GetByEvent_不存在的事件回404()
    {
        var response = await factory.AnonymousClient().GetAsync("/api/v1/events/event-does-not-exist/controversies");

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }

    [Fact]
    public async Task GetByEvent_漢禪魏事件含正統性爭議點()
    {
        var response = await factory.AnonymousClient().GetAsync("/api/v1/events/event-han-abdicates-wei-220/controversies");
        var (_, _, data) = await response.ReadEnvelopeAsync();

        Assert.Contains(data.EnumerateArray(), c => c.GetProperty("topic").GetString()!.Contains("正統"));
    }

    [Fact]
    public async Task Create成功後GetByEvent查得到()
    {
        var client = factory.AuthorizedClient();

        var createResponse = await client.PostAsJsonAsync("/api/v1/events/event-chibi-208/controversies", new
        {
            topic = "測試爭議點",
            neutralDescription = "測試中立敘述",
        });
        Assert.Equal(HttpStatusCode.Created, createResponse.StatusCode);
        var (_, message, _) = await createResponse.ReadEnvelopeAsync();
        Assert.Equal("CREATE_SUCCESS", message);

        var getResponse = await client.GetAsync("/api/v1/events/event-chibi-208/controversies");
        var (_, _, data) = await getResponse.ReadEnvelopeAsync();
        Assert.Contains(data.EnumerateArray(), c => c.GetProperty("topic").GetString() == "測試爭議點");
    }
}
