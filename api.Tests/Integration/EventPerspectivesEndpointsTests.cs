using System.Net;
using System.Net.Http.Json;

namespace WorldLine.Api.Tests.Integration;

/// <summary>task 2.15：task 2.12（觀察者類別＋多重視角敘事）integration test。</summary>
[Collection(IntegrationTestCollection.Name)]
public class EventPerspectivesEndpointsTests(WorldLineApiFactory factory)
{
    [Fact]
    public async Task ObserverCategories_GetAll_至少有一筆種子資料()
    {
        var response = await factory.AnonymousClient().GetAsync("/api/v1/observer-categories");
        var (_, _, data) = await response.ReadEnvelopeAsync();

        Assert.NotEmpty(data.EnumerateArray());
    }

    [Fact]
    public async Task GetByEvent_不存在的事件回404()
    {
        var response = await factory.AnonymousClient().GetAsync("/api/v1/events/event-does-not-exist/perspectives");

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        var (_, message, _) = await response.ReadEnvelopeAsync();
        Assert.Equal("EVENT_NOT_FOUND", message);
    }

    [Fact]
    public async Task GetByEvent_赤壁之戰至少有兩筆視角()
    {
        // 種子資料：赤壁之戰讓蜀漢、東吳都留下視角（task 3.7 AC#3 的驗證錨點）。
        var response = await factory.AnonymousClient().GetAsync("/api/v1/events/event-chibi-208/perspectives");
        var (_, _, data) = await response.ReadEnvelopeAsync();

        Assert.True(data.GetArrayLength() >= 2);
    }

    [Fact]
    public async Task Create_regimeId跟observerCategoryId都沒填時擋下()
    {
        var client = factory.AuthorizedClient();

        var response = await client.PostAsJsonAsync("/api/v1/events/event-chibi-208/perspectives", new
        {
            localName = "測試視角",
            narrativeSummary = "測試敘事",
        });

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        var (_, message, _) = await response.ReadEnvelopeAsync();
        Assert.Equal("PERSPECTIVE_PARTY_REQUIRED", message);
    }

    [Fact]
    public async Task Create成功後GetByEvent查得到()
    {
        var client = factory.AuthorizedClient();
        var weiId = await client.FindRegimeIdBySelfNameAsync("魏");

        var createResponse = await client.PostAsJsonAsync("/api/v1/events/event-chibi-208/perspectives", new
        {
            regimeId = weiId,
            localName = "測試魏方視角",
            narrativeSummary = "測試敘事內容",
        });
        Assert.Equal(HttpStatusCode.Created, createResponse.StatusCode);

        var getResponse = await client.GetAsync("/api/v1/events/event-chibi-208/perspectives");
        var (_, _, data) = await getResponse.ReadEnvelopeAsync();
        Assert.Contains(data.EnumerateArray(), p => p.GetProperty("localName").GetString() == "測試魏方視角");
    }
}
