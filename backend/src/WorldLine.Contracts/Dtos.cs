using System.Text.Json;

namespace WorldLine.Contracts;

// PRD §7：日期一律 YYYY-MM-DD；區間為半開 [start, end)。
// LocalizedText（PRD §6.1-3，Q8 待拍板）：{"zh-Hant": "...", "en": "..."}，第一階段只接受這兩個 key。
// 幾何一律 GeoJSON（WGS84）；以 JsonElement 傳遞，Contracts 不依賴 NetTopologySuite。

/// <summary>半開區間 [start, end)。</summary>
public sealed record DatePeriodDto(DateOnly? Start, DateOnly? End);

/// <summary>回應用的時間區間：主區間＋起訖不確定範圍（PRD §7）。</summary>
public sealed record IntervalDto(DateOnly Start, DateOnly End, DatePeriodDto? StartUncertainty = null, DatePeriodDto? EndUncertainty = null);

// ───────────── 來源（R7） ─────────────
public sealed record CreateSourceRequest(
    string? SourceKind, string? Title, string? Publisher, string? Authors = null, string? PublishedText = null,
    string? LicenseCode = null, string? LicenseEvidenceUrl = null, string? Url = null, string? ArchiveUrl = null,
    string? LocalCopyPath = null, string? CatalogId = null, string? Note = null);

public sealed record SourceDto(
    Guid Id, string SourceKind, string Title, string Publisher, string? Authors, string? PublishedText,
    string? LicenseCode, string? LicenseEvidenceUrl, string? Url, string? ArchiveUrl, string? LocalCopyPath,
    string? CatalogId, string? Note);

// ───────────── 政權（I2、I4、R4） ─────────────
public sealed record RegimeNameInput(
    string? NameKind, string? OriginalText, string? OriginalLang, IReadOnlyDictionary<string, string>? Display,
    Guid? ObserverRegimeId = null, DatePeriodDto? ValidPeriod = null, bool IsPrimary = false);

public sealed record CreateRegimeRequest(string? Slug, string? WikidataQid, IReadOnlyList<RegimeNameInput>? Names);

public sealed record RegimeNameDto(
    Guid Id, string NameKind, string OriginalText, string OriginalLang, IReadOnlyDictionary<string, string> Display,
    Guid? ObserverRegimeId, DatePeriodDto? ValidPeriod, bool IsPrimary);

public sealed record RegimeDto(Guid Id, string Slug, string? WikidataQid, IReadOnlyList<RegimeNameDto> Names);

// ───────────── 戰區與史料快照（§9） ─────────────
public sealed record CreateTheaterRequest(string? Code, IReadOnlyDictionary<string, string>? Name, JsonElement? Extent = null);

public sealed record TheaterDto(Guid Id, string Code, IReadOnlyDictionary<string, string> Name);

public sealed record CreateControlSnapshotRequest(
    Guid? TheaterId, DateOnly? AsOf, string? Attestation = null, DatePeriodDto? AttestedPeriod = null,
    IReadOnlyDictionary<string, string>? AsOfNote = null, IReadOnlyDictionary<string, string>? Title = null);

public sealed record ControlSnapshotDto(
    Guid Id, Guid TheaterId, DateOnly AsOf, string Attestation, DatePeriodDto? AttestedPeriod,
    IReadOnlyDictionary<string, string>? AsOfNote, IReadOnlyDictionary<string, string>? Title);

// ───────────── 控制軸（R6、I1、I3、I6、R7） ─────────────
public sealed record CitationInput(Guid? SourceId, string? Locator, string? Role, string? EvidenceNote);

public sealed record CreateControlRecordRequest(
    Guid? ControllerRegimeId, Guid? SnapshotId, string? ControlType, DatePeriodDto? ValidPeriod, JsonElement? Geometry,
    IReadOnlyList<CitationInput>? Citations, Guid? PatronRegimeId = null,
    DatePeriodDto? StartUncertainty = null, DatePeriodDto? EndUncertainty = null, bool IsDisputed = false);

public sealed record ControlRecordCreatedDto(Guid ControlRecordId, Guid VersionId);

public sealed record CitationDto(
    Guid SourceId, string SourceTitle, string Publisher, string? LicenseCode, string Locator, string Role, string EvidenceNote);

public sealed record ControlFeatureProperties(
    Guid ControlRecordId, Guid VersionId, Guid ControllerRegimeId, string ControlType, Guid? PatronRegimeId,
    string TheaterCode, Guid SnapshotId, bool IsDisputed, IntervalDto ValidPeriod, IReadOnlyList<CitationDto> Citations);

public sealed record ControlFeature(Guid Id, JsonElement Geometry, ControlFeatureProperties Properties)
{
    public string Type => "Feature";
}

public sealed record ControlFeatureCollection(IReadOnlyList<ControlFeature> Features)
{
    public string Type => "FeatureCollection";
}

public sealed record SnapshotRefDto(Guid Id, DateOnly AsOf);

/// <summary>
/// 戰區在該日期的狀態（PRD §6.7）：<c>attested</c>（史料）、<c>interpolated</c>（兩快照之間，推估）。
/// <c>outside</c>（早於第一個或晚於最後一個快照）PRD Story 3 尚為 TODO，暫以此值如實回報，待拍板。
/// </summary>
public sealed record TheaterStateDto(
    string TheaterCode, string State, SnapshotRefDto? AttestingSnapshot, SnapshotRefDto? PrevSnapshot, SnapshotRefDto? NextSnapshot);

public sealed record ControlMapDto(DateOnly Date, ControlFeatureCollection FeatureCollection, IReadOnlyList<TheaterStateDto> Theaters);

// ───────────── 時間軸 ─────────────
public sealed record SnapshotSourceDto(Guid SourceId, string Title, string Locator);

public sealed record TimelineSnapshotDto(
    Guid Id, string TheaterCode, DateOnly AsOf, string Attestation, DatePeriodDto? AttestedPeriod,
    IReadOnlyDictionary<string, string>? Title, IReadOnlyList<SnapshotSourceDto> PrimarySources);

// ───────────── 持續關係（§6「政權間互動」(2)） ─────────────
/// <summary>patron_puppet 方向：regimeA＝扶植方、regimeB＝傀儡（Tai 2026-10-28：與控制紀錄的 patronRegimeId 並存）。</summary>
public sealed record CreateRegimeRelationRequest(
    Guid? RegimeAId, Guid? RegimeBId, string? RelationType, DatePeriodDto? ValidPeriod,
    DatePeriodDto? StartUncertainty = null, DatePeriodDto? EndUncertainty = null,
    IReadOnlyDictionary<string, string>? Note = null);

public sealed record RegimeRelationDto(
    Guid Id, Guid RegimeAId, Guid RegimeBId, string RelationType, DatePeriodDto ValidPeriod,
    DatePeriodDto? StartUncertainty, DatePeriodDto? EndUncertainty, IReadOnlyDictionary<string, string>? Note);

/// <summary>聚焦政權在某日的持續關係。<c>role</c>：patron／puppet（patron_puppet）或 party（其他關係）。</summary>
public sealed record RegimeInteractionDto(Guid CounterpartRegimeId, string Role, RegimeRelationDto Relation);

/// <summary>聚焦面板資料（PRD §7.1）。離散事件需 event_participants，尚未建置，暫不回傳。</summary>
public sealed record RegimeInteractionsDto(Guid RegimeId, DateOnly Date, IReadOnlyList<RegimeInteractionDto> Relations);

// ───────────── 事件（R8、§9） ─────────────
/// <summary>
/// occurred 為事件發生地的「當地日期」（半開區間）；timeNote 為選填多語時間備註
/// （例：「東京時間 12 月 8 日」）。Tai 2026-10-28 修正：不記時區欄位。
/// </summary>
public sealed record CreateEventRequest(
    string? EventKind, DatePeriodDto? Occurred, string? DatePrecision,
    IReadOnlyDictionary<string, string>? TimeNote = null,
    IReadOnlyDictionary<string, string>? Summary = null, Guid? ParentEventId = null, JsonElement? Location = null);

public sealed record EventDto(
    Guid Id, string EventKind, Guid? ParentEventId, IReadOnlyDictionary<string, string>? Summary,
    DatePeriodDto Occurred, string DatePrecision, IReadOnlyDictionary<string, string>? TimeNote,
    JsonElement? Location);
