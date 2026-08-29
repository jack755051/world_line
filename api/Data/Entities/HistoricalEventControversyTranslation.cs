namespace WorldLine.Api.Data.Entities;

/// <summary>
/// `historical_event_controversies.topic`/`neutral_description` 的其他語言版本
/// （憲法 R4，PRD §6）。`viewpoints`（誰主張什麼）不翻譯，見 PRD §6 核心設計原則。
/// </summary>
public class HistoricalEventControversyTranslation
{
    public Guid Id { get; set; }
    public Guid ControversyId { get; set; }
    public string Locale { get; set; } = null!;
    public string Topic { get; set; } = null!;
    public string NeutralDescription { get; set; } = null!;
    public DateTimeOffset CreatedAt { get; set; }
}
