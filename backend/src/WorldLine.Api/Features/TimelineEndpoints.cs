using Microsoft.EntityFrameworkCore;
using WorldLine.Api.Common;
using WorldLine.Api.Domain;
using WorldLine.Api.Infrastructure;
using WorldLine.Contracts;

namespace WorldLine.Api.Features;

/// <summary>時間軸標記：各戰區的快照日期、標題、主要來源（PRD §7.1、§9、Story 3）。</summary>
public static class TimelineEndpoints
{
    public const int MaxPageSize = 500;

    public static void Map(RouteGroupBuilder read) =>
        read.MapGet("/timeline/snapshots", GetSnapshots).WithTags("Timeline").WithName("GetTimelineSnapshots");

    public static async Task<IResult> GetSnapshots(DateOnly? from, DateOnly? to, int? page, int? pageSize,
        WorldLineDbContext db, CancellationToken ct)
    {
        if (from is { } f0 && to is { } t0 && f0 >= t0)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "from 必須早於 to（半開區間 [from, to)）。", "from");
        var p = Math.Max(1, page ?? 1);
        var size = Math.Clamp(pageSize ?? 100, 1, MaxPageSize);

        var q = from s in db.ControlSnapshots.AsNoTracking()
                join t in db.Theaters on s.TheaterId equals t.Id
                select new { s, t.Code };
        if (from is { } f) q = q.Where(x => x.s.AsOf >= f);
        if (to is { } t1) q = q.Where(x => x.s.AsOf < t1);

        var total = await q.CountAsync(ct);
        var rows = await q.OrderBy(x => x.s.AsOf).ThenBy(x => x.Code).Skip((p - 1) * size).Take(size).ToListAsync(ct);

        var ids = rows.Select(x => x.s.Id).ToList();
        var sources = (await (
                from v in db.ControlRecordVersions.AsNoTracking()
                join c in db.ControlRecordCitations on v.Id equals c.ControlRecordVersionId
                join src in db.Sources on c.SourceId equals src.Id
                where ids.Contains(v.SnapshotId) && v.SupersededBy == null && !v.IsRetraction && c.Role == CitationRoles.Primary
                select new { v.SnapshotId, src.Id, src.Title, c.Locator })
            .Distinct()
            .ToListAsync(ct))
            .ToLookup(x => x.SnapshotId, x => new SnapshotSourceDto(x.Id, x.Title, x.Locator));

        var items = rows.Select(x => new TimelineSnapshotDto(
            x.s.Id, x.Code, x.s.AsOf, x.s.Attestation, Mapping.ToDto(x.s.AttestedPeriod),
            Mapping.ReadLocalizedOrNull(x.s.Title),
            sources[x.s.Id].OrderBy(s => s.Title).ThenBy(s => s.Locator).ToList())).ToList();

        return ApiResults.Ok(new PaginatedResponse<TimelineSnapshotDto>(items, p, size, total));
    }
}
