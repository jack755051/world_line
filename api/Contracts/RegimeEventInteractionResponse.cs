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
    /// <summary>原始 EDTF 字串（例："0220"、"1046?"）——task 3.10（Story 5「模糊/爭議
    /// 年份的呈現」）需要這個，不能只給 <see cref="StartDecimal"/>：`?`/`~` 不確定標記、
    /// 以及「只精確到年還是精確到日」這個精度層級，只有原始字串留得住，decimal 換算
    /// 過程本身就會把這些資訊丟失（見 `EdtfService`/`EdtfDate` 的說明）。</summary>
    public required string StartEdtf { get; init; }
    public required string EndEdtf { get; init; }
    public required decimal StartDecimal { get; init; }
    public required decimal EndDecimal { get; init; }
}
