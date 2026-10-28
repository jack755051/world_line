using Microsoft.EntityFrameworkCore;
using WorldLine.Api.Common;
using WorldLine.Api.Domain;
using WorldLine.Api.Infrastructure;
using WorldLine.Contracts;

namespace WorldLine.Api.Features;

/// <summary>控制軸（R6）：新增控制紀錄（I1、I3、I6、R7）與依日期查詢。</summary>
public static class ControlEndpoints
{
    public static void Map(RouteGroupBuilder read, RouteGroupBuilder write)
    {
        read.MapGet("/control", GetControl).WithTags("Control").WithName("GetControl");
        write.MapPost("/control-records", Create).WithTags("Control").WithName("CreateControlRecord").RequiresApiKey();
    }

    /// <summary>POST /control-records：新增控制紀錄（第一版）。身分、版本、引用同一 transaction 寫入。</summary>
    public static async Task<IResult> Create(CreateControlRecordRequest req, WorldLineDbContext db, CancellationToken ct)
    {
        // I1：期間必填且兩端有界
        var period = Mapping.RequireBounded(req.ValidPeriod, "validPeriod");

        // I6：至少一筆引用
        var citations = req.Citations ?? [];
        if (citations.Count == 0)
            throw ApiError.BadRequest(ErrorCodes.CitationRequired, "控制紀錄必須附至少一筆來源引用（I6）。", "citations");

        var controlType = Mapping.RequireOneOf(req.ControlType, ControlTypes.All, "controlType");
        var geom = Mapping.RequireMultiPolygon(req.Geometry, "geometry");
        var startU = Mapping.Optional(req.StartUncertainty, "startUncertainty");
        var endU = Mapping.Optional(req.EndUncertainty, "endUncertainty");

        if (req.ControllerRegimeId is not { } controllerId)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "controllerRegimeId 為必填。", "controllerRegimeId");
        if (req.SnapshotId is not { } snapshotId)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "snapshotId 為必填（控制紀錄掛在史料快照底下，§9）。", "snapshotId");
        if (!await db.Regimes.AnyAsync(x => x.Id == controllerId && x.RetractedAt == null, ct))
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "controllerRegimeId 指向的政權不存在。", "controllerRegimeId");
        if (!await db.ControlSnapshots.AnyAsync(x => x.Id == snapshotId, ct))
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "snapshotId 指向的快照不存在。", "snapshotId");
        if (req.PatronRegimeId is { } patronId && !await db.Regimes.AnyAsync(x => x.Id == patronId && x.RetractedAt == null, ct))
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "patronRegimeId 指向的政權不存在。", "patronRegimeId");

        // 引用欄位與 R7（primary citation 必須是地圖類、有 locator、授權在允許清單）
        var sourceIds = citations.Select(c => c.SourceId).OfType<Guid>().Distinct().ToList();
        var sources = await db.Sources.AsNoTracking().Where(s => sourceIds.Contains(s.Id)).ToDictionaryAsync(s => s.Id, ct);
        var rows = new List<ControlRecordCitation>();
        for (var i = 0; i < citations.Count; i++)
        {
            var c = citations[i];
            var f = $"citations[{i}]";
            if (c.SourceId is not { } sid || !sources.TryGetValue(sid, out var source))
                throw ApiError.BadRequest(ErrorCodes.CitationRequired, "引用的來源不存在。", $"{f}.sourceId");
            var role = Mapping.RequireOneOf(c.Role ?? CitationRoles.Primary, CitationRoles.All, $"{f}.role");
            if (string.IsNullOrWhiteSpace(c.Locator))
                throw ApiError.BadRequest(ErrorCodes.SourceNotQualified, "引用必須標出圖集與圖號／頁碼（locator，R7）。", $"{f}.locator");
            var note = Mapping.RequireText(c.EvidenceNote, $"{f}.evidenceNote");
            if (role == CitationRoles.Primary && CitationPolicy.WhyNotQualifiedPrimary(source, c.Locator) is { } why)
                throw ApiError.BadRequest(ErrorCodes.SourceNotQualified, why + "（R7）", $"{f}.sourceId");
            rows.Add(new ControlRecordCitation { SourceId = sid, Locator = c.Locator.Trim(), Role = role, EvidenceNote = note });
        }
        if (!rows.Any(r => r.Role == CitationRoles.Primary))
            throw ApiError.BadRequest(ErrorCodes.CitationRequired, "控制紀錄至少要有一筆 role = primary 的地圖類引用（I6＋R7）。", "citations");
        if (rows.GroupBy(r => (r.SourceId, r.Locator)).Any(g => g.Count() > 1))
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "同一來源與 locator 的引用重複。", "citations");

        // I3：同控制方、時間重疊、幾何相交面積 > 容差，且雙方都非 is_disputed 的現行版本 → 409。
        // 容差數值 PRD 標 TODO；暫用 0（任何正面積重疊都算，邊界相接不算）。
        if (!req.IsDisputed)
        {
            var conflict = await db.ControlRecordVersions.AsNoTracking()
                .Where(v => v.SupersededBy == null && !v.IsRetraction && !v.IsDisputed
                            && v.ValidPeriod.Overlaps(period)
                            && db.ControlRecords.Any(r => r.Id == v.ControlRecordId && r.ControllerRegimeId == controllerId)
                            && v.Geom.Intersects(geom) && v.Geom.Intersection(geom).Area > 0)
                .Select(v => new { v.Id, v.ControlRecordId })
                .FirstOrDefaultAsync(ct);
            if (conflict is not null)
                throw new ApiError(StatusCodes.Status409Conflict, ErrorCodes.ConflictingOfficialVersion,
                    $"同一控制方在重疊期間已有幾何重疊的現行紀錄（control record {conflict.ControlRecordId}，version {conflict.Id}）。" +
                    "請改為修正既有紀錄，或明確標記 isDisputed（I3）。");
        }

        var record = new ControlRecord { Id = Guid.CreateVersion7(), ControllerRegimeId = controllerId };
        var version = new ControlRecordVersion
        {
            Id = Guid.CreateVersion7(),
            SnapshotId = snapshotId,
            ControlType = controlType,
            PatronRegimeId = req.PatronRegimeId,
            ValidPeriod = period,
            StartUncertainty = startU,
            EndUncertainty = endU,
            Geom = geom,
            IsDisputed = req.IsDisputed,
            Citations = rows,
        };
        record.Versions.Add(version);
        db.ControlRecords.Add(record);
        await db.SaveChangesAsync(ct); // 單一 SaveChanges＝單一 transaction（I6：引用與版本同時寫入）

        return ApiResults.Created($"/api/v1/control-records/{record.Id}", new ControlRecordCreatedDto(record.Id, version.Id));
    }

    /// <summary>GET /control?date=：指定日期的控制區（現行版本），並依戰區回報史料／推估狀態（PRD §6.7）。</summary>
    public static async Task<IResult> GetControl(DateOnly? date, WorldLineDbContext db, CancellationToken ct)
    {
        if (date is not { } d)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "date 為必填（YYYY-MM-DD）。", "date");

        var versions = await (
                from v in db.ControlRecordVersions.AsNoTracking()
                join r in db.ControlRecords on v.ControlRecordId equals r.Id
                join s in db.ControlSnapshots on v.SnapshotId equals s.Id
                join t in db.Theaters on s.TheaterId equals t.Id
                where v.SupersededBy == null && !v.IsRetraction && v.ValidPeriod.Contains(d)
                orderby t.Code, v.Id
                select new { v, r.ControllerRegimeId, TheaterCode = t.Code })
            .ToListAsync(ct);

        var versionIds = versions.Select(x => x.v.Id).ToList();
        var citations = (await (
                from c in db.ControlRecordCitations.AsNoTracking()
                join s in db.Sources on c.SourceId equals s.Id
                where versionIds.Contains(c.ControlRecordVersionId)
                orderby c.Role, s.Title
                select new { c.ControlRecordVersionId, Dto = new CitationDto(s.Id, s.Title, s.Publisher, s.LicenseCode, c.Locator, c.Role, c.EvidenceNote) })
            .ToListAsync(ct))
            .ToLookup(x => x.ControlRecordVersionId, x => x.Dto);

        var features = versions.Select(x => new ControlFeature(
            x.v.Id,
            Mapping.ToGeoJson(x.v.Geom),
            new ControlFeatureProperties(
                x.v.ControlRecordId, x.v.Id, x.ControllerRegimeId, x.v.ControlType, x.v.PatronRegimeId,
                x.TheaterCode, x.v.SnapshotId, x.v.IsDisputed,
                Mapping.ToInterval(x.v.ValidPeriod, x.v.StartUncertainty, x.v.EndUncertainty),
                citations[x.v.Id].ToList()))).ToList();

        var theaters = await TheaterStatesAsync(db, d, ct);
        return ApiResults.Ok(new ControlMapDto(d, new ControlFeatureCollection(features), theaters));
    }

    /// <summary>
    /// PRD §6.7（Q4 已拍板）：d 等於某快照 as_of，或落在 interval 快照的 attested_period 內 → attested；
    /// d 位於兩個快照之間 → interpolated（附前後快照）。早於第一個／晚於最後一個快照 → outside（Story 3 TODO，待拍板）。
    /// </summary>
    internal static async Task<IReadOnlyList<TheaterStateDto>> TheaterStatesAsync(WorldLineDbContext db, DateOnly d, CancellationToken ct)
    {
        var snapshots = await (
                from s in db.ControlSnapshots.AsNoTracking()
                join t in db.Theaters on s.TheaterId equals t.Id
                orderby t.Code, s.AsOf
                select new { t.Code, s.Id, s.AsOf, s.AttestedPeriod })
            .ToListAsync(ct);

        return snapshots.GroupBy(s => s.Code).Select(g =>
        {
            var list = g.ToList();
            var attesting = list.FirstOrDefault(s => s.AsOf == d)
                            ?? list.FirstOrDefault(s => s.AttestedPeriod is { } p && Contains(p, d));
            var prev = list.LastOrDefault(s => s.AsOf < d);
            var next = list.FirstOrDefault(s => s.AsOf > d);
            static SnapshotRefDto? Ref(DateOnly? asOf, Guid? id) => id is { } i && asOf is { } a ? new SnapshotRefDto(i, a) : null;
            var state = attesting is not null ? "attested" : prev is not null && next is not null ? "interpolated" : "outside";
            return new TheaterStateDto(g.Key, state, Ref(attesting?.AsOf, attesting?.Id), Ref(prev?.AsOf, prev?.Id), Ref(next?.AsOf, next?.Id));
        }).ToList();
    }

    private static bool Contains(NpgsqlTypes.NpgsqlRange<DateOnly> r, DateOnly d) =>
        !r.IsEmpty
        && (r.LowerBoundInfinite || (r.LowerBoundIsInclusive ? d >= r.LowerBound : d > r.LowerBound))
        && (r.UpperBoundInfinite || (r.UpperBoundIsInclusive ? d <= r.UpperBound : d < r.UpperBound));
}
