namespace WorldLine.Api.Contracts;

/// <summary>`GET /api/v1/reign-eras`／`GET /api/v1/regimes/{regimeId}/reign-eras` 的回應形狀。</summary>
public class ReignEraResponse
{
    public required Guid Id { get; init; }
    public required Guid RegimeId { get; init; }
    public required string EraName { get; init; }
    public required int StartYear { get; init; }
    public required int? EndYear { get; init; }
}
