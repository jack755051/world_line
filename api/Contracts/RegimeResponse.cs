namespace WorldLine.Api.Contracts;

/// <summary>
/// `GET /api/v1/regimes`／`GET /api/v1/regimes/{id}` 的回應形狀。**不含代稱清單**——雖然
/// PRD §7 契約表原本寫「含自稱名稱、狀態、代稱清單」，但代稱（`regime_aliases`）的
/// `alias_type` 受控值還沒拍板（task 2.9a 的開放問題），這裡刻意不提前碰，等 2.9a
/// 定案代稱查詢本身要長怎樣再一起做，不是遺漏。
/// </summary>
public class RegimeResponse
{
    public required Guid Id { get; init; }
    public required string SelfName { get; init; }
    public required string Status { get; init; }
    public required Guid? PredecessorRegimeId { get; init; }
    public required string? OriginTransitionType { get; init; }
    public required Guid? DestroyedByRegimeId { get; init; }
}
