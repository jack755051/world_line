using Microsoft.EntityFrameworkCore;
using NetTopologySuite.Geometries;
using WorldLine.Api.Data;
using WorldLine.Api.Domain;

namespace WorldLine.Api.Api;

/// <summary>二戰階段（憲法 2026-10-28）：控制關係（佔領／傀儡／保護／殖民／託管）與同盟陣營。</summary>
public static class ControlEndpoints
{
    private static readonly GeometryFactory Factory = new(new PrecisionModel(), 4326);

    public static void Map(RouteGroupBuilder api)
    {
        var c = api.MapGroup("/control-relations").WithTags("ControlRelations");
        c.MapGet("/", ListControlAsync)
            .WithSummary("查詢控制關係（控制方 → 被控制方）")
            .WithDescription("date=YYYY-MM-DD 或 year=YYYY 過濾當時有效的關係；regimeId 只看與某政權有關者（任一方）；type 過濾類型（occupation／puppet／protectorate／colony／mandate）。");
        c.MapGet("/areas", AreasAsync)
            .WithSummary("某日的控制範圍（佔領區等）GeoJSON FeatureCollection")
            .WithDescription("只含有記錄控制範圍幾何的關係；沒有幾何代表控制整個被控制方（用其疆域即可）。");
        c.MapPost("/", CreateControlAsync).AddEndpointFilter<ApiKeyFilter>()
            .WithSummary("新增控制關係（需 X-Api-Key；I6：兩方必須存在、不可相同、必須有起訖日期且落在兩方存續期間內）");

        var a = api.MapGroup("/alliances").WithTags("Alliances");
        a.MapGet("/", ListAlliancesAsync)
            .WithSummary("同盟陣營清單")
            .WithDescription("date／year：只列當時存在的陣營，成員也只列當時在籍者（例：1943-10-01 的軸心國不含義大利）。observer 決定陣營與成員的顯示名。");
        a.MapGet("/{id:guid}", GetAllianceAsync).WithName("GetAlliance").WithSummary("單一陣營（含全部成員的加入／退出日期）");
        a.MapPost("/", CreateAllianceAsync).AddEndpointFilter<ApiKeyFilter>().WithSummary("新增陣營（需 X-Api-Key）");
        a.MapPost("/{id:guid}/members", AddMemberAsync).AddEndpointFilter<ApiKeyFilter>()
            .WithSummary("新增陣營成員期間（需 X-Api-Key；同一政權在同一陣營的期間不可重疊）");
    }

    // ---------- 控制關係 ----------

    private static async Task<IResult> ListControlAsync(
        WorldLineDbContext db, DateOnly? date, int? year, Guid? regimeId, string? type, Guid? observer, string? names, CancellationToken ct)
    {
        if (!Periods.TryWindow(date, year, out var window, out var werr)) return Results.ValidationProblem(werr!);
        if (type is not null && !ControlType.All.Contains(type))
            return Results.ValidationProblem(new Dictionary<string, string[]> { ["type"] = [$"type 必須是 {string.Join("/", ControlType.All)}"] });

        var q = db.RegimeControlRelations.AsNoTracking().Include(x => x.ControllerRegime).Include(x => x.ControlledRegime).AsQueryable();
        if (window is not null) q = q.Where(x => x.ValidPeriod.Overlaps(window.Value));
        if (regimeId is not null) q = q.Where(x => x.ControllerRegimeId == regimeId || x.ControlledRegimeId == regimeId);
        if (type is not null) q = q.Where(x => x.ControlType == type);
        var rows = await q.ToListAsync(ct);

        var ids = rows.SelectMany(r => new[] { r.ControllerRegimeId, r.ControlledRegimeId }).Distinct().ToList();
        var display = await RegimeEndpoints.DisplayNamesAsync(db, ids, observer, names, ct);
        return Results.Ok(rows
            .OrderBy(r => Periods.Lower(r.ValidPeriod)).ThenBy(r => r.ControlledRegime.SelfName)
            .Select(r => RegimeEndpoints.ToControlDto(r, display.GetValueOrDefault(r.ControllerRegimeId), display.GetValueOrDefault(r.ControlledRegimeId)))
            .ToList());
    }

    private static async Task<IResult> AreasAsync(WorldLineDbContext db, DateOnly? date, int? year, Guid? observer, string? names, CancellationToken ct)
    {
        if (!Periods.TryWindow(date, year, out var window, out var werr)) return Results.ValidationProblem(werr!);
        if (window is null) return Results.ValidationProblem(Periods.Required());
        var rows = await db.RegimeControlRelations.AsNoTracking().Include(x => x.ControllerRegime).Include(x => x.ControlledRegime)
            .Where(x => x.Area != null && x.ValidPeriod.Overlaps(window.Value)).ToListAsync(ct);
        var ids = rows.SelectMany(r => new[] { r.ControllerRegimeId, r.ControlledRegimeId }).Distinct().ToList();
        var display = await RegimeEndpoints.DisplayNamesAsync(db, ids, observer, names, ct);
        var features = rows.OrderBy(r => r.ControlledRegime.SelfName).Select(r =>
        {
            var dto = RegimeEndpoints.ToControlDto(r, display.GetValueOrDefault(r.ControllerRegimeId), display.GetValueOrDefault(r.ControlledRegimeId));
            return new GeoJsonFeature(r.Id, r.Area!, new Dictionary<string, object?>
            {
                ["relationId"] = r.Id,
                ["controlType"] = r.ControlType,
                ["controllerRegimeId"] = r.ControllerRegimeId,
                ["controllerName"] = dto.ControllerDisplayName,
                ["controlledRegimeId"] = r.ControlledRegimeId,
                ["controlledName"] = dto.ControlledDisplayName,
                ["validFrom"] = dto.ValidFrom,
                ["validFromPrecision"] = dto.ValidFromPrecision,
                ["validTo"] = dto.ValidTo,
                ["validToPrecision"] = dto.ValidToPrecision,
                ["isDisputed"] = r.IsDisputed,
                ["isIllustrative"] = r.IsIllustrative,
                ["source"] = r.Source,
            });
        }).ToList();
        return Results.Ok(new GeoJsonFeatureCollection(features, new Dictionary<string, object?>
        {
            ["date"] = date?.ToString("yyyy-MM-dd"),
            ["year"] = year,
            ["count"] = features.Count,
        }));
    }

    private static async Task<IResult> CreateControlAsync(WorldLineDbContext db, CreateControlRelationRequest req, CancellationToken ct)
    {
        var errors = new Dictionary<string, string[]>();
        if (req.ControllerRegimeId is null) errors["controllerRegimeId"] = ["I6：必須記錄控制方"];
        if (req.ControlledRegimeId is null) errors["controlledRegimeId"] = ["I6：必須記錄被控制方"];
        if (req.ControllerRegimeId is not null && req.ControllerRegimeId == req.ControlledRegimeId)
            errors["controlledRegimeId"] = ["I6：政權不可控制自己"];
        if (req.ControlType is null || !ControlType.All.Contains(req.ControlType))
            errors["controlType"] = [$"controlType 必須是 {string.Join("/", ControlType.All)}"];
        var period = PeriodInput.Parse(req.ValidFrom, req.ValidTo, requireTo: true, "validFrom", "validTo", errors); // I6

        MultiPolygon? area = null;
        if (req.Area is not null)
        {
            area = req.Area switch
            {
                MultiPolygon mp => mp,
                Polygon p => Factory.CreateMultiPolygon([p]),
                _ => null,
            };
            if (area is null) errors["area"] = [$"area 必須是 Polygon 或 MultiPolygon，收到 {req.Area.GeometryType}"];
            else if (!area.IsValid) errors["area"] = ["area 不是合法的多邊形"];
            else area.SRID = 4326;
        }

        var ids = new[] { req.ControllerRegimeId, req.ControlledRegimeId }.Where(x => x is not null).Select(x => x!.Value).Distinct().ToList();
        var regimes = await db.Regimes.Where(r => ids.Contains(r.Id)).ToDictionaryAsync(r => r.Id, ct);
        foreach (var missing in ids.Where(i => !regimes.ContainsKey(i))) errors[$"regime:{missing}"] = ["I6：參照的政權不存在"];
        if (period is not null)
        {
            foreach (var r in regimes.Values.Where(r => !Periods.Within(period.Range, r.ExistencePeriod)))
                errors[$"regime:{r.Id}"] = [$"I6：控制期間 {Periods.Describe(period.Range)} 超出「{r.SelfName}」存續期間 {Periods.Describe(r.ExistencePeriod)}"];
        }
        if (errors.Count > 0) return Results.ValidationProblem(errors, title: "控制關係驗證失敗");

        var rel = new RegimeControlRelation
        {
            ControllerRegimeId = req.ControllerRegimeId!.Value,
            ControlledRegimeId = req.ControlledRegimeId!.Value,
            ControlType = req.ControlType!,
            ValidPeriod = period!.Range,
            ValidFromPrecision = period.From.Precision,
            ValidToPrecision = period.To!.Precision,
            Area = area,
            IsIllustrative = req.IsIllustrative,
            IsDisputed = req.IsDisputed,
            Description = req.Description,
            Source = req.Source,
        };
        db.RegimeControlRelations.Add(rel);
        await db.SaveChangesAsync(ct); // 同類型、同方向、期間重疊且非爭議 → exclusion constraint → 409
        rel.ControllerRegime = regimes[rel.ControllerRegimeId];
        rel.ControlledRegime = regimes[rel.ControlledRegimeId];
        return Results.Created($"/api/v1/control-relations?regimeId={rel.ControlledRegimeId}", RegimeEndpoints.ToControlDto(rel));
    }

    // ---------- 同盟陣營 ----------

    private static async Task<Dictionary<Guid, string>> AllianceNamesAsync(WorldLineDbContext db, IReadOnlyCollection<Guid> ids, Guid? observer, string? names, CancellationToken ct)
    {
        if (observer is null && names != AliasPerspective.Historiographic) return [];
        var q = db.AllianceAliases.AsNoTracking().Where(a => ids.Contains(a.AllianceId));
        q = observer is not null ? q.Where(a => a.ObserverRegimeId == observer) : q.Where(a => a.AliasType == AliasPerspective.Historiographic);
        var rows = await q.OrderBy(a => a.AliasName.Length).ThenBy(a => a.AliasName).ToListAsync(ct);
        return rows.GroupBy(a => a.AllianceId).ToDictionary(g => g.Key, g => g.First().AliasName);
    }

    private static async Task<List<AllianceDto>> LoadAlliancesAsync(
        WorldLineDbContext db, Guid? id, NpgsqlTypes.NpgsqlRange<DateOnly>? window, Guid? observer, string? names, CancellationToken ct)
    {
        var q = db.Alliances.AsNoTracking()
            .Include(a => a.Aliases).ThenInclude(x => x.ObserverRegime)
            .Include(a => a.Memberships).ThenInclude(m => m.Regime)
            .AsSplitQuery().AsQueryable();
        if (id is not null) q = q.Where(a => a.Id == id);
        if (window is not null) q = q.Where(a => a.ExistencePeriod.Overlaps(window.Value));
        var alliances = await q.ToListAsync(ct);

        var regimeIds = alliances.SelectMany(a => a.Memberships.Select(m => m.RegimeId)).Distinct().ToList();
        var regimeNames = await RegimeEndpoints.DisplayNamesAsync(db, regimeIds, observer, names, ct);
        var allianceNames = await AllianceNamesAsync(db, alliances.Select(a => a.Id).ToList(), observer, names, ct);

        return alliances.OrderBy(a => Periods.Lower(a.ExistencePeriod)).Select(a => new AllianceDto(
            a.Id, a.SelfName, allianceNames.GetValueOrDefault(a.Id) ?? a.SelfName,
            Periods.FromText(a.ExistencePeriod, a.ExistenceFromPrecision), a.ExistenceFromPrecision,
            Periods.ToText(a.ExistencePeriod, a.ExistenceToPrecision), a.ExistenceToPrecision,
            a.Description,
            a.Aliases.OrderBy(x => x.AliasName).Select(x => new AliasDto(x.Id, x.AliasName, x.AliasType,
                x.ObserverRegime is null ? null : new RegimeRef(x.ObserverRegime.Id, x.ObserverRegime.SelfName))).ToList(),
            a.Memberships
                .Where(m => window is null || Overlaps(m.ValidPeriod, window.Value))
                .OrderBy(m => Periods.Lower(m.ValidPeriod)).ThenBy(m => m.Regime.SelfName)
                .Select(m => new AllianceMemberDto(m.Id, new RegimeRef(m.Regime.Id, m.Regime.SelfName),
                    regimeNames.GetValueOrDefault(m.RegimeId) ?? m.Regime.SelfName, m.Role,
                    Periods.FromText(m.ValidPeriod, m.ValidFromPrecision), m.ValidFromPrecision,
                    Periods.ToText(m.ValidPeriod, m.ValidToPrecision), m.ValidToPrecision, m.Note))
                .ToList(),
            a.Version)).ToList();
    }

    private static bool Overlaps(NpgsqlTypes.NpgsqlRange<DateOnly> a, NpgsqlTypes.NpgsqlRange<DateOnly> b)
    {
        var aTo = Periods.UpperInclusive(a);
        var bTo = Periods.UpperInclusive(b);
        return (aTo is null || aTo >= Periods.Lower(b)) && (bTo is null || bTo >= Periods.Lower(a));
    }

    private static async Task<IResult> ListAlliancesAsync(WorldLineDbContext db, DateOnly? date, int? year, Guid? observer, string? names, CancellationToken ct)
    {
        if (!Periods.TryWindow(date, year, out var window, out var werr)) return Results.ValidationProblem(werr!);
        return Results.Ok(await LoadAlliancesAsync(db, null, window, observer, names, ct));
    }

    private static async Task<IResult> GetAllianceAsync(WorldLineDbContext db, Guid id, Guid? observer, string? names, CancellationToken ct)
    {
        var rows = await LoadAlliancesAsync(db, id, null, observer, names, ct);
        return rows.Count == 0 ? RegimeEndpoints.NotFound("陣營", id) : Results.Ok(rows[0]);
    }

    private static async Task<IResult> CreateAllianceAsync(WorldLineDbContext db, CreateAllianceRequest req, CancellationToken ct)
    {
        var errors = new Dictionary<string, string[]>();
        if (string.IsNullOrWhiteSpace(req.SelfName)) errors["selfName"] = ["陣營必須有自稱名稱（比照 I2）"];
        var period = PeriodInput.Parse(req.ExistenceFrom, req.ExistenceTo, requireTo: false, "existenceFrom", "existenceTo", errors);
        RegimeEndpoints.ValidateAliases(req.Aliases, errors);
        var observers = req.Aliases?.Where(a => a.ObserverRegimeId is not null).Select(a => a.ObserverRegimeId!.Value).Distinct().ToList() ?? [];
        var found = await db.Regimes.Where(r => observers.Contains(r.Id)).Select(r => r.Id).ToListAsync(ct);
        foreach (var missing in observers.Except(found)) errors[$"regime:{missing}"] = ["參照的政權不存在"];
        if (errors.Count > 0) return Results.ValidationProblem(errors, title: "陣營資料驗證失敗");

        var alliance = new Alliance
        {
            SelfName = req.SelfName!.Trim(),
            Description = req.Description,
            ExistencePeriod = period!.Range,
            ExistenceFromPrecision = period.From.Precision,
            ExistenceToPrecision = period.To?.Precision,
        };
        foreach (var x in req.Aliases ?? [])
            alliance.Aliases.Add(new AllianceAlias { AliasName = x.AliasName!.Trim(), AliasType = x.AliasType ?? AliasPerspective.Contemporary, ObserverRegimeId = x.ObserverRegimeId });
        db.Alliances.Add(alliance);
        await db.SaveChangesAsync(ct);
        return Results.CreatedAtRoute("GetAlliance", new { id = alliance.Id }, (await LoadAlliancesAsync(db, alliance.Id, null, null, null, ct))[0]);
    }

    private static async Task<IResult> AddMemberAsync(WorldLineDbContext db, Guid id, AddAllianceMemberRequest req, CancellationToken ct)
    {
        var alliance = await db.Alliances.FirstOrDefaultAsync(a => a.Id == id, ct);
        if (alliance is null) return RegimeEndpoints.NotFound("陣營", id);

        var errors = new Dictionary<string, string[]>();
        var role = req.Role ?? MembershipRole.Member;
        if (!MembershipRole.All.Contains(role)) errors["role"] = [$"role 必須是 {string.Join("/", MembershipRole.All)}"];
        if (req.RegimeId is null) errors["regimeId"] = ["regimeId 必填"];
        var period = PeriodInput.Parse(req.JoinedOn, req.LeftOn, requireTo: false, "joinedOn", "leftOn", errors);
        var regime = req.RegimeId is null ? null : await db.Regimes.FirstOrDefaultAsync(r => r.Id == req.RegimeId, ct);
        if (req.RegimeId is not null && regime is null) errors["regimeId"] = ["參照的政權不存在"];
        if (period is not null && !Periods.Within(period.Range, alliance.ExistencePeriod))
            errors["joinedOn"] = [$"成員期間 {Periods.Describe(period.Range)} 超出陣營存續期間 {Periods.Describe(alliance.ExistencePeriod)}"];
        if (period is not null && regime is not null && Periods.Lower(period.Range) < Periods.Lower(regime.ExistencePeriod))
            errors["joinedOn"] = [$"加入日早於「{regime.SelfName}」建立日"];
        if (errors.Count > 0) return Results.ValidationProblem(errors, title: "陣營成員驗證失敗");

        var m = new AllianceMembership
        {
            AllianceId = id,
            RegimeId = regime!.Id,
            Role = role,
            ValidPeriod = period!.Range,
            ValidFromPrecision = period.From.Precision,
            ValidToPrecision = period.To?.Precision,
            Note = req.Note,
        };
        db.AllianceMemberships.Add(m);
        await db.SaveChangesAsync(ct); // 同政權同陣營期間重疊 → exclusion constraint → 409
        return Results.Created($"/api/v1/alliances/{id}", (await LoadAlliancesAsync(db, id, null, null, null, ct))[0]);
    }
}
