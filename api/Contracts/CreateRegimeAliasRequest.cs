using WorldLine.Api.Domain;

namespace WorldLine.Api.Contracts;

/// <summary>
/// task 2.9a：`POST /api/v1/regimes/:id/aliases` 的 request body——路由的 `{id}` 就是
/// 這筆代稱指回的自稱本體（`regime_id`，I4 FK），body 不重複這個欄位，跟
/// `CreateRegimeRelationRequest` 刻意不重複 `regimeAId` 同一個理由（避免路由參數跟
/// body 兩個等效欄位不一致時該聽誰的這種歧義）。
/// </summary>
public class CreateRegimeAliasRequest
{
    /// <summary>給予此代稱的觀察視角主體；`null` 代表通用他稱，不特定於某個政權視角
    /// （例：「孫吳」，後世史學消歧義用語）。</summary>
    public Guid? ObserverRegimeId { get; set; }

    public string AliasName { get; set; } = null!;

    /// <summary>受控值見 <see cref="Domain.RegimeAliasType"/>；省略/`null` 合法。</summary>
    public string? AliasType { get; set; }
}
