using NetTopologySuite.Geometries;
using NpgsqlTypes;

namespace WorldLine.Api.Domain;

/// <summary>政權間持續性關係（貿易、朝貢、和親、同盟、敵對…），與離散事件（historical_events）分開。</summary>
public class RegimeRelation
{
    public Guid Id { get; set; }

    /// <summary>方向性關係的發起方（例：朝貢方）。</summary>
    public Guid RegimeAId { get; set; }
    public Regime RegimeA { get; set; } = null!;

    /// <summary>方向性關係的接受方（例：受貢方）。</summary>
    public Guid RegimeBId { get; set; }
    public Regime RegimeB { get; set; } = null!;

    /// <summary>見 <see cref="Domain.RelationType"/>。</summary>
    public string RelationType { get; set; } = null!;

    /// <summary>關係存續區間（同 I1 精神，必填且有上下界）。</summary>
    public NpgsqlRange<DateOnly> ValidPeriod { get; set; }
    public string ValidFromPrecision { get; set; } = DatePrecision.Day;
    public string ValidToPrecision { get; set; } = DatePrecision.Day;

    /// <summary>可選：關係對應路線（例：絲路）。</summary>
    public MultiLineString? Route { get; set; }

    public string? Description { get; set; }

    public DateTimeOffset CreatedAt { get; set; }
}
