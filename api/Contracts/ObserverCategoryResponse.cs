namespace WorldLine.Api.Contracts;

/// <summary>`GET /api/v1/observer-categories` 的回應形狀（task 2.12）。</summary>
public class ObserverCategoryResponse
{
    public required int Id { get; init; }
    public required string CategoryName { get; init; }
}
