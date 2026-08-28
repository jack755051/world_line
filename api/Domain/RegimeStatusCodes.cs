namespace WorldLine.Api.Domain;

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
