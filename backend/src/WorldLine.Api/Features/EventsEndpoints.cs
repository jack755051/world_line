using Microsoft.EntityFrameworkCore;
using NetTopologySuite.Geometries;
using WorldLine.Api.Common;
using WorldLine.Api.Domain;
using WorldLine.Api.Infrastructure;
using WorldLine.Contracts;

namespace WorldLine.Api.Features;

/// <summary>
/// 歷史事件（PRD §6.3 historical_events）。日期規則（Tai 2026-10-28 修正）：
/// occurred 記發生地的當地日期；time_note 為選填多語備註（不記時區欄位）。
/// 參與方（event_participants）與引用（event_citations）2026-10-31 實作（AI 提案・待拍板）：
/// 隨事件同一 transaction 寫入，寫入後不可改、不可刪（I5）；引用必須有 locator 且授權在允許清單（有使用權）。
/// 命名、爭議點仍待後續。
/// </summary>
public static class EventsEndpoints
{
    public static void Map(RouteGroupBuilder read, RouteGroupBuilder write)
    {
        write.MapPost("/events", Create).WithTags("Events").WithName("CreateEvent")
            .RequiresApiKey().Created<EventDto>().Errors(400, 401);
        write.MapPost("/events/{id:guid}/participants", AppendParticipant).WithTags("Events").WithName("AppendEventParticipant")
            .RequiresApiKey().Created<EventDto>().Errors(400, 401, 404, 409);
        read.MapGet("/events/{id:guid}", Get).WithTags("Events").WithName("GetEvent").Ok<EventDto>().Errors(404);
        read.MapGet("/regimes/{id:guid}/events", ListForRegime).WithTags("Events").WithName("ListRegimeEvents")
            .Ok<IReadOnlyList<RegimeEventDto>>().Errors(404);
    }

    public static async Task<IResult> Create(CreateEventRequest req, WorldLineDbContext db, CancellationToken ct)
    {
        var kind = Mapping.RequireOneOf(req.EventKind, EventKinds.All, "eventKind");
        var occurred = Mapping.RequireBounded(req.Occurred, "occurred");
        var precision = Mapping.RequireOneOf(req.DatePrecision, DatePrecisions.All, "datePrecision");

        Geometry? location = null;
        if (req.Location is { } loc)
        {
            location = Mapping.RequireGeometry(loc, "location");
        }
        if (req.ParentEventId is { } parent && !await db.HistoricalEvents.AnyAsync(x => x.Id == parent && x.RetractedAt == null, ct))
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "parentEventId 指向的事件不存在。", "parentEventId");

        var e = new HistoricalEvent
        {
            Id = Guid.CreateVersion7(),
            EventKind = kind,
            ParentEventId = req.ParentEventId,
            Summary = Mapping.OptionalLocalized(req.Summary, "summary"),
            Occurred = occurred,
            DatePrecision = precision,
            TimeNote = Mapping.OptionalLocalized(req.TimeNote, "timeNote"),
            Location = location,
        };

        // 參與方
        var parts = new List<EventParticipant>();
        var pin = req.Participants ?? [];
        var regimeIds = pin.Select(p => p.RegimeId).OfType<Guid>().Distinct().ToList();
        var existing = await db.Regimes.AsNoTracking().Where(r => regimeIds.Contains(r.Id) && r.RetractedAt == null).Select(r => r.Id).ToListAsync(ct);
        for (var i = 0; i < pin.Count; i++)
        {
            var f = $"participants[{i}]";
            if (pin[i].RegimeId is not { } rid || !existing.Contains(rid))
                throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "參與方政權不存在。", $"{f}.regimeId");
            var role = Mapping.RequireOneOf(pin[i].Role, EventParticipantRoles.All, $"{f}.role");
            parts.Add(new EventParticipant { EventId = e.Id, RegimeId = rid, Role = role });
        }
        if (parts.GroupBy(p => (p.RegimeId, p.Role)).Any(g => g.Count() > 1))
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "同一政權與角色重複。", "participants");

        // 引用（R8 合格史料；有使用權）
        var cites = new List<EventCitation>();
        var cin = req.Citations ?? [];
        var sourceIds = cin.Select(c => c.SourceId).OfType<Guid>().Distinct().ToList();
        var sources = await db.Sources.AsNoTracking().Where(s => sourceIds.Contains(s.Id)).ToDictionaryAsync(s => s.Id, ct);
        for (var i = 0; i < cin.Count; i++)
        {
            var c = cin[i];
            var f = $"citations[{i}]";
            if (c.SourceId is not { } sid || !sources.TryGetValue(sid, out var source))
                throw ApiError.BadRequest(ErrorCodes.CitationRequired, "引用的來源不存在。", $"{f}.sourceId");
            if (CitationPolicy.WhyNotQualifiedAlignmentPrimary(source, c.Locator ?? "") is { } why)
                throw ApiError.BadRequest(ErrorCodes.SourceNotQualified, why, $"{f}.sourceId");
            cites.Add(new EventCitation { EventId = e.Id, SourceId = sid, Locator = c.Locator!.Trim(), EvidenceNote = Mapping.RequireText(c.EvidenceNote, $"{f}.evidenceNote") });
        }
        if (cites.GroupBy(c => (c.SourceId, c.Locator)).Any(g => g.Count() > 1))
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "同一來源與 locator 的引用重複。", "citations");

        db.HistoricalEvents.Add(e);
        db.EventParticipants.AddRange(parts);
        db.EventCitations.AddRange(cites);
        await db.SaveChangesAsync(ct); // 事件、參與方、引用同一 transaction
        return ApiResults.Created($"/api/v1/events/{e.Id}", (await ToDtosAsync(db, [e], ct)).Single());
    }

    /// <summary>
    /// 事後追加參與方（方案 A）：事件存在且未撤回、政權存在且未撤回、角色在清單內、理由必填；
    /// 同一政權＋角色已存在 → 409（不重複、不覆蓋）。原有參與方、引用、事件欄位都不動（I5）。
    /// </summary>
    public static async Task<IResult> AppendParticipant(Guid id, AppendEventParticipantRequest req, WorldLineDbContext db, CancellationToken ct)
    {
        var e = await db.HistoricalEvents.AsNoTracking().FirstOrDefaultAsync(x => x.Id == id && x.RetractedAt == null, ct)
                ?? throw ApiError.NotFound("事件");
        if (req.RegimeId is not { } rid || !await db.Regimes.AnyAsync(r => r.Id == rid && r.RetractedAt == null, ct))
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "參與方政權不存在。", "regimeId");
        var role = Mapping.RequireOneOf(req.Role, EventParticipantRoles.All, "role");
        var note = Mapping.RequireLocalized(req.Note, "note");
        if (await db.EventParticipants.AnyAsync(p => p.EventId == id && p.RegimeId == rid && p.Role == role, ct))
            throw new ApiError(StatusCodes.Status409Conflict, ErrorCodes.ConflictingOfficialVersion, "此事件已有同一政權與角色的參與方。");
        db.EventParticipants.Add(new EventParticipant { EventId = id, RegimeId = rid, Role = role, AddedAt = DateTimeOffset.UtcNow, AdditionNote = note });
        try
        {
            await db.SaveChangesAsync(ct);
        }
        catch (DbUpdateException ex) when (ex.InnerException is Npgsql.PostgresException { SqlState: "23505" })
        {
            throw new ApiError(StatusCodes.Status409Conflict, ErrorCodes.ConflictingOfficialVersion, "此事件已有同一政權與角色的參與方。");
        }
        return ApiResults.Created($"/api/v1/events/{id}", (await ToDtosAsync(db, [e], ct)).Single());
    }

    public static async Task<IResult> Get(Guid id, WorldLineDbContext db, CancellationToken ct)
    {
        var e = await db.HistoricalEvents.AsNoTracking().FirstOrDefaultAsync(x => x.Id == id && x.RetractedAt == null, ct)
                ?? throw ApiError.NotFound("事件");
        return ApiResults.Ok((await ToDtosAsync(db, [e], ct)).Single());
    }

    /// <summary>
    /// 政權相關事件（依日期排序）：此政權為參與方的事件，加上此政權國界紀錄、衝突紀錄的起訖事件（皆排除已撤回）。
    /// 不推測、不補造：沒有引用的事件 verification = pending。
    /// </summary>
    public static async Task<IResult> ListForRegime(Guid id, WorldLineDbContext db, CancellationToken ct)
    {
        if (!await db.Regimes.AsNoTracking().AnyAsync(r => r.Id == id && r.RetractedAt == null, ct))
            throw ApiError.NotFound("政權");
        var roles = new Dictionary<Guid, SortedSet<string>>();
        void Add(Guid? ev, string role)
        {
            if (ev is not { } g) return;
            if (!roles.TryGetValue(g, out var set)) roles[g] = set = new SortedSet<string>(StringComparer.Ordinal);
            set.Add(role);
        }
        var additions = new Dictionary<Guid, List<ParticipantAdditionDto>>();
        foreach (var p in await db.EventParticipants.AsNoTracking().Where(p => p.RegimeId == id)
                     .Select(p => new { p.EventId, p.Role, p.AddedAt, p.AdditionNote }).ToListAsync(ct))
        {
            Add(p.EventId, p.Role);
            if (p.AddedAt is { } at)
            {
                if (!additions.TryGetValue(p.EventId, out var l)) additions[p.EventId] = l = [];
                l.Add(new ParticipantAdditionDto(p.Role, at, Mapping.ReadLocalizedOrNull(p.AdditionNote)));
            }
        }
        foreach (var r in await db.SovereigntyRecords.AsNoTracking().Where(r => r.RegimeId == id && r.RetractedAt == null)
                     .Select(r => new { r.StartEventId, r.EndEventId }).ToListAsync(ct))
        {
            Add(r.StartEventId, "border_start");
            Add(r.EndEventId, "border_end");
        }
        foreach (var c in await db.ConflictRecords.AsNoTracking().Where(c => (c.RegimeAId == id || c.RegimeBId == id) && c.RetractedAt == null)
                     .Select(c => new { c.StartEventId, c.EndEventId }).ToListAsync(ct))
        {
            Add(c.StartEventId, "conflict_start");
            Add(c.EndEventId, "conflict_end");
        }
        var refs = await SovereigntyEndpoints.EventRefsAsync(db, roles.Keys.ToList(), ct);
        IReadOnlyList<RegimeEventDto> list = refs.Values
            .OrderBy(e => e.Occurred.Start).ThenBy(e => e.Id)
            .Select(e => new RegimeEventDto(e.Id, e.EventKind, e.Occurred, e.Summary, e.Verification, e.Citations, roles[e.Id].ToList(),
                additions.TryGetValue(e.Id, out var adds) ? adds.OrderBy(a => a.AddedAt).ThenBy(a => a.Role, StringComparer.Ordinal).ToList() : null))
            .ToList();
        return ApiResults.Ok(list);
    }

    internal static async Task<List<EventDto>> ToDtosAsync(WorldLineDbContext db, List<HistoricalEvent> rows, CancellationToken ct)
    {
        var ids = rows.Select(r => r.Id).ToList();
        var parts = (await db.EventParticipants.AsNoTracking().Where(p => ids.Contains(p.EventId))
                .OrderBy(p => p.Role).ThenBy(p => p.RegimeId).ToListAsync(ct))
            .ToLookup(p => p.EventId, p => new EventParticipantDto(p.RegimeId, p.Role, p.AddedAt, Mapping.ReadLocalizedOrNull(p.AdditionNote)));
        var cites = (await (
                from c in db.EventCitations.AsNoTracking()
                join s in db.Sources on c.SourceId equals s.Id
                where ids.Contains(c.EventId)
                orderby s.Title, c.Locator
                select new { c.EventId, Dto = new CitationDto(s.Id, s.Title, s.Publisher, s.LicenseCode, c.Locator, "event", c.EvidenceNote) })
            .ToListAsync(ct))
            .ToLookup(x => x.EventId, x => x.Dto);
        return rows.Select(e => new EventDto(
            e.Id, e.EventKind, e.ParentEventId, Mapping.ReadLocalizedOrNull(e.Summary), Mapping.ToDto(e.Occurred)!,
            e.DatePrecision, Mapping.ReadLocalizedOrNull(e.TimeNote),
            e.Location is null ? null : Mapping.ToGeoJson(e.Location),
            parts[e.Id].ToList(), cites[e.Id].ToList())).ToList();
    }

    /// <summary>
    /// 陣營「補充」（使用者 2026-10-31 拍板）：各政權在 d 當日或之前參與、且附引用的事件（war／treaty／political）。
    /// 只作補充呈現，不參與陣營判定（陣營只依 regime_alignments）。
    /// </summary>
    internal static readonly string[] SupplementKinds = ["war", "treaty", "political"];

    internal static async Task<ILookup<Guid, SupplementEventDto>> SupplementsOnAsync(
        WorldLineDbContext db, IReadOnlyCollection<Guid> regimeIds, DateOnly d, CancellationToken ct)
    {
        if (regimeIds.Count == 0) return Array.Empty<(Guid, SupplementEventDto)>().ToLookup(x => x.Item1, x => x.Item2);
        var hits = await (
                from p in db.EventParticipants.AsNoTracking()
                join e in db.HistoricalEvents on p.EventId equals e.Id
                where regimeIds.Contains(p.RegimeId) && e.RetractedAt == null
                      && SupplementKinds.Contains(e.EventKind)
                      && e.Occurred.LowerBound <= d
                      && db.EventCitations.Any(c => c.EventId == e.Id)
                select new { p.RegimeId, Event = e })
            .ToListAsync(ct);
        var events = hits.Select(h => h.Event).DistinctBy(e => e.Id).ToList();
        var dtos = (await ToDtosAsync(db, events, ct)).ToDictionary(x => x.Id);
        return hits
            .DistinctBy(h => (h.RegimeId, h.Event.Id))
            .OrderBy(h => h.Event.Occurred.LowerBound).ThenBy(h => h.Event.Id)
            .ToLookup(h => h.RegimeId, h =>
            {
                var x = dtos[h.Event.Id];
                return new SupplementEventDto(x.Id, x.EventKind, x.Occurred, x.Summary, x.Participants ?? [], x.Citations ?? []);
            });
    }
}
