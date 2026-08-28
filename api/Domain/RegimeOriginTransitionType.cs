namespace WorldLine.Api.Domain;

/// <summary>
/// 政權「起源」轉換的類型——只有 Split（分裂而來）與 Succeeded（被取代/禪讓而來）兩種，
/// 沒有 Conquered：政權不會是「被消滅出來的」，消滅是終止方式，不是起源方式。
/// 純型別定義，不含轉換/驗證邏輯——字串代碼轉換見 <see cref="RegimeStatusCodes"/>，
/// 一致性驗證見 <see cref="RegimeTransitionValidator"/>。
/// </summary>
public enum RegimeOriginTransitionType
{
    Split,
    Succeeded,
}
