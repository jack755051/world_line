namespace WorldLine.Api.Contracts;

/// <summary>`GET /api/v1/event-tags` 的回應形狀（task 2.11），也重用在
/// `HistoricalEventResponse.Tags`——同一個政權查一次可用標籤清單，跟每筆事件自己
/// 掛哪些標籤，是同一個資料形狀（id + 名稱），不用另外設計第二種。不支援
/// `?locale=`——PRD §6「次要/輔助內容」清單明講 `event_tags.tag_name` 目前是待評估、
/// 不現在處理的翻譯範圍，不是遺漏。</summary>
public class EventTagResponse
{
    public required int Id { get; init; }
    public required string TagName { get; init; }
}
