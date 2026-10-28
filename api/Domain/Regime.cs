namespace WorldLine.Api.Domain;

/// <summary>政權主體（Aggregate Root）。I2：自稱名稱必填。</summary>
public class Regime
{
    public Guid Id { get; set; }

    /// <summary>自稱名稱（I2 硬約束，例：「唐」「阿拔斯王朝」）。</summary>
    public string SelfName { get; set; } = null!;

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

    public DateTimeOffset CreatedAt { get; set; }
    public DateTimeOffset UpdatedAt { get; set; }

    /// <summary>樂觀併發版本號。</summary>
    public int Version { get; set; }

    public List<RegimeAlias> Aliases { get; set; } = [];
    public List<RegimeTerritory> Territories { get; set; } = [];
}
