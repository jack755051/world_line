using Microsoft.EntityFrameworkCore;
using NetTopologySuite.Geometries;
using NpgsqlTypes;
using WorldLine.Api.Common;
using WorldLine.Api.Domain;
using WorldLine.Api.Infrastructure;
using WorldLine.Contracts;

namespace WorldLine.Api.Features;

/// <summary>
/// 首都圖層（capital_records；2026-11-02 試驗，AI 提案・待拍板）。
/// - 每筆附出處文字（sourceRef）；查不到標「待查證」。
/// - 同一政權同一時間只能有一筆有效紀錄（EXCLUDE 約束）。
/// - 修正走軟撤回（I5），不硬刪。
/// </summary>
public static class CapitalsEndpoints
{
    public static void Map(RouteGroupBuilder read, RouteGroupBuilder write)
    {
        read.MapGet("/capitals", GetOnDate).WithTags("Capitals").WithName("GetCapitals")
            .Ok<CapitalMapDto>().Errors(400);
        write.MapPost("/capital-records", Create).WithTags("Capitals").WithName("CreateCapitalRecord")
            .RequiresApiKey().Created<CapitalRecordDto>().Errors(400, 401, 409);
        write.MapPost("/capital-records/{id:guid}/retraction", Retract).WithTags("Capitals").WithName("RetractCapitalRecord")
            .RequiresApiKey().Ok<RetractionDto>().Errors(400, 401, 404, 409);
    }

    public static async Task<IResult> Create(CreateCapitalRecordRequest req, WorldLineDbContext db, CancellationToken ct)
    {
        if (req.RegimeId is not { } regimeId || !await db.Regimes.AnyAsync(x => x.Id == regimeId && x.RetractedAt == null, ct))
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "regimeId 指向的政權不存在。", "regimeId");

        var cityName = Mapping.RequireLocalized(req.CityName, "cityName");

        if (req.Location is not { } locJson)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "location（GeoJSON Point）為必填。", "location");
        if (Mapping.RequireGeometry(locJson, "location") is not Point point)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "location 必須是 GeoJSON Point。", "location");

        if (req.ValidStart is null || !DateOnly.TryParse(req.ValidStart, out var start))
            throw ApiError.BadRequest(ErrorCodes.PeriodRequired, "validStart（YYYY-MM-DD）為必填。", "validStart");
        DateOnly? endDate = null;
        if (req.ValidEnd is not null)
        {
            if (!DateOnly.TryParse(req.ValidEnd, out var e))
                throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "validEnd 格式必須是 YYYY-MM-DD。", "validEnd");
            if (e <= start)
                throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "validEnd 必須晚於 validStart。", "validEnd");
            endDate = e;
        }
        var period = new NpgsqlRange<DateOnly>(start, true, false, endDate ?? default, false, endDate is null);

        var r = new CapitalRecord
        {
            Id = Guid.CreateVersion7(),
            RegimeId = regimeId,
            CityName = cityName,
            Location = point,
            ValidPeriod = period,
            SourceRef = string.IsNullOrWhiteSpace(req.SourceRef) ? null : req.SourceRef.Trim(),
            Note = string.IsNullOrWhiteSpace(req.Note) ? null : req.Note.Trim(),
        };
        db.CapitalRecords.Add(r);
        try
        {
            await db.SaveChangesAsync(ct);
        }
        catch (Microsoft.EntityFrameworkCore.DbUpdateException ex)
            when (ex.InnerException?.Message.Contains("excl_capital_records_no_overlap") == true)
        {
            throw new ApiError(StatusCodes.Status409Conflict, ErrorCodes.ConflictingOfficialVersion,
                $"政權 {regimeId} 在指定期間已有有效的首都紀錄（不可重疊）。");
        }
        return ApiResults.Created($"/api/v1/capital-records/{r.Id}", ToDto(r));
    }

    /// <summary>撤回首都紀錄（I5：只寫一次 retracted_at＋原因，不刪除）。</summary>
    public static async Task<IResult> Retract(Guid id, RetractionRequest req, WorldLineDbContext db, CancellationToken ct)
    {
        var reason = Mapping.RequireText(req.Reason, "reason");
        var row = await db.CapitalRecords.AsNoTracking()
            .Select(x => new { x.Id, x.RetractedAt })
            .FirstOrDefaultAsync(x => x.Id == id, ct)
            ?? throw ApiError.NotFound("首都紀錄");
        if (row.RetractedAt is not null)
            throw new ApiError(StatusCodes.Status409Conflict, ErrorCodes.ConflictingOfficialVersion,
                $"首都紀錄 {id} 已於 {row.RetractedAt:O} 撤回。");
        var now = DateTimeOffset.UtcNow;
        var n = await db.CapitalRecords.Where(x => x.Id == id && x.RetractedAt == null)
            .ExecuteUpdateAsync(u => u.SetProperty(x => x.RetractedAt, now).SetProperty(x => x.RetractionReason, reason), ct);
        if (n != 1)
            throw new ApiError(StatusCodes.Status409Conflict, ErrorCodes.ConflictingOfficialVersion,
                $"首都紀錄 {id} 已被撤回。");
        return ApiResults.Ok(new RetractionDto(id, now, reason));
    }

    /// <summary>GET /capitals?date=YYYY-MM-DD — 回傳指定日期所有有效首都（retracted_at IS NULL 且 valid_period @> date）。</summary>
    public static async Task<IResult> GetOnDate(DateOnly? date, WorldLineDbContext db, CancellationToken ct)
    {
        if (date is not { } d)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "date 為必填（YYYY-MM-DD）。", "date");
        var features = await BuildOnDateAsync(d, db, ct);
        return ApiResults.Ok(new CapitalMapDto(d, features));
    }

    internal static async Task<List<CapitalFeature>> BuildOnDateAsync(DateOnly d, WorldLineDbContext db, CancellationToken ct)
    {
        var rows = await (
                from c in db.CapitalRecords.AsNoTracking()
                join r in db.Regimes on c.RegimeId equals r.Id
                where c.RetractedAt == null && c.ValidPeriod.Contains(d)
                orderby c.RegimeId, c.Id
                select new { c, r.Slug })
            .ToListAsync(ct);
        return rows.Select(x => new CapitalFeature(
            x.c.Id,
            x.c.RegimeId,
            x.Slug,
            Mapping.ReadLocalized(x.c.CityName),
            Mapping.ToGeoJson(x.c.Location),
            Mapping.ToDto(x.c.ValidPeriod)!,
            x.c.SourceRef)).ToList();
    }

    private static CapitalRecordDto ToDto(CapitalRecord r) =>
        new(r.Id, r.RegimeId, Mapping.ReadLocalized(r.CityName),
            Mapping.ToGeoJson(r.Location), Mapping.ToDto(r.ValidPeriod)!,
            r.SourceRef, r.Note);
}
