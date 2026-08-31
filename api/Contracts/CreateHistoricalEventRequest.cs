using System.Text.Json;

namespace WorldLine.Api.Contracts;

/// <summary>
/// `POST /api/v1/events` 的請求形狀（task 2.10）。**只涵蓋事件骨幹**：id/name/
/// parent_event_id/start_edtf/end_edtf/sections——task 名稱「事件骨幹 CRUD」本身就
/// 排除了幾件事，不是遺漏：
/// - `origin_point`/`influence_area`/`routes` 這三個地理欄位刻意不開放寫入。現有種子
///   資料完全沒有填過這三欄，也還沒有任何前端畫面會消費它們（事件地圖圖層是 notes §七
///   提到但還沒排進 M3 任務清單的功能），沒有真實資料/消費端可以驗證寫入格式對不對，
///   先只做唯讀（見 `HistoricalEventResponse` 有回傳這三欄），等真的有需求再開放寫入。
/// </summary>
public class CreateHistoricalEventRequest
{
    /// <summary>手動指定的 slug（例："event-marco-polo-bridge"），不是資料庫自動產生——
    /// 見 `HistoricalEvent.Id` 的類別註解。</summary>
    public required string Id { get; init; }
    public required string Name { get; init; }
    public string? ParentEventId { get; init; }
    public required string StartEdtf { get; init; }
    public required string EndEdtf { get; init; }
    public JsonElement? Sections { get; init; }

    /// <summary>task 2.11：這筆事件掛哪些 `event_tags`（受控詞彙，見
    /// `GET /api/v1/event-tags`）。省略/`null`／空陣列代表不掛任何標籤，不是必填。</summary>
    public IReadOnlyList<int>? TagIds { get; init; }
}
