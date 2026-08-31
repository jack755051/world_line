using System.Text.Json;

namespace WorldLine.Api.Tests.Integration;

/// <summary>
/// task 2.15：「ASP.NET 產生的 OpenAPI 必須包含所有已實作端點、request/response
/// schema 與主要狀態碼」——動工前這條完全不成立：這個 API 直到 2.15 之前都沒有任何
/// `[ProducesResponseType]` 標註，`AddOpenApi()`/`MapOpenApi()`（ASP.NET Core 內建的
/// OpenAPI 產生器，不是 Swashbuckle）只能從 action 的宣告回傳型別推論出唯一一個
/// 「預設」狀態碼，完全不知道 `NotFound()`/`BadRequest()`/`Conflict()` 這些分支的存在
/// ——這個測試檔案同時是 2.15 本身的驗收依據，也是之後新增端點忘記補
/// `[ProducesResponseType]` 時的迴歸警報。
///
/// **一個容易踩的坑，記錄下來**：一旦對某個 action 加了任何一個
/// `[ProducesResponseType]`，ASP.NET 就完全停止自動推論「預設成功狀態碼」——不是
/// 疊加關係，是取代關係。半吊子只加錯誤狀態碼（例如只加 404）會讓原本存在的 200
/// 反而從文件裡消失，比完全不加還糟。所以每個 action 只要出現一個
/// `[ProducesResponseType]`，就必須把該 action 實際會回傳的**所有**狀態碼（含成功）
/// 都列全，這裡逐一驗證，不只驗證「有沒有 400/404」，也驗證「200/201 還在」。
/// </summary>
[Collection(IntegrationTestCollection.Name)]
public class OpenApiContractTests(WorldLineApiFactory factory)
{
    private readonly Lazy<Task<JsonDocument>> document = new(async () =>
    {
        var response = await factory.AnonymousClient().GetAsync("/openapi/v1.json");
        response.EnsureSuccessStatusCode();
        return JsonDocument.Parse(await response.Content.ReadAsStringAsync());
    });

    public static readonly TheoryData<string, string, int[]> ExpectedEndpoints = new()
    {
        // task 2.4/2.5
        { "get", "/api/v1/regimes", [200] },
        { "post", "/api/v1/regimes", [201, 400, 401] },
        { "get", "/api/v1/regimes/{id}", [200, 404] },
        { "patch", "/api/v1/regimes/{id}", [200, 400, 401, 404] },
        // task 2.6/2.7
        { "get", "/api/v1/territories", [200, 400] },
        { "get", "/api/v1/regimes/{regimeId}/territories", [200, 404] },
        { "post", "/api/v1/regimes/{regimeId}/territories", [201, 400, 401, 404] },
        { "patch", "/api/v1/territories/{id}/correct", [200, 400, 401, 404] },
        // task 2.8
        { "get", "/api/v1/lineage-presets", [200] },
        { "get", "/api/v1/lineage-presets/{id}/regimes", [200, 404] },
        // task 2.9
        { "get", "/api/v1/regimes/{regimeId}/relations", [200, 400, 404] },
        { "post", "/api/v1/regimes/{regimeId}/relations", [201, 400, 401, 404] },
        // task 2.9a
        { "get", "/api/v1/regimes/{regimeId}/aliases", [200, 404] },
        { "post", "/api/v1/regimes/{regimeId}/aliases", [201, 400, 401, 404] },
        // task 2.9b
        { "get", "/api/v1/place-names", [200, 400] },
        { "get", "/api/v1/place-names/{id}", [200, 404] },
        // task 2.10/2.11
        { "get", "/api/v1/events", [200, 400] },
        { "get", "/api/v1/events/{id}", [200, 404] },
        { "post", "/api/v1/events", [201, 400, 401, 409] },
        { "get", "/api/v1/regimes/{regimeId}/events", [200, 404] },
        { "get", "/api/v1/event-tags", [200] },
        // task 2.12
        { "get", "/api/v1/observer-categories", [200] },
        { "get", "/api/v1/events/{eventId}/perspectives", [200, 404] },
        { "post", "/api/v1/events/{eventId}/perspectives", [201, 400, 401, 404] },
        // task 2.13
        { "get", "/api/v1/events/{eventId}/controversies", [200, 404] },
        { "post", "/api/v1/events/{eventId}/controversies", [201, 400, 401, 404] },
        // task 2.3（雖然不在 2.15 明列的 2.4-2.13 範圍內，已實作的端點沒有理由排除在外）
        { "get", "/api/v1/reign-eras", [200, 400] },
        { "get", "/api/v1/regimes/{regimeId}/reign-eras", [200, 404] },
    };

    [Theory]
    [MemberData(nameof(ExpectedEndpoints))]
    public async Task 每個已實作端點都有文件且列出全部主要狀態碼(string verb, string path, int[] expectedCodes)
    {
        var doc = await document.Value;

        Assert.True(doc.RootElement.GetProperty("paths").TryGetProperty(path, out var pathItem),
            $"OpenAPI 文件缺少路徑 {path}");
        Assert.True(pathItem.TryGetProperty(verb, out var operation),
            $"OpenAPI 文件的 {path} 缺少 {verb.ToUpperInvariant()} 方法");

        var actualCodes = operation.GetProperty("responses").EnumerateObject()
            .Select(p => int.Parse(p.Name))
            .OrderBy(c => c)
            .ToArray();

        Assert.Equal(expectedCodes.OrderBy(c => c), actualCodes);
    }

    [Theory]
    [MemberData(nameof(ExpectedEndpoints))]
    public async Task 每個非2xx回應都有schema不是空的(string verb, string path, int[] expectedCodes)
    {
        var doc = await document.Value;
        var operation = doc.RootElement.GetProperty("paths").GetProperty(path).GetProperty(verb);
        var responses = operation.GetProperty("responses");

        foreach (var code in expectedCodes.Where(c => c >= 400))
        {
            var response = responses.GetProperty(code.ToString());
            Assert.True(response.TryGetProperty("content", out var content) && content.EnumerateObject().Any(),
                $"{verb.ToUpperInvariant()} {path} 的 {code} 回應沒有 content schema");
        }
    }
}
