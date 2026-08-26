namespace WorldLine.Api.Data.Entities;

/// <summary>Join row, composite PK (EventId, TagId), table name is singular "historical_event_tag_map" (matches PRD SQL).</summary>
public class HistoricalEventTagMap
{
    public string EventId { get; set; } = null!;
    public int TagId { get; set; }
}
