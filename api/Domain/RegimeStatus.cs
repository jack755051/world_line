namespace WorldLine.Api.Domain;

/// <summary>
/// 憲法 §4 政權狀態機的四種狀態（存續／分裂／被取代(禪讓)／被滅亡）。
/// 資料庫存的是中立英文代碼（2026-08-28 從中文字面值改過來，見 PRD §6 設計原則），
/// 憲法本身的中文業務詞彙才是權威定義，這裡只是型別安全的程式碼表示。
/// </summary>
public enum RegimeStatus
{
    Active,
    Split,
    Succeeded,
    Conquered,
}

/// <summary>
/// 政權「起源」轉換的類型——只有 Split（分裂而來）與 Succeeded（被取代/禪讓而來）兩種，
/// 沒有 Conquered：政權不會是「被消滅出來的」，消滅是終止方式，不是起源方式。
/// </summary>
public enum RegimeOriginTransitionType
{
    Split,
    Succeeded,
}

/// <summary>
/// <see cref="RegimeStatus"/>/<see cref="RegimeOriginTransitionType"/> 與資料庫實際儲存的小寫
/// 字串代碼之間的雙向轉換。獨立集中在這裡，是因為這兩個欄位先前直接存中文字面值時，
/// 曾經在只有 5 筆種子資料時就飄出兩種寫法（見 2026-08-28 commit 958666e）——把轉換邏輯
/// 收斂到單一個 Dictionary 對照表，之後不會再有第二處自己拼字串的地方。
/// </summary>
public static class RegimeStatusCodes
{
    private static readonly Dictionary<string, RegimeStatus> StatusByCode = new(StringComparer.Ordinal)
    {
        ["active"] = RegimeStatus.Active,
        ["split"] = RegimeStatus.Split,
        ["succeeded"] = RegimeStatus.Succeeded,
        ["conquered"] = RegimeStatus.Conquered,
    };

    private static readonly Dictionary<string, RegimeOriginTransitionType> OriginTypeByCode = new(StringComparer.Ordinal)
    {
        ["split"] = RegimeOriginTransitionType.Split,
        ["succeeded"] = RegimeOriginTransitionType.Succeeded,
    };

    public static bool TryParseStatus(string? code, out RegimeStatus status) =>
        StatusByCode.TryGetValue(code ?? string.Empty, out status);

    public static bool TryParseOriginType(string? code, out RegimeOriginTransitionType type) =>
        OriginTypeByCode.TryGetValue(code ?? string.Empty, out type);

    public static string ToCode(this RegimeStatus status) => status switch
    {
        RegimeStatus.Active => "active",
        RegimeStatus.Split => "split",
        RegimeStatus.Succeeded => "succeeded",
        RegimeStatus.Conquered => "conquered",
        _ => throw new ArgumentOutOfRangeException(nameof(status), status, "未知的 RegimeStatus 值"),
    };

    public static string ToCode(this RegimeOriginTransitionType type) => type switch
    {
        RegimeOriginTransitionType.Split => "split",
        RegimeOriginTransitionType.Succeeded => "succeeded",
        _ => throw new ArgumentOutOfRangeException(nameof(type), type, "未知的 RegimeOriginTransitionType 值"),
    };
}
