using Microsoft.EntityFrameworkCore;
using NpgsqlTypes;
using WorldLine.Api.Common;
using WorldLine.Api.Domain;
using WorldLine.Api.Infrastructure;
using WorldLine.Contracts;

namespace WorldLine.Api.Features;

/// <summary>
/// 領導人圖層（leader_records；2026-11-03 試驗，AI 提案・待拍板）。
/// - 每筆附出處文字（source）；查不到標「待查證」（verified=false）。
/// - 修正走軟撤回（I5），不硬刪。
/// </summary>
public static class LeadersEndpoints
{
    public static void Map(RouteGroupBuilder read, RouteGroupBuilder write)
    {
        read.MapGet("/leaders", GetOnDate).WithTags("Leaders").WithName("GetLeaders")
            .Ok<LeaderMapDto>().Errors(400);
        write.MapPost("/leader-records", Create).WithTags("Leaders").WithName("CreateLeaderRecord")
            .RequiresApiKey().Created<LeaderRecordDto>().Errors(400, 401);
    }

    public static async Task<IResult> Create(CreateLeaderRecordRequest req, WorldLineDbContext db, CancellationToken ct)
    {
        if (req.RegimeId is not { } regimeId || !await db.Regimes.AnyAsync(x => x.Id == regimeId && x.RetractedAt == null, ct))
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "regimeId 指向的政權不存在。", "regimeId");

        var name = Mapping.RequireText(req.Name, "name");
        var role = Mapping.RequireOneOf(req.Role, LeaderRoles.All, "role");
        var source = Mapping.RequireText(req.Source, "source");

        if (req.ValidFrom is null || !DateOnly.TryParse(req.ValidFrom, out var start))
            throw ApiError.BadRequest(ErrorCodes.PeriodRequired, "validFrom（YYYY-MM-DD）為必填。", "validFrom");

        DateOnly? endDate = null;
        if (req.ValidTo is not null)
        {
            if (!DateOnly.TryParse(req.ValidTo, out var e))
                throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "validTo 格式必須是 YYYY-MM-DD。", "validTo");
            if (e <= start)
                throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "validTo 必須晚於 validFrom。", "validTo");
            endDate = e;
        }
        var period = new NpgsqlRange<DateOnly>(start, true, false, endDate ?? default, false, endDate is null);

        var r = new LeaderRecord
        {
            Id = Guid.CreateVersion7(),
            RegimeId = regimeId,
            Name = name,
            NameZh = string.IsNullOrWhiteSpace(req.NameZh) ? null : req.NameZh.Trim(),
            Role = role,
            Title = string.IsNullOrWhiteSpace(req.Title) ? null : req.Title.Trim(),
            ValidPeriod = period,
            Source = source,
            SourceUrl = string.IsNullOrWhiteSpace(req.SourceUrl) ? null : req.SourceUrl.Trim(),
            Verified = req.Verified,
        };
        db.LeaderRecords.Add(r);
        await db.SaveChangesAsync(ct);
        return ApiResults.Created($"/api/v1/leader-records/{r.Id}", ToDto(r));
    }

    /// <summary>GET /leaders?date=YYYY-MM-DD[&amp;regime={slug}] — 回傳指定日期所有在任領導人（retracted_at IS NULL 且 valid_period @> date）。</summary>
    public static async Task<IResult> GetOnDate(DateOnly? date, string? regime, WorldLineDbContext db, CancellationToken ct)
    {
        if (date is not { } d)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "date 為必填（YYYY-MM-DD）。", "date");

        var features = await BuildOnDateAsync(d, regime, db, ct);
        return ApiResults.Ok(new LeaderMapDto(d, features));
    }

    internal static async Task<List<LeaderFeature>> BuildOnDateAsync(DateOnly d, string? regimeSlug, WorldLineDbContext db, CancellationToken ct)
    {
        var rows = await (
                from l in db.LeaderRecords.AsNoTracking()
                join r in db.Regimes on l.RegimeId equals r.Id
                where l.RetractedAt == null && l.ValidPeriod.Contains(d)
                    && (regimeSlug == null || r.Slug == regimeSlug)
                orderby l.RegimeId, l.Role, l.Id
                select new { l, r.Slug })
            .ToListAsync(ct);

        return rows.Select(x => new LeaderFeature(
            x.l.Id,
            x.l.RegimeId,
            x.Slug,
            x.l.Name,
            x.l.NameZh,
            x.l.Role,
            x.l.Title,
            Mapping.ToDto(x.l.ValidPeriod)!,
            x.l.Source,
            x.l.SourceUrl,
            x.l.Verified)).ToList();
    }

    private static LeaderRecordDto ToDto(LeaderRecord r) =>
        new(r.Id, r.RegimeId, r.Name, r.NameZh, r.Role, r.Title,
            Mapping.ToDto(r.ValidPeriod)!, r.Source, r.SourceUrl, r.Verified);
}
