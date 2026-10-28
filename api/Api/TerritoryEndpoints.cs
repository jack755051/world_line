using Microsoft.EntityFrameworkCore;
using NetTopologySuite.Geometries;
using WorldLine.Api.Data;
using WorldLine.Api.Domain;

namespace WorldLine.Api.Api;

public static class TerritoryEndpoints
{
    private static readonly GeometryFactory Factory = new(new PrecisionModel(), 4326);

    public static void Map(RouteGroupBuilder api)
    {
        var g = api.MapGroup("").WithTags("Territories");

        g.MapGet("/territories", SnapshotAsync)
            .WithSummary("某日所有政權疆域並存快照（GeoJSON FeatureCollection）")
            .WithDescription("date=YYYY-MM-DD（快照建議用 date）；year=YYYY 為捷徑（該年任一天有效即納入，同一政權可能回傳多個版本）。只回傳現行版本（未被取代）。properties.controlledBy 列出當時控制此政權的一方（佔領／傀儡…，憲法 §4 控制關係）。observer / names 同 GET /regimes。");
        g.MapGet("/regimes/{id:guid}/territories", HistoryAsync)
            .WithSummary("某政權的疆域歷史（含被取代的版本鏈，I5）");
        g.MapPost("/regimes/{id:guid}/territories", CreateAsync).AddEndpointFilter<ApiKeyFilter>()
            .WithSummary("新增疆域記錄（需 X-Api-Key；I1 時間區間必填，I3 正式版本不可重疊）");
        g.MapPatch("/territories/{id:guid}/correct", CorrectAsync).AddEndpointFilter<ApiKeyFilter>()
            .WithSummary("史料修正（需 X-Api-Key；I5：產生新版本，舊版本保留並指向新版本，附原因與時間）");
    }

    private static GeoJsonFeature ToFeature(RegimeTerritory t, Regime regime, string? displayName, IReadOnlyList<ControlRefDto>? controlledBy = null) =>
        new(t.Id, t.Geom, new Dictionary<string, object?>
        {
            ["territoryId"] = t.Id,
            ["regimeId"] = regime.Id,
            ["selfName"] = regime.SelfName,
            ["displayName"] = displayName ?? regime.SelfName,
            ["status"] = regime.Status,
            ["validFrom"] = Periods.FromText(t.ValidPeriod, t.ValidFromPrecision),
            ["validFromPrecision"] = t.ValidFromPrecision,
            ["validTo"] = Periods.ToText(t.ValidPeriod, t.ValidToPrecision),
            ["validToPrecision"] = t.ValidToPrecision,
            ["controlledBy"] = controlledBy ?? [],
            ["isDisputed"] = t.IsDisputed,
            ["isIllustrative"] = t.IsIllustrative,
            ["source"] = t.Source,
            ["supersededBy"] = t.SupersededBy,
            ["correctionReason"] = t.CorrectionReason,
            ["correctedAt"] = t.CorrectedAt,
            ["version"] = t.Version,
        });

    private static async Task<IResult> SnapshotAsync(
        WorldLineDbContext db, DateOnly? date, int? year, Guid? observer, string? names, CancellationToken ct)
    {
        if (!Periods.TryWindow(date, year, out var window, out var werr)) return Results.ValidationProblem(werr!);
        if (window is null) return Results.ValidationProblem(Periods.Required());
        var w = window.Value;

        var rows = await db.RegimeTerritories.AsNoTracking().Include(t => t.Regime)
            .Where(t => t.SupersededBy == null && t.ValidPeriod.Overlaps(w))
            .ToListAsync(ct);
        var ids = rows.Select(r => r.RegimeId).Distinct().ToList();
        var display = await RegimeEndpoints.DisplayNamesAsync(db, ids, observer, names, ct);
        var controlled = await RegimeEndpoints.ControlledByAsync(db, ids, w, observer, names, ct);
        var features = rows
            .OrderBy(t => t.Regime.SelfName).ThenBy(t => t.IsDisputed).ThenBy(t => Periods.Lower(t.ValidPeriod))
            .Select(t => ToFeature(t, t.Regime, display.GetValueOrDefault(t.RegimeId), controlled.GetValueOrDefault(t.RegimeId)))
            .ToList();
        // features 為空時前端顯示空狀態（PRD Story 1：資料缺漏的日期不報錯）
        return Results.Ok(new GeoJsonFeatureCollection(features, new Dictionary<string, object?>
        {
            ["date"] = date?.ToString("yyyy-MM-dd"),
            ["year"] = year,
            ["count"] = features.Count,
        }));
    }

    private static async Task<IResult> HistoryAsync(WorldLineDbContext db, Guid id, CancellationToken ct)
    {
        var regime = await db.Regimes.AsNoTracking().FirstOrDefaultAsync(r => r.Id == id, ct);
        if (regime is null) return RegimeEndpoints.NotFound("政權", id);
        var rows = await db.RegimeTerritories.AsNoTracking().Where(t => t.RegimeId == id).ToListAsync(ct);
        var features = rows.OrderBy(t => Periods.Lower(t.ValidPeriod)).ThenBy(t => t.CreatedAt)
            .Select(t => ToFeature(t, regime, null)).ToList();
        return Results.Ok(new GeoJsonFeatureCollection(features));
    }

    private static MultiPolygon? NormalizeGeometry(Geometry? geometry, Dictionary<string, string[]> errors)
    {
        MultiPolygon? multi = geometry switch
        {
            null => null,
            MultiPolygon mp => mp,
            Polygon p => Factory.CreateMultiPolygon([p]),
            _ => null,
        };
        if (geometry is null) errors["geometry"] = ["geometry 必填（GeoJSON Polygon 或 MultiPolygon，WGS84）"];
        else if (multi is null) errors["geometry"] = [$"geometry 必須是 Polygon 或 MultiPolygon，收到 {geometry.GeometryType}"];
        else if (!multi.IsValid) errors["geometry"] = ["geometry 不是合法的多邊形（自相交等）"];
        if (multi is not null) multi.SRID = 4326;
        return multi;
    }

    private static void ValidateWithin(Regime regime, PeriodInput.Parsed? period, Dictionary<string, string[]> errors)
    {
        if (period is null) return;
        if (!Periods.Within(period.Range, regime.ExistencePeriod))
            errors["validFrom"] = [$"疆域期間 {Periods.Describe(period.Range)} 超出政權存續期間 {Periods.Describe(regime.ExistencePeriod)}"];
    }

    private static async Task<IResult> CreateAsync(WorldLineDbContext db, Guid id, CreateTerritoryRequest req, CancellationToken ct)
    {
        var regime = await db.Regimes.FirstOrDefaultAsync(r => r.Id == id, ct);
        if (regime is null) return RegimeEndpoints.NotFound("政權", id);

        var errors = new Dictionary<string, string[]>();
        var period = PeriodInput.Parse(req.ValidFrom, req.ValidTo, requireTo: true, "validFrom", "validTo", errors); // I1
        ValidateWithin(regime, period, errors);
        var geom = NormalizeGeometry(req.Geometry, errors);
        if (errors.Count > 0) return Results.ValidationProblem(errors, title: "疆域資料驗證失敗");

        var territory = new RegimeTerritory
        {
            RegimeId = id,
            ValidPeriod = period!.Range,
            ValidFromPrecision = period.From.Precision,
            ValidToPrecision = period.To!.Precision,
            Geom = geom!,
            IsDisputed = req.IsDisputed,
            IsIllustrative = req.IsIllustrative,
            Source = req.Source,
        };
        db.RegimeTerritories.Add(territory);
        await db.SaveChangesAsync(ct); // I3 衝突在 commit 時由 DB exclusion constraint 擋下 → 409

        return Results.Created($"/api/v1/regimes/{id}/territories", ToFeature(territory, regime, null));
    }

    private static async Task<IResult> CorrectAsync(WorldLineDbContext db, Guid id, CorrectTerritoryRequest req, CancellationToken ct)
    {
        var old = await db.RegimeTerritories.Include(t => t.Regime).FirstOrDefaultAsync(t => t.Id == id, ct);
        if (old is null) return RegimeEndpoints.NotFound("疆域版本", id);

        var errors = new Dictionary<string, string[]>();
        if (req.Version is null) errors["version"] = ["version 必填（樂觀併發）"];
        if (string.IsNullOrWhiteSpace(req.Reason)) errors["reason"] = ["I5：史料修正必須提供原因"];
        var period = PeriodInput.Parse(
            req.ValidFrom ?? Periods.FromText(old.ValidPeriod, old.ValidFromPrecision),
            req.ValidTo ?? Periods.ToText(old.ValidPeriod, old.ValidToPrecision),
            requireTo: true, "validFrom", "validTo", errors);
        ValidateWithin(old.Regime, period, errors);
        var geom = req.Geometry is null ? old.Geom : NormalizeGeometry(req.Geometry, errors);
        if (errors.Count > 0) return Results.ValidationProblem(errors, title: "史料修正驗證失敗");

        if (old.SupersededBy is not null)
            return Results.Problem(title: "此版本已被取代", detail: $"請修正目前的現行版本 {old.SupersededBy}。", statusCode: 409);
        if (req.Version != old.Version)
            return Results.Problem(title: "版本衝突", detail: $"目前版本為 {old.Version}，請重新讀取後再送出。", statusCode: 409);

        var corrected = new RegimeTerritory
        {
            Id = Guid.NewGuid(),
            RegimeId = old.RegimeId,
            ValidPeriod = period!.Range,
            ValidFromPrecision = period.From.Precision,
            ValidToPrecision = period.To!.Precision,
            Geom = (MultiPolygon)geom!.Copy(),
            IsDisputed = req.IsDisputed ?? old.IsDisputed,
            IsIllustrative = req.IsIllustrative ?? old.IsIllustrative,
            Source = req.Source ?? old.Source,
        };
        db.RegimeTerritories.Add(corrected);
        db.Entry(old).Property(t => t.Version).OriginalValue = req.Version!.Value;
        old.SupersededBy = corrected.Id;
        old.CorrectionReason = req.Reason!.Trim();
        old.CorrectedAt = DateTimeOffset.UtcNow;
        await db.SaveChangesAsync(ct); // 新版本與舊版本標記在同一交易內（I3 延遲檢查）

        return Results.Ok(new
        {
            previousId = old.Id,
            current = ToFeature(corrected, old.Regime, null),
        });
    }
}
