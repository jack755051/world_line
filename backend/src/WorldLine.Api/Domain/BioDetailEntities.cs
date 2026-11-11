using NpgsqlTypes;

namespace WorldLine.Api.Domain;

/// <summary>
/// B3 分段生平（ARCHITECTURE §16.2、§16.3、§16.4，2026-11-11；Tai 同意六張新表）。
/// 地圖時間軸不讀這些表（T6）；overlay／GET /leaders 不含段落、經歷、角色。I5 trigger 與部分唯一索引在 migration 建立。
/// </summary>
public abstract class BioDetailCitationBase
{
    public Guid Id { get; set; }
    public Guid SourceId { get; set; }
    public string Locator { get; set; } = "";
    public string Quote { get; set; } = "";
    public string? QuoteLang { get; set; }
    public string? EvidenceNote { get; set; }
    public DateOnly AccessedOn { get; set; }
    /// <summary>來源等級 A｜B；NULL＝未評等。</summary>
    public string? Grade { get; set; }
    public string? DatePrecision { get; set; }
    /// <summary>選填句序區間；本批全空（seed 的字串 claimSpan 併入 EvidenceNote）。</summary>
    public NpgsqlRange<int>? ClaimSpan { get; set; }
    public string? PolicyVersion { get; set; }
    public DateTimeOffset? RetractedAt { get; set; }
    public string? RetractionReason { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
}

/// <summary>生平段落（leader_bio_paragraphs）。同 bio 有效列內 ord 唯一。</summary>
public sealed class LeaderBioParagraph
{
    public Guid Id { get; set; }
    public Guid BioId { get; set; }
    public int Ord { get; set; }
    /// <summary>半開；整段無法定期間才 NULL；上界缺＝無界。</summary>
    public NpgsqlRange<DateOnly>? Period { get; set; }
    public string? PeriodStartPrecision { get; set; }
    public string? PeriodEndPrecision { get; set; }
    /// <summary>jsonb 物件（zh-Hant／en）。</summary>
    public string? Heading { get; set; }
    /// <summary>jsonb 物件（zh-Hant／en）；字數上限只在寫入層檢查。</summary>
    public string Body { get; set; } = "{}";
    public Guid[]? RelatedRecordIds { get; set; }
    public Guid? SupersededBy { get; set; }
    public DateTimeOffset? RetractedAt { get; set; }
    public string? RetractionReason { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
    public int Version { get; set; }
}

public sealed class LeaderBioParagraphCitation : BioDetailCitationBase
{
    public Guid ParagraphId { get; set; }
}

/// <summary>經歷（person_positions）：只供詳情「經歷」區，不決定出卡。元首／首腦／實質領導種類走 person_roles。</summary>
public sealed class PersonPosition
{
    public Guid Id { get; set; }
    public Guid BioId { get; set; }
    public string SeedKey { get; set; } = "";
    public Guid? RegimeId { get; set; }
    public string? Organization { get; set; }
    public string Title { get; set; } = "{}";
    public string PositionKind { get; set; } = "";
    public NpgsqlRange<DateOnly> Period { get; set; }
    public string? StartPrecision { get; set; }
    public string? EndPrecision { get; set; }
    public string? Note { get; set; }
    public Guid? SupersededBy { get; set; }
    public DateTimeOffset? RetractedAt { get; set; }
    public string? RetractionReason { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
    public int Version { get; set; }
}

public sealed class PersonPositionCitation : BioDetailCitationBase
{
    public Guid PositionId { get; set; }
}

/// <summary>角色（person_roles）：元首／首腦／實質領導／閣員。不是地圖出卡資料（T13 未決，leader_records 不變）。</summary>
public sealed class PersonRole
{
    public Guid Id { get; set; }
    public Guid BioId { get; set; }
    public string SeedKey { get; set; } = "";
    public Guid? RegimeId { get; set; }
    public string? Organization { get; set; }
    public string Title { get; set; } = "{}";
    public string RoleKind { get; set; } = "";
    public NpgsqlRange<DateOnly> Period { get; set; }
    public string? StartPrecision { get; set; }
    public string? EndPrecision { get; set; }
    public bool Acting { get; set; }
    public string? T14Rule { get; set; }
    public string? Note { get; set; }
    public Guid? SupersededBy { get; set; }
    public DateTimeOffset? RetractedAt { get; set; }
    public string? RetractionReason { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
    public int Version { get; set; }
}

public sealed class PersonRoleCitation : BioDetailCitationBase
{
    public Guid RoleId { get; set; }
}
