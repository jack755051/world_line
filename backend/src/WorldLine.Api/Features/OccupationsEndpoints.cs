using Microsoft.EntityFrameworkCore;
using NpgsqlTypes;
using WorldLine.Api.Common;
using WorldLine.Api.Domain;
using WorldLine.Api.Infrastructure;
using WorldLine.Contracts;

namespace WorldLine.Api.Features;

/// <summary>
/// 佔領歸屬（2026-10-31 Tai：「德國佔領大半歐陸但地圖上看不出來」→ 主權圖層的佔領區以佔領國顏色為底、依控制程度分深淺，再疊斜線）。
/// 依被佔領政權＋期間記錄佔領方與控制程度；依據事件沒有引用（或沒有事件）＝待查證。I5：只新增、只撤回一次。AI 提案・待拍板。
/// </summary>
public static class OccupationsEndpoints
{
    public static void Map(RouteGroupBuilder read, RouteGroupBuilder write)
    {
        write.MapPost("/occupation-attributions", Create).WithTags("Sovereignty").WithName("CreateOccupationAttribution")
            .RequiresApiKey().Created<OccupationAttributionDto>().Errors(400, 401, 409);
        write.MapPost("/occupation-attributions/{id:guid}/retraction", Retract).WithTags("Sovereignty").WithName("RetractOccupationAttribution")
            .RequiresApiKey().Ok<RetractionDto>().Errors(400, 401, 404, 409);
    }

    public static async Task<IResult> Create(CreateOccupationAttributionRequest req, WorldLineDbContext db, CancellationToken ct)
    {
        if (req.OccupiedRegimeId is not { } occupied || req.OccupierRegimeId is not { } occupier)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "occupiedRegimeId 與 occupierRegimeId 為必填。", req.OccupiedRegimeId is null ? "occupiedRegimeId" : "occupierRegimeId");
        if (occupied == occupier)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "被佔領方與佔領方不可是同一政權。", "occupierRegimeId");
        if (await db.Regimes.CountAsync(x => (x.Id == occupied || x.Id == occupier) && x.RetractedAt == null, ct) != 2)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "occupiedRegimeId 或 occupierRegimeId 指向的政權不存在。", "occupiedRegimeId");
        var kind = Mapping.RequireOneOf(req.ControlKind, OccupationControlKinds.All, "controlKind");
        if (req.ValidPeriod?.Start is null)
            throw ApiError.BadRequest(ErrorCodes.PeriodRequired, "validPeriod.start 為必填；迄日未知可留空。", "validPeriod");
        var period = Mapping.Optional(req.ValidPeriod, "validPeriod")!.Value;
        if (req.BasisEventId is { } ev && !await db.HistoricalEvents.AnyAsync(x => x.Id == ev && x.RetractedAt == null, ct))
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "basisEventId 指向的事件不存在。", "basisEventId");

        var overlap = await db.OccupationAttributions.AsNoTracking()
            .Where(x => x.OccupiedRegimeId == occupied && x.RetractedAt == null && x.ValidPeriod.Overlaps(period))
            .Select(x => x.Id).FirstOrDefaultAsync(ct);
        if (overlap != Guid.Empty)
            throw new ApiError(StatusCodes.Status409Conflict, ErrorCodes.ConflictingOfficialVersion,
                $"此政權在重疊期間已有佔領歸屬（id {overlap}）。改變請分段，修正請先撤回。");

        var r = new OccupationAttribution
        {
            Id = Guid.CreateVersion7(),
            OccupiedRegimeId = occupied,
            OccupierRegimeId = occupier,
            ControlKind = kind,
            ValidPeriod = period,
            BasisEventId = req.BasisEventId,
            CoOccupied = req.CoOccupied ?? false,
            Note = Mapping.OptionalLocalized(req.Note, "note"),
        };
        db.OccupationAttributions.Add(r);
        await db.SaveChangesAsync(ct);
        return ApiResults.Created($"/api/v1/occupation-attributions/{r.Id}", new OccupationAttributionDto(
            r.Id, r.OccupiedRegimeId, r.OccupierRegimeId, r.ControlKind, Mapping.ToDto((NpgsqlRange<DateOnly>?)r.ValidPeriod)!,
            r.BasisEventId, r.CoOccupied, Mapping.ReadLocalizedOrNull(r.Note)));
    }

    public static async Task<IResult> Retract(Guid id, RetractionRequest req, WorldLineDbContext db, CancellationToken ct)
    {
        var reason = Mapping.RequireText(req.Reason, "reason");
        var row = await db.OccupationAttributions.AsNoTracking().Select(x => new { x.Id, x.RetractedAt }).FirstOrDefaultAsync(x => x.Id == id, ct)
                  ?? throw ApiError.NotFound("佔領歸屬");
        if (row.RetractedAt is not null)
            throw new ApiError(StatusCodes.Status409Conflict, ErrorCodes.ConflictingOfficialVersion, $"佔領歸屬 {id} 已於 {row.RetractedAt:O} 撤回。");
        var now = DateTimeOffset.UtcNow;
        var n = await db.OccupationAttributions.Where(x => x.Id == id && x.RetractedAt == null)
            .ExecuteUpdateAsync(u => u.SetProperty(x => x.RetractedAt, now).SetProperty(x => x.RetractionReason, reason), ct);
        if (n != 1)
            throw new ApiError(StatusCodes.Status409Conflict, ErrorCodes.ConflictingOfficialVersion, $"佔領歸屬 {id} 已被撤回。");
        return ApiResults.Ok(new RetractionDto(id, now, reason));
    }

    /// <summary>某日有效的佔領歸屬（依被佔領政權）＋佔領方 slug＋依據事件（沒有引用＝待查證）。</summary>
    internal static async Task<Dictionary<Guid, OccupationRefDto>> ActiveOnAsync(WorldLineDbContext db, IReadOnlyCollection<Guid> regimeIds, DateOnly d, CancellationToken ct)
    {
        if (regimeIds.Count == 0) return [];
        var rows = await (
                from o in db.OccupationAttributions.AsNoTracking()
                join g in db.Regimes on o.OccupierRegimeId equals g.Id
                where o.RetractedAt == null && regimeIds.Contains(o.OccupiedRegimeId) && o.ValidPeriod.Contains(d)
                select new { o, g.Slug })
            .ToListAsync(ct);
        var evIds = rows.Select(x => x.o.BasisEventId).OfType<Guid>().Distinct().ToList();
        var events = await SovereigntyEndpoints.EventRefsAsync(db, evIds, ct);
        return rows.GroupBy(x => x.o.OccupiedRegimeId).ToDictionary(x => x.Key, x =>
        {
            var o = x.First().o;
            var ev = o.BasisEventId is { } e ? events.GetValueOrDefault(e) : null;
            return new OccupationRefDto(o.Id, o.OccupierRegimeId, x.First().Slug, o.ControlKind, o.CoOccupied,
                Mapping.ToDto((NpgsqlRange<DateOnly>?)o.ValidPeriod)!, ev, ev?.Verification ?? "pending", Mapping.ReadLocalizedOrNull(o.Note));
        });
    }
}
