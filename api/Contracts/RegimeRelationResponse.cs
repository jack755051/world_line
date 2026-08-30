using NetTopologySuite.Geometries;

namespace WorldLine.Api.Contracts;

/// <summary>
/// `GET /api/v1/regimes/{regimeId}/relations`／`POST /api/v1/regimes/{regimeId}/relations`
/// 的回應形狀（task 2.9）。**沒有 `?locale=`**：`relation_type`/`description` 是 PRD §6
/// 明確列在「次要/輔助內容，維持待評估、不現在處理」的翻譯範圍外（見該段落），跟 task
/// 2.10 的 `sections` 是「這個任務動工前才決定」不同——這裡是 PRD 已經先拍板過的，不用
/// 這個任務重新決定。
/// </summary>
public class RegimeRelationResponse
{
    public required Guid Id { get; init; }
    public required Guid RegimeAId { get; init; }
    public required Guid RegimeBId { get; init; }
    public required string RelationType { get; init; }
    public required int StartYear { get; init; }
    public required int EndYear { get; init; }
    public string? Description { get; init; }
    public MultiLineString? Route { get; init; }
}
