namespace WorldLine.Api.Tests.Integration;

/// <summary>task 2.15：task 2.11（事件類型標籤）唯讀端點 integration test。</summary>
[Collection(IntegrationTestCollection.Name)]
public class EventTagsEndpointsTests(WorldLineApiFactory factory)
{
    [Fact]
    public async Task GetAll_回傳種子資料的三個標籤()
    {
        var response = await factory.AnonymousClient().GetAsync("/api/v1/event-tags");
        var (_, _, data) = await response.ReadEnvelopeAsync();

        var tagNames = data.EnumerateArray().Select(t => t.GetProperty("tagName").GetString()).ToList();
        Assert.Equal(["戰爭", "政權更替", "神話援引"], tagNames);
    }
}
