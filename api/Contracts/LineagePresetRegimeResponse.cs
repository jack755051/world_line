namespace WorldLine.Api.Contracts;

/// <summary>
/// `GET /api/v1/lineage-presets/{id}/regimes` 的回應形狀（task 2.8）——preset 底下依
/// `sort_order` 排序的政權序列。政權欄位刻意跟 `RegimeResponse` 同一組（`SelfName`/
/// `Status`/`PredecessorRegimeId`/`OriginTransitionType`/`DestroyedByRegimeId`），
/// 不是重新設計一套——這是任務 3.9（政權狀態轉換視覺呈現）畫「主線上相鄰兩個政權之間
/// 是禪讓還是滅亡」需要的同一批資料，沒有理由跟既有的政權摘要契約不一致。**不含代稱
/// 清單**，跟 `RegimeResponse` 同樣的理由（`alias_type` 受控值是 task 2.9a 的未解開放
/// 問題，見該端點的說明）。
/// </summary>
public class LineagePresetRegimeResponse
{
    public required int SortOrder { get; init; }
    public required Guid Id { get; init; }
    public required string SelfName { get; init; }
    public required string Status { get; init; }
    public required Guid? PredecessorRegimeId { get; init; }
    public required string? OriginTransitionType { get; init; }
    public required Guid? DestroyedByRegimeId { get; init; }
}
