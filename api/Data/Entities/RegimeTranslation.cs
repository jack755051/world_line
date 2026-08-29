namespace WorldLine.Api.Data.Entities;

/// <summary>`regimes.self_name` 的其他語言版本（憲法 R4，PRD §6「多語言內容設計」）。</summary>
public class RegimeTranslation
{
    public Guid Id { get; set; }
    public Guid RegimeId { get; set; }
    public string Locale { get; set; } = null!;
    public string SelfName { get; set; } = null!;
    public DateTimeOffset CreatedAt { get; set; }
}
