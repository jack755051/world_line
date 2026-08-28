namespace WorldLine.Api.Domain;

/// <summary>
/// 憲法 §4 政權狀態機的四種狀態（存續／分裂／被取代(禪讓)／被滅亡）。
/// 資料庫存的是中立英文代碼（2026-08-28 從中文字面值改過來，見 PRD §6 設計原則），
/// 憲法本身的中文業務詞彙才是權威定義，這裡只是型別安全的程式碼表示。
/// 純型別定義，不含轉換/驗證邏輯——字串代碼轉換見 <see cref="RegimeStatusCodes"/>，
/// 合法轉換規則見 <see cref="RegimeTransitionValidator"/>。
/// </summary>
public enum RegimeStatus
{
    Active,
    Split,
    Succeeded,
    Conquered,
}
