using NetTopologySuite.Geometries;

namespace WorldLine.Api.Api;

public sealed record RegimeRef(Guid Id, string SelfName);

/// <summary>
/// 政權摘要。日期依精度輸出（I7：只知年就只輸出 YYYY）。
/// HasTerritory／ControlledBy／Alliances 只有在查詢帶 date 或 year 時才有值（該時間點的狀態）。
/// </summary>
public sealed record RegimeSummary(
    Guid Id,
    string SelfName,
    string DisplayName,
    string Status,
    string ExistenceFrom,
    string ExistenceFromPrecision,
    string? ExistenceTo,
    string? ExistenceToPrecision,
    Guid? PredecessorRegimeId,
    string? OriginTransitionType,
    Guid? DestroyedByRegimeId,
    Guid? AnnexedByRegimeId,
    int Version,
    bool? HasTerritory = null,
    IReadOnlyList<ControlRefDto>? ControlledBy = null,
    IReadOnlyList<AllianceRefDto>? Alliances = null);

/// <summary>某時間點的控制關係摘要（控制方或被控制方）。</summary>
public sealed record ControlRefDto(Guid RelationId, RegimeRef Regime, string DisplayName, string ControlType, bool IsDisputed);

public sealed record AllianceRefDto(Guid AllianceId, string SelfName, string Role);

public sealed record AliasDto(Guid Id, string AliasName, string AliasType, RegimeRef? Observer);

public sealed record SuccessorDto(Guid Id, string SelfName, string OriginTransitionType);

public sealed record RelationDto(
    Guid Id, string RelationType, string Direction, RegimeRef OtherRegime,
    string ValidFrom, string ValidFromPrecision, string ValidTo, string ValidToPrecision, string? Description);

public sealed record ReignEraDto(Guid Id, Guid RegimeId, string RegimeSelfName, string EraName, string? MonarchName,
    string StartDate, string StartPrecision, string? EndDate, string? EndPrecision);

public sealed record PresetMembershipDto(Guid PresetId, string PresetName, int SortOrder);

public sealed record RegimeDetail(
    RegimeSummary Regime,
    IReadOnlyList<AliasDto> Aliases,
    RegimeRef? Predecessor,
    IReadOnlyList<SuccessorDto> Successors,
    RegimeRef? DestroyedBy,
    IReadOnlyList<RegimeRef> Destroyed,
    RegimeRef? AnnexedBy,
    IReadOnlyList<RegimeRef> Annexed,
    IReadOnlyList<RelationDto> Relations,
    IReadOnlyList<ControlRelationDto> ControlRelations,
    IReadOnlyList<RegimeAllianceDto> Alliances,
    IReadOnlyList<ReignEraDto> ReignEras,
    IReadOnlyList<PresetMembershipDto> LineagePresets);

public sealed record RegimeAllianceDto(Guid AllianceId, string AllianceSelfName, string Role,
    string JoinedOn, string JoinedPrecision, string? LeftOn, string? LeftPrecision);

public sealed record AliasInput(string? AliasName, string? AliasType, Guid? ObserverRegimeId);

/// <summary>existenceFrom／existenceTo：YYYY、YYYY-MM 或 YYYY-MM-DD（寫法即精度，I7）。</summary>
public sealed record CreateRegimeRequest(
    string? SelfName,
    string? ExistenceFrom,
    string? ExistenceTo,
    string? Status,
    Guid? PredecessorRegimeId,
    string? OriginTransitionType,
    Guid? DestroyedByRegimeId,
    Guid? AnnexedByRegimeId,
    List<AliasInput>? Aliases);

/// <summary>PATCH：只更新有給的欄位；version 與 changeReason 必填（樂觀併發 + I5）。</summary>
public sealed record UpdateRegimeRequest(
    int? Version,
    string? ChangeReason,
    string? SelfName,
    string? Status,
    Guid? DestroyedByRegimeId,
    Guid? AnnexedByRegimeId,
    string? ExistenceFrom,
    string? ExistenceTo);

public sealed record CreateTerritoryRequest(
    string? ValidFrom,
    string? ValidTo,
    Geometry? Geometry,
    bool IsDisputed,
    bool IsIllustrative,
    string? Source);

public sealed record CorrectTerritoryRequest(
    int? Version,
    string? Reason,
    string? ValidFrom,
    string? ValidTo,
    Geometry? Geometry,
    bool? IsDisputed,
    bool? IsIllustrative,
    string? Source);

public sealed record GeoJsonFeature(string Type, Guid Id, Geometry Geometry, IDictionary<string, object?> Properties)
{
    public GeoJsonFeature(Guid id, Geometry geometry, IDictionary<string, object?> properties)
        : this("Feature", id, geometry, properties) { }
}

public sealed record GeoJsonFeatureCollection(string Type, IReadOnlyList<GeoJsonFeature> Features, IDictionary<string, object?>? Metadata)
{
    public GeoJsonFeatureCollection(IReadOnlyList<GeoJsonFeature> features, IDictionary<string, object?>? metadata = null)
        : this("FeatureCollection", features, metadata) { }
}

public sealed record EventDto(
    string Id,
    string Name,
    string? ParentEventId,
    string StartEdtf,
    string EndEdtf,
    decimal StartDecimal,
    decimal EndDecimal,
    string Precision,
    bool Uncertain,
    bool Approximate,
    IReadOnlyList<string> Tags,
    string? TimeZone,
    string? TimeNote,
    Geometry? OriginPoint,
    int PerspectiveCount,
    int ControversyCount);

public sealed record PerspectiveDto(
    Guid Id, RegimeRef? Regime, string? ObserverCategory, string LocalName, string NarrativeSummary,
    string? OfficialJustification, object? PrimarySources, object? ClaimedCasualties);

public sealed record ControversyDto(Guid Id, string Topic, string NeutralDescription, object? Viewpoints);

public sealed record LineagePresetDto(Guid Id, string PresetName, string? Description, bool IsDefault, int MemberCount);

public sealed record LineageMemberDto(int SortOrder, RegimeSummary Regime);

public sealed record ReignEraYearDto(Guid RegimeId, string RegimeSelfName, string EraName, string? MonarchName, int EraYear, string Label);

// ---- 二戰階段（2026-10-28）：控制關係、同盟陣營 ----

public sealed record ControlRelationDto(
    Guid Id,
    RegimeRef Controller,
    string ControllerDisplayName,
    RegimeRef Controlled,
    string ControlledDisplayName,
    string ControlType,
    string ValidFrom,
    string ValidFromPrecision,
    string ValidTo,
    string ValidToPrecision,
    bool IsDisputed,
    bool HasArea,
    bool IsIllustrative,
    string? Description,
    string? Source,
    int Version);

public sealed record CreateControlRelationRequest(
    Guid? ControllerRegimeId,
    Guid? ControlledRegimeId,
    string? ControlType,
    string? ValidFrom,
    string? ValidTo,
    Geometry? Area,
    bool IsIllustrative,
    bool IsDisputed,
    string? Description,
    string? Source);

public sealed record AllianceMemberDto(
    Guid Id, RegimeRef Regime, string DisplayName, string Role,
    string JoinedOn, string JoinedPrecision, string? LeftOn, string? LeftPrecision, string? Note);

public sealed record AllianceDto(
    Guid Id,
    string SelfName,
    string DisplayName,
    string ExistenceFrom,
    string ExistenceFromPrecision,
    string? ExistenceTo,
    string? ExistenceToPrecision,
    string? Description,
    IReadOnlyList<AliasDto> Aliases,
    IReadOnlyList<AllianceMemberDto> Members,
    int Version);

public sealed record CreateAllianceRequest(
    string? SelfName, string? ExistenceFrom, string? ExistenceTo, string? Description, List<AliasInput>? Aliases);

public sealed record AddAllianceMemberRequest(Guid? RegimeId, string? Role, string? JoinedOn, string? LeftOn, string? Note);
