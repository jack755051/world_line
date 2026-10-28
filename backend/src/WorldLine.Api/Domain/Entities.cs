using NetTopologySuite.Geometries;
using NpgsqlTypes;

namespace WorldLine.Api.Domain;

// PRD §6.3 M0 最小 schema。跨 Aggregate 只用 ID 連結（§6.8）。
// JSONB 欄位（LocalizedText 等）以原始 JSON 字串保存，序列化／驗證在應用層（Q8 待拍板，格式可能再變）。

public sealed class Source
{
    public Guid Id { get; set; }
    public string SourceKind { get; set; } = "";
    public string Title { get; set; } = "";
    public string Publisher { get; set; } = "";
    public string? Authors { get; set; }
    public string? PublishedText { get; set; }
    public string? LicenseCode { get; set; }
    public string? LicenseEvidenceUrl { get; set; }
    public string? Url { get; set; }
    public string? ArchiveUrl { get; set; }
    public string? LocalCopyPath { get; set; }
    public string? CatalogId { get; set; }
    public string? Note { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
    public DateTimeOffset UpdatedAt { get; set; }
    public int Version { get; set; }
}

public sealed class Regime
{
    public Guid Id { get; set; }
    public string Slug { get; set; } = "";
    public string? WikidataQid { get; set; }
    public DateTimeOffset? RetractedAt { get; set; }
    public string? RetractionReason { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
    public DateTimeOffset UpdatedAt { get; set; }
    public int Version { get; set; }
    public List<RegimeName> Names { get; set; } = [];
}

public sealed class RegimeName
{
    public Guid Id { get; set; }
    public Guid RegimeId { get; set; }
    public string NameKind { get; set; } = "";
    public string OriginalText { get; set; } = "";
    public string OriginalLang { get; set; } = "";
    public string Display { get; set; } = "{}";
    public Guid? ObserverRegimeId { get; set; }
    public NpgsqlRange<DateOnly>? ValidPeriod { get; set; }
    public bool IsPrimary { get; set; }
    public DateTimeOffset? RetractedAt { get; set; }
    public string? RetractionReason { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
    public int Version { get; set; }
}

public sealed class Theater
{
    public Guid Id { get; set; }
    public string Code { get; set; } = "";
    public string Name { get; set; } = "{}";
    public MultiPolygon? Extent { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
}

public sealed class ControlSnapshot
{
    public Guid Id { get; set; }
    public Guid TheaterId { get; set; }
    public DateOnly AsOf { get; set; }
    public string? AsOfNote { get; set; }
    public string Attestation { get; set; } = Attestations.Point;
    public NpgsqlRange<DateOnly>? AttestedPeriod { get; set; }
    public string? Title { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
}

/// <summary>控制紀錄的穩定身分（PRD §6.3 方案 A）。</summary>
public sealed class ControlRecord
{
    public Guid Id { get; set; }
    public Guid ControllerRegimeId { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
    public List<ControlRecordVersion> Versions { get; set; } = [];
}

/// <summary>控制紀錄版本（I5：只能 INSERT；舊版本只允許寫入 superseded_by／superseded_at）。</summary>
public sealed class ControlRecordVersion
{
    public Guid Id { get; set; }
    public Guid ControlRecordId { get; set; }
    public Guid SnapshotId { get; set; }
    public string ControlType { get; set; } = "";
    public Guid? PatronRegimeId { get; set; }
    public NpgsqlRange<DateOnly> ValidPeriod { get; set; }
    public NpgsqlRange<DateOnly>? StartUncertainty { get; set; }
    public NpgsqlRange<DateOnly>? EndUncertainty { get; set; }
    public MultiPolygon Geom { get; set; } = null!;
    public bool IsDisputed { get; set; }
    public bool IsRetraction { get; set; }
    public string? RevisionReason { get; set; }
    public Guid? SupersededBy { get; set; }
    public DateTimeOffset? SupersededAt { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
    public List<ControlRecordCitation> Citations { get; set; } = [];
}

/// <summary>I6 引用：source＋locator（圖集＋圖號／頁碼）＋role＋evidence note。</summary>
public sealed class ControlRecordCitation
{
    public Guid ControlRecordVersionId { get; set; }
    public Guid SourceId { get; set; }
    public string Locator { get; set; } = "";
    public string Role { get; set; } = CitationRoles.Primary;
    public string EvidenceNote { get; set; } = "";
}

/// <summary>陸地底圖（「控制資料缺」推導用，PRD §6.4）。</summary>
public sealed class ReferenceLand
{
    public int Id { get; set; }
    public MultiPolygon Geom { get; set; } = null!;
    public Guid SourceId { get; set; }
}
