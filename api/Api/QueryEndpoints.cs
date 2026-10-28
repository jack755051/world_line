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
            .WithSummary("查詢某日（或區間）的歷史事件")
            .WithDescription("date=YYYY-MM-DD：與當天有交集的事件；year=YYYY 捷徑；或 from/to（YYYY、YYYY-MM 或 YYYY-MM-DD）。依 start_decimal/end_decimal（由 EDTF 推算）比對，模糊區間只要有交集就納入（憲法 §9「允許區間」）。日期為事件發生地的當地日期，timeZone/timeNote 為時區備註（憲法 §9）。");
        events.MapGet("/{id}/perspectives", PerspectivesAsync).WithSummary("事件的多重視角敘事");
        events.MapGet("/{id}/controversies", ControversiesAsync).WithSummary("事件的爭議點");

        var presets = api.MapGroup("/lineage-presets").WithTags("LineagePresets");
        presets.MapGet("/", PresetsAsync).WithSummary("可用的史觀主線 preset（方案 D）");
        presets.MapGet("/{id:guid}/regimes", PresetRegimesAsync).WithSummary("某 preset 依序排列的政權序列");

        api.MapGet("/reign-eras", ReignErasAsync).WithTags("ReignEras")
            .WithSummary("日期 → 各政權年號（例：1942-06-01 → 昭和十七年、民國三十一年；year=742 → 天寶元年）");
    }

    /// <summary>日期 → 小數年份（與 EDTF 推算同一公式，見 <see cref="EdtfDate"/>）。</summary>
    internal static decimal ToDecimal(DateOnly d) => EdtfDate.Parse(d.ToString("yyyy-MM-dd")).EarliestDecimal;

    private static async Task<IResult> EventsAsync(
        WorldLineDbContext db, DateOnly? date, int? year, string? from, string? to, CancellationToken ct)
    {
        DateOnly lo, hi;
        if (from is not null || to is not null)
        {
            var errors = new Dictionary<string, string[]>();
            var period = PeriodInput.Parse(from, to, requireTo: true, "from", "to", errors);
            if (period is null) return Results.ValidationProblem(errors);
            (lo, hi) = (period.From.Earliest, period.To!.Latest);
        }
        else
        {
            if (!Periods.TryWindow(date, year, out var window, out var werr)) return Results.ValidationProblem(werr!);
            if (window is null) return Results.ValidationProblem(Periods.Required());
            (lo, hi) = (Periods.Lower(window.Value), Periods.UpperInclusive(window.Value)!.Value);
        }
        var loDec = ToDecimal(lo);
        var hiExclusive = hi.Year == 9999 && hi.DayOfYear == 365 ? 10000m : ToDecimal(hi.AddDays(1));

        var rows = await db.HistoricalEvents.AsNoTracking()
            .Where(e => e.StartDecimal < hiExclusive && e.EndDecimal >= loDec)
            .Select(e => new
            {
                e.Id, e.Name, e.ParentEventId, e.StartEdtf, e.EndEdtf, e.StartDecimal, e.EndDecimal, e.OriginPoint, e.TimeZone, e.TimeNote,
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
                e.Tags.OrderBy(t => t).ToList(), e.TimeZone, e.TimeNote, e.OriginPoint, e.PerspectiveCount, e.ControversyCount);
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

    private static async Task<IResult> ReignErasAsync(WorldLineDbContext db, DateOnly? date, int? year, CancellationToken ct)
    {
        if (!Periods.TryWindow(date, year, out var window, out var werr)) return Results.ValidationProblem(werr!);
        if (window is null) return Results.ValidationProblem(Periods.Required());
        var lo = Periods.Lower(window.Value);
        var hi = Periods.UpperInclusive(window.Value)!.Value;
        var rows = await db.ReignEras.AsNoTracking().Include(e => e.Regime)
            .Where(e => e.StartDate <= hi && (e.EndDate == null || e.EndDate >= lo))
            .OrderBy(e => e.Regime.SelfName).ThenBy(e => e.StartDate).ToListAsync(ct);
        var targetYear = lo.Year;
        return Results.Ok(rows.Select(e =>
        {
            var n = targetYear - e.StartDate.Year + 1;
            return new ReignEraYearDto(e.RegimeId, e.Regime.SelfName, e.EraName, e.MonarchName, n,
                $"{e.EraName}{EraNumber(n)}年");
        }).ToList());
    }

    private static readonly string[] Digits = ["〇", "一", "二", "三", "四", "五", "六", "七", "八", "九"];

    /// <summary>年號年序的中文寫法：1 → 元、17 → 十七、31 → 三十一、64 → 六十四、100 → 一百。</summary>
    public static string EraNumber(int n)
    {
        if (n == 1) return "元";
        if (n <= 0) return n.ToString();
        var parts = new System.Text.StringBuilder();
        var hundreds = n / 100;
        var tens = n / 10 % 10;
        var ones = n % 10;
        if (hundreds > 0) parts.Append(Digits[hundreds]).Append('百');
        if (tens > 0)
        {
            if (!(hundreds == 0 && tens == 1)) parts.Append(Digits[tens]);
            parts.Append('十');
        }
        else if (hundreds > 0 && ones > 0) parts.Append('〇');
        if (ones > 0) parts.Append(Digits[ones]);
        return parts.ToString();
    }
}
