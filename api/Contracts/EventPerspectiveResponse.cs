using System.Text.Json;

namespace WorldLine.Api.Contracts;

/// <summary>
/// `GET /api/v1/events/{eventId}/perspectives`／`POST .../perspectives` 的回應形狀
/// （task 2.12）。**沒有 `?locale=`**：`historical_event_perspectives` 整張表不進翻譯
/// 範圍（立場性敘事，各自用原語言寫，見 PRD §6「多重視角並列」）。
/// </summary>
public class EventPerspectiveResponse
{
    public required Guid Id { get; init; }
    public required string EventId { get; init; }
    public required Guid? RegimeId { get; init; }
    public required int? ObserverCategoryId { get; init; }
    public required string LocalName { get; init; }
    public required string NarrativeSummary { get; init; }
    public string? OfficialJustification { get; init; }

    /// <summary>資料庫存 jsonb 原始文字，回傳時解析回真正的巢狀 JSON 值——同
    /// `HistoricalEventResponse.Sections` 的處理原則，見該類別註解。慣例形狀（task 2.12
    /// 拍板，見 <see cref="CreateEventPerspectiveRequest"/> 類別註解）：陣列，每筆
    /// <c>{ "title": "...", "author": "...", "year": 1937 }</c>。</summary>
    public JsonElement? PrimarySources { get; init; }

    /// <summary>慣例形狀：物件，例如 <c>{ "own_loss": "...", "enemy_loss": "..." }</c>，
    /// 鍵名依史料實際記載彈性增減，不強制固定清單。</summary>
    public JsonElement? ClaimedCasualties { get; init; }
}
