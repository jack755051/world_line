using Microsoft.EntityFrameworkCore;
using NpgsqlTypes;
using WorldLine.Api.Data;
using WorldLine.Api.Domain;

namespace WorldLine.Api.Api;

public static class RegimeEndpoints
{
    private static readonly string[] OriginTypes = [OriginTransitionType.Split, OriginTransitionType.Abdication];
    internal static readonly string[] AliasTypes = [AliasPerspective.Contemporary, AliasPerspective.Historiographic];

    public static void Map(RouteGroupBuilder api)
    {
        var g = api.MapGroup("/regimes").WithTags("Regimes");

        g.MapGet("/", ListAsync)
            .WithSummary("依日期查詢政權清單")
            .WithDescription("date=YYYY-MM-DD：當天存續的政權，並附當天的實控疆域有無（流亡政府為 false）、被誰控制（佔領／傀儡…）、所屬陣營；year=YYYY 為捷徑（該年任一天存續即納入）。observer：以某政權為觀察視角顯示代稱（例：中華民國視角下「滿洲國」顯示「偽滿洲國」）；names=historiographic 改用後世史學稱呼。");
        g.MapGet("/{id:guid}", GetAsync).WithName("GetRegime")
            .WithSummary("取得單一政權詳情（含代稱、前身、繼承者、關係、控制關係、陣營、年號、史觀主線；date/year 可過濾關係）");
        g.MapPost("/", CreateAsync).AddEndpointFilter<ApiKeyFilter>().WithSummary("新增政權（需 X-Api-Key）");
        g.MapPatch("/{id:guid}", UpdateAsync).AddEndpointFilter<ApiKeyFilter>()
            .WithSummary("更新政權（需 X-Api-Key；version、changeReason 必填；狀態轉換依憲法 §4 驗證）");
    }

    internal static RegimeSummary ToSummary(Regime r, string? displayName = null) => new(
        r.Id, r.SelfName, displayName ?? r.SelfName, r.Status,
        Periods.FromText(r.ExistencePeriod, r.ExistenceFromPrecision), r.ExistenceFromPrecision,
        Periods.ToText(r.ExistencePeriod, r.ExistenceToPrecision), r.ExistenceToPrecision,
        r.PredecessorRegimeId, r.OriginTransitionType, r.DestroyedByRegimeId, r.AnnexedByRegimeId, r.Version);

    /// <summary>依觀察視角決定顯示名稱（憲法 §6 政權命名機制）；名稱一律可經 id 追溯回自稱本體（I4）。</summary>
    internal static async Task<Dictionary<Guid, string>> DisplayNamesAsync(
        WorldLineDbContext db, IReadOnlyCollection<Guid> regimeIds, Guid? observer, string? names, CancellationToken ct)
    {
        if (observer is null && names != AliasPerspective.Historiographic) return [];
        var q = db.RegimeAliases.AsNoTracking().Where(a => regimeIds.Contains(a.RegimeId));
        q = observer is not null
            ? q.Where(a => a.ObserverRegimeId == observer)
            : q.Where(a => a.AliasType == AliasPerspective.Historiographic);
        // 同一視角有多個代稱時取最短者（例：「大食」優先於「黑衣大食」），結果穩定可預期
        var aliases = await q.OrderBy(a => a.AliasName.Length).ThenBy(a => a.AliasName).ToListAsync(ct);
        return aliases.GroupBy(a => a.RegimeId).ToDictionary(x => x.Key, x => x.First().AliasName);
    }

    /// <summary>某時間窗內，各政權「被誰控制」（控制方顯示名依觀察視角）。</summary>
    internal static async Task<Dictionary<Guid, List<ControlRefDto>>> ControlledByAsync(
        WorldLineDbContext db, IReadOnlyCollection<Guid> regimeIds, NpgsqlRange<DateOnly> window, Guid? observer, string? names, CancellationToken ct)
    {
        var rows = await db.RegimeControlRelations.AsNoTracking().Include(c => c.ControllerRegime)
            .Where(c => regimeIds.Contains(c.ControlledRegimeId) && c.ValidPeriod.Overlaps(window))
            .ToListAsync(ct);
        var display = await DisplayNamesAsync(db, rows.Select(r => r.ControllerRegimeId).Distinct().ToList(), observer, names, ct);
        return rows.GroupBy(r => r.ControlledRegimeId).ToDictionary(g => g.Key, g => g
            .OrderBy(r => r.ControlType)
            .Select(r => new ControlRefDto(r.Id, new RegimeRef(r.ControllerRegime.Id, r.ControllerRegime.SelfName),
                display.GetValueOrDefault(r.ControllerRegimeId) ?? r.ControllerRegime.SelfName, r.ControlType, r.IsDisputed))
            .ToList());
    }

    private static async Task<IResult> ListAsync(
        WorldLineDbContext db, DateOnly? date, int? year, Guid? observer, string? names, CancellationToken ct)
    {
        if (!Periods.TryWindow(date, year, out var window, out var werr)) return Results.ValidationProblem(werr!);
        var q = db.Regimes.AsNoTracking();
        if (window is not null) q = q.Where(r => r.ExistencePeriod.Overlaps(window.Value));
        var regimes = await q.ToListAsync(ct);
        var ids = regimes.Select(r => r.Id).ToList();
        var display = await DisplayNamesAsync(db, ids, observer, names, ct);

        HashSet<Guid> withTerritory = [];
        Dictionary<Guid, List<ControlRefDto>> controlled = [];
        Dictionary<Guid, List<AllianceRefDto>> alliances = [];
        if (window is not null)
        {
            var w = window.Value;
            withTerritory = (await db.RegimeTerritories.AsNoTracking()
                .Where(t => t.SupersededBy == null && ids.Contains(t.RegimeId) && t.ValidPeriod.Overlaps(w))
                .Select(t => t.RegimeId).Distinct().ToListAsync(ct)).ToHashSet();
            controlled = await ControlledByAsync(db, ids, w, observer, names, ct);
            alliances = (await db.AllianceMemberships.AsNoTracking().Include(m => m.Alliance)
                    .Where(m => ids.Contains(m.RegimeId) && m.ValidPeriod.Overlaps(w)).ToListAsync(ct))
                .GroupBy(m => m.RegimeId)
                .ToDictionary(g => g.Key, g => g.Select(m => new AllianceRefDto(m.AllianceId, m.Alliance.SelfName, m.Role)).ToList());
        }

        var result = regimes
            .OrderBy(r => Periods.Lower(r.ExistencePeriod)).ThenBy(r => r.SelfName)
            .Select(r =>
            {
                var s = ToSummary(r, display.GetValueOrDefault(r.Id));
                return window is null ? s : s with
                {
                    HasTerritory = withTerritory.Contains(r.Id),
                    ControlledBy = controlled.GetValueOrDefault(r.Id) ?? [],
                    Alliances = alliances.GetValueOrDefault(r.Id) ?? [],
                };
            })
            .ToList();
        return Results.Ok(result);
    }

    private static async Task<IResult> GetAsync(WorldLineDbContext db, Guid id, DateOnly? date, int? year, CancellationToken ct)
    {
        if (!Periods.TryWindow(date, year, out var window, out var werr)) return Results.ValidationProblem(werr!);
        var detail = await LoadDetailAsync(db, id, window, ct);
        return detail is null ? NotFound("政權", id) : Results.Ok(detail);
    }

    internal static ControlRelationDto ToControlDto(RegimeControlRelation c, string? controllerName = null, string? controlledName = null) => new(
        c.Id,
        new RegimeRef(c.ControllerRegime.Id, c.ControllerRegime.SelfName), controllerName ?? c.ControllerRegime.SelfName,
        new RegimeRef(c.ControlledRegime.Id, c.ControlledRegime.SelfName), controlledName ?? c.ControlledRegime.SelfName,
        c.ControlType,
        Periods.FromText(c.ValidPeriod, c.ValidFromPrecision), c.ValidFromPrecision,
        Periods.ToText(c.ValidPeriod, c.ValidToPrecision)!, c.ValidToPrecision,
        c.IsDisputed, c.Area is not null, c.IsIllustrative, c.Description, c.Source, c.Version);

    internal static async Task<RegimeDetail?> LoadDetailAsync(WorldLineDbContext db, Guid id, NpgsqlRange<DateOnly>? window, CancellationToken ct)
    {
        var r = await db.Regimes.AsNoTracking()
            .Include(x => x.PredecessorRegime)
            .Include(x => x.DestroyedByRegime)
            .Include(x => x.AnnexedByRegime)
            .Include(x => x.Aliases).ThenInclude(a => a.ObserverRegime)
            .Include(x => x.ReignEras)
            .AsSplitQuery()
            .FirstOrDefaultAsync(x => x.Id == id, ct);
        if (r is null) return null;

        var successors = await db.Regimes.AsNoTracking().Where(x => x.PredecessorRegimeId == id)
            .Select(x => new SuccessorDto(x.Id, x.SelfName, x.OriginTransitionType!)).ToListAsync(ct);
        var destroyed = await db.Regimes.AsNoTracking().Where(x => x.DestroyedByRegimeId == id)
            .Select(x => new RegimeRef(x.Id, x.SelfName)).ToListAsync(ct);
        var annexed = await db.Regimes.AsNoTracking().Where(x => x.AnnexedByRegimeId == id)
            .Select(x => new RegimeRef(x.Id, x.SelfName)).ToListAsync(ct);

        var relQ = db.RegimeRelations.AsNoTracking().Include(x => x.RegimeA).Include(x => x.RegimeB)
            .Where(x => x.RegimeAId == id || x.RegimeBId == id);
        if (window is not null) relQ = relQ.Where(x => x.ValidPeriod.Overlaps(window.Value));
        var relations = (await relQ.ToListAsync(ct)).Select(x =>
        {
            var outgoing = x.RegimeAId == id;
            var other = outgoing ? x.RegimeB : x.RegimeA;
            return new RelationDto(x.Id, x.RelationType, outgoing ? "outgoing" : "incoming",
                new RegimeRef(other.Id, other.SelfName),
                Periods.FromText(x.ValidPeriod, x.ValidFromPrecision), x.ValidFromPrecision,
                Periods.ToText(x.ValidPeriod, x.ValidToPrecision)!, x.ValidToPrecision, x.Description);
        }).OrderBy(x => x.ValidFrom, StringComparer.Ordinal).ToList();

        var ctrlQ = db.RegimeControlRelations.AsNoTracking().Include(c => c.ControllerRegime).Include(c => c.ControlledRegime)
            .Where(c => c.ControllerRegimeId == id || c.ControlledRegimeId == id);
        if (window is not null) ctrlQ = ctrlQ.Where(c => c.ValidPeriod.Overlaps(window.Value));
        var controls = (await ctrlQ.ToListAsync(ct))
            .OrderBy(c => Periods.Lower(c.ValidPeriod)).Select(c => ToControlDto(c)).ToList();

        var memQ = db.AllianceMemberships.AsNoTracking().Include(m => m.Alliance).Where(m => m.RegimeId == id);
        if (window is not null) memQ = memQ.Where(m => m.ValidPeriod.Overlaps(window.Value));
        var memberships = (await memQ.ToListAsync(ct)).OrderBy(m => Periods.Lower(m.ValidPeriod))
            .Select(m => new RegimeAllianceDto(m.AllianceId, m.Alliance.SelfName, m.Role,
                Periods.FromText(m.ValidPeriod, m.ValidFromPrecision), m.ValidFromPrecision,
                Periods.ToText(m.ValidPeriod, m.ValidToPrecision), m.ValidToPrecision)).ToList();

        var presets = await db.LineagePresetMembers.AsNoTracking().Where(m => m.RegimeId == id)
            .Select(m => new PresetMembershipDto(m.PresetId, m.Preset.PresetName, m.SortOrder)).ToListAsync(ct);

        return new RegimeDetail(
            ToSummary(r),
            r.Aliases.OrderBy(a => a.AliasType).ThenBy(a => a.AliasName).Select(a => new AliasDto(a.Id, a.AliasName, a.AliasType,
                a.ObserverRegime is null ? null : new RegimeRef(a.ObserverRegime.Id, a.ObserverRegime.SelfName))).ToList(),
            r.PredecessorRegime is null ? null : new RegimeRef(r.PredecessorRegime.Id, r.PredecessorRegime.SelfName),
            successors,
            r.DestroyedByRegime is null ? null : new RegimeRef(r.DestroyedByRegime.Id, r.DestroyedByRegime.SelfName),
            destroyed,
            r.AnnexedByRegime is null ? null : new RegimeRef(r.AnnexedByRegime.Id, r.AnnexedByRegime.SelfName),
            annexed,
            relations,
            controls,
            memberships,
            r.ReignEras.OrderBy(e => e.StartDate).Select(e => ToEraDto(e, r)).ToList(),
            presets);
    }

    internal static ReignEraDto ToEraDto(ReignEra e, Regime r) => new(e.Id, r.Id, r.SelfName, e.EraName, e.MonarchName,
        PartialDate.Format(e.StartDate, e.StartPrecision), e.StartPrecision,
        e.EndDate is { } end ? PartialDate.Format(end, e.EndPrecision ?? DatePrecision.Day) : null, e.EndPrecision);

    /// <summary>終止方式對應的「對方」欄位規則（憲法 §4：被滅亡記消滅方、被併吞記併吞方，兩者互斥）。</summary>
    private static void ValidateTerminalParty(string status, Guid? destroyedBy, Guid? annexedBy, Guid? selfId, Dictionary<string, string[]> errors)
    {
        if ((status == RegimeStatus.Destroyed) != (destroyedBy is not null))
            errors["destroyedByRegimeId"] = ["只有 status = destroyed 時必須且只能提供消滅方政權（憲法 §4）"];
        if ((status == RegimeStatus.Annexed) != (annexedBy is not null))
            errors["annexedByRegimeId"] = ["只有 status = annexed 時必須且只能提供併吞方政權（憲法 §4）"];
        if (selfId is not null && (destroyedBy == selfId || annexedBy == selfId))
            errors["status"] = ["政權不可被自己消滅或併吞"];
    }

    private static async Task<IResult> CreateAsync(WorldLineDbContext db, CreateRegimeRequest req, CancellationToken ct)
    {
        var errors = new Dictionary<string, string[]>();
        var status = req.Status ?? RegimeStatus.Existing;

        if (string.IsNullOrWhiteSpace(req.SelfName)) errors["selfName"] = ["I2：政權必須有自稱名稱"];
        var period = PeriodInput.Parse(req.ExistenceFrom, req.ExistenceTo, requireTo: false, "existenceFrom", "existenceTo", errors);
        if (!RegimeStatus.All.Contains(status)) errors["status"] = [$"status 必須是 {string.Join("/", RegimeStatus.All)}"];
        if (status != RegimeStatus.Existing && string.IsNullOrWhiteSpace(req.ExistenceTo))
            errors["existenceTo"] = ["已終止的政權必須有存續結束日期"];
        if ((req.PredecessorRegimeId is null) != (req.OriginTransitionType is null))
            errors["originTransitionType"] = ["predecessorRegimeId 與 originTransitionType 必須同時提供（分裂／禪讓而來）或同時省略（獨立建國）"];
        if (req.OriginTransitionType is not null && !OriginTypes.Contains(req.OriginTransitionType))
            errors["originTransitionType"] = ["originTransitionType 必須是 split 或 abdication"];
        ValidateTerminalParty(status, req.DestroyedByRegimeId, req.AnnexedByRegimeId, null, errors);
        ValidateAliases(req.Aliases, errors);

        var refs = new[] { req.PredecessorRegimeId, req.DestroyedByRegimeId, req.AnnexedByRegimeId }
            .Concat(req.Aliases?.Select(a => a.ObserverRegimeId) ?? [])
            .Where(x => x is not null).Select(x => x!.Value).Distinct().ToList();
        var found = await db.Regimes.Where(r => refs.Contains(r.Id)).Select(r => r.Id).ToListAsync(ct);
        foreach (var missing in refs.Except(found)) errors[$"regime:{missing}"] = ["參照的政權不存在"];

        if (errors.Count > 0) return Results.ValidationProblem(errors, title: "政權資料驗證失敗");

        var regime = new Regime
        {
            SelfName = req.SelfName!.Trim(),
            ExistencePeriod = period!.Range,
            ExistenceFromPrecision = period.From.Precision,
            ExistenceToPrecision = period.To?.Precision,
            Status = status,
            PredecessorRegimeId = req.PredecessorRegimeId,
            OriginTransitionType = req.OriginTransitionType,
            DestroyedByRegimeId = req.DestroyedByRegimeId,
            AnnexedByRegimeId = req.AnnexedByRegimeId,
        };
        foreach (var a in req.Aliases ?? [])
        {
            regime.Aliases.Add(new RegimeAlias
            {
                AliasName = a.AliasName!.Trim(),
                AliasType = a.AliasType ?? AliasPerspective.Contemporary,
                ObserverRegimeId = a.ObserverRegimeId,
            });
        }
        db.Regimes.Add(regime);
        await db.SaveChangesAsync(ct);

        var detail = await LoadDetailAsync(db, regime.Id, null, ct);
        return Results.CreatedAtRoute("GetRegime", new { id = regime.Id }, detail);
    }

    private static async Task<IResult> UpdateAsync(WorldLineDbContext db, Guid id, UpdateRegimeRequest req, CancellationToken ct)
    {
        var regime = await db.Regimes.FirstOrDefaultAsync(r => r.Id == id, ct);
        if (regime is null) return NotFound("政權", id);

        var errors = new Dictionary<string, string[]>();
        if (req.Version is null) errors["version"] = ["version 必填（樂觀併發）"];
        if (string.IsNullOrWhiteSpace(req.ChangeReason)) errors["changeReason"] = ["I5：修改必須提供原因"];
        if (req.SelfName is not null && string.IsNullOrWhiteSpace(req.SelfName)) errors["selfName"] = ["I2：自稱名稱不可為空"];

        var newStatus = req.Status ?? regime.Status;
        if (req.Status is not null && req.Status != regime.Status && !RegimeStatus.IsLegalTransition(regime.Status, req.Status))
            errors["status"] = [$"憲法 §4：不合法的狀態轉換 {regime.Status} → {req.Status}（只允許 existing → split / abdicated / destroyed / annexed）"];

        var newDestroyedBy = newStatus == RegimeStatus.Destroyed ? req.DestroyedByRegimeId ?? regime.DestroyedByRegimeId : req.DestroyedByRegimeId;
        var newAnnexedBy = newStatus == RegimeStatus.Annexed ? req.AnnexedByRegimeId ?? regime.AnnexedByRegimeId : req.AnnexedByRegimeId;
        ValidateTerminalParty(newStatus, newDestroyedBy, newAnnexedBy, id, errors);
        foreach (var other in new[] { newDestroyedBy, newAnnexedBy }.Where(x => x is not null && x != id))
        {
            if (!await db.Regimes.AnyAsync(r => r.Id == other, ct)) errors[$"regime:{other}"] = ["參照的政權不存在"];
        }

        // 起訖：有給就用新值（字串即精度），沒給沿用原值與原精度
        PartialDate? newFrom = null, newTo = null;
        if (req.ExistenceFrom is not null && !PartialDate.TryParse(req.ExistenceFrom, out newFrom, out var e1)) errors["existenceFrom"] = [e1!];
        if (req.ExistenceTo is not null && !PartialDate.TryParse(req.ExistenceTo, out newTo, out var e2)) errors["existenceTo"] = [e2!];
        var fromDate = newFrom?.Earliest ?? Periods.Lower(regime.ExistencePeriod);
        var fromPrecision = newFrom?.Precision ?? regime.ExistenceFromPrecision;
        var toDate = newTo?.Latest ?? Periods.UpperInclusive(regime.ExistencePeriod);
        var toPrecision = newTo?.Precision ?? regime.ExistenceToPrecision;
        if (toDate is not null && toDate < fromDate) errors["existenceTo"] = ["結束日期不可早於起始日期"];
        if (newStatus != RegimeStatus.Existing && toDate is null) errors["existenceTo"] = ["已終止的政權必須有存續結束日期"];

        if (errors.Count > 0) return Results.ValidationProblem(errors, title: "政權更新驗證失敗");
        if (req.Version != regime.Version)
            return Results.Problem(title: "版本衝突", detail: $"目前版本為 {regime.Version}，請重新讀取後再送出。", statusCode: 409);

        db.Entry(regime).Property(r => r.Version).OriginalValue = req.Version!.Value;
        if (req.SelfName is not null) regime.SelfName = req.SelfName.Trim();
        regime.Status = newStatus;
        regime.DestroyedByRegimeId = newDestroyedBy;
        regime.AnnexedByRegimeId = newAnnexedBy;
        regime.ExistencePeriod = Periods.Of(fromDate, toDate);
        regime.ExistenceFromPrecision = fromPrecision;
        regime.ExistenceToPrecision = toDate is null ? null : toPrecision;

        db.ChangeReason = req.ChangeReason!.Trim();
        await db.SaveChangesAsync(ct);
        return Results.Ok(await LoadDetailAsync(db, id, null, ct));
    }

    internal static void ValidateAliases(List<AliasInput>? aliases, Dictionary<string, string[]> errors)
    {
        for (var i = 0; i < (aliases?.Count ?? 0); i++)
        {
            var a = aliases![i];
            if (string.IsNullOrWhiteSpace(a.AliasName)) errors[$"aliases[{i}].aliasName"] = ["代稱不可為空"];
            if (a.AliasType is not null && !AliasTypes.Contains(a.AliasType))
                errors[$"aliases[{i}].aliasType"] = ["aliasType 必須是 contemporary 或 historiographic"];
        }
    }

    internal static IResult NotFound(string what, object id) =>
        Results.Problem(title: $"找不到{what}", detail: $"{what} {id} 不存在", statusCode: 404);
}
