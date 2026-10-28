using NetTopologySuite.Geometries;

namespace WorldLine.Api.Api;

public sealed record RegimeRef(Guid Id, string SelfName);

public sealed record RegimeSummary(
    Guid Id,
    string SelfName,
    string DisplayName,
    string Status,
    int ExistenceFrom,
    int? ExistenceTo,
    Guid? PredecessorRegimeId,
    string? OriginTransitionType,
    Guid? DestroyedByRegimeId,
    int Version);

public sealed record AliasDto(Guid Id, string AliasName, string AliasType, RegimeRef? Observer);

public sealed record SuccessorDto(Guid Id, string SelfName, string OriginTransitionType);

public sealed record RelationDto(
    Guid Id, string RelationType, string Direction, RegimeRef OtherRegime, int ValidFrom, int ValidTo, string? Description);

public sealed record ReignEraDto(Guid Id, Guid RegimeId, string RegimeSelfName, string EraName, string? MonarchName, int StartYear, int EndYear);

public sealed record PresetMembershipDto(Guid PresetId, string PresetName, int SortOrder);

public sealed record RegimeDetail(
    RegimeSummary Regime,
    IReadOnlyList<AliasDto> Aliases,
    RegimeRef? Predecessor,
    IReadOnlyList<SuccessorDto> Successors,
    RegimeRef? DestroyedBy,
    IReadOnlyList<RegimeRef> Destroyed,
    IReadOnlyList<RelationDto> Relations,
    IReadOnlyList<ReignEraDto> ReignEras,
    IReadOnlyList<PresetMembershipDto> LineagePresets);

public sealed record AliasInput(string? AliasName, string? AliasType, Guid? ObserverRegimeId);

public sealed record CreateRegimeRequest(
    string? SelfName,
    int? ExistenceFrom,
    int? ExistenceTo,
    string? Status,
    Guid? PredecessorRegimeId,
    string? OriginTransitionType,
    Guid? DestroyedByRegimeId,
    List<AliasInput>? Aliases);

/// <summary>PATCH：只更新有給的欄位；version 與 changeReason 必填（樂觀併發 + I5）。</summary>
public sealed record UpdateRegimeRequest(
    int? Version,
    string? ChangeReason,
    string? SelfName,
    string? Status,
    Guid? DestroyedByRegimeId,
    int? ExistenceFrom,
    int? ExistenceTo);

public sealed record CreateTerritoryRequest(
    int? ValidFrom,
    int? ValidTo,
    Geometry? Geometry,
    bool IsDisputed,
    bool IsIllustrative,
    string? Source);

public sealed record CorrectTerritoryRequest(
    int? Version,
    string? Reason,
    int? ValidFrom,
    int? ValidTo,
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
