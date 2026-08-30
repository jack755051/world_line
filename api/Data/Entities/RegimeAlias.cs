namespace WorldLine.Api.Data.Entities;

/// <summary>
/// I4: must always trace back to a self-named regime — enforced via required FK on RegimeId.
/// ObserverRegimeId is the viewpoint that uses this alias (e.g. Tang calling the Abbasid
/// Caliphate "大食"); null means a generic/unattributed exonym.
/// </summary>
public class RegimeAlias
{
    public Guid Id { get; set; }
    public Guid RegimeId { get; set; }
    public Guid? ObserverRegimeId { get; set; }
    public string AliasName { get; set; } = null!;

    /// <summary>受控值見 `WorldLine.Api.Domain.RegimeAliasType`（task 2.9a，2026-08-30
    /// 拍板）；null 代表沒有分類/不確定，不是「還沒拍板」的佔位狀態。</summary>
    public string? AliasType { get; set; }

    public DateTimeOffset CreatedAt { get; set; }
}
