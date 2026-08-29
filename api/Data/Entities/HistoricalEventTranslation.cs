namespace WorldLine.Api.Data.Entities;

/// <summary>
/// `historical_events.name` 的其他語言版本（憲法 R4，PRD §6「多語言內容設計」）。
/// `sections` JSONB 要不要連帶翻譯尚未拍板，這裡先只處理 `name`。
/// </summary>
public class HistoricalEventTranslation
{
    public Guid Id { get; set; }
    public string EventId { get; set; } = null!;
    public string Locale { get; set; } = null!;
    public string Name { get; set; } = null!;
    public DateTimeOffset CreatedAt { get; set; }
}
