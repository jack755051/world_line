using NetTopologySuite.Geometries;
using NpgsqlTypes;

namespace WorldLine.Api.Domain;

/// <summary>控制關係類型（憲法 §4 選項 A、§6）。</summary>
public static class ControlType
{
    /// <summary>佔領（例：德國佔領法國北部 1940–1944）</summary>
    public const string Occupation = "occupation";
    /// <summary>傀儡（例：日本 → 滿洲國）。「傀儡」定性屬觀察視角，此處只記錄可佐證的控制事實</summary>
    public const string Puppet = "puppet";
    /// <summary>保護（例：波希米亞-摩拉維亞保護國）</summary>
    public const string Protectorate = "protectorate";
    /// <summary>殖民（例：日本 → 朝鮮、臺灣）</summary>
    public const string Colony = "colony";
    /// <summary>託管（例：國際聯盟委任統治地）</summary>
    public const string Mandate = "mandate";

    public static readonly IReadOnlyList<string> All = [Occupation, Puppet, Protectorate, Colony, Mandate];
}

/// <summary>
/// 控制關係（控制方 → 被控制方）。I6：控制方、被控制方、時間區間必填，兩方都必須是已存在的政權本體，且不可自己控制自己。
/// 被控制的政權在控制期間仍為「存續」（法理延續）；關係結束即恢復，視為同一政權延續（憲法 §4）。
/// </summary>
public class RegimeControlRelation
{
    public Guid Id { get; set; }

    public Guid ControllerRegimeId { get; set; }
    public Regime ControllerRegime { get; set; } = null!;

    public Guid ControlledRegimeId { get; set; }
    public Regime ControlledRegime { get; set; } = null!;

    /// <summary>見 <see cref="Domain.ControlType"/>。</summary>
    public string ControlType { get; set; } = null!;

    public NpgsqlRange<DateOnly> ValidPeriod { get; set; }
    public string ValidFromPrecision { get; set; } = DatePrecision.Day;
    public string ValidToPrecision { get; set; } = DatePrecision.Day;

    /// <summary>可選：實際控制範圍（佔領區）。沒有就代表控制整個被控制方。</summary>
    public MultiPolygon? Area { get; set; }
    public bool IsIllustrative { get; set; }

    /// <summary>史學上對此控制關係的性質有爭議（例：維琪法國是否為傀儡）。</summary>
    public bool IsDisputed { get; set; }

    public string? Description { get; set; }
    public string? Source { get; set; }

    public DateTimeOffset CreatedAt { get; set; }
    public int Version { get; set; }
}

/// <summary>同盟陣營（獨立實體，憲法 §6 2026-10-28）：例：軸心國、同盟國。</summary>
public class Alliance
{
    public Guid Id { get; set; }

    /// <summary>自稱名稱（比照 I2）。</summary>
    public string SelfName { get; set; } = null!;
    public string? Description { get; set; }

    public NpgsqlRange<DateOnly> ExistencePeriod { get; set; }
    public string ExistenceFromPrecision { get; set; } = DatePrecision.Day;
    public string? ExistenceToPrecision { get; set; }

    public DateTimeOffset CreatedAt { get; set; }
    public DateTimeOffset UpdatedAt { get; set; }
    public int Version { get; set; }

    public List<AllianceAlias> Aliases { get; set; } = [];
    public List<AllianceMembership> Memberships { get; set; } = [];
}

/// <summary>陣營他稱（命名機制同政權，比照 I4 不可孤兒）。</summary>
public class AllianceAlias
{
    public Guid Id { get; set; }
    public Guid AllianceId { get; set; }
    public Alliance Alliance { get; set; } = null!;
    public Guid? ObserverRegimeId { get; set; }
    public Regime? ObserverRegime { get; set; }
    public string AliasName { get; set; } = null!;
    public string AliasType { get; set; } = AliasPerspective.Contemporary;
    public DateTimeOffset CreatedAt { get; set; }
}

/// <summary>陣營成員角色。</summary>
public static class MembershipRole
{
    /// <summary>正式成員（例：簽署《三國同盟條約》《聯合國家宣言》）</summary>
    public const string Member = "member";
    /// <summary>共同交戰國（例：義大利 1943-10-13 起對德宣戰，與同盟國並肩作戰但非正式盟國）</summary>
    public const string CoBelligerent = "co_belligerent";
    /// <summary>協同國</summary>
    public const string Associate = "associate";

    public static readonly IReadOnlyList<string> All = [Member, CoBelligerent, Associate];
}

/// <summary>陣營成員（加入日＝區間起點、退出日＝區間終點；無終點＝本階段未記錄退出）。</summary>
public class AllianceMembership
{
    public Guid Id { get; set; }
    public Guid AllianceId { get; set; }
    public Alliance Alliance { get; set; } = null!;
    public Guid RegimeId { get; set; }
    public Regime Regime { get; set; } = null!;
    public string Role { get; set; } = MembershipRole.Member;

    public NpgsqlRange<DateOnly> ValidPeriod { get; set; }
    public string ValidFromPrecision { get; set; } = DatePrecision.Day;
    public string? ValidToPrecision { get; set; }

    public string? Note { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
    public int Version { get; set; }
}
