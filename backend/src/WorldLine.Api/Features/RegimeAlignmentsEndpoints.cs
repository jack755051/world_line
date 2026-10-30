using Microsoft.EntityFrameworkCore;
using NpgsqlTypes;
using WorldLine.Api.Common;
using WorldLine.Api.Domain;
using WorldLine.Api.Infrastructure;
using WorldLine.Contracts;

namespace WorldLine.Api.Features;

/// <summary>
/// 陣營時間切片（憲法 §6「陣營」、PRD §6.3 regime_alignments、§12 Q11 地圖依陣營色系上色）。
/// - 軸心與同盟只依有文件的正式加入判定，系統不依交戰關係推導；每段歸類都須附來源（R8 合格史料）。
/// - 同一政權的有效切片不可重疊（DB EXCLUDE，衝突回 409）。
/// - 沒有切片的政權不回傳任何陣營，前端顯示「陣營未建置」。
/// 端點路徑為實作提案（PRD §7 尚未列），待拍板。
/// </summary>
public static class RegimeAlignmentsEndpoints
{
    public static void Map(RouteGroupBuilder read, RouteGroupBuilder write)
    {
        read.MapGet("/regimes/{id:guid}/alignments", List).WithTags("Regimes").WithName("GetRegimeAlignments")
            .Ok<IReadOnlyList<RegimeAlignmentDto>>().Errors(404);
        write.MapPost("/regimes/{id:guid}/alignments", Create).WithTags("Regimes").WithName("CreateRegimeAlignment")
            .RequiresApiKey().Created<RegimeAlignmentDto>().Errors(400, 401, 404, 409);
    }

    public static async Task<IResult> List(Guid id, WorldLineDbContext db, CancellationToken ct)
    {
        if (!await db.Regimes.AnyAsync(x => x.Id == id && x.RetractedAt == null, ct))
            throw ApiError.NotFound("政權");
        var rows = await db.RegimeAlignments.AsNoTracking()
            .Where(a => a.RegimeId == id && a.RetractedAt == null)
            .ToListAsync(ct);
        var dtos = await ToDtosAsync(db, rows.OrderBy(a => a.ValidPeriod.LowerBound).ToList(), ct);
        return ApiResults.Ok<IReadOnlyList<RegimeAlignmentDto>>(dtos);
    }

    public static async Task<IResult> Create(Guid id, CreateRegimeAlignmentRequest req, WorldLineDbContext db, CancellationToken ct)
    {
        if (!await db.Regimes.AnyAsync(x => x.Id == id && x.RetractedAt == null, ct))
            throw ApiError.NotFound("政權");

        var camp = Mapping.RequireOneOf(req.Camp, Camps.All, "camp");
        if (req.ValidPeriod?.Start is null)
            throw ApiError.BadRequest(ErrorCodes.PeriodRequired, "validPeriod.start 為必填（正式加入日：條約簽署、宣戰或參戰日）；迄日未知可留空。", "validPeriod");
        var period = Mapping.Optional(req.ValidPeriod, "validPeriod")!.Value;

        if (req.BasisEventId is { } ev && !await db.HistoricalEvents.AnyAsync(x => x.Id == ev && x.RetractedAt == null, ct))
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "basisEventId 指向的事件不存在。", "basisEventId");

        // 憲法 §6「陣營」：每段歸類都須附來源
        var citations = req.Citations ?? [];
        if (citations.Count == 0)
            throw ApiError.BadRequest(ErrorCodes.CitationRequired, "陣營切片必須附至少一筆來源引用（憲法 §6「陣營」）。", "citations");
        var sourceIds = citations.Select(c => c.SourceId).OfType<Guid>().Distinct().ToList();
        var sources = await db.Sources.AsNoTracking().Where(s => sourceIds.Contains(s.Id)).ToDictionaryAsync(s => s.Id, ct);
        var rows = new List<RegimeAlignmentCitation>();
        for (var i = 0; i < citations.Count; i++)
        {
            var c = citations[i];
            var f = $"citations[{i}]";
            if (c.SourceId is not { } sid || !sources.TryGetValue(sid, out var source))
                throw ApiError.BadRequest(ErrorCodes.CitationRequired, "引用的來源不存在。", $"{f}.sourceId");
            var role = Mapping.RequireOneOf(c.Role ?? CitationRoles.Primary, CitationRoles.All, $"{f}.role");
            if (string.IsNullOrWhiteSpace(c.Locator))
                throw ApiError.BadRequest(ErrorCodes.SourceNotQualified, "引用必須標出頁碼、文件號或條文（locator）。", $"{f}.locator");
            var note = Mapping.RequireText(c.EvidenceNote, $"{f}.evidenceNote");
            if (role == CitationRoles.Primary && CitationPolicy.WhyNotQualifiedAlignmentPrimary(source, c.Locator) is { } why)
                throw ApiError.BadRequest(ErrorCodes.SourceNotQualified, why, $"{f}.sourceId");
            rows.Add(new RegimeAlignmentCitation { SourceId = sid, Locator = c.Locator.Trim(), Role = role, EvidenceNote = note });
        }
        if (!rows.Any(r => r.Role == CitationRoles.Primary))
            throw ApiError.BadRequest(ErrorCodes.CitationRequired, "陣營切片至少要有一筆 role = primary 的引用。", "citations");
        if (rows.GroupBy(r => (r.SourceId, r.Locator)).Any(g => g.Count() > 1))
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "同一來源與 locator 的引用重複。", "citations");

        // 同政權有效切片不可重疊（DB 另有 EXCLUDE 兜底）。先查，給出明確訊息。
        var overlap = await db.RegimeAlignments.AsNoTracking()
            .Where(a => a.RegimeId == id && a.RetractedAt == null && a.ValidPeriod.Overlaps(period))
            .Select(a => new { a.Id, a.Camp })
            .FirstOrDefaultAsync(ct);
        if (overlap is not null)
            throw new ApiError(StatusCodes.Status409Conflict, ErrorCodes.ConflictingOfficialVersion,
                $"此政權在重疊期間已有陣營切片（{overlap.Camp}，id {overlap.Id}）。陣營改變請先撤回或分段，不可重疊。");

        var a = new RegimeAlignment
        {
            Id = Guid.CreateVersion7(),
            RegimeId = id,
            Camp = camp,
            ValidPeriod = period,
            BasisEventId = req.BasisEventId,
            Note = Mapping.OptionalLocalized(req.Note, "note"),
            Citations = rows,
        };
        db.RegimeAlignments.Add(a);
        await db.SaveChangesAsync(ct); // 切片與引用同一 transaction
        var dto = (await ToDtosAsync(db, [a], ct)).Single();
        return ApiResults.Created($"/api/v1/regimes/{id}/alignments/{a.Id}", dto);
    }

    /// <summary>指定日期各政權有效的陣營切片（給 GET /control 用）。沒有切片的政權不在結果內。</summary>
    internal static async Task<Dictionary<Guid, RegimeAlignmentDto>> ActiveOnAsync(
        WorldLineDbContext db, IReadOnlyCollection<Guid> regimeIds, DateOnly d, CancellationToken ct)
    {
        if (regimeIds.Count == 0) return [];
        var rows = await db.RegimeAlignments.AsNoTracking()
            .Where(a => a.RetractedAt == null && regimeIds.Contains(a.RegimeId) && a.ValidPeriod.Contains(d))
            .ToListAsync(ct);
        var dtos = await ToDtosAsync(db, rows, ct);
        // EXCLUDE 保證同政權同日最多一筆
        return dtos.ToDictionary(x => x.RegimeId);
    }

    private static async Task<List<RegimeAlignmentDto>> ToDtosAsync(WorldLineDbContext db, List<RegimeAlignment> rows, CancellationToken ct)
    {
        var ids = rows.Select(r => r.Id).ToList();
        var cites = (await (
                from c in db.RegimeAlignmentCitations.AsNoTracking()
                join s in db.Sources on c.SourceId equals s.Id
                where ids.Contains(c.RegimeAlignmentId)
                orderby c.Role, s.Title, c.Locator
                select new { c.RegimeAlignmentId, Dto = new CitationDto(s.Id, s.Title, s.Publisher, s.LicenseCode, c.Locator, c.Role, c.EvidenceNote) })
            .ToListAsync(ct))
            .ToLookup(x => x.RegimeAlignmentId, x => x.Dto);
        return rows.Select(a => new RegimeAlignmentDto(
            a.Id, a.RegimeId, a.Camp, Mapping.ToDto((NpgsqlRange<DateOnly>?)a.ValidPeriod)!, a.BasisEventId,
            Mapping.ReadLocalizedOrNull(a.Note), cites[a.Id].ToList())).ToList();
    }
}
