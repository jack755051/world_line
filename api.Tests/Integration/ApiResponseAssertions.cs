using System.Net.Http.Json;
using System.Text.Json;

namespace WorldLine.Api.Tests.Integration;

/// <summary>
/// task 2.15：所有 integration test 共用的小工具——這個 API 統一包裝格式是
/// `{statusCode, message, data}`（task 2.0），這裡集中處理「拆包裝、拿 message 代碼、
/// 拿 data」，避免每個測試類別各自重複寫一次 JSON 解析。刻意用 `JsonElement` 而不是
/// 對回每個 controller 的強型別 Contracts 類別——那些型別（例如
/// `HistoricalEventResponse`）在序列化時吃 `Program.cs` 掛的 `GeoJsonConverterFactory`
/// 才能正確處理幾何欄位，測試端要重建同一組 `JsonSerializerOptions` 才能對稱反序列化，
/// 不如直接用 `JsonElement` 讀取測試實際關心的那幾個欄位，兩邊都不用維護一份重複的
/// 序列化設定。
/// </summary>
public static class ApiResponseAssertions
{
    public static async Task<(int StatusCode, string? Message, JsonElement Data)> ReadEnvelopeAsync(
        this HttpResponseMessage response)
    {
        var json = await response.Content.ReadFromJsonAsync<JsonElement>();
        var statusCode = json.GetProperty("statusCode").GetInt32();
        var message = json.TryGetProperty("message", out var m) && m.ValueKind != JsonValueKind.Null
            ? m.GetString()
            : null;
        var data = json.GetProperty("data");
        return (statusCode, message, data);
    }

    /// <summary>依 `selfName` 從 `GET /api/v1/regimes` 找出政權 id——seed 資料的
    /// `Regime.Id` 是 `Guid.NewGuid()` 隨機產生，不是固定值，每次測試執行都要重新查，
    /// 不能寫死 GUID 字面值。</summary>
    public static async Task<Guid> FindRegimeIdBySelfNameAsync(this HttpClient client, string selfName)
    {
        var response = await client.GetAsync("/api/v1/regimes");
        var (_, _, data) = await response.ReadEnvelopeAsync();

        foreach (var regime in data.EnumerateArray())
        {
            if (regime.GetProperty("selfName").GetString() == selfName)
            {
                return regime.GetProperty("id").GetGuid();
            }
        }

        throw new InvalidOperationException($"種子資料裡找不到自稱名稱是「{selfName}」的政權");
    }
}
