using System.Collections.Concurrent;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using NetTopologySuite.Geometries;
using NetTopologySuite.Precision;
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
    /// <summary>GET /sovereignty 回傳幾何的預設簡化容差（度，約 200 公尺）；原始幾何不變。</summary>
    public const double ResponseSimplifyTolerance = 0.002;

    /// <summary>
    /// 依地圖縮放層級選擇簡化容差：
    /// zoom ≤ 4.5 → 0.010°（粗，≈1km，低縮歐洲全圖不可見）；
    /// zoom ≤ 6.5 → 0.004°（中，≈440m）；
    /// 其餘  → 0.002°（原始精細度）。
    /// </summary>
    public static double ToleranceForZoom(float? zoom) => zoom switch
    {
        <= 4.5f => 0.010,
        <= 6.5f => 0.004,
        _ => ResponseSimplifyTolerance,
    };

    public static void Map(RouteGroupBuilder read, RouteGroupBuilder write)
    {
        read.MapGet("/sovereignty", GetOnDate).WithTags("Sovereignty").WithName("GetSovereignty")
            .Ok<SovereigntyMapDto>().Errors(400);
        // ARCHITECTURE.md §9「介面」：被選政權的完整幾何（tiles 模式點選政權時取，供蒙版、可見國名重算、高亮）；不提供全世界疆界
        read.MapGet("/regimes/{id:guid}/geometry", GetRegimeGeometry).WithTags("Sovereignty").WithName("GetRegimeGeometry")
            .Ok<SovereigntyMapDto>().Errors(400, 404);
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

    public static async Task<IResult> GetOnDate(DateOnly? date, float? zoom, WorldLineDbContext db, DateIntervalCache cache, CancellationToken ct)
    {
        if (date is not { } d)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "date 為必填（YYYY-MM-DD）。", "date");
        // 同一變動區間內每天結果相同；不同縮放桶（容差）各自快取，互不影響
        var tolerance = ToleranceForZoom(zoom);
        var kind = $"sovereignty:{tolerance:F3}";
        var features = await cache.GetOrAddAsync(kind, d, db, (day, ctx, c) => BuildOnDateAsync(day, ctx, tolerance, c), ct);
        return ApiResults.Ok(new SovereigntyMapDto(d, new SovereigntyFeatureCollection(features)));
    }

    /// <summary>
    /// GET /regimes/{id}/geometry?date=&amp;zoom=：該政權當天的主權紀錄，加上當天由它佔領的政權的紀錄（聚焦時一起挖亮）。
    /// 每筆 feature 與 GET /sovereignty 同一天、同一縮放桶回傳的那筆完全相同（同一個建構函式、同一份幾何快取）。
    /// </summary>
    public static async Task<IResult> GetRegimeGeometry(Guid id, DateOnly? date, float? zoom, WorldLineDbContext db, CancellationToken ct)
    {
        if (date is not { } d)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "date 為必填（YYYY-MM-DD）。", "date");
        if (!await db.Regimes.AnyAsync(x => x.Id == id && x.RetractedAt == null, ct))
            throw ApiError.NotFound("政權");
        var occupied = await db.OccupationAttributions.AsNoTracking()
            .Where(o => o.RetractedAt == null && o.OccupierRegimeId == id && o.ValidPeriod.Contains(d))
            .Select(o => o.OccupiedRegimeId).Distinct().ToListAsync(ct);
        var regimes = new HashSet<Guid>(occupied) { id };
        var features = await BuildOnDateAsync(d, db, ToleranceForZoom(zoom), ct, regimes);
        // 佔領方不是 id 的被佔領紀錄（同一被佔領政權在當天換手等）不算
        features = features.Where(f => f.Properties.RegimeId == id || f.Properties.Occupation?.OccupierRegimeId == id).ToList();
        return ApiResults.Ok(new SovereigntyMapDto(d, new SovereigntyFeatureCollection(features)));
    }

    private static async Task<List<SovereigntyFeature>> BuildOnDateAsync(DateOnly d, WorldLineDbContext db, double tolerance, CancellationToken ct,
        IReadOnlyCollection<Guid>? onlyRegimes = null)
    {
        // 第 1 層（Tai 2026-11-04）：由 PostGIS 依有效期間篩出當天有效的紀錄（valid_period @> d，即 lower <= d AND (upper IS NULL OR upper > d)，
        // 走 ix_sovereignty_records_valid_period GiST 索引）；這一步不取幾何，只取屬性。
        var rows = await (
                from r in db.SovereigntyRecords.AsNoTracking()
                join g in db.Regimes on r.RegimeId equals g.Id
                join s in db.Sources on r.GeometrySourceId equals s.Id
                where r.RetractedAt == null && r.ValidPeriod.Contains(d) && (onlyRegimes == null || onlyRegimes.Contains(r.RegimeId))
                orderby g.Slug, r.Id
                select new
                {
                    r.Id, r.RegimeId, r.LayerStatus, r.ValidPeriod, r.StartEventId, r.EndEventId,
                    r.GeometrySourceId, r.GeometryLocator, r.GeometryLicense, r.Attribution,
                    r.OhmRelationId, r.OhmVersion, r.OhmFetchedAt, r.OhmStartRaw, r.OhmEndRaw, r.Provenance, r.Note,
                    g.Slug, s.Title, s.Publisher, s.LicenseCode,
                })
            .ToListAsync(ct);

        var eventIds = rows.SelectMany(x => new[] { x.StartEventId, x.EndEventId }).OfType<Guid>().Distinct().ToList();
        var events = await EventRefsAsync(db, eventIds, ct);
        var regimeIds = rows.Select(x => x.RegimeId).Distinct().ToList();
        var alignments = await RegimeAlignmentsEndpoints.ActiveOnAsync(db, regimeIds, d, ct);
        var occupations = await OccupationsEndpoints.ActiveOnAsync(db, regimeIds, d, ct);

        // 幾何只對還沒簡化過的紀錄才從 PostGIS 取原始幾何（以前每次都把當天全部原始幾何讀進來，一天約 80 萬點）
        var geometries = await GeoJsonForAsync(db, rows.Select(x => x.Id).ToList(), tolerance, ct);

        return rows.Select(r =>
        {
            JsonElement? flags = r.Provenance is null ? null : JsonDocument.Parse(r.Provenance).RootElement.Clone();
            return new SovereigntyFeature(r.Id, geometries[r.Id], new SovereigntyFeatureProperties(
                r.Id, r.RegimeId, r.Slug, r.LayerStatus, Mapping.ToDto((NpgsqlRange<DateOnly>?)r.ValidPeriod)!,
                r.StartEventId is { } se ? events.GetValueOrDefault(se) : null,
                r.EndEventId is { } ee ? events.GetValueOrDefault(ee) : null,
                new GeometryProvenanceDto(r.GeometrySourceId, r.Title, r.Publisher, r.LicenseCode, r.GeometryLocator,
                    r.GeometryLicense, r.Attribution, r.OhmRelationId, r.OhmVersion, r.OhmFetchedAt, r.OhmStartRaw, r.OhmEndRaw, flags),
                Mapping.ReadLocalizedOrNull(r.Note),
                alignments.GetValueOrDefault(r.RegimeId),
                occupations.GetValueOrDefault(r.RegimeId)));
        }).ToList();
    }

    /// <summary>
    /// 回應用幾何（已簡化、已序列化成 GeoJSON）的行程內快取（(recordId, tolerance) → JsonElement）。主權紀錄不可變，
    /// 同一筆 record 在相同容差下的結果永遠相同，可跨日期區間共用：各日期快取的 FeatureCollection 參照同一份幾何，不再各存一份。
    /// 寫入作廢（DateIntervalCache.Invalidate）不清除此快取：撤回後的 record 不會再被查詢。
    /// 上限＝sovereignty_records 筆數 × 容差層數。
    /// </summary>
    private static readonly ConcurrentDictionary<(Guid Id, double Tolerance), JsonElement> _geoJsonCache = new();

    /// <summary>ids 各自的回應用幾何：命中快取直接用；其餘一次向 PostGIS 取原始幾何，平行簡化＋序列化後存入快取。</summary>
    internal static async Task<Dictionary<Guid, JsonElement>> GeoJsonForAsync(WorldLineDbContext db, IReadOnlyCollection<Guid> ids, double tolerance, CancellationToken ct)
    {
        var result = new Dictionary<Guid, JsonElement>(ids.Count);
        var missing = new List<Guid>();
        foreach (var id in ids)
            if (_geoJsonCache.TryGetValue((id, tolerance), out var hit)) result[id] = hit; else missing.Add(id);
        if (missing.Count == 0) return result;

        var raw = await db.SovereigntyRecords.AsNoTracking().Where(r => missing.Contains(r.Id))
            .Select(r => new { r.Id, r.Geom }).ToListAsync(ct);
        // 簡化（TopologyPreservingSimplifier）與 GeoJSON 序列化皆為純 CPU 無副作用，平行執行縮短含大幾何（如俄國）的首次計算
        foreach (var (id, json) in raw.AsParallel().Select(x => (x.Id, _geoJsonCache.GetOrAdd((x.Id, tolerance), _ => Mapping.ToGeoJson(Simplify(x.Geom, tolerance))))).ToList())
            result[id] = json;
        return result;
    }

    /// <summary>
    /// 回應用的簡化幾何（保留拓撲，一律回 MultiPolygon）；簡化後無效或變空就回原幾何。
    /// 簡化後再以 5 位小數精度（≈1 m）縮減座標，減少 JSON 大小約 50%；
    /// 若精度縮減後幾何無效，回退到未縮減的簡化結果。
    /// </summary>
    internal static MultiPolygon Simplify(MultiPolygon g, double tolerance)
    {
        var s = TopologyPreservingSimplifier.Simplify(g, tolerance);
        if (s is not { IsEmpty: false, IsValid: true }) return g;
        // 5dp 精度（PrecisionModel scale=100000）已遠高於簡化容差（≥ 200m），安全截斷多餘小數
        var r = GeometryPrecisionReducer.Reduce(s, new PrecisionModel(100000));
        var geom = r is { IsEmpty: false, IsValid: true } ? r : s;
        return geom switch
        {
            MultiPolygon mp => mp,
            Polygon p => new MultiPolygon([p], geom.Factory),
            _ => g,
        };
    }

    /// <summary>
    /// 預熱單一日期（供啟動背景任務呼叫）；依序填充三個縮放容差層（0.010 / 0.004 / 0.002）的快取。
    /// 幾何共用 <see cref="GeoJsonForAsync"/> 的快取，已算過的紀錄不再讀原始幾何。
    /// </summary>
    public static async Task WarmupAsync(DateOnly d, WorldLineDbContext db, DateIntervalCache cache)
    {
        foreach (var tolerance in new[] { 0.010, 0.004, ResponseSimplifyTolerance })
            await cache.GetOrAddAsync($"sovereignty:{tolerance:F3}", d, db,
                (day, ctx, c) => BuildOnDateAsync(day, ctx, tolerance, c), CancellationToken.None);
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
