using NetTopologySuite.Geometries;
using NpgsqlTypes;

namespace WorldLine.Api.Domain;

// 戰役 C1（ARCHITECTURE §19.1，D13＝A′，2026-11-11，新增式）：戰役＝一筆 historical_events（event_kind='battle'）＋以下子表。
// person_event_participations、battle_figures 留到 C3／C4。所有表禁止 DELETE，只能軟撤回（I5，trigger 在 migration 以 SQL 建立）。
// 偏離 §19.1 DDL 草稿處（已在 §19.1.8 加註）：battle_map_features 加 feature_key／side_camp／props；citation 表 grade NOT NULL。

public static class BattleStatuses
{
    public const string Pending = "pending";
    public const string Verified = "verified";
    public static readonly string[] All = [Verified, Pending];
}

public static class BattleObjectiveKinds
{
    public static readonly string[] All = ["place", "line", "regime"];
}

public static class BattleOutcomeKinds
{
    public static readonly string[] All = ["decisive", "indecisive", "withdrawal", "stalemate", "other"];
}

public static class BattleFeatureKinds
{
    public const string Front = "front";
    public const string Arrow = "arrow";
    public const string Site = "site";
    public static readonly string[] All = [Front, Arrow, Site];
}

public static class BattleGeomBases
{
    public const string SourceMap = "source_map";
    public const string SourceText = "source_text";
    public const string Derived = "derived";
    public static readonly string[] All = [SourceMap, SourceText, Derived];
}

/// <summary>簡報圖配色組（沿用 wl-campaign-web/0.1 的 group 值；不是政權，也不從交戰關係推導）。</summary>
public static class BattleSideCamps
{
    public static readonly string[] All = ["allied", "axis", "soviet", "contested", "unknown"];
}

/// <summary>battle_profile_citations.field 值域（§19.4.1）。</summary>
public static class BattleProfileFields
{
    public static readonly string[] All = ["objective", "control_change", "outcome", "theater_area", "name"];
}

/// <summary>戰役屬性（§19.1.1）：1:1 掛 historical_events，只有 event_kind='battle' 可掛（寫入層檢查）。</summary>
public sealed class BattleProfile
{
    public Guid EventId { get; set; }
    public string Slug { get; set; } = "";
    /// <summary>jsonb：{"zh-Hant": "...", "en": "..."}。</summary>
    public string Name { get; set; } = "{}";
    /// <summary>jsonb；憲法 §6 條件 (2)。</summary>
    public string Objective { get; set; } = "{}";
    public string ObjectiveKind { get; set; } = "";
    public MultiPolygon? TheaterArea { get; set; }
    public Guid? ConflictRecordId { get; set; }
    public string? OutcomeKind { get; set; }
    public string? OutcomeText { get; set; }
    /// <summary>jsonb；憲法 §6 條件 (3)，必填。</summary>
    public string ControlChange { get; set; } = "{}";
    public string Status { get; set; } = BattleStatuses.Pending;
    public DateTimeOffset? RetractedAt { get; set; }
    public string? RetractionReason { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
}

/// <summary>戰役階段（§19.1.2）。period 半開區間（§14.6）；「上旬」改 month 精度（Q6）。</summary>
public sealed class BattlePhase
{
    public Guid Id { get; set; }
    public Guid EventId { get; set; }
    public int Seq { get; set; }
    public string Name { get; set; } = "{}";
    public NpgsqlRange<DateOnly> Period { get; set; }
    public string StartPrecision { get; set; } = DatePrecisions.Day;
    public string EndPrecision { get; set; } = DatePrecisions.Day;
    /// <summary>jsonb；沒有出處就留 NULL（I6）。</summary>
    public string? Summary { get; set; }
    public string Status { get; set; } = BattleStatuses.Pending;
    public DateTimeOffset? RetractedAt { get; set; }
    public string? RetractionReason { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
}

/// <summary>簡報圖幾何（§19.1.3，PostGIS SRID 4326）。只收出處明載的戰線、進攻方向、據點（G3）。</summary>
public sealed class BattleMapFeature
{
    public Guid Id { get; set; }
    public Guid PhaseId { get; set; }
    /// <summary>穩定鍵（例 dunkirk_1940_p1-front-0），對應 wl-campaign-web/0.1 的 properties.id；seed 可重跑。§19.1.8 偏離 1。</summary>
    public string FeatureKey { get; set; } = "";
    public string FeatureKind { get; set; } = "";
    public Guid? SideRegimeId { get; set; }
    /// <summary>配色組（allied／axis／…），對應 JSON 的 group。§19.1.8 偏離 2。</summary>
    public string? SideCamp { get; set; }
    public Geometry Geom { get; set; } = null!;
    public string? Label { get; set; }
    /// <summary>jsonb 物件：只供顯示的附屬屬性（from／to／unit／name／controller／date／note／vertices…）。§19.1.8 偏離 3。</summary>
    public string? Props { get; set; }
    public string GeomBasis { get; set; } = BattleGeomBases.Derived;
    public string Status { get; set; } = BattleStatuses.Pending;
    public DateTimeOffset? RetractedAt { get; set; }
    public string? RetractionReason { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
}

/// <summary>參戰部隊（§19.1.6）。指揮官不放本表；部隊不建幾何（G3）。unit_echelon 值域 C1 暫不鎖（待考證組定）。</summary>
public sealed class BattleUnit
{
    public Guid Id { get; set; }
    public Guid EventId { get; set; }
    public Guid SideRegimeId { get; set; }
    public Guid? ParentUnitId { get; set; }
    public string UnitName { get; set; } = "{}";
    public string? UnitEchelon { get; set; }
    public string Status { get; set; } = BattleStatuses.Pending;
    public DateTimeOffset? RetractedAt { get; set; }
    public string? RetractionReason { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
}

/// <summary>§16.4.1／§19.1.7 統一 citation 欄位（四張戰役 citation 表共用）。</summary>
public abstract class BattleCitationBase
{
    public Guid Id { get; set; }
    public Guid SourceId { get; set; }
    public string Locator { get; set; } = "";
    /// <summary>引文原文（≤ 80 字，程式端檢查）。</summary>
    public string Quote { get; set; } = "";
    public string? QuoteLang { get; set; }
    public string? EvidenceNote { get; set; }
    public DateOnly AccessedOn { get; set; }
    /// <summary>A｜B（G6：C／X 不進庫）。</summary>
    public string Grade { get; set; } = "";
    public string? DatePrecision { get; set; }
    public string? PolicyVersion { get; set; }
    public DateTimeOffset? RetractedAt { get; set; }
    public string? RetractionReason { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
}

public sealed class BattleProfileCitation : BattleCitationBase
{
    public Guid EventId { get; set; }
    /// <summary><see cref="BattleProfileFields"/>。</summary>
    public string Field { get; set; } = "";
}

public sealed class BattlePhaseCitation : BattleCitationBase
{
    public Guid PhaseId { get; set; }
    /// <summary>選填：支撐的句序號（半開區間，同 T4）。</summary>
    public NpgsqlRange<int>? ClaimSpan { get; set; }
}

public sealed class BattleMapFeatureCitation : BattleCitationBase
{
    public Guid FeatureId { get; set; }
}

public sealed class BattleUnitCitation : BattleCitationBase
{
    public Guid UnitId { get; set; }
}
