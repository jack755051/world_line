using NetTopologySuite.Geometries;
using NpgsqlTypes;

namespace WorldLine.Api.Data.Entities;

/// <summary>
/// Ongoing relationship state between two regimes (trade/tribute/marriage-alliance/etc.) —
/// distinct from discrete HistoricalEvent rows (PRD §6 設計原則: 離散事件 vs 持續關係拆兩張表).
/// </summary>
public class RegimeRelation
{
    public Guid Id { get; set; }
    public Guid RegimeAId { get; set; }
    public Guid RegimeBId { get; set; }
    public string RelationType { get; set; } = null!;
    public NpgsqlRange<int> ValidPeriod { get; set; }
    public MultiLineString? Route { get; set; }
    public string? Description { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
}
