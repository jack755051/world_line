namespace WorldLine.Api.Data.Entities;

/// <summary>`regime_aliases.alias_name` 的其他語言版本（憲法 R4，PRD §6「多語言內容設計」）。</summary>
public class RegimeAliasTranslation
{
    public Guid Id { get; set; }
    public Guid RegimeAliasId { get; set; }
    public string Locale { get; set; } = null!;
    public string AliasName { get; set; } = null!;
    public DateTimeOffset CreatedAt { get; set; }
}
