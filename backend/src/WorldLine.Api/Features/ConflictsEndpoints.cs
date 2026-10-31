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
        var features = rows
            .Where(x => events.ContainsKey(x.r.StartEventId))
            .Select(x => new ConflictFeature(x.r.Id, Mapping.ToGeoJson(x.r.Location), new ConflictFeatureProperties(
                x.r.Id, x.r.RegimeAId, x.SlugA, x.r.RegimeBId, x.SlugB, Mapping.ToDto((NpgsqlRange<DateOnly>?)x.r.ValidPeriod)!,
                events[x.r.StartEventId], x.r.EndEventId is { } ee ? events.GetValueOrDefault(ee) : null,
                x.r.LocationMethod, Mapping.ReadLocalizedOrNull(x.r.Note))))
            .ToList();
        return ApiResults.Ok(new ConflictMapDto(d, new ConflictFeatureCollection(features)));
    }
}
