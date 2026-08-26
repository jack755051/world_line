using NetTopologySuite.Geometries;
using NpgsqlTypes;

namespace WorldLine.Api.Data.Entities;

/// <summary>
/// Dual-track place naming (憲法 §6): historical name is primary, modern name is the optional
/// parenthetical cross-reference.
/// </summary>
public class PlaceName
{
    public Guid Id { get; set; }
    public string HistoricalName { get; set; } = null!;
    public string? ModernName { get; set; }
    public NpgsqlRange<int>? ValidPeriod { get; set; }
    public Point? Geom { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
}
