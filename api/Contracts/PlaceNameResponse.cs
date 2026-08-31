namespace WorldLine.Api.Contracts;

/// <summary>`GET /api/v1/place-names`／`GET /api/v1/place-names/{id}` 的回應形狀
/// （task 2.9b，憲法 §6 地名雙軌）。`ModernName` 可為 `null`——古今同名時依規範留空
/// （見 `SeedData.cs` 洛陽/成都的例子），不是資料缺漏。`StartYear`/`EndYear` 也可能
/// 同時為 `null`——`valid_period` 本身整欄可為 `NULL`，代表這個名稱的使用期間尚未
/// 考證清楚，不是「從西元 0 年用到永遠」。</summary>
public class PlaceNameResponse
{
    public required Guid Id { get; init; }
    public required string HistoricalName { get; init; }
    public string? ModernName { get; init; }
    public int? StartYear { get; init; }
    public int? EndYear { get; init; }
}
