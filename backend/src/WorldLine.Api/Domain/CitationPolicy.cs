namespace WorldLine.Api.Domain;

/// <summary>
/// I6、R7 中程式可判斷的部分（PRD §6.8 Domain 服務）。「是否真為公有領域或 CC」「引用是否真的支撐資料」仍需人工審查。
/// </summary>
public static class CitationPolicy
{
    /// <summary>
    /// R7：控制軸 primary citation 允許的授權（公有領域或 CC）。
    /// PRD §6.3 的 license_code 清單為 AI 提案；licence_ouverte_2 不屬於公有領域／CC，故不列入（待拍板）。
    /// </summary>
    public static readonly IReadOnlySet<string> PrimaryLicenseAllowlist =
        new HashSet<string>(StringComparer.Ordinal) { "us_federal_pd", "pd_expired", "cc0", "cc_by", "cc_by_sa" };

    /// <summary>R7：只標「自製」的來源不採用。比對時忽略大小寫與前後空白（清單為實作提案，待拍板）。</summary>
    private static readonly HashSet<string> SelfMadePublishers =
        new(StringComparer.OrdinalIgnoreCase) { "自製", "自制", "self-made", "self made", "selfmade", "own work" };

    public static bool IsSelfMadePublisher(string publisher) => SelfMadePublishers.Contains(publisher.Trim());

    /// <summary>控制紀錄的 primary citation 是否合格：地圖類、有 locator、授權在允許清單。</summary>
    public static string? WhyNotQualifiedPrimary(Source source, string locator)
    {
        if (!SourceKinds.MapKinds.Contains(source.SourceKind))
            return $"來源「{source.Title}」不是地圖類（{source.SourceKind}）；控制紀錄的 primary citation 必須是 map 或 atlas_map。";
        if (string.IsNullOrWhiteSpace(locator))
            return "primary citation 必須標出圖集與圖號／頁碼（locator）。";
        if (source.LicenseCode is null || !PrimaryLicenseAllowlist.Contains(source.LicenseCode))
            return $"來源「{source.Title}」的授權（{source.LicenseCode ?? "未標示"}）不在允許清單（{string.Join(", ", PrimaryLicenseAllowlist)}）。";
        return null;
    }
}
