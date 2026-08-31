namespace WorldLine.Api.Contracts;

/// <summary>
/// `PATCH /api/v1/regimes/:id` 的請求形狀（task 2.5）——目前唯一用途是憲法 §4 的狀態
/// 轉換（`active` → `split`／`succeeded`／`conquered`），不是通用的「改任何欄位」端點。
/// 沒有開放 `selfName`／`predecessorRegimeId`／`originTransitionType` 的修改——這些是
/// 建立時就定案的起源事實，不是這個端點的範圍（跟 task 名稱「政權寫入端點」裡
/// PATCH 只負責「呼叫 2.1 驗證器擋非法轉換」的敘述一致）。
/// </summary>
public class UpdateRegimeRequest
{
    /// <summary>目標狀態，受控值見 `Domain.RegimeStatus`（`RegimeTransitionValidator.
    /// ValidateStatusTransition` 驗證是否為合法轉換）。</summary>
    public required string Status { get; init; }

    /// <summary>消滅方政權——`Status` 為 `conquered` 時必填，其餘狀態必須留空（見
    /// `SeedData.cs` 既有慣例：只有 `conquered` 的政權才會設這個欄位）。</summary>
    public Guid? DestroyedByRegimeId { get; init; }
}
