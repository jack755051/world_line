namespace WorldLine.Api.Domain;

/// <summary>結果物件：合法與否 + 不合法時的人類可讀原因（供 §7 統一回應格式的 message 使用）。</summary>
public readonly record struct RegimeTransitionValidationResult(bool IsLegal, string? Reason)
{
    public static RegimeTransitionValidationResult Legal() => new(true, null);
    public static RegimeTransitionValidationResult Illegal(string reason) => new(false, reason);
}

public interface IRegimeTransitionValidator
{
    /// <summary>既有政權的 status 從 <paramref name="currentStatusCode"/> 改成
    /// <paramref name="requestedStatusCode"/> 是否合法（憲法 §4）。</summary>
    RegimeTransitionValidationResult ValidateStatusTransition(string? currentStatusCode, string? requestedStatusCode);

    /// <summary>新建政權的 predecessor_regime_id／origin_transition_type 組合是否內部一致。</summary>
    RegimeTransitionValidationResult ValidateOriginLinkage(Guid? predecessorRegimeId, string? originTransitionTypeCode);
}

/// <summary>
/// 憲法 §4 政權狀態機合法轉換規則的唯一信任來源（後端）。前端 XState（Phase 3 任務 3.1）
/// 只做 UI 層防呆，不是信任邊界——即使前端沒擋住、request 直接打 API，這裡也要擋下來
/// （PRD §5「XState 前後端狀態機驗證分工」已拍板）。
/// </summary>
public class RegimeTransitionValidator : IRegimeTransitionValidator
{
    // 憲法 §4：合法轉換只有這三條，全部只能從 Active 出發；一旦進入三個終止狀態
    // （Split/Succeeded/Conquered），沒有任何合法的後續轉換——「取代跟消滅應該是兩種不同的
    // 定義」，不可合併，也不可逆轉（不會有政權從「被滅亡」變回「存續」）。
    private static readonly HashSet<(RegimeStatus From, RegimeStatus To)> LegalStatusTransitions =
    [
        (RegimeStatus.Active, RegimeStatus.Split),
        (RegimeStatus.Active, RegimeStatus.Succeeded),
        (RegimeStatus.Active, RegimeStatus.Conquered),
    ];

    public RegimeTransitionValidationResult ValidateStatusTransition(string? currentStatusCode, string? requestedStatusCode)
    {
        if (!RegimeStatusCodes.TryParseStatus(currentStatusCode, out var current))
        {
            return RegimeTransitionValidationResult.Illegal($"未知的目前狀態代碼：{currentStatusCode}");
        }

        if (!RegimeStatusCodes.TryParseStatus(requestedStatusCode, out var requested))
        {
            return RegimeTransitionValidationResult.Illegal($"未知的目標狀態代碼：{requestedStatusCode}");
        }

        if (current == requested)
        {
            return RegimeTransitionValidationResult.Illegal("目標狀態與目前狀態相同，不構成轉換");
        }

        return LegalStatusTransitions.Contains((current, requested))
            ? RegimeTransitionValidationResult.Legal()
            : RegimeTransitionValidationResult.Illegal(
                $"「{current.ToCode()} → {requested.ToCode()}」不是憲法 §4 允許的合法轉換");
    }

    public RegimeTransitionValidationResult ValidateOriginLinkage(Guid? predecessorRegimeId, string? originTransitionTypeCode)
    {
        var hasPredecessor = predecessorRegimeId.HasValue;
        var hasOriginTypeCode = !string.IsNullOrEmpty(originTransitionTypeCode);

        // I1/I2 精神的延伸：有前身就必須說明是哪種轉換產生的；獨立建國（無前身）則不該帶
        // origin_transition_type——兩者必須同時有值或同時為空，不允許只填一半。
        if (hasPredecessor != hasOriginTypeCode)
        {
            return RegimeTransitionValidationResult.Illegal(
                "predecessor_regime_id 與 origin_transition_type 必須同時有值（有前身的政權）或同時為空（獨立建國）");
        }

        if (!hasPredecessor)
        {
            return RegimeTransitionValidationResult.Legal(); // 獨立建國，無前身，合法
        }

        return RegimeStatusCodes.TryParseOriginType(originTransitionTypeCode, out _)
            ? RegimeTransitionValidationResult.Legal()
            : RegimeTransitionValidationResult.Illegal(
                $"未知或不合法的起源轉換類型：{originTransitionTypeCode}（只能是 split 或 succeeded，" +
                "被滅亡的政權不會是「起源」轉換）");
    }
}
