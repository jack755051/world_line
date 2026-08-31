using NetTopologySuite.Geometries;

namespace WorldLine.Api.Contracts;

/// <summary>
/// `POST /api/v1/regimes/{regimeId}/territories` 的請求形狀（task 2.7）。`{regimeId}`
/// 是路由參數，body 不重複這個欄位，跟 `CreateRegimeRelationRequest`/
/// `CreateRegimeAliasRequest` 同一個「路由參數就是主體」慣例。<see cref="Geom"/> 直接
/// 收 GeoJSON geometry，靠 `Program.cs` 掛的 `GeoJsonConverterFactory`（task 2.6 已
/// 註冊）自動解析成 <see cref="MultiPolygon"/>，不用自己寫轉換。
/// </summary>
public class CreateRegimeTerritoryRequest
{
    /// <summary>I1 校驗必填——半開區間 `[startYear, endYear)`，跟既有 `regime_relations`/
    /// `reign_eras` 同一個語意。</summary>
    public required int StartYear { get; init; }
    public required int EndYear { get; init; }

    public required MultiPolygon Geom { get; init; }

    /// <summary>是否為「並存的不同史觀版本」（I3）——不是新舊版本關係，見
    /// `RegimeTerritory` 類別文件。省略時預設 `false`。</summary>
    public bool IsDisputed { get; init; }
}
