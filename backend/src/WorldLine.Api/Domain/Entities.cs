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
    /// <summary>來源等級 A／B／C／X（docs/source-rules.md §2）；NULL＝尚未評等。評的是這份出處本身，不因來源數目更動。</summary>
    public string? Grade { get; set; }
    /// <summary>評等依據（為什麼是這一級）。</summary>
    public string? GradeBasis { get; set; }
    /// <summary>來源家族：同機構、同底稿或互相轉引者填同一個代號，只算一個獨立來源；NULL＝自成一族。</summary>
    public string? Family { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
    public DateTimeOffset UpdatedAt { get; set; }
    public int Version { get; set; }
}

public sealed class Regime
{
    public Guid Id { get; set; }
    public string Slug { get; set; } = "";
    public string? WikidataQid { get; set; }
    /// <summary>名稱與起訖的出處（docs/source-rules.md §6）；NULL＝只取自資料集，待查證。</summary>
    public Guid? SourceId { get; set; }
    public string? SourceLocator { get; set; }
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

/// <summary>持續關係（PRD §6.3；§6「政權間互動」(2)）。</summary>
public sealed class RegimeRelation
{
    public Guid Id { get; set; }
    public Guid RegimeAId { get; set; }
    public Guid RegimeBId { get; set; }
    public string RelationType { get; set; } = "";
    public NpgsqlRange<DateOnly> ValidPeriod { get; set; }
    public NpgsqlRange<DateOnly>? StartUncertainty { get; set; }
    public NpgsqlRange<DateOnly>? EndUncertainty { get; set; }
    public string? Note { get; set; }
    public DateTimeOffset? RetractedAt { get; set; }
    public string? RetractionReason { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
    public int Version { get; set; }
}

/// <summary>
/// 歷史事件（PRD §6.3）。日期記事件發生地的「當地日期」；另有選填多語時間備註
/// （Tai 2026-10-28 修正：不記時區欄位，例：珍珠港 1941-12-07，備註「東京時間 12 月 8 日」）。
/// </summary>
public sealed class HistoricalEvent
{
    public Guid Id { get; set; }
    public string EventKind { get; set; } = "";
    public Guid? ParentEventId { get; set; }
    public string? Summary { get; set; }
    public NpgsqlRange<DateOnly> Occurred { get; set; }
    public string DatePrecision { get; set; } = DatePrecisions.Day;
    public string? TimeNote { get; set; }
    public Geometry? Location { get; set; }
    public DateTimeOffset? RetractedAt { get; set; }
    public string? RetractionReason { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
    public DateTimeOffset UpdatedAt { get; set; }
    public int Version { get; set; }
}

/// <summary>
/// 陣營時間切片（憲法 §6「陣營」、PRD §6.3 regime_alignments）：政權在某期間屬於哪一個陣營。
/// 起點＝有文件的正式加入日（條約簽署、宣戰／參戰日）；迄日未知可無界。同一政權的有效切片不可重疊（EXCLUDE）。
/// 修正走軟撤回（retracted_at＋原因，I5），不硬刪。
/// </summary>
public sealed class RegimeAlignment
{
    public Guid Id { get; set; }
    public Guid RegimeId { get; set; }
    public string Camp { get; set; } = "";
    public NpgsqlRange<DateOnly> ValidPeriod { get; set; }
    public Guid? BasisEventId { get; set; }
    public string? Note { get; set; }
    public DateTimeOffset? RetractedAt { get; set; }
    public string? RetractionReason { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
    public int Version { get; set; }
    public List<RegimeAlignmentCitation> Citations { get; set; } = [];
}

/// <summary>陣營切片的引用（PRD §6.3「regime_alignment_citations，格式同其他 citation 表」）。</summary>
public sealed class RegimeAlignmentCitation
{
    public Guid RegimeAlignmentId { get; set; }
    public Guid SourceId { get; set; }
    public string Locator { get; set; } = "";
    public string Role { get; set; } = CitationRoles.Primary;
    public string EvidenceNote { get; set; } = "";
}

/// <summary>事件參與方（PRD §6.3 event_participants；2026-10-31 實作，AI 提案・待拍板）。寫入後不可改、不可刪（I5）。</summary>
public sealed class EventParticipant
{
    public Guid EventId { get; set; }
    public Guid RegimeId { get; set; }
    public string Role { get; set; } = "";
    /// <summary>事後追加（方案 A，Tai 2026-10-31）的時間；隨事件一起寫入的為 null。</summary>
    public DateTimeOffset? AddedAt { get; set; }
    /// <summary>追加理由（多語 jsonb，追加時必填）。</summary>
    public string? AdditionNote { get; set; }
}

/// <summary>
/// 事件引文的等級（docs/source-rules.md §2：評的是實際讀到的那份文件，不是整冊）。
/// event_citations 寫入後不可改，所以等級另存一表；有這一列時優先於 sources.grade。更正用「撤回＋重寫」（I5）。
/// </summary>
public sealed class EventCitationGrade
{
    public Guid Id { get; set; }
    public Guid EventId { get; set; }
    public Guid SourceId { get; set; }
    public string Locator { get; set; } = "";
    public string Grade { get; set; } = "";
    public string GradeBasis { get; set; } = "";
    public DateTimeOffset? RetractedAt { get; set; }
    public string? RetractionReason { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
}

/// <summary>事件引用（PRD §6.3 event_citations；格式同其他 citation 表）。寫入後不可改、不可刪（I5）。</summary>
public sealed class EventCitation
{
    public Guid EventId { get; set; }
    public Guid SourceId { get; set; }
    public string Locator { get; set; } = "";
    public string EvidenceNote { get; set; } = "";
}

/// <summary>
/// 涵蓋備註（PRD §6.3 control_coverage_notes、§6.4 選項 C）：說明某範圍某期間「控制資料缺」的原因，
/// 不產生任何控制類型（R9）。修正走軟撤回（retracted_at＋原因，I5）。
/// </summary>
public sealed class ControlCoverageNote
{
    public Guid Id { get; set; }
    public Guid? TheaterId { get; set; }
    public MultiPolygon Geom { get; set; } = null!;
    public NpgsqlRange<DateOnly> ValidPeriod { get; set; }
    public string Reason { get; set; } = "";
    public string? Note { get; set; }
    public string? ResearchRef { get; set; }
    public DateTimeOffset? RetractedAt { get; set; }
    public string? RetractionReason { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
    public int Version { get; set; }
}

/// <summary>
/// 主權圖層（法理國界，sovereignty_records）：某政權在某期間的國土範圍，與控制區圖層（control_records）分開。
/// - 幾何來自外部資料集（目前為 OpenHistoricalMap admin_level=2 關係），釘選關係 id＋版本＋抓取時間。
/// - 疆界變動由起訖事件（historical_events）說明；事件沒有合格引用即為「待查證」，不推測。
/// - 同一政權的有效紀錄期間不可重疊（EXCLUDE）；修正走軟撤回（I5），不硬刪。
/// 2026-10-31 試驗（feature/borders-1938-1940），AI 提案・待拍板。
/// </summary>
public sealed class SovereigntyRecord
{
    public Guid Id { get; set; }
    public Guid RegimeId { get; set; }
    public MultiPolygon Geom { get; set; } = null!;
    public NpgsqlRange<DateOnly> ValidPeriod { get; set; }
    /// <summary>de_jure（法理國土）| not_sovereign（資料集列為國家層級、但其實是佔領行政區，非主權）。</summary>
    public string LayerStatus { get; set; } = SovereigntyLayerStatuses.DeJure;
    public Guid? StartEventId { get; set; }
    public Guid? EndEventId { get; set; }
    public Guid GeometrySourceId { get; set; }
    public string GeometryLocator { get; set; } = "";
    /// <summary>幾何本身的授權（逐筆判定：成員線段帶 CC BY 標籤者為 cc_by，否則依 OHM 整體的 cc0）。</summary>
    public string GeometryLicense { get; set; } = "";
    public string? Attribution { get; set; }
    public long? OhmRelationId { get; set; }
    public int? OhmVersion { get; set; }
    public DateTimeOffset? OhmFetchedAt { get; set; }
    public string? OhmStartRaw { get; set; }
    public string? OhmEndRaw { get; set; }
    /// <summary>出處旗標（jsonb 物件）：成員線段的授權／來源統計、需人工審查的項目。</summary>
    public string? Provenance { get; set; }
    public string? Note { get; set; }
    public DateTimeOffset? RetractedAt { get; set; }
    public string? RetractionReason { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
    public int Version { get; set; }
}

/// <summary>
/// 主權紀錄的來歷（docs/source-rules.md §5、D5）。sovereignty_records 寫入後不可改，所以「這一筆是怎麼來的」另存一表：
/// kind＝baseline（第一階段起點時既有）｜continuation（接續同政權的前一筆、形狀相同，只是資料分段）｜
/// minor_revision（接續前一筆、形狀只有細微差異）｜change（接續前一筆、形狀有變）｜new（同政權沒有前一筆）。
/// continuation 的可信程度沿用前一筆；也可事後補上起始事件（StartEventId）。更正用「撤回＋重寫」（I5）。
/// </summary>
public sealed class SovereigntyRecordLink
{
    public Guid Id { get; set; }
    public Guid RecordId { get; set; }
    public string Kind { get; set; } = "";
    public Guid? ContinuesRecordId { get; set; }
    public Guid? StartEventId { get; set; }
    /// <summary>與前一筆的形狀差（對稱差面積／前一筆面積）；沒有前一筆為 null。</summary>
    public double? ShapeChangeRatio { get; set; }
    public string? Note { get; set; }
    public DateTimeOffset? RetractedAt { get; set; }
    public string? RetractionReason { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
}

/// <summary>
/// 佔領歸屬（occupation_attributions）：某政權（非主權的佔領區、併入區）在某期間由哪個政權佔領、控制程度為何。
/// 依政權＋期間（不綁單筆主權紀錄，國界修正撤回再新增時不必重寫）；同一被佔領政權的有效紀錄期間不可重疊（EXCLUDE）。
/// basis_event_id＝有出處的事件；沒有事件或事件沒有引用＝「待查證」。共同佔領缺分區幾何時記主要佔領方並 co_occupied＝true、在 note 註記。
/// I5：不可刪；只允許一次撤回。2026-10-31 試驗，AI 提案・待拍板。
/// </summary>
public sealed class OccupationAttribution
{
    public Guid Id { get; set; }
    public Guid OccupiedRegimeId { get; set; }
    public Guid OccupierRegimeId { get; set; }
    public string ControlKind { get; set; } = "";
    public NpgsqlRange<DateOnly> ValidPeriod { get; set; }
    public Guid? BasisEventId { get; set; }
    public bool CoOccupied { get; set; }
    public string? Note { get; set; }
    public DateTimeOffset? RetractedAt { get; set; }
    public string? RetractionReason { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
    public int Version { get; set; }
}

/// <summary>
/// 衝突（conflict_records）：兩個政權之間的交戰，地圖上在兩國交界畫「交叉雙劍」圖示（Tai 2026-10-31）。
/// - 每筆衝突一定對應有日期的開戰事件（start_event_id 必填）；停戰／投降事件可空（試驗範圍內未結束）。
/// - 顯示期間由事件推得：[開戰日, 停戰或投降日 + 1)，結束日當天仍顯示；不另存可與事件不一致的日期。
/// - 事件沒有合格引用即「待查證」，不推測；圖示位置與算法（location_method）一併存放。
/// - 修正走軟撤回（I5），不硬刪。2026-10-31 試驗（feature/borders-1938-1940），AI 提案・待拍板。
/// </summary>
public sealed class ConflictRecord
{
    public Guid Id { get; set; }
    public Guid RegimeAId { get; set; }
    public Guid RegimeBId { get; set; }
    public Guid StartEventId { get; set; }
    public Guid? EndEventId { get; set; }
    public NpgsqlRange<DateOnly> ValidPeriod { get; set; }
    public Point Location { get; set; } = null!;
    /// <summary>圖示位置怎麼來的（例：兩國主權圖層在開戰日的共同邊界中點）。</summary>
    public string LocationMethod { get; set; } = "";
    public string? Note { get; set; }
    public DateTimeOffset? RetractedAt { get; set; }
    public string? RetractionReason { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
    public int Version { get; set; }
}

/// <summary>
/// 領導人紀錄（leader_records）：某政權在某期間由誰擔任國家元首或政府首腦。
/// - role：head_of_state（國家元首）| head_of_government（政府首腦）。
/// - 每筆附出處文字（source），查不到標「待查證」（verified=false）。
/// - 修正走軟撤回（I5），不硬刪。2026-11-03 試驗，AI 提案・待拍板。
/// </summary>
public sealed class LeaderRecord
{
    public Guid Id { get; set; }
    public Guid RegimeId { get; set; }
    /// <summary>FK → leader_bios.id（選填，同一人多筆任期共用一份生平）。</summary>
    public Guid? PersonId { get; set; }
    public string Name { get; set; } = "";
    public string? NameZh { get; set; }
    /// <summary>head_of_state | head_of_government。</summary>
    public string Role { get; set; } = "";
    /// <summary>選填職銜（如 Reichspräsident）。</summary>
    public string? Title { get; set; }
    public NpgsqlRange<DateOnly> ValidPeriod { get; set; }
    /// <summary>出處文字（「待查證」若未找到文獻）。</summary>
    public string Source { get; set; } = "";
    public string? SourceUrl { get; set; }
    /// <summary>true＝已有可信出處；false＝待查證。</summary>
    public bool Verified { get; set; }
    public DateTimeOffset? RetractedAt { get; set; }
    public string? RetractionReason { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
    public int Version { get; set; }
}

/// <summary>
/// 領導人生平（leader_bios）：一人一筆，跨越多個任期共用。
/// - 與 leader_records（任期粒度）分開，避免同一人多筆任期重複儲存生平且出處難維護。
/// - LeaderRecord.PersonId（nullable FK）指向此表。
/// - birth_place / party / summary：jsonb 雙語 {"zh-Hant": "...", "en": "..."}。
/// - field_sources：各欄位出處 {"birthDate": {"source": "...", "url": "..."}, ...}。
/// - is_test=true 標記測試資料；修正走軟撤回（I5）。2026-11-03 試驗，AI 提案・待拍板。
/// </summary>
public sealed class LeaderBio
{
    public Guid Id { get; set; }
    public string Name { get; set; } = "";
    public string? NameZh { get; set; }
    public DateOnly? BirthDate { get; set; }
    /// <summary>day | month | year（NULL 表示精確度未知）。</summary>
    public string? BirthDatePrecision { get; set; }
    public DateOnly? DeathDate { get; set; }
    /// <summary>出生地（jsonb 雙語）。</summary>
    public string? BirthPlace { get; set; }
    /// <summary>卒地（jsonb 雙語）。ARCHITECTURE §16.6，2026-11-10 新增（B1）；有 conflict 缺口時須為 NULL。</summary>
    public string? DeathPlace { get; set; }
    /// <summary>黨籍（jsonb 雙語）。</summary>
    public string? Party { get; set; }
    /// <summary>簡介（jsonb 雙語）。</summary>
    public string? Summary { get; set; }
    /// <summary>各欄位出處 {"birthDate": {"source": "...", "url": "..."}, ...}。</summary>
    public string? FieldSources { get; set; }
    /// <summary>測試資料標記，測試完成後可依此批次撤回。</summary>
    public bool IsTest { get; set; }
    /// <summary>卒日精確度：day | month | year（NULL 表示精確度未知）。2026-11-07 新增。</summary>
    public string? DeathDatePrecision { get; set; }
    /// <summary>Wikidata 項目（Q 號），只當辨識線索，不是出處。2026-11-07 新增。</summary>
    public string? WikidataQid { get; set; }
    /// <summary>照片檔案 URL（只收允許授權；欄位不全不可寫入，見 CHECK）。2026-11-07 新增。</summary>
    public string? PortraitUrl { get; set; }
    /// <summary>照片出處頁（例：Wikimedia Commons 檔案頁）。</summary>
    public string? PortraitSourceUrl { get; set; }
    public string? PortraitAuthor { get; set; }
    /// <summary>授權代碼，限 <see cref="CitationPolicy.PrimaryLicenseAllowlist"/>。</summary>
    public string? PortraitLicenseCode { get; set; }
    public string? PortraitLicenseUrl { get; set; }
    /// <summary>署名文字（顯示用）。</summary>
    public string? PortraitAttribution { get; set; }
    /// <summary>查證授權的日期。</summary>
    public DateOnly? PortraitRetrievedOn { get; set; }
    /// <summary>撤回重寫時指向取代它的新生平（I5）。2026-11-07 新增。</summary>
    public Guid? SupersededBy { get; set; }
    public DateTimeOffset? RetractedAt { get; set; }
    public string? RetractionReason { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
    public int Version { get; set; }
}

/// <summary>
/// 生平欄位引用（leader_bio_field_citations；2026-11-07）：把生平的單一欄位（或簡介段落）接到 <see cref="Source"/>。
/// - 格式照 event_citations：source_id＋locator＋evidence_note，另加查證日期 accessed_on。
/// - field：name | nameZh | birthDate | deathDate | birthPlace | deathPlace | party | summary | portrait。
/// - 修正走軟撤回（I5），不硬刪。
/// - 2026-11-10（ARCHITECTURE §16.4.1，B1）新增式補欄：quote、quote_lang、grade、date_precision、policy_version，全部可空（舊列留空）。
///   quote 給了就不可空白（DB CHECK）；≤ 80 字（NFC 後字元，Tai 2026-11-10 21:52）只在 <see cref="BioSourcePolicy"/> 檢查。grade DB CHECK 只收 A／B。
/// </summary>
public sealed class LeaderBioFieldCitation
{
    public Guid Id { get; set; }
    public Guid BioId { get; set; }
    public string Field { get; set; } = "";
    public Guid SourceId { get; set; }
    public string Locator { get; set; } = "";
    public string? EvidenceNote { get; set; }
    public DateOnly AccessedOn { get; set; }
    /// <summary>引文原文（證據）；舊列為 NULL，B2 由 seed evidence 回填。</summary>
    public string? Quote { get; set; }
    /// <summary>引文語言（BCP 47），可空。</summary>
    public string? QuoteLang { get; set; }
    /// <summary>來源等級 A｜B（T1）；未評等為 NULL。</summary>
    public string? Grade { get; set; }
    /// <summary>這份來源支撐到的日期精度：day | month | year。</summary>
    public string? DatePrecision { get; set; }
    /// <summary>寫入時的 <see cref="BioSourcePolicy.PolicyVersion"/>。</summary>
    public string? PolicyVersion { get; set; }
    public DateTimeOffset? RetractedAt { get; set; }
    public string? RetractionReason { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
}

/// <summary>
/// 任期引用（leader_record_citations；ARCHITECTURE §16.3-2、§16.4.1，B1，2026-11-10）：
/// 每筆 leader_records 任期可接多筆 sources，取代自由文字 leader_records.source（過渡期該欄只當備註）。
/// 欄位採 §16.4.1 統一 citation 格式；修正走軟撤回（I5，trigger 在 migration 以 SQL 建立）。
/// - Grade：T1 已決只收 A／B（C／X 不進 DB）；DB CHECK 依 Tai 2026-11-10 16:20 核准，於 migration BioCitationFieldsAndGaps 加上（未套用前 DB 尚無此 CHECK）。
/// - PolicyVersion：T2（白名單）未決；寫入時記 <see cref="BioSourcePolicy.PolicyVersion"/>，DB 不檢查。
/// - ClaimSpan：T4 已決選填；任期引用通常不用，保留是為了與其他 citation 表同格式。
/// </summary>
public sealed class LeaderRecordCitation
{
    public Guid Id { get; set; }
    public Guid RecordId { get; set; }
    public Guid SourceId { get; set; }
    /// <summary>頁碼／條目／檔號／URL 錨點。</summary>
    public string Locator { get; set; } = "";
    /// <summary>引文原文（證據，不是顯示用正文）。</summary>
    public string Quote { get; set; } = "";
    /// <summary>引文語言（BCP 47）。</summary>
    public string? QuoteLang { get; set; }
    public string? EvidenceNote { get; set; }
    /// <summary>當天實際打開來源的日期。</summary>
    public DateOnly AccessedOn { get; set; }
    /// <summary>來源等級（T1：A｜B）；NULL＝未評等。</summary>
    public string? Grade { get; set; }
    /// <summary>這份來源支撐到的日期精度：day | month | year。</summary>
    public string? DatePrecision { get; set; }
    /// <summary>選填：支撐的句序號（半開區間）。</summary>
    public NpgsqlRange<int>? ClaimSpan { get; set; }
    /// <summary>寫入當時套用的來源政策版本（§16.4.4，T2 未決，預留）。</summary>
    public string? PolicyVersion { get; set; }
    public DateTimeOffset? RetractedAt { get; set; }
    public string? RetractionReason { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
}

/// <summary>
/// 生平缺口（leader_bio_gaps；ARCHITECTURE §16.4.2，B1，2026-11-10）：記錄「為什麼空」——來源矛盾、查無、身分推定。
/// - 不是資料值：candidate_citations 只並列各說法的證據（source／locator／quote），不得據以填欄位。
/// - 解決時填 resolved_at（與 resolved_by_citation_id），不刪；登錄錯誤走軟撤回。I5 trigger 在 migration 以 SQL 建立。
/// - 「欄位有 conflict 時該欄必須為 NULL」屬寫入層檢查（DB 不跨表檢查）。
/// </summary>
public sealed class LeaderBioGap
{
    public Guid Id { get; set; }
    public Guid BioId { get; set; }
    /// <summary>field:birthDate、field:deathPlace、position:&lt;id&gt;、paragraph:&lt;topic&gt;、identity。</summary>
    public string Target { get; set; } = "";
    /// <summary><see cref="LeaderBioGapKinds"/>。</summary>
    public string GapKind { get; set; } = "";
    public string? Note { get; set; }
    /// <summary>jsonb 陣列：[{source, url, locator, quote, value}]，只是證據並列。</summary>
    public string? CandidateCitations { get; set; }
    public DateOnly CheckedOn { get; set; }
    public DateTimeOffset? ResolvedAt { get; set; }
    /// <summary>解決此缺口的 citation id（可能在任一生平 citation 表，故不設 FK）。</summary>
    public Guid? ResolvedByCitationId { get; set; }
    public DateTimeOffset? RetractedAt { get; set; }
    public string? RetractionReason { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
}

/// <summary>
/// 首都紀錄（capital_records）：某政權在某期間的首都城市與座標，地圖上顯示小圓點＋城市名。
/// - 城市名以雙語 JSON 儲存（{"zh-Hant": "...", "en": "..."}）；Location 為 WGS84 點。
/// - 同一政權在同一時間只能有一筆有效紀錄（EXCLUDE 約束）。
/// - 每筆附 source_ref（出處文字，簡化引用），查不到標「待查證」。
/// - 修正走軟撤回（I5），不硬刪。2026-11-02 試驗，AI 提案・待拍板。
/// </summary>
public sealed class CapitalRecord
{
    public Guid Id { get; set; }
    public Guid RegimeId { get; set; }
    /// <summary>城市名（jsonb 物件：{"zh-Hant": "...", "en": "..."}）。</summary>
    public string CityName { get; set; } = "{}";
    public Point Location { get; set; } = null!;
    public NpgsqlRange<DateOnly> ValidPeriod { get; set; }
    /// <summary>出處文字（「待查證」若未找到文獻）。舊欄位；新資料改用 SourceId＋SourceLocator。</summary>
    public string? SourceRef { get; set; }
    /// <summary>出處接到來源登記（docs/source-rules.md D6）；NULL＝只有自由文字。</summary>
    public Guid? SourceId { get; set; }
    public string? SourceLocator { get; set; }
    public string? Note { get; set; }
    public DateTimeOffset? RetractedAt { get; set; }
    public string? RetractionReason { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
    public int Version { get; set; }
}
