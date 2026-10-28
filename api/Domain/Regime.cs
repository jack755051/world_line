using NpgsqlTypes;

namespace WorldLine.Api.Domain;

/// <summary>政權主體（Aggregate Root）。I2：自稱名稱必填。</summary>
public class Regime
{
    public Guid Id { get; set; }

    /// <summary>自稱名稱（I2 硬約束，例：「唐」「阿拔斯王朝」）。</summary>
    public string SelfName { get; set; } = null!;

    /// <summary>
    /// 存續日期區間（含頭含尾；憲法 §9 2026-10-28：全面日期區間＋精度）。必填且有起點；
    /// 只有 status = existing 時允許無終點（仍存續，或本階段未記錄終止）。
    /// </summary>
    public NpgsqlRange<DateOnly> ExistencePeriod { get; set; }

    /// <summary>起日精度（I7，見 <see cref="DatePrecision"/>）。</summary>
    public string ExistenceFromPrecision { get; set; } = DatePrecision.Day;

    /// <summary>迄日精度；無終點時為 null。</summary>
    public string? ExistenceToPrecision { get; set; }

    /// <summary>見 <see cref="RegimeStatus"/>。</summary>
    public string Status { get; set; } = RegimeStatus.Existing;

    /// <summary>因「分裂」或「禪讓」而來的前身政權；獨立建國為 null。</summary>
    public Guid? PredecessorRegimeId { get; set; }
    public Regime? PredecessorRegime { get; set; }

    /// <summary>見 <see cref="OriginTransitionType"/>；與 PredecessorRegimeId 同時有值或同時為 null。</summary>
    public string? OriginTransitionType { get; set; }

    /// <summary>status = destroyed 時必填的消滅方政權；其餘狀態為 null。</summary>
    public Guid? DestroyedByRegimeId { get; set; }
    public Regime? DestroyedByRegime { get; set; }

    /// <summary>status = annexed 時必填的併吞方政權（憲法 §4 2026-10-28：被併吞與被滅亡不可合併）。</summary>
    public Guid? AnnexedByRegimeId { get; set; }
    public Regime? AnnexedByRegime { get; set; }

    public DateTimeOffset CreatedAt { get; set; }
    public DateTimeOffset UpdatedAt { get; set; }

    /// <summary>樂觀併發版本號。</summary>
    public int Version { get; set; }

    public List<RegimeAlias> Aliases { get; set; } = [];
    public List<RegimeTerritory> Territories { get; set; } = [];
    public List<ReignEra> ReignEras { get; set; } = [];
}
