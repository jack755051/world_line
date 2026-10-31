using Microsoft.EntityFrameworkCore;
using NetTopologySuite.Geometries;
using NpgsqlTypes;
using WorldLine.Api.Common;
using WorldLine.Api.Domain;
using WorldLine.Api.Infrastructure;
using WorldLine.Contracts;

namespace WorldLine.Api.Features;

/// <summary>
/// 衝突圖示（交叉雙劍，Tai 2026-10-31；試驗 feature/borders-1938-1940，AI 提案・待拍板）。
/// - 每筆衝突一定有開戰事件；停戰／投降事件可空（試驗範圍內未結束）。
/// - 顯示期間由事件日期推得 [開戰日, 結束日 + 1)，不另收可能與事件不一致的日期。
/// - 起訖事件沿用主權圖層的事件摘要（沒有合格引用＝pending「待查證」），卡片結構一致。
/// </summary>
public static class ConflictsEndpoints
{
    public static void Map(RouteGroupBuilder read, RouteGroupBuilder write)
    {
        read.MapGet("/conflicts", GetOnDate).WithTags("Conflicts").WithName("GetConflicts")
            .Ok<ConflictMapDto>().Errors(400);
        write.MapPost("/conflict-records", Create).WithTags("Conflicts").WithName("CreateConflictRecord")
            .RequiresApiKey().Created<ConflictRecordDto>().Errors(400, 401);
        write.MapPost("/conflict-records/{id:guid}/retraction", Retract).WithTags("Conflicts").WithName("RetractConflictRecord")
            .RequiresApiKey().Ok<RetractionDto>().Errors(400, 401, 404, 409);
    }

    public static async Task<IResult> Create(CreateConflictRecordRequest req, WorldLineDbContext db, CancellationToken ct)
    {
        if (req.RegimeAId is not { } a || req.RegimeBId is not { } b)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "regimeAId 與 regimeBId 為必填。", req.RegimeAId is null ? "regimeAId" : "regimeBId");
        if (a == b)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "交戰雙方不可是同一政權。", "regimeBId");
        if (await db.Regimes.CountAsync(x => (x.Id == a || x.Id == b) && x.RetractedAt == null, ct) != 2)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "regimeAId 或 regimeBId 指向的政權不存在。", "regimeAId");

        if (req.StartEventId is not { } startId)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "startEventId（開戰事件）為必填：每個衝突都要對應有日期的事件。", "startEventId");
        var start = await db.HistoricalEvents.AsNoTracking().FirstOrDefaultAsync(x => x.Id == startId && x.RetractedAt == null, ct)
                    ?? throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "startEventId 指向的事件不存在。", "startEventId");
        HistoricalEvent? end = null;
        if (req.EndEventId is { } endId)
            end = await db.HistoricalEvents.AsNoTracking().FirstOrDefaultAsync(x => x.Id == endId && x.RetractedAt == null, ct)
                  ?? throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "endEventId 指向的事件不存在。", "endEventId");
        var from = start.Occurred.LowerBound;
        if (end is not null && end.Occurred.LowerBound < from)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "停戰／投降事件日期早於開戰事件。", "endEventId");
        var period = end is null
            ? new NpgsqlRange<DateOnly>(from, true, false, default, false, true)
            : new NpgsqlRange<DateOnly>(from, true, end.Occurred.LowerBound.AddDays(1), false);

        if (req.Location is not { } locJson)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "location（圖示位置，GeoJSON Point）為必填。", "location");
        if (Mapping.RequireGeometry(locJson, "location") is not Point point)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "location 必須是 GeoJSON Point。", "location");
        var method = Mapping.RequireText(req.LocationMethod, "locationMethod");

        var r = new ConflictRecord
        {
            Id = Guid.CreateVersion7(),
            RegimeAId = a,
            RegimeBId = b,
            StartEventId = startId,
            EndEventId = end?.Id,
            ValidPeriod = period,
            Location = point,
            LocationMethod = method,
            Note = Mapping.OptionalLocalized(req.Note, "note"),
        };
        db.ConflictRecords.Add(r);
        await db.SaveChangesAsync(ct);
        return ApiResults.Created($"/api/v1/conflict-records/{r.Id}", new ConflictRecordDto(
            r.Id, r.RegimeAId, r.RegimeBId, r.StartEventId, r.EndEventId, Mapping.ToDto((NpgsqlRange<DateOnly>?)r.ValidPeriod)!,
            Mapping.ToGeoJson(r.Location), r.LocationMethod));
    }

    /// <summary>撤回衝突（I5：不刪除，只寫一次 retracted_at＋原因）。修正＝撤回後新增。</summary>
    public static async Task<IResult> Retract(Guid id, RetractionRequest req, WorldLineDbContext db, CancellationToken ct)
    {
        var reason = Mapping.RequireText(req.Reason, "reason");
        var row = await db.ConflictRecords.AsNoTracking().Select(x => new { x.Id, x.RetractedAt }).FirstOrDefaultAsync(x => x.Id == id, ct)
                  ?? throw ApiError.NotFound("衝突紀錄");
        if (row.RetractedAt is not null)
            throw new ApiError(StatusCodes.Status409Conflict, ErrorCodes.ConflictingOfficialVersion, $"衝突紀錄 {id} 已於 {row.RetractedAt:O} 撤回。");
        var now = DateTimeOffset.UtcNow;
        var n = await db.ConflictRecords.Where(x => x.Id == id && x.RetractedAt == null)
            .ExecuteUpdateAsync(u => u.SetProperty(x => x.RetractedAt, now).SetProperty(x => x.RetractionReason, reason), ct);
        if (n != 1)
            throw new ApiError(StatusCodes.Status409Conflict, ErrorCodes.ConflictingOfficialVersion, $"衝突紀錄 {id} 已被撤回。");
        return ApiResults.Ok(new RetractionDto(id, now, reason));
    }

    public static async Task<IResult> GetOnDate(DateOnly? date, WorldLineDbContext db, CancellationToken ct)
    {
        if (date is not { } d)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "date 為必填（YYYY-MM-DD）。", "date");
        var rows = await (
                from r in db.ConflictRecords.AsNoTracking()
                join ga in db.Regimes on r.RegimeAId equals ga.Id
                join gb in db.Regimes on r.RegimeBId equals gb.Id
                where r.RetractedAt == null && r.ValidPeriod.Contains(d)
                orderby r.Id
                select new { r, SlugA = ga.Slug, SlugB = gb.Slug })
            .ToListAsync(ct);
        var eventIds = rows.SelectMany(x => new Guid?[] { x.r.StartEventId, x.r.EndEventId }).OfType<Guid>().Distinct().ToList();
        var events = await SovereigntyEndpoints.EventRefsAsync(db, eventIds, ct);
        var geo = await ArcsOnAsync(db, rows.Select(x => x.r.Id).ToList(), d, ct);
        var features = rows
            .Where(x => events.ContainsKey(x.r.StartEventId))
            .Select(x =>
            {
                var has = geo.TryGetValue(x.r.Id, out var g);
                return new ConflictFeature(x.r.Id, Mapping.ToGeoJson(x.r.Location), new ConflictFeatureProperties(
                    x.r.Id, x.r.RegimeAId, x.SlugA, x.r.RegimeBId, x.SlugB, Mapping.ToDto((NpgsqlRange<DateOnly>?)x.r.ValidPeriod)!,
                    events[x.r.StartEventId], x.r.EndEventId is { } ee ? events.GetValueOrDefault(ee) : null,
                    x.r.LocationMethod, Mapping.ReadLocalizedOrNull(x.r.Note), has ? g.Adjacent : null, has ? g.Arc : null));
            })
            .ToList();
        return ApiResults.Ok(new ConflictMapDto(d, new ConflictFeatureCollection(features)));
    }

    /// <summary>
    /// 當日相鄰判定與虛線弧端點（只讀）：
    /// - 控制範圍＝該政權當日主權紀錄＋當日以它為佔領方（occupation_attributions）的政權紀錄；
    /// - 相鄰＝雙方控制範圍有任何幾何相交（OHM 共用邊界線段，相接即相交；用 ST_Intersects 而非 ST_DWithin，大國幾何下快約 50 倍）；
    /// - 端點＝雙方當日主權紀錄的 ST_PointOnSurface；任一方當日沒有主權紀錄就不畫弧（Adjacent 仍回傳）。
    /// </summary>
    internal static async Task<Dictionary<Guid, (bool Adjacent, ConflictArcDto? Arc)>> ArcsOnAsync(
        WorldLineDbContext db, List<Guid> ids, DateOnly d, CancellationToken ct)
    {
        var result = new Dictionary<Guid, (bool, ConflictArcDto?)>();
        if (ids.Count == 0) return result;
        const string sql = """
            WITH c AS (SELECT id, regime_a_id AS a, regime_b_id AS b FROM conflict_records WHERE id = ANY(@ids)),
            own AS (SELECT regime_id, geom FROM sovereignty_records WHERE retracted_at IS NULL AND valid_period @> @d),
            ctl AS (
              SELECT regime_id AS holder, geom FROM own
              UNION ALL
              SELECT o.occupier_regime_id, s.geom FROM occupation_attributions o JOIN own s ON s.regime_id = o.occupied_regime_id
              WHERE o.retracted_at IS NULL AND o.valid_period @> @d)
            SELECT c.id,
              EXISTS (SELECT 1 FROM ctl x JOIN ctl y ON x.geom && y.geom AND ST_Intersects(x.geom, y.geom) WHERE x.holder = c.a AND y.holder = c.b),
              ST_X(pa), ST_Y(pa), ST_X(pb), ST_Y(pb)
            FROM c
            LEFT JOIN LATERAL (SELECT ST_PointOnSurface(geom) AS pa FROM own WHERE regime_id = c.a LIMIT 1) qa ON true
            LEFT JOIN LATERAL (SELECT ST_PointOnSurface(geom) AS pb FROM own WHERE regime_id = c.b LIMIT 1) qb ON true
            """;
        var conn = (Npgsql.NpgsqlConnection)db.Database.GetDbConnection();
        var opened = conn.State != System.Data.ConnectionState.Open;
        if (opened) await db.Database.OpenConnectionAsync(ct);
        try
        {
            await using var cmd = new Npgsql.NpgsqlCommand(sql, conn);
            cmd.Parameters.AddWithValue("ids", ids.ToArray());
            cmd.Parameters.AddWithValue("d", d);
            await using var rd = await cmd.ExecuteReaderAsync(ct);
            while (await rd.ReadAsync(ct))
            {
                var adjacent = rd.GetBoolean(1);
                ConflictArcDto? arc = null;
                if (!adjacent && !rd.IsDBNull(2) && !rd.IsDBNull(4))
                    arc = new ConflictArcDto([Math.Round(rd.GetDouble(2), 4), Math.Round(rd.GetDouble(3), 4)], [Math.Round(rd.GetDouble(4), 4), Math.Round(rd.GetDouble(5), 4)]);
                result[rd.GetGuid(0)] = (adjacent, arc);
            }
        }
        finally
        {
            if (opened) await db.Database.CloseConnectionAsync();
        }
        return result;
    }
}
