using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using NetTopologySuite.Geometries;
using NetTopologySuite.Simplify;
using NpgsqlTypes;
using WorldLine.Api.Common;
using WorldLine.Api.Domain;
using WorldLine.Api.Infrastructure;
using WorldLine.Contracts;

namespace WorldLine.Api.Features;

/// <summary>
/// 主權圖層（法理國界），與控制區圖層分開（2026-10-31 試驗 feature/borders-1938-1940，AI 提案・待拍板）。
/// - 地圖填色依政權（一個政權一種顏色）；陣營只在資訊卡作補充，不決定填色（Tai 2026-10-31：政權優先於陣營）。
/// - 疆界變動對應起訖事件；事件沒有合格引用 → verification = pending（「待查證」），不推測。
/// - 幾何授權逐筆標示；cc_by／cc_by_sa 必須附署名。
/// </summary>
public static class SovereigntyEndpoints
{
    /// <summary>GET /sovereignty 回傳幾何的簡化容差（度，約 200 公尺）；原始幾何不變。</summary>
    public const double ResponseSimplifyTolerance = 0.002;

    public static void Map(RouteGroupBuilder read, RouteGroupBuilder write)
    {
        read.MapGet("/sovereignty", GetOnDate).WithTags("Sovereignty").WithName("GetSovereignty")
            .Ok<SovereigntyMapDto>().Errors(400);
        write.MapPost("/sovereignty-records", Create).WithTags("Sovereignty").WithName("CreateSovereigntyRecord")
            .RequiresApiKey().Created<SovereigntyRecordDto>().Errors(400, 401, 409);
        write.MapPost("/sovereignty-records/{id:guid}/retraction", Retract).WithTags("Sovereignty").WithName("RetractSovereigntyRecord")
            .RequiresApiKey().Ok<RetractionDto>().Errors(400, 401, 404, 409);
    }

    public static async Task<IResult> Create(CreateSovereigntyRecordRequest req, WorldLineDbContext db, CancellationToken ct)
    {
        if (req.RegimeId is not { } regimeId || !await db.Regimes.AnyAsync(x => x.Id == regimeId && x.RetractedAt == null, ct))
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "regimeId 指向的政權不存在。", "regimeId");
        var geom = Mapping.RequireMultiPolygon(req.Geometry, "geometry");
        if (req.ValidPeriod?.Start is null)
            throw ApiError.BadRequest(ErrorCodes.PeriodRequired, "validPeriod.start 為必填；迄日未知可留空。", "validPeriod");
        var period = Mapping.Optional(req.ValidPeriod, "validPeriod")!.Value;
        var status = Mapping.RequireOneOf(req.LayerStatus ?? SovereigntyLayerStatuses.DeJure, SovereigntyLayerStatuses.All, "layerStatus");

        // 幾何來源：必須存在、授權在允許清單、要有 locator（關係 id／版本）
        var source = req.GeometrySourceId is { } sid ? await db.Sources.AsNoTracking().FirstOrDefaultAsync(s => s.Id == sid, ct) : null;
        if (source is null)
            throw ApiError.BadRequest(ErrorCodes.CitationRequired, "geometrySourceId 指向的來源不存在。", "geometrySourceId");
        var locator = req.GeometryLocator ?? "";
        if (CitationPolicy.WhyNotQualifiedAlignmentPrimary(source, locator) is { } why)
            throw ApiError.BadRequest(ErrorCodes.SourceNotQualified, why, "geometrySourceId");
        var license = Mapping.RequireOneOf(req.GeometryLicense, CitationPolicy.PrimaryLicenseAllowlist.Order().ToArray(), "geometryLicense");
        var attribution = string.IsNullOrWhiteSpace(req.Attribution) ? null : req.Attribution.Trim();
        if (license is "cc_by" or "cc_by_sa" && attribution is null)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, $"geometryLicense = {license} 必須附 attribution（署名）。", "attribution");
        if (req.OhmRelationId is not null && (req.OhmVersion is null || req.OhmFetchedAt is null))
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "有 ohmRelationId 時必須釘選 ohmVersion 與 ohmFetchedAt。", "ohmVersion");

        foreach (var (ev, field) in new[] { (req.StartEventId, "startEventId"), (req.EndEventId, "endEventId") })
            if (ev is { } id && !await db.HistoricalEvents.AnyAsync(x => x.Id == id && x.RetractedAt == null, ct))
                throw ApiError.BadRequest(ErrorCodes.ValidationFailed, $"{field} 指向的事件不存在。", field);

        string? provenance = null;
        if (req.Provenance is { } p)
        {
            if (p.ValueKind != JsonValueKind.Object)
                throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "provenance 必須是 JSON 物件。", "provenance");
            provenance = p.GetRawText();
        }

        // 同政權有效紀錄期間不可重疊（DB 另有 EXCLUDE 兜底）
        var overlap = await db.SovereigntyRecords.AsNoTracking()
            .Where(x => x.RegimeId == regimeId && x.RetractedAt == null && x.ValidPeriod.Overlaps(period))
            .Select(x => x.Id).FirstOrDefaultAsync(ct);
        if (overlap != Guid.Empty)
            throw new ApiError(StatusCodes.Status409Conflict, ErrorCodes.ConflictingOfficialVersion,
                $"此政權在重疊期間已有主權紀錄（id {overlap}）。疆界改變請分段，修正請先撤回。");

        var r = new SovereigntyRecord
        {
            Id = Guid.CreateVersion7(),
            RegimeId = regimeId,
            Geom = geom,
            ValidPeriod = period,
            LayerStatus = status,
            StartEventId = req.StartEventId,
            EndEventId = req.EndEventId,
            GeometrySourceId = source.Id,
            GeometryLocator = locator.Trim(),
            GeometryLicense = license,
            Attribution = attribution,
            OhmRelationId = req.OhmRelationId,
            OhmVersion = req.OhmVersion,
            OhmFetchedAt = req.OhmFetchedAt?.ToUniversalTime(),
            OhmStartRaw = req.OhmStartRaw,
            OhmEndRaw = req.OhmEndRaw,
            Provenance = provenance,
            Note = Mapping.OptionalLocalized(req.Note, "note"),
        };
        db.SovereigntyRecords.Add(r);
        await db.SaveChangesAsync(ct);
        return ApiResults.Created($"/api/v1/sovereignty-records/{r.Id}", new SovereigntyRecordDto(
            r.Id, r.RegimeId, Mapping.ToDto((NpgsqlRange<DateOnly>?)r.ValidPeriod)!, r.LayerStatus, r.StartEventId, r.EndEventId,
            r.GeometrySourceId, r.GeometryLocator, r.GeometryLicense, r.Attribution, r.OhmRelationId, r.OhmVersion, r.OhmFetchedAt));
    }

    /// <summary>撤回主權紀錄（I5：不刪除，只寫一次 retracted_at＋原因）。修正＝撤回後新增。</summary>
    public static async Task<IResult> Retract(Guid id, RetractionRequest req, WorldLineDbContext db, CancellationToken ct)
    {
        var reason = Mapping.RequireText(req.Reason, "reason");
        var row = await db.SovereigntyRecords.AsNoTracking().Select(x => new { x.Id, x.RetractedAt }).FirstOrDefaultAsync(x => x.Id == id, ct)
                  ?? throw ApiError.NotFound("主權紀錄");
        if (row.RetractedAt is not null)
            throw new ApiError(StatusCodes.Status409Conflict, ErrorCodes.ConflictingOfficialVersion, $"主權紀錄 {id} 已於 {row.RetractedAt:O} 撤回。");
        var now = DateTimeOffset.UtcNow;
        var n = await db.SovereigntyRecords.Where(x => x.Id == id && x.RetractedAt == null)
            .ExecuteUpdateAsync(u => u.SetProperty(x => x.RetractedAt, now).SetProperty(x => x.RetractionReason, reason), ct);
        if (n != 1)
            throw new ApiError(StatusCodes.Status409Conflict, ErrorCodes.ConflictingOfficialVersion, $"主權紀錄 {id} 已被撤回。");
        return ApiResults.Ok(new RetractionDto(id, now, reason));
    }

    public static async Task<IResult> GetOnDate(DateOnly? date, WorldLineDbContext db, DateIntervalCache cache, CancellationToken ct)
    {
        if (date is not { } d)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "date 為必填（YYYY-MM-DD）。", "date");
        // 同一變動區間內每天結果相同：依區間快取（寫入即作廢，見 DateIntervalCache）
        var features = await cache.GetOrAddAsync("sovereignty", d, db, () => BuildOnDateAsync(d, db, ct), ct);
        return ApiResults.Ok(new SovereigntyMapDto(d, new SovereigntyFeatureCollection(features)));
    }

    private static async Task<List<SovereigntyFeature>> BuildOnDateAsync(DateOnly d, WorldLineDbContext db, CancellationToken ct)
    {

        var rows = await (
                from r in db.SovereigntyRecords.AsNoTracking()
                join g in db.Regimes on r.RegimeId equals g.Id
                join s in db.Sources on r.GeometrySourceId equals s.Id
                where r.RetractedAt == null && r.ValidPeriod.Contains(d)
                orderby g.Slug, r.Id
                select new { r, g.Slug, s.Title, s.Publisher, s.LicenseCode })
            .ToListAsync(ct);

        var eventIds = rows.SelectMany(x => new[] { x.r.StartEventId, x.r.EndEventId }).OfType<Guid>().Distinct().ToList();
        var events = await EventRefsAsync(db, eventIds, ct);
        var regimeIds = rows.Select(x => x.r.RegimeId).Distinct().ToList();
        var alignments = await RegimeAlignmentsEndpoints.ActiveOnAsync(db, regimeIds, d, ct);
        var occupations = await OccupationsEndpoints.ActiveOnAsync(db, regimeIds, d, ct);

        var features = rows.Select(x =>
        {
            var r = x.r;
            var simplified = Simplify(r.Geom);
            JsonElement? flags = r.Provenance is null ? null : JsonDocument.Parse(r.Provenance).RootElement.Clone();
            return new SovereigntyFeature(r.Id, Mapping.ToGeoJson(simplified), new SovereigntyFeatureProperties(
                r.Id, r.RegimeId, x.Slug, r.LayerStatus, Mapping.ToDto((NpgsqlRange<DateOnly>?)r.ValidPeriod)!,
                r.StartEventId is { } se ? events.GetValueOrDefault(se) : null,
                r.EndEventId is { } ee ? events.GetValueOrDefault(ee) : null,
                new GeometryProvenanceDto(r.GeometrySourceId, x.Title, x.Publisher, x.LicenseCode, r.GeometryLocator,
                    r.GeometryLicense, r.Attribution, r.OhmRelationId, r.OhmVersion, r.OhmFetchedAt, r.OhmStartRaw, r.OhmEndRaw, flags),
                Mapping.ReadLocalizedOrNull(r.Note),
                alignments.GetValueOrDefault(r.RegimeId),
                occupations.GetValueOrDefault(r.RegimeId)));
        }).ToList();
        return features;
    }

    /// <summary>回應用的簡化幾何（保留拓撲，一律回 MultiPolygon）；簡化後無效或變空就回原幾何。</summary>
    internal static MultiPolygon Simplify(MultiPolygon g)
    {
        var s = TopologyPreservingSimplifier.Simplify(g, ResponseSimplifyTolerance);
        if (s is not { IsEmpty: false, IsValid: true }) return g;
        return s switch
        {
            MultiPolygon mp => mp,
            Polygon p => new MultiPolygon([p], g.Factory),
            _ => g,
        };
    }

    /// <summary>事件摘要＋引用；沒有任何引用的事件 verification = pending（「待查證」）。</summary>
    internal static async Task<Dictionary<Guid, SovereigntyEventRefDto>> EventRefsAsync(WorldLineDbContext db, IReadOnlyCollection<Guid> ids, CancellationToken ct)
    {
        if (ids.Count == 0) return [];
        var evs = await db.HistoricalEvents.AsNoTracking().Where(e => ids.Contains(e.Id) && e.RetractedAt == null).ToListAsync(ct);
        var cites = (await (
                from c in db.EventCitations.AsNoTracking()
                join s in db.Sources on c.SourceId equals s.Id
                where ids.Contains(c.EventId)
                orderby s.Title, c.Locator
                select new { c.EventId, Dto = new CitationDto(s.Id, s.Title, s.Publisher, s.LicenseCode, c.Locator, CitationRoles.Primary, c.EvidenceNote) })
            .ToListAsync(ct))
            .ToLookup(x => x.EventId, x => x.Dto);
        return evs.ToDictionary(e => e.Id, e =>
        {
            var list = cites[e.Id].ToList();
            return new SovereigntyEventRefDto(e.Id, e.EventKind, Mapping.ToDto((NpgsqlRange<DateOnly>?)e.Occurred)!,
                Mapping.ReadLocalizedOrNull(e.Summary), list.Count > 0 ? "verified" : "pending", list);
        });
    }
}
