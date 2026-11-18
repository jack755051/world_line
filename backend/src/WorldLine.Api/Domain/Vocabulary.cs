namespace WorldLine.Api.Domain;

/// <summary>受控詞彙（與 DB CHECK 一致，PRD §6.3）。</summary>
public static class SourceKinds
{
    public const string Map = "map";
    public const string AtlasMap = "atlas_map";
    /// <summary>具名百科條目（B3，2026-11-11）。</summary>
    public const string Encyclopedia = "encyclopedia";
    /// <summary>官方機構／政府網頁（B3，2026-11-11）。</summary>
    public const string OfficialWebsite = "official_website";
    /// <summary>檔案典藏（B3，2026-11-11）。</summary>
    public const string Archive = "archive";
    public static readonly string[] All =
        [Map, AtlasMap, "treaty", "official_record", "trial_record", "peer_reviewed", "official_history", "dataset", Encyclopedia, OfficialWebsite, Archive];
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
    public static readonly string[] All = ["war", "campaign", "battle", "treaty", "armistice", "surrender", "political", "atrocity", "operation"];
}

public static class DatePrecisions
{
    public const string Day = "day";
    public static readonly string[] All = [Day, "month", "year"];
}

/// <summary>
/// 陣營（憲法 §6「陣營」，2026-10-28 拍板）：軸心、同盟、共同交戰／合作、中立／未結盟。
/// 軸心與同盟只依有文件的正式加入判定；系統不依交戰關係自行推導。
/// </summary>
public static class Camps
{
    public const string Axis = "axis";
    public const string Allies = "allies";
    public const string CoBelligerent = "co_belligerent";
    public const string Neutral = "neutral";
    public static readonly string[] All = [Axis, Allies, CoBelligerent, Neutral];
}

/// <summary>事件參與角色（PRD §6.3 event_participants；TODO：清單待拍板）。</summary>
public static class EventParticipantRoles
{
    public const string Belligerent = "belligerent";
    public const string Signatory = "signatory";
    public static readonly string[] All = [Belligerent, Signatory, "perpetrator", "other"];
}

/// <summary>控制資料缺的原因（PRD §6.3 control_coverage_notes）。</summary>
public static class CoverageReasons
{
    public static readonly string[] All = ["no_qualified_source", "not_yet_digitized"];
}

/// <summary>主權圖層紀錄的性質（sovereignty_records.layer_status；2026-10-31 試驗，待拍板）。</summary>
public static class SovereigntyLayerStatuses
{
    /// <summary>法理國土。</summary>
    public const string DeJure = "de_jure";
    /// <summary>資料集列為國家層級、但實為佔領行政區（例：比利時與北法軍政府），不是主權；只為避免地圖空白而顯示，前端另以斜線標示。</summary>
    public const string NotSovereign = "not_sovereign";
    public static readonly string[] All = [DeJure, NotSovereign];
}

/// <summary>
/// 佔領的控制程度（2026-10-31 Tai：主權圖層依佔領國上色，深淺分三級；AI 提案・待拍板）。
/// annexed＝併入（正式或事實併入，最深）；civil_administration＝帝國專員轄區／總督轄區／總督府等民政管理（中等）；
/// military_administration＝軍事管理（最淺）。
/// </summary>
public static class OccupationControlKinds
{
    public const string Annexed = "annexed";
    public const string CivilAdministration = "civil_administration";
    public const string MilitaryAdministration = "military_administration";
    public static readonly string[] All = [Annexed, CivilAdministration, MilitaryAdministration];
}

/// <summary>領導人職位（leader_records.role；2026-11-03 試驗，AI 提案・待拍板）。</summary>
public static class LeaderRoles
{
    public const string HeadOfState = "head_of_state";
    public const string HeadOfGovernment = "head_of_government";
    public static readonly string[] All = [HeadOfState, HeadOfGovernment];
}

/// <summary>
/// 生平欄位引用可指向的欄位（leader_bio_field_citations.field；2026-11-07）。summary 視為一段簡介。
/// deathPlace：ARCHITECTURE §16.6（2026-11-10，B1）。
/// </summary>
public static class LeaderBioFields
{
    public static readonly string[] All = ["name", "nameZh", "birthDate", "deathDate", "birthPlace", "deathPlace", "party", "summary", "portrait"];
}

/// <summary>
/// 生平缺口種類（leader_bio_gaps.gap_kind；ARCHITECTURE §16.4.2，2026-11-10，B1）：
/// conflict＝來源互相矛盾（該欄必須為 NULL）；not_found＝查無可開啟來源；identity_uncertain＝身分由職銜等推定。
/// </summary>
public static class LeaderBioGapKinds
{
    public const string Conflict = "conflict";
    public const string NotFound = "not_found";
    public const string IdentityUncertain = "identity_uncertain";
    public static readonly string[] All = [Conflict, NotFound, IdentityUncertain];

    /// <summary>target 格式：field:&lt;LeaderBioFields&gt;｜position:&lt;id&gt;｜paragraph:&lt;topic&gt;｜role:&lt;seed_key&gt;｜identity。</summary>
    public const string TargetPattern = "^(field|position|paragraph|role):[^[:space:]].*$|^identity$";
}


/// <summary>經歷種類（person_positions.position_kind；B3 本批已出現值）。元首／首腦／實質領導走 <see cref="PersonRoleKinds"/>。</summary>
public static class PersonPositionKinds
{
    public static readonly string[] All =
        ["minister", "legislator", "diplomat", "military_command", "military_education", "judicial", "police", "other"];
    /// <summary>寫入層拒絕：應走角色層。</summary>
    public static readonly string[] RoleLayerKinds = ["head_of_state", "head_of_government", "de_facto_leader"];
}

/// <summary>
/// 角色種類（person_roles.role_kind）。草案 P1 為前三種；本批 82 筆含 1 筆 cabinet_minister，
/// Tai 要求 82 筆一起寫入，故 CHECK 加上 cabinet_minister（2026-11-11，對草案的必要擴充）。
/// </summary>
public static class PersonRoleKinds
{
    public static readonly string[] All = ["head_of_state", "head_of_government", "de_facto_leader", "cabinet_minister"];
}

/// <summary>來源等級（docs/source-rules.md §2；data/source-policy.json）。</summary>
public static class SourceGrades
{
    public static readonly string[] All = ["A", "B", "C", "X"];
}
