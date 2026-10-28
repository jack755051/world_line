namespace WorldLine.Api.Domain;

/// <summary>
/// 政權狀態（憲法 §4 狀態機）。以英文代碼存入資料庫，與前端 map-colors.ts 的 PolityState 一致。
/// 合法轉換只有：existing → split / abdicated / destroyed；「被取代（禪讓）」與「被滅亡」不可合併。
/// </summary>
public static class RegimeStatus
{
    /// <summary>存續</summary>
    public const string Existing = "existing";
    /// <summary>分裂（同時產生多個新政權）</summary>
    public const string Split = "split";
    /// <summary>被取代（禪讓，和平轉移）</summary>
    public const string Abdicated = "abdicated";
    /// <summary>被滅亡（武力消滅，須記錄消滅方）</summary>
    public const string Destroyed = "destroyed";

    public static readonly IReadOnlyList<string> All = [Existing, Split, Abdicated, Destroyed];

    /// <summary>後端唯一信任來源的合法轉換規則（PRD §5：前端 XState 僅做 UI 防呆）。</summary>
    public static bool IsLegalTransition(string from, string to) =>
        from == Existing && (to == Split || to == Abdicated || to == Destroyed);
}

/// <summary>政權「如何產生」：因分裂或因禪讓而來；獨立建國則為 null（無前身）。</summary>
public static class OriginTransitionType
{
    public const string Split = "split";
    public const string Abdication = "abdication";
}

/// <summary>
/// 他稱代稱的觀察視角（PRD §6 alias_type TODO 的落地決定，對應憲法 §6「朝代／帝國／國家」是觀察視角產物）：
/// - contemporary：同時代其他政權的稱呼（「國家」視角，例：唐稱阿拉伯帝國為「大食」）
/// - historiographic：後世／現代史學的稱呼（「朝代」視角，例：「東漢」「曹魏」）
/// 政權自身視角（「帝國」視角）即 regimes.self_name，不放在代稱表。
/// </summary>
public static class AliasPerspective
{
    public const string Contemporary = "contemporary";
    public const string Historiographic = "historiographic";
}

/// <summary>政權間持續性關係類型（PRD §6 regime_relations）。方向性關係以 regime_a → regime_b 表示（例：A 向 B 朝貢）。</summary>
public static class RelationType
{
    public const string Trade = "trade";
    public const string Tributary = "tributary";
    public const string MarriageAlliance = "marriage_alliance";
    public const string Alliance = "alliance";
    public const string Hostility = "hostility";
    public const string Other = "other";
}
