using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using WorldLine.Api.Data;
using WorldLine.Api.Edtf;

namespace WorldLine.Api.Api;

/// <summary>事件、史觀主線、年號等唯讀端點。</summary>
public static class QueryEndpoints
{
    public static void Map(RouteGroupBuilder api)
    {
        var events = api.MapGroup("/events").WithTags("Events");
        events.MapGet("/", EventsAsync)
            .WithSummary("查詢某年份（或區間）的歷史事件")
            .WithDescription("year：與該年有交集的事件；或用 from/to 指定年份區間。依 start_decimal/end_decimal（由 EDTF 推算）比對，模糊區間只要有交集就納入（憲法 §9「允許區間」）。");
        events.MapGet("/{id}/perspectives", PerspectivesAsync).WithSummary("事件的多重視角敘事");
        events.MapGet("/{id}/controversies", ControversiesAsync).WithSummary("事件的爭議點");

        var presets = api.MapGroup("/lineage-presets").WithTags("LineagePresets");
        presets.MapGet("/", PresetsAsync).WithSummary("可用的史觀主線 preset（方案 D）");
        presets.MapGet("/{id:guid}/regimes", PresetRegimesAsync).WithSummary("某 preset 依序排列的政權序列");

        api.MapGet("/reign-eras", ReignErasAsync).WithTags("ReignEras")
            .WithSummary("西元年 → 各政權年號（例：742 → 唐 天寶元年）");
    }

    private static async Task<IResult> EventsAsync(WorldLineDbContext db, int? year, int? from, int? to, CancellationToken ct)
    {
        if (year is null && (from is null || to is null))
            return Results.ValidationProblem(new Dictionary<string, string[]> { ["year"] = ["請提供 year，或同時提供 from 與 to"] });
        decimal lo = year ?? from!.Value;
        decimal hiExclusive = (year ?? to!.Value) + 1;

        var rows = await db.HistoricalEvents.AsNoTracking()
            .Where(e => e.StartDecimal < hiExclusive && e.EndDecimal >= lo)
            .Select(e => new
            {
                e.Id, e.Name, e.ParentEventId, e.StartEdtf, e.EndEdtf, e.StartDecimal, e.EndDecimal, e.OriginPoint,
                Tags = e.Tags.Select(t => t.Tag.TagName).ToList(),
                PerspectiveCount = e.Perspectives.Count,
                ControversyCount = e.Controversies.Count,
            })
            .OrderBy(e => e.StartDecimal)
            .ToListAsync(ct);

        return Results.Ok(rows.Select(e =>
        {
            var start = EdtfDate.Parse(e.StartEdtf);
            var end = EdtfDate.Parse(e.EndEdtf);
            var precision = (EdtfPrecision)Math.Min((int)start.Precision, (int)end.Precision);
            return new EventDto(e.Id, e.Name, e.ParentEventId, e.StartEdtf, e.EndEdtf, e.StartDecimal, e.EndDecimal,
                precision.ToString().ToLowerInvariant(),
                start.Uncertain || end.Uncertain || start.Unspecified || end.Unspecified,
                start.Approximate || end.Approximate,
                e.Tags.OrderBy(t => t).ToList(), e.OriginPoint, e.PerspectiveCount, e.ControversyCount);
        }).ToList());
    }

    private static object? Json(string? raw) => raw is null ? null : JsonSerializer.Deserialize<JsonElement>(raw);

    private static async Task<IResult> PerspectivesAsync(WorldLineDbContext db, string id, CancellationToken ct)
    {
        if (!await db.HistoricalEvents.AnyAsync(e => e.Id == id, ct)) return RegimeEndpoints.NotFound("事件", id);
        var rows = await db.HistoricalEventPerspectives.AsNoTracking()
            .Include(p => p.Regime).Include(p => p.ObserverCategory)
            .Where(p => p.EventId == id).OrderBy(p => p.CreatedAt).ToListAsync(ct);
        return Results.Ok(rows.Select(p => new PerspectiveDto(p.Id,
            p.Regime is null ? null : new RegimeRef(p.Regime.Id, p.Regime.SelfName),
            p.ObserverCategory?.CategoryName, p.LocalName, p.NarrativeSummary, p.OfficialJustification,
            Json(p.PrimarySources), Json(p.ClaimedCasualties))).ToList());
    }

    private static async Task<IResult> ControversiesAsync(WorldLineDbContext db, string id, CancellationToken ct)
    {
        if (!await db.HistoricalEvents.AnyAsync(e => e.Id == id, ct)) return RegimeEndpoints.NotFound("事件", id);
        var rows = await db.HistoricalEventControversies.AsNoTracking()
            .Where(c => c.EventId == id).OrderBy(c => c.CreatedAt).ToListAsync(ct);
        return Results.Ok(rows.Select(c => new ControversyDto(c.Id, c.Topic, c.NeutralDescription, Json(c.Viewpoints))).ToList());
    }

    private static async Task<IResult> PresetsAsync(WorldLineDbContext db, CancellationToken ct) =>
        Results.Ok(await db.LineagePresets.AsNoTracking()
            .OrderByDescending(p => p.IsDefault).ThenBy(p => p.PresetName)
            .Select(p => new LineagePresetDto(p.Id, p.PresetName, p.Description, p.IsDefault, p.Members.Count))
            .ToListAsync(ct));

    private static async Task<IResult> PresetRegimesAsync(WorldLineDbContext db, Guid id, CancellationToken ct)
    {
        if (!await db.LineagePresets.AnyAsync(p => p.Id == id, ct)) return RegimeEndpoints.NotFound("史觀主線", id);
        var members = await db.LineagePresetMembers.AsNoTracking().Include(m => m.Regime)
            .Where(m => m.PresetId == id).OrderBy(m => m.SortOrder).ToListAsync(ct);
        return Results.Ok(members.Select(m => new LineageMemberDto(m.SortOrder, RegimeEndpoints.ToSummary(m.Regime))).ToList());
    }

    private static async Task<IResult> ReignErasAsync(WorldLineDbContext db, int? year, CancellationToken ct)
    {
        if (year is null)
            return Results.ValidationProblem(new Dictionary<string, string[]> { ["year"] = ["year 必填"] });
        var rows = await db.ReignEras.AsNoTracking().Include(e => e.Regime)
            .Where(e => e.StartYear <= year && e.EndYear >= year)
            .OrderBy(e => e.Regime.SelfName).ThenBy(e => e.StartYear).ToListAsync(ct);
        return Results.Ok(rows.Select(e =>
        {
            var n = year.Value - e.StartYear + 1;
            return new ReignEraYearDto(e.RegimeId, e.Regime.SelfName, e.EraName, e.MonarchName, n,
                $"{e.EraName}{(n == 1 ? "元" : n.ToString())}年");
        }).ToList());
    }
}
