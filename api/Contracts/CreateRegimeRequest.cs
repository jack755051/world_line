namespace WorldLine.Api.Contracts;

/// <summary>
/// `POST /api/v1/regimes` 的請求形狀（task 2.5）。**不接受 `status`**——新建的政權一律
/// 從 <see cref="Domain.RegimeStatus.Active"/> 開始（憲法 §4 合法轉換全部從 Active
/// 出發，見 `RegimeTransitionValidator`），要變成分裂/禪讓/滅亡是之後另外呼叫
/// `PATCH /api/v1/regimes/:id` 的事，不是建立當下就能決定終局狀態。
/// </summary>
public class CreateRegimeRequest
{
    /// <summary>I2 校驗必填——政權自稱名稱。</summary>
    public required string SelfName { get; init; }

    /// <summary>前身政權；獨立建國則為 `null`。必須跟 <see cref="OriginTransitionType"/>
    /// 同時有值或同時為空（`RegimeTransitionValidator.ValidateOriginLinkage`）。</summary>
    public Guid? PredecessorRegimeId { get; init; }

    /// <summary>受控值只有 `split`／`succeeded`（見 `Domain.RegimeOriginTransitionType`）
    /// ——沒有 `conquered`，消滅是終止方式不是起源方式。</summary>
    public string? OriginTransitionType { get; init; }
}
