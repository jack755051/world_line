namespace WorldLine.Api.Domain;

/// <summary>
/// task 2.9a：<c>regime_aliases.alias_type</c> 的受控值（PRD §12 TODO，2026-08-30 拍板）。
/// 跟 <see cref="RegimeStatus"/> 不同，這裡沒有狀態機/合法轉換規則要驗證，只是描述性
/// 分類，不需要真的 enum + 轉換字典這麼重的機制，直接用字串常數 + <c>HashSet</c> 驗證
/// 就夠。
///
/// **四個值不是憑空發明的分類**——動工前先看了種子資料既有的兩筆代稱，發現「他稱的理由」
/// 本身就已經展現出不同性質：
/// - <see cref="Political"/>：政治敵意稱呼（例：蜀漢視角稱魏為「賊」，見《出師表》
///   「漢賊不兩立」——`api/Data/SeedData.cs` 的 `weiAlias`）
/// - <see cref="Scholarly"/>：後世史學消歧義稱呼，不依附任何特定政權視角（例：「孫吳」，
///   用來跟十國吳區隔——`api/Data/SeedData.cs` 的 `wuAlias`，`ObserverRegimeId` 是 null）
/// - <see cref="Transliteration"/>：音譯外來稱呼（`regime_aliases` schema 註解原本就舉
///   的例子：唐朝視角下阿拉伯帝國「大食」、拜占庭「拂菻」——PRD Story 3 的核心案例，
///   目前種子資料還沒有這個時代的政權，先把類別留好，等真的匯入才有資料可以標）
/// - <see cref="Geographic"/>：地理方位代稱——跟音譯不同，音譯是聲音的近似，地理代稱是
///   描述性質的（例如以所在方位稱呼），成因不同，值得分開
///
/// 跟 `observer_regime_id` 的關係：`observer_regime_id` 回答「誰給的稱呼」（可以是
/// null，代表通用他稱），`alias_type` 回答「為什麼這樣稱呼」，兩個維度正交——同一個
/// political 稱呼可以是任何一個 observer 給的，這就是這個欄位比單靠 `observer_regime_id`
/// 多出來的語意（PRD §12 TODO 原文「若無法提供比 observer relationship 更清楚的語意，
/// 移除欄位」——這裡確認提供得出來，保留欄位）。
/// </summary>
public static class RegimeAliasType
{
    public const string Political = "political";
    public const string Scholarly = "scholarly";
    public const string Transliteration = "transliteration";
    public const string Geographic = "geographic";

    private static readonly HashSet<string> AllValues = [Political, Scholarly, Transliteration, Geographic];

    /// <summary><c>null</c> 合法（欄位本身是 nullable，代表「沒有分類/不確定」），
    /// 只有「有值但不是這四個之一」才算不合法。</summary>
    public static bool IsValid(string? value) => value is null || AllValues.Contains(value);
}
