namespace WorldLine.Api.Domain;

/// <summary>受控詞彙（與 DB CHECK 一致，PRD §6.3）。</summary>
public static class SourceKinds
{
    public const string Map = "map";
    public const string AtlasMap = "atlas_map";
    public static readonly string[] All =
        [Map, AtlasMap, "treaty", "official_record", "trial_record", "peer_reviewed", "official_history", "dataset"];
    /// <summary>R7：控制紀錄的 primary citation 只能用地圖類來源。</summary>
    public static readonly string[] MapKinds = [Map, AtlasMap];
}

public static class NameKinds
{
    public const string Self = "self";
    public const string Exonym = "exonym";
    public static readonly string[] All = [Self, Exonym];
}

/// <summary>控制類型（憲法 R6）。R9：「控制資料缺」刻意不在此清單。</summary>
public static class ControlTypes
{
    public const string PuppetAdministration = "puppet_administration";
    public static readonly string[] All =
        ["direct_rule", "military_occupation", PuppetAdministration, "partial", "contested"];
}

public static class CitationRoles
{
    public const string Primary = "primary";
    public static readonly string[] All = [Primary, "auxiliary_geometry", "date_check"];
}

public static class Attestations
{
    public const string Point = "point";
    public const string Interval = "interval";
    public static readonly string[] All = [Point, Interval];
}

/// <summary>多語文字（PRD §6.1-3、§12 Q8 待拍板）：第一階段只接受這兩個 key。</summary>
public static class Languages
{
    public static readonly string[] Supported = ["zh-Hant", "en"];
}

/// <summary>
/// 持續關係類型（PRD §6.3 regime_relations；清單仍屬 §12 Q6 待拍板）。
/// patron_puppet 方向：regime_a＝扶植方、regime_b＝傀儡（Tai 2026-10-28：與控制紀錄的 patron_regime_id 並存）。
/// </summary>
public static class RelationTypes
{
    public const string PatronPuppet = "patron_puppet";
    public static readonly string[] All = ["at_war", "alliance", "non_aggression_pact", PatronPuppet, "trade"];
}

/// <summary>事件類型（PRD §6.3 AI 提案・待拍板）。</summary>
public static class EventKinds
{
    public static readonly string[] All = ["war", "campaign", "battle", "treaty", "armistice", "surrender", "political", "atrocity"];
}

public static class DatePrecisions
{
    public const string Day = "day";
    public static readonly string[] All = [Day, "month", "year"];
}
