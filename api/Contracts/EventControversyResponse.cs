using System.Text.Json;

namespace WorldLine.Api.Contracts;

/// <summary>
/// `GET /api/v1/events/{eventId}/controversies`／`POST .../controversies` 的回應形狀
/// （task 2.13）。支援 `?locale=`：僅 `topic`/`neutralDescription` 在翻譯範圍內
/// （`historical_event_controversy_translations`，task 2.16），`viewpoints`（誰主張
/// 什麼）不翻譯，同 `RegimesController` 既有慣例。
/// </summary>
public class EventControversyResponse
{
    public required Guid Id { get; init; }
    public required string EventId { get; init; }
    public required string Topic { get; init; }
    public required string NeutralDescription { get; init; }

    /// <summary>慣例形狀（task 2.13 拍板，見 <see cref="CreateEventControversyRequest"/>
    /// 類別註解）：陣列，每筆 <c>{ "stance": "...", "source": "..." }</c>。</summary>
    public JsonElement? Viewpoints { get; init; }
}
