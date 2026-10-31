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
    /// - 端點＝雙方當日主權紀錄的 ST_PointOnSurface；任一方當日沒有主權紀錄就不畫弧（Adjacent 仍回傳）；
    /// - 有事件地點時其中一端改用事件地點（規則見 ConflictArcDto）。
    /// </summary>
    internal static async Task<Dictionary<Guid, (bool Adjacent, ConflictArcDto? Arc)>> ArcsOnAsync(
        WorldLineDbContext db, List<Guid> ids, DateOnly d, CancellationToken ct)
    {
        var result = new Dictionary<Guid, (bool, ConflictArcDto?)>();
        if (ids.Count == 0) return result;
        const string sql = """
            WITH c AS (
              SELECT r.id, r.regime_a_id AS a, r.regime_b_id AS b,
                     COALESCE(e.location, CASE WHEN r.location_method LIKE '開戰地點%' THEN r.location END) AS ev
              FROM conflict_records r LEFT JOIN historical_events e ON e.id = r.start_event_id
              WHERE r.id = ANY(@ids)),
            own AS (SELECT regime_id, geom FROM sovereignty_records WHERE retracted_at IS NULL AND valid_period @> @d),
            ctl AS (
              SELECT regime_id AS holder, geom FROM own
              UNION ALL
              SELECT o.occupier_regime_id, s.geom FROM occupation_attributions o JOIN own s ON s.regime_id = o.occupied_regime_id
              WHERE o.retracted_at IS NULL AND o.valid_period @> @d),
            q AS (
              SELECT c.id, c.ev,
                EXISTS (SELECT 1 FROM ctl x JOIN ctl y ON x.geom && y.geom AND ST_Intersects(x.geom, y.geom) WHERE x.holder = c.a AND y.holder = c.b) AS adjacent,
                (SELECT ST_PointOnSurface(geom) FROM own WHERE regime_id = c.a LIMIT 1) AS pa,
                (SELECT ST_PointOnSurface(geom) FROM own WHERE regime_id = c.b LIMIT 1) AS pb,
                c.ev IS NOT NULL AND EXISTS (SELECT 1 FROM ctl x WHERE x.holder = c.a AND ST_DWithin(x.geom, c.ev, 1.0)) AS near_a,
                c.ev IS NOT NULL AND EXISTS (SELECT 1 FROM ctl x WHERE x.holder = c.b AND ST_DWithin(x.geom, c.ev, 1.0)) AS near_b
              FROM c),
            k AS (
              SELECT q.*,
                CASE WHEN ev IS NULL OR pa IS NULL OR pb IS NULL THEN NULL
                     WHEN near_a AND NOT near_b THEN 'from'
                     WHEN near_b AND NOT near_a THEN 'to'
                     WHEN near_a AND near_b THEN NULL
                     WHEN ST_Distance(pa, ev) >= ST_Distance(pb, ev) THEN 'from' ELSE 'to' END AS ev_end
              FROM q),
            -- 有事件地點時，另一端改用「該方控制範圍中離事件地點最近的點」（例：日—英從日本控制區接到哥打巴魯，而不是北海道），
            -- 弧線短、雙劍（弧線中點）落在事件附近，線與圖示一致；距離把事件點 ±360° 一起比，跨換日線（日本→珍珠港）取東邊而不是繞地球一圈
            m AS (
              SELECT k.*,
                CASE WHEN ev_end = 'to' THEN (SELECT ST_ClosestPoint(x.geom, ST_Translate(k.ev, w, 0)) FROM ctl x JOIN c ON c.id = k.id CROSS JOIN (VALUES (-360.0), (0.0), (360.0)) sh(w) WHERE x.holder = c.a ORDER BY ST_Distance(x.geom, ST_Translate(k.ev, w, 0)) LIMIT 1)
                     WHEN ev_end = 'from' THEN (SELECT ST_ClosestPoint(x.geom, ST_Translate(k.ev, w, 0)) FROM ctl x JOIN c ON c.id = k.id CROSS JOIN (VALUES (-360.0), (0.0), (360.0)) sh(w) WHERE x.holder = c.b ORDER BY ST_Distance(x.geom, ST_Translate(k.ev, w, 0)) LIMIT 1)
                END AS near_other
              FROM k)
            SELECT id, adjacent,
              ST_X(CASE WHEN ev_end = 'from' THEN ev WHEN ev_end = 'to' THEN COALESCE(near_other, pa) ELSE pa END),
              ST_Y(CASE WHEN ev_end = 'from' THEN ev WHEN ev_end = 'to' THEN COALESCE(near_other, pa) ELSE pa END),
              ST_X(CASE WHEN ev_end = 'to' THEN ev WHEN ev_end = 'from' THEN COALESCE(near_other, pb) ELSE pb END),
              ST_Y(CASE WHEN ev_end = 'to' THEN ev WHEN ev_end = 'from' THEN COALESCE(near_other, pb) ELSE pb END),
              ev_end
            FROM m
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
                    arc = new ConflictArcDto([Math.Round(rd.GetDouble(2), 4), Math.Round(rd.GetDouble(3), 4)], [Math.Round(rd.GetDouble(4), 4), Math.Round(rd.GetDouble(5), 4)],
                        rd.IsDBNull(6) ? null : rd.GetString(6));
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
