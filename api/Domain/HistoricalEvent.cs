using NetTopologySuite.Geometries;

namespace WorldLine.Api.Domain;

/// <summary>
/// 歷史事件骨幹（客觀事實層，PRD §6）。時間以 EDTF 字串為 single source of truth，
/// start_decimal / end_decimal 由後端寫入時自動推算（<see cref="Edtf.EdtfDate"/>），不可手動分別填寫。
/// </summary>
public class HistoricalEvent
{
    /// <summary>人類可讀的 slug，例：battle-of-talas-751。</summary>
    public string Id { get; set; } = null!;
    public string Name { get; set; } = null!;

    /// <summary>組成關係：大事件底下的子事件，同時驅動語意縮放。</summary>
    public string? ParentEventId { get; set; }
    public HistoricalEvent? ParentEvent { get; set; }

    public string StartEdtf { get; set; } = null!;
    public string EndEdtf { get; set; } = null!;
    public decimal StartDecimal { get; set; }
    public decimal EndDecimal { get; set; }

    /// <summary>
    /// 事件發生地時區（IANA，例：Pacific/Honolulu）。憲法 §9 2026-10-28：日期以發生地當地日期為準，另附時區備註。
    /// </summary>
    public string? TimeZone { get; set; }

    /// <summary>時區／跨時區說明（例：「日本時間為 1941-12-08」）。</summary>
    public string? TimeNote { get; set; }

    public Point? OriginPoint { get; set; }
    public MultiPolygon? InfluenceArea { get; set; }
    public MultiLineString? Routes { get; set; }

    /// <summary>手風琴三層結構化內容（背景起因／關鍵轉折時間點／歷史影響），JSON。</summary>
    public string? Sections { get; set; }

    public DateTimeOffset CreatedAt { get; set; }
    public DateTimeOffset UpdatedAt { get; set; }
    public int Version { get; set; }

    public List<HistoricalEventTagMap> Tags { get; set; } = [];
    public List<HistoricalEventPerspective> Perspectives { get; set; } = [];
    public List<HistoricalEventControversy> Controversies { get; set; } = [];
}

/// <summary>事件類型標籤（多對多，取代單一 event_type）。</summary>
public class EventTag
{
    public int Id { get; set; }
    /// <summary>例：war、trade、reform、revolution、treaty（小寫英文代碼，UI 再翻譯）。</summary>
    public string TagName { get; set; } = null!;
}

public class HistoricalEventTagMap
{
    public string EventId { get; set; } = null!;
    public HistoricalEvent Event { get; set; } = null!;
    public int TagId { get; set; }
    public EventTag Tag { get; set; } = null!;
}

/// <summary>非政權觀察者的受控類別（國際第三者、後世史學界…），取代自由文字。</summary>
public class ObserverCategory
{
    public int Id { get; set; }
    public string CategoryName { get; set; } = null!;
}

/// <summary>各方主觀敘事層。regime_id 與 observer_category_id 恰好擇一。</summary>
public class HistoricalEventPerspective
{
    public Guid Id { get; set; }
    public string EventId { get; set; } = null!;
    public HistoricalEvent Event { get; set; } = null!;
    public Guid? RegimeId { get; set; }
    public Regime? Regime { get; set; }
    public int? ObserverCategoryId { get; set; }
    public ObserverCategory? ObserverCategory { get; set; }
    public string LocalName { get; set; } = null!;
    public string NarrativeSummary { get; set; } = null!;
    public string? OfficialJustification { get; set; }
    /// <summary>JSON 陣列。</summary>
    public string? PrimarySources { get; set; }
    /// <summary>JSON 物件。</summary>
    public string? ClaimedCasualties { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
}

/// <summary>
/// 爭議點層。viewpoints 為 JSON 陣列，每個元素 { "holder": 持論者, "summary": 觀點摘要, "sources": [文獻…] }；
/// DB 只檢查是陣列，sources 非空由寫入端（服務層）負責（PRD §6 TODO 的決定）。
/// </summary>
public class HistoricalEventControversy
{
    public Guid Id { get; set; }
    public string EventId { get; set; } = null!;
    public HistoricalEvent Event { get; set; } = null!;
    public string Topic { get; set; } = null!;
    public string NeutralDescription { get; set; } = null!;
    public string? Viewpoints { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
}
