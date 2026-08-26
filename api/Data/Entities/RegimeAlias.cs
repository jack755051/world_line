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

    // TODO(PRD §6): 朝代/帝國/國家 觀察視角標籤如何落地成欄位值，尚未拍板，先留 nullable string
    public string? AliasType { get; set; }

    public DateTimeOffset CreatedAt { get; set; }
}
