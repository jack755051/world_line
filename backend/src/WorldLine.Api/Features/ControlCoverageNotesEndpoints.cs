using Microsoft.EntityFrameworkCore;
using NpgsqlTypes;
using WorldLine.Api.Common;
using WorldLine.Api.Domain;
using WorldLine.Api.Infrastructure;
using WorldLine.Contracts;

namespace WorldLine.Api.Features;

/// <summary>
/// 涵蓋備註（R9「控制資料缺」、PRD §6.3 control_coverage_notes、§6.4 選項 C、§7 POST /control-coverage-notes）。
/// 只說明「缺」及原因，不產生任何控制類型。PRD 選項 C 的缺口本應由 reference_land − 控制紀錄聯集推導；
/// 戰區範圍與 reference_land 尚未建置，暫由備註幾何直接呈現（2026-10-31 實作，AI 提案・待拍板）。
/// </summary>
public static class ControlCoverageNotesEndpoints
{
    public static void Map(RouteGroupBuilder read, RouteGroupBuilder write)
    {
        write.MapPost("/control-coverage-notes", Create).WithTags("Control").WithName("CreateControlCoverageNote")
            .RequiresApiKey().Created<CoverageNoteDto>().Errors(400, 401, 409);
    }

    public static async Task<IResult> Create(CreateCoverageNoteRequest req, WorldLineDbContext db, CancellationToken ct)
    {
        var reason = Mapping.RequireOneOf(req.Reason, CoverageReasons.All, "reason");
        var period = Mapping.RequireBounded(req.ValidPeriod, "validPeriod");
        var geom = Mapping.RequireMultiPolygon(req.Geometry, "geometry");
        if (req.TheaterId is { } tid && !await db.Theaters.AnyAsync(t => t.Id == tid, ct))
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "theaterId 指向的戰區不存在。", "theaterId");

        // R9：缺口不可與同期間的現行控制紀錄有正面積重疊（否則同一地方既「有控制」又「資料缺」）
        var conflict = await db.ControlRecordVersions.AsNoTracking()
            .Where(v => v.SupersededBy == null && !v.IsRetraction && v.ValidPeriod.Overlaps(period)
                        && v.Geom.Intersects(geom) && v.Geom.Intersection(geom).Area > 1e-8)
            .Select(v => new { v.Id, v.ControlRecordId })
            .FirstOrDefaultAsync(ct);
        if (conflict is not null)
            throw new ApiError(StatusCodes.Status409Conflict, ErrorCodes.ConflictingOfficialVersion,
                $"缺口範圍與同期間的現行控制紀錄重疊（control record {conflict.ControlRecordId}，version {conflict.Id}）（R9）。");

        var n = new ControlCoverageNote
        {
            Id = Guid.CreateVersion7(),
            TheaterId = req.TheaterId,
            Geom = geom,
            ValidPeriod = period,
            Reason = reason,
            Note = Mapping.OptionalLocalized(req.Note, "note"),
            ResearchRef = string.IsNullOrWhiteSpace(req.ResearchRef) ? null : req.ResearchRef.Trim(),
        };
        db.ControlCoverageNotes.Add(n);
        await db.SaveChangesAsync(ct);
        return ApiResults.Created($"/api/v1/control-coverage-notes/{n.Id}", ToDto(n));
    }

    internal static async Task<IReadOnlyList<CoverageNoteDto>> ActiveOnAsync(WorldLineDbContext db, DateOnly d, CancellationToken ct)
    {
        var rows = await db.ControlCoverageNotes.AsNoTracking()
            .Where(x => x.RetractedAt == null && x.ValidPeriod.Contains(d))
            .OrderBy(x => x.Id)
            .ToListAsync(ct);
        return rows.Select(ToDto).ToList();
    }

    private static CoverageNoteDto ToDto(ControlCoverageNote n) => new(
        n.Id, n.TheaterId, Mapping.ToGeoJson(n.Geom), Mapping.ToDto((NpgsqlRange<DateOnly>?)n.ValidPeriod)!, n.Reason,
        Mapping.ReadLocalizedOrNull(n.Note), n.ResearchRef);
}
