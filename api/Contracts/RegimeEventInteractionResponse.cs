namespace WorldLine.Api.Contracts;

/// <summary>
/// `GET /api/v1/regimes/{regimeId}/events` 的回應形狀（PRD Story 2 AC#3「互動清單」）——
/// 一筆代表「這個政權（路由 `regimeId`）跟 <see cref="OtherRegimeId"/> 在
/// <see cref="EventId"/> 這個事件裡有記錄在案的互動」，不是「這個政權存在的當下剛好也有
/// 其他事件發生」。判斷來源見 `EventsController.GetInteractionsByRegime()` 的方法註解。
/// </summary>
public class RegimeEventInteractionResponse
{
    public required string EventId { get; init; }
    public required string EventName { get; init; }
    public required Guid OtherRegimeId { get; init; }
    public required decimal StartDecimal { get; init; }
    public required decimal EndDecimal { get; init; }
}
