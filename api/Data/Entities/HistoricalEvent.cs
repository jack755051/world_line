using NetTopologySuite.Geometries;

namespace WorldLine.Api.Data.Entities;

/// <summary>
/// Objective-fact backbone of an event. Id is a manually-assigned slug (e.g.
/// "event-marco-polo-bridge"), not database-generated. Three independent dimensions
/// (PRD §6 設計原則): duration lives in Start/EndEdtf+decimal (no separate field needed),
/// category is a many-to-many tag set (EventTag), composition is ParentEventId — which also
/// drives semantic zoom (notes §六): year-scale shows only top-level events, day/month-scale
/// expands children.
/// </summary>
public class HistoricalEvent
{
    public string Id { get; set; } = null!;
    public string Name { get; set; } = null!;
    public string? ParentEventId { get; set; }

    public string StartEdtf { get; set; } = null!;
    public string EndEdtf { get; set; } = null!;
    public decimal StartDecimal { get; set; }
    public decimal EndDecimal { get; set; }

    public Point? OriginPoint { get; set; }
    public MultiPolygon? InfluenceArea { get; set; }
    public MultiLineString? Routes { get; set; }

    /// <summary>Raw JSON text for the three-tier accordion content (notes §八).</summary>
    public string? Sections { get; set; }

    public DateTimeOffset CreatedAt { get; set; }
    public DateTimeOffset UpdatedAt { get; set; }
}
