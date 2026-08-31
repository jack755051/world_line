namespace WorldLine.Api.Data.Entities;

/// <summary>`historical_events` 逐筆可追溯來源（PRD §12「source/citation model」
/// TODO）。`HistoricalEventId` 是字串 slug（跟 `HistoricalEvent.Id` 同一種識別碼型別，
/// 不是 GUID）。**不含視角/爭議點**——`historical_event_perspectives.primary_sources`
/// 與 `historical_event_controversies.viewpoints` 已經有自己專屬的 JSON citation
/// 慣例（task 2.12/2.13 拍板），這裡只涵蓋事件骨幹本身，不重複做一套。</summary>
public class HistoricalEventCitation
{
    public Guid Id { get; set; }
    public string HistoricalEventId { get; set; } = null!;
    public Guid SourceId { get; set; }
    public string EvidenceNote { get; set; } = null!;
    public DateTimeOffset CreatedAt { get; set; }
}
