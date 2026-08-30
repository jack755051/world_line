using NetTopologySuite.Geometries;

namespace WorldLine.Api.Contracts;

/// <summary>
/// `POST /api/v1/regimes/{regimeId}/relations` 的請求形狀（task 2.9）。**故意不重複
/// `regimeAId`——路由裡的 `{regimeId}` 就是關係的一端，request body 只需要指定「關係
/// 另一端是誰」（<see cref="OtherRegimeId"/>），避免路由參數跟 body 裡兩個等效欄位不一致
/// 時該聽誰的這種歧義。</summary>
public class CreateRegimeRelationRequest
{
    public required Guid OtherRegimeId { get; init; }
    public required string RelationType { get; init; }
    public required int StartYear { get; init; }
    public required int EndYear { get; init; }
    public string? Description { get; init; }
    public MultiLineString? Route { get; init; }
}
