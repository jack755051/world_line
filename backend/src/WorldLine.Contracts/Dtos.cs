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

/// <summary>
/// <c>controllerAlignment</c>：控制方在該日期的陣營切片（憲法 §6「陣營」），附引用；
/// 沒有陣營資料時為 null，前端顯示「陣營未建置」，不自行推定。
/// </summary>
public sealed record ControlFeatureProperties(
    Guid ControlRecordId, Guid VersionId, Guid ControllerRegimeId, string ControlType, Guid? PatronRegimeId,
    string TheaterCode, Guid SnapshotId, bool IsDisputed, IntervalDto ValidPeriod, IReadOnlyList<CitationDto> Citations,
    RegimeAlignmentDto? ControllerAlignment = null, IReadOnlyList<SupplementEventDto>? ControllerSupplements = null);

/// <summary>
/// 陣營「補充」（使用者 2026-10-31 拍板：陣營以最嚴謹的正式文件為主，其他有紀錄者只作補充）：
/// 控制方在該日之前參與、且附引用的事件（宣戰、承認等）。不改變陣營判定，前端標「補充」。實作為 AI 提案・待拍板。
/// </summary>
public sealed record SupplementEventDto(
    Guid EventId, string EventKind, DatePeriodDto Occurred, IReadOnlyDictionary<string, string>? Summary,
    IReadOnlyList<EventParticipantDto> Participants, IReadOnlyList<CitationDto> Citations);

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

/// <summary>
/// <c>coverageNotes</c>：該日有效的涵蓋備註（R9「控制資料缺」及原因，PRD §6.4 選項 C）。
/// 戰區範圍與 reference_land 尚未建置，暫以備註幾何直接呈現缺口（2026-10-31 實作，AI 提案・待拍板）。
/// </summary>
public sealed record ControlMapDto(
    DateOnly Date, ControlFeatureCollection FeatureCollection, IReadOnlyList<TheaterStateDto> Theaters,
    IReadOnlyList<CoverageNoteDto>? CoverageNotes = null);

// ───────────── 控制資料缺（R9、PRD §6.3 control_coverage_notes） ─────────────
/// <summary>reason：no_qualified_source（已調查、無合格來源）| not_yet_digitized（尚未建置／地圖沒畫到）。期間兩端有界。</summary>
public sealed record CreateCoverageNoteRequest(
    Guid? TheaterId, JsonElement? Geometry, DatePeriodDto? ValidPeriod, string? Reason,
    IReadOnlyDictionary<string, string>? Note = null, string? ResearchRef = null);

public sealed record CoverageNoteDto(
    Guid Id, Guid? TheaterId, JsonElement Geometry, DatePeriodDto ValidPeriod, string Reason,
    IReadOnlyDictionary<string, string>? Note, string? ResearchRef);

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
    IReadOnlyDictionary<string, string>? Summary = null, Guid? ParentEventId = null, JsonElement? Location = null,
    IReadOnlyList<EventParticipantInput>? Participants = null, IReadOnlyList<EventCitationInput>? Citations = null);

/// <summary>事件參與方（PRD §6.3 event_participants）。role：belligerent | signatory | perpetrator | other（清單待拍板）。</summary>
public sealed record EventParticipantInput(Guid? RegimeId, string? Role);

/// <summary>事件引用（PRD §6.3 event_citations）：來源＋locator（頁碼、文件號）＋審查依據。</summary>
public sealed record EventCitationInput(Guid? SourceId, string? Locator, string? EvidenceNote);

public sealed record EventParticipantDto(Guid RegimeId, string Role);

public sealed record EventDto(
    Guid Id, string EventKind, Guid? ParentEventId, IReadOnlyDictionary<string, string>? Summary,
    DatePeriodDto Occurred, string DatePrecision, IReadOnlyDictionary<string, string>? TimeNote,
    JsonElement? Location, IReadOnlyList<EventParticipantDto>? Participants = null, IReadOnlyList<CitationDto>? Citations = null);

// ───────────── 陣營（憲法 §6「陣營」、PRD §6.3 regime_alignments） ─────────────
/// <summary>
/// 新增陣營切片。camp：axis | allies | co_belligerent | neutral。validPeriod.start 必填（正式加入日），迄日未知可留空。
/// citations 至少一筆 role = primary（有 locator、授權在允許清單）。basisEventId 選填（依據事件）。
/// </summary>
public sealed record CreateRegimeAlignmentRequest(
    string? Camp, DatePeriodDto? ValidPeriod, IReadOnlyList<CitationInput>? Citations,
    Guid? BasisEventId = null, IReadOnlyDictionary<string, string>? Note = null);

/// <summary>陣營切片。validPeriod 為半開區間 [start, end)；end 為 null 表示迄日未定（不推測）。</summary>
public sealed record RegimeAlignmentDto(
    Guid Id, Guid RegimeId, string Camp, DatePeriodDto ValidPeriod, Guid? BasisEventId,
    IReadOnlyDictionary<string, string>? Note, IReadOnlyList<CitationDto> Citations);

/// <summary>撤回（I5：不硬刪，只寫一次撤回時間與原因）。</summary>
public sealed record RetractionRequest(string? Reason);

public sealed record RetractionDto(Guid Id, DateTimeOffset RetractedAt, string Reason);

// ───────────── 主權圖層（法理國界；2026-10-31 試驗 feature/borders-1938-1940，AI 提案・待拍板） ─────────────
/// <summary>
/// 新增主權紀錄。validPeriod.start 必填，迄日未知可留空。geometrySourceId 必須是授權在允許清單的資料集來源；
/// geometryLicense 為此筆幾何的授權（cc0／cc_by…），cc_by／cc_by_sa 必須附 attribution。
/// </summary>
public sealed record CreateSovereigntyRecordRequest(
    Guid? RegimeId, JsonElement? Geometry, DatePeriodDto? ValidPeriod, string? LayerStatus,
    Guid? GeometrySourceId, string? GeometryLocator, string? GeometryLicense, string? Attribution = null,
    Guid? StartEventId = null, Guid? EndEventId = null,
    long? OhmRelationId = null, int? OhmVersion = null, DateTimeOffset? OhmFetchedAt = null,
    string? OhmStartRaw = null, string? OhmEndRaw = null,
    JsonElement? Provenance = null, IReadOnlyDictionary<string, string>? Note = null);

public sealed record SovereigntyRecordDto(
    Guid Id, Guid RegimeId, DatePeriodDto ValidPeriod, string LayerStatus, Guid? StartEventId, Guid? EndEventId,
    Guid GeometrySourceId, string GeometryLocator, string GeometryLicense, string? Attribution,
    long? OhmRelationId, int? OhmVersion, DateTimeOffset? OhmFetchedAt);

/// <summary>疆界變動事件摘要。verification：verified（有合格引用）| pending（待查證：尚無合格引用）。</summary>
public sealed record SovereigntyEventRefDto(
    Guid Id, string EventKind, DatePeriodDto Occurred, IReadOnlyDictionary<string, string>? Summary,
    string Verification, IReadOnlyList<CitationDto> Citations);

/// <summary>幾何出處：來源（資料集）＋locator（關係 id／版本）＋此筆幾何授權與署名。</summary>
public sealed record GeometryProvenanceDto(
    Guid SourceId, string SourceTitle, string Publisher, string? SourceLicenseCode, string Locator,
    string GeometryLicense, string? Attribution, long? OhmRelationId, int? OhmVersion, DateTimeOffset? OhmFetchedAt,
    string? OhmStartRaw, string? OhmEndRaw, JsonElement? Flags);

/// <summary>
/// 主權圖層要素屬性。地圖依 regimeSlug 上色（一個政權一種顏色）；陣營只作補充（regimeAlignment），不決定填色。
/// </summary>
public sealed record SovereigntyFeatureProperties(
    Guid RecordId, Guid RegimeId, string RegimeSlug, string LayerStatus, DatePeriodDto ValidPeriod,
    SovereigntyEventRefDto? StartEvent, SovereigntyEventRefDto? EndEvent, GeometryProvenanceDto Geometry,
    IReadOnlyDictionary<string, string>? Note, RegimeAlignmentDto? RegimeAlignment = null);

public sealed record SovereigntyFeature(Guid Id, JsonElement Geometry, SovereigntyFeatureProperties Properties)
{
    public string Type => "Feature";
}

public sealed record SovereigntyFeatureCollection(IReadOnlyList<SovereigntyFeature> Features)
{
    public string Type => "FeatureCollection";
}

public sealed record SovereigntyMapDto(DateOnly Date, SovereigntyFeatureCollection FeatureCollection);

// ───────────── 衝突圖示（交叉雙劍；2026-10-31 試驗 feature/borders-1938-1940，AI 提案・待拍板） ─────────────
/// <summary>
/// 新增衝突。regimeAId／regimeBId＝交戰雙方；startEventId（開戰事件）必填，endEventId（停戰／投降）可空。
/// 顯示期間由事件推得：[開戰日, 結束日 + 1)。location＝圖示位置（GeoJSON Point），locationMethod 說明位置怎麼算的。
/// </summary>
public sealed record CreateConflictRecordRequest(
    Guid? RegimeAId, Guid? RegimeBId, Guid? StartEventId, Guid? EndEventId,
    JsonElement? Location, string? LocationMethod, IReadOnlyDictionary<string, string>? Note = null);

public sealed record ConflictRecordDto(
    Guid Id, Guid RegimeAId, Guid RegimeBId, Guid StartEventId, Guid? EndEventId, DatePeriodDto ValidPeriod,
    JsonElement Location, string LocationMethod);

/// <summary>衝突圖示屬性：起訖事件與主權卡同一結構（事件名稱、日期、查證狀態、出處）。</summary>
public sealed record ConflictFeatureProperties(
    Guid RecordId, Guid RegimeAId, string RegimeASlug, Guid RegimeBId, string RegimeBSlug, DatePeriodDto ValidPeriod,
    SovereigntyEventRefDto StartEvent, SovereigntyEventRefDto? EndEvent, string LocationMethod,
    IReadOnlyDictionary<string, string>? Note);

public sealed record ConflictFeature(Guid Id, JsonElement Geometry, ConflictFeatureProperties Properties)
{
    public string Type => "Feature";
}

public sealed record ConflictFeatureCollection(IReadOnlyList<ConflictFeature> Features)
{
    public string Type => "FeatureCollection";
}

public sealed record ConflictMapDto(DateOnly Date, ConflictFeatureCollection FeatureCollection);
