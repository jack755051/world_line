using Microsoft.EntityFrameworkCore;
using NetTopologySuite.Geometries;
using WorldLine.Api.Common;
using WorldLine.Api.Domain;
using WorldLine.Api.Infrastructure;
using WorldLine.Contracts;

namespace WorldLine.Api.Features;

/// <summary>
/// 歷史事件（PRD §6.3 historical_events）。日期規則（Tai 2026-10-28）：
/// occurred 記發生地的當地日期；local_time_zone 記發生地 IANA 時區；time_note 為選填多語備註。
/// 不在伺服器端做時區換算（史料多只給當地日期）。命名、參與方、引用、爭議點於 M1 補上。
/// </summary>
public static class EventsEndpoints
{
    public static void Map(RouteGroupBuilder read, RouteGroupBuilder write)
    {
        write.MapPost("/events", Create).WithTags("Events").WithName("CreateEvent")
            .RequiresApiKey().Created<EventDto>().Errors(400, 401);
        read.MapGet("/events/{id:guid}", Get).WithTags("Events").WithName("GetEvent").Ok<EventDto>().Errors(404);
    }

    /// <summary>只接受 IANA 時區 ID（例：Asia/Tokyo），不接受 Windows ID 或固定偏移。</summary>
    public static bool IsIanaTimeZone(string id) =>
        id.Contains('/') && !id.StartsWith("Etc/", StringComparison.Ordinal)
        && TimeZoneInfo.TryFindSystemTimeZoneById(id, out var tz) && tz.HasIanaId;

    public static async Task<IResult> Create(CreateEventRequest req, WorldLineDbContext db, CancellationToken ct)
    {
        var kind = Mapping.RequireOneOf(req.EventKind, EventKinds.All, "eventKind");
        var occurred = Mapping.RequireBounded(req.Occurred, "occurred");
        var precision = Mapping.RequireOneOf(req.DatePrecision, DatePrecisions.All, "datePrecision");

        string? zone = null;
        if (!string.IsNullOrWhiteSpace(req.LocalTimeZone))
        {
            zone = req.LocalTimeZone.Trim();
            if (!IsIanaTimeZone(zone))
                throw ApiError.BadRequest(ErrorCodes.ValidationFailed, $"localTimeZone 必須是 IANA 時區（例：Asia/Tokyo、Pacific/Honolulu），收到「{zone}」。", "localTimeZone");
        }

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
            LocalTimeZone = zone,
            TimeNote = Mapping.OptionalLocalized(req.TimeNote, "timeNote"),
            Location = location,
        };
        db.HistoricalEvents.Add(e);
        await db.SaveChangesAsync(ct);
        return ApiResults.Created($"/api/v1/events/{e.Id}", ToDto(e));
    }

    public static async Task<IResult> Get(Guid id, WorldLineDbContext db, CancellationToken ct)
    {
        var e = await db.HistoricalEvents.AsNoTracking().FirstOrDefaultAsync(x => x.Id == id && x.RetractedAt == null, ct)
                ?? throw ApiError.NotFound("事件");
        return ApiResults.Ok(ToDto(e));
    }

    public static EventDto ToDto(HistoricalEvent e) => new(
        e.Id, e.EventKind, e.ParentEventId, Mapping.ReadLocalizedOrNull(e.Summary), Mapping.ToDto(e.Occurred)!,
        e.DatePrecision, e.LocalTimeZone, Mapping.ReadLocalizedOrNull(e.TimeNote),
        e.Location is null ? null : Mapping.ToGeoJson(e.Location));
}
