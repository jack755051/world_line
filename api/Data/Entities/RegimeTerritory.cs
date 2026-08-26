using NetTopologySuite.Geometries;
using NpgsqlTypes;

namespace WorldLine.Api.Data.Entities;

/// <summary>
/// Snapshot table — a regime has MANY of these over its lifetime, not one row spanning its
/// whole existence (2026-08-26 拍板). Snapshot density is event-driven, not fixed-interval;
/// ValidPeriod stays year-precision (int4range), it does not follow HistoricalEvent's EDTF model
/// (PRD §6 設計原則). SupersededBy is for I5 corrections only, not for normal temporal succession.
/// </summary>
public class RegimeTerritory
{
    public Guid Id { get; set; }
    public Guid RegimeId { get; set; }
    public NpgsqlRange<int> ValidPeriod { get; set; }
    public MultiPolygon Geom { get; set; } = null!;
    public bool IsDisputed { get; set; }

    public Guid? SupersededBy { get; set; }
    public string? CorrectionReason { get; set; }
    public DateTimeOffset? CorrectedAt { get; set; }

    public DateTimeOffset CreatedAt { get; set; }
    public int Version { get; set; }
}
