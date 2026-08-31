using System.Text.Json;
using NetTopologySuite.Geometries;

namespace WorldLine.Api.Contracts;

/// <summary>
/// `GET /api/v1/events`／`GET /api/v1/events/{id}`／`POST /api/v1/events` 的回應形狀
/// （task 2.10）。
/// </summary>
public class HistoricalEventResponse
{
    public required string Id { get; init; }
    public required string Name { get; init; }
    public required string? ParentEventId { get; init; }
    public required string StartEdtf { get; init; }
    public required string EndEdtf { get; init; }
    public required decimal StartDecimal { get; init; }
    public required decimal EndDecimal { get; init; }

    /// <summary>資料庫存的是 jsonb 原始文字（見 <c>HistoricalEvent.Sections</c> 的類別註解），
    /// 這裡解析回真正的巢狀 JSON 值，不是把整個 JSON 字串再包一層字串——不然前端還要多做
    /// 一次 <c>JSON.parse()</c> 才能用，等於把後端的實作細節（jsonb 存成字串）洩漏給前端。</summary>
    public JsonElement? Sections { get; init; }

    public Point? OriginPoint { get; init; }
    public MultiPolygon? InfluenceArea { get; init; }
    public MultiLineString? Routes { get; init; }

    /// <summary>task 2.11：這筆事件掛的 `event_tags`，跟 `CreateHistoricalEventRequest.
    /// TagIds` 對應——沒掛任何標籤時是空陣列，不是 `null`（讀端不用另外判斷 null）。</summary>
    public required IReadOnlyList<EventTagResponse> Tags { get; init; }
}
