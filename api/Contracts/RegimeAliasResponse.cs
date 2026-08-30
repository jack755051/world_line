namespace WorldLine.Api.Contracts;

/// <summary>task 2.9a：`GET /api/v1/regimes/:id/aliases` 回應的一筆代稱。</summary>
public class RegimeAliasResponse
{
    public Guid Id { get; set; }
    public Guid RegimeId { get; set; }
    public Guid? ObserverRegimeId { get; set; }
    public string AliasName { get; set; } = null!;
    public string? AliasType { get; set; }
}
