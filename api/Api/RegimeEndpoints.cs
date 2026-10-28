using Microsoft.EntityFrameworkCore;
using WorldLine.Api.Data;
using WorldLine.Api.Domain;

namespace WorldLine.Api.Api;

public static class RegimeEndpoints
{
    private static readonly string[] OriginTypes = [OriginTransitionType.Split, OriginTransitionType.Abdication];
    private static readonly string[] AliasTypes = [AliasPerspective.Contemporary, AliasPerspective.Historiographic];

    public static void Map(RouteGroupBuilder api)
    {
        var g = api.MapGroup("/regimes").WithTags("Regimes");

        g.MapGet("/", ListAsync)
            .WithSummary("依年份查詢政權清單")
            .WithDescription("year：該年存續的政權（天文紀年，負數為西元前）。observer：以某政權為觀察視角顯示代稱（例：唐視角下阿拉伯帝國顯示「大食」）；names=historiographic 改用後世史學稱呼。");
        g.MapGet("/{id:guid}", GetAsync).WithName("GetRegime").WithSummary("取得單一政權詳情（含代稱、前身、繼承者、關係、年號、史觀主線）");
        g.MapPost("/", CreateAsync).AddEndpointFilter<ApiKeyFilter>().WithSummary("新增政權（需 X-Api-Key）");
        g.MapPatch("/{id:guid}", UpdateAsync).AddEndpointFilter<ApiKeyFilter>()
            .WithSummary("更新政權（需 X-Api-Key；version、changeReason 必填；狀態轉換依憲法 §4 驗證）");
    }

    internal static RegimeSummary ToSummary(Regime r, string? displayName = null) => new(
        r.Id, r.SelfName, displayName ?? r.SelfName, r.Status,
        Ranges.Lower(r.ExistencePeriod), Ranges.UpperInclusive(r.ExistencePeriod),
        r.PredecessorRegimeId, r.OriginTransitionType, r.DestroyedByRegimeId, r.Version);

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

    private static async Task<IResult> ListAsync(
        WorldLineDbContext db, int? year, Guid? observer, string? names, CancellationToken ct)
    {
        var q = db.Regimes.AsNoTracking();
        if (year is not null) q = q.Where(r => r.ExistencePeriod.Contains(year.Value));
        var regimes = await q.ToListAsync(ct);
        var display = await DisplayNamesAsync(db, regimes.Select(r => r.Id).ToList(), observer, names, ct);
        var result = regimes
            .OrderBy(r => Ranges.Lower(r.ExistencePeriod)).ThenBy(r => r.SelfName)
            .Select(r => ToSummary(r, display.GetValueOrDefault(r.Id)))
            .ToList();
        return Results.Ok(result);
    }

    private static async Task<IResult> GetAsync(WorldLineDbContext db, Guid id, int? year, CancellationToken ct)
    {
        var detail = await LoadDetailAsync(db, id, year, ct);
        return detail is null ? NotFound("政權", id) : Results.Ok(detail);
    }

    internal static async Task<RegimeDetail?> LoadDetailAsync(WorldLineDbContext db, Guid id, int? year, CancellationToken ct)
    {
        var r = await db.Regimes.AsNoTracking()
            .Include(x => x.PredecessorRegime)
            .Include(x => x.DestroyedByRegime)
            .Include(x => x.Aliases).ThenInclude(a => a.ObserverRegime)
            .Include(x => x.ReignEras)
            .AsSplitQuery()
            .FirstOrDefaultAsync(x => x.Id == id, ct);
        if (r is null) return null;

        var successors = await db.Regimes.AsNoTracking().Where(x => x.PredecessorRegimeId == id)
            .Select(x => new SuccessorDto(x.Id, x.SelfName, x.OriginTransitionType!)).ToListAsync(ct);
        var destroyed = await db.Regimes.AsNoTracking().Where(x => x.DestroyedByRegimeId == id)
            .Select(x => new RegimeRef(x.Id, x.SelfName)).ToListAsync(ct);

        var relQ = db.RegimeRelations.AsNoTracking().Include(x => x.RegimeA).Include(x => x.RegimeB)
            .Where(x => x.RegimeAId == id || x.RegimeBId == id);
        if (year is not null) relQ = relQ.Where(x => x.ValidPeriod.Contains(year.Value));
        var relations = (await relQ.ToListAsync(ct)).Select(x =>
        {
            var outgoing = x.RegimeAId == id;
            var other = outgoing ? x.RegimeB : x.RegimeA;
            return new RelationDto(x.Id, x.RelationType, outgoing ? "outgoing" : "incoming",
                new RegimeRef(other.Id, other.SelfName),
                Ranges.Lower(x.ValidPeriod), Ranges.UpperInclusive(x.ValidPeriod)!.Value, x.Description);
        }).OrderBy(x => x.ValidFrom).ToList();

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
            relations,
            r.ReignEras.OrderBy(e => e.StartYear).Select(e => new ReignEraDto(e.Id, r.Id, r.SelfName, e.EraName, e.MonarchName, e.StartYear, e.EndYear)).ToList(),
            presets);
    }

    private static async Task<IResult> CreateAsync(WorldLineDbContext db, CreateRegimeRequest req, CancellationToken ct)
    {
        var errors = new Dictionary<string, string[]>();
        var status = req.Status ?? RegimeStatus.Existing;

        if (string.IsNullOrWhiteSpace(req.SelfName)) errors["selfName"] = ["I2：政權必須有自稱名稱"];
        if (req.ExistenceFrom is null) errors["existenceFrom"] = ["存續起始年必填"];
        if (req.ExistenceTo is not null && req.ExistenceFrom is not null && req.ExistenceTo < req.ExistenceFrom)
            errors["existenceTo"] = ["結束年不可早於起始年"];
        if (!RegimeStatus.All.Contains(status)) errors["status"] = [$"status 必須是 {string.Join("/", RegimeStatus.All)}"];
        if (status != RegimeStatus.Existing && req.ExistenceTo is null)
            errors["existenceTo"] = ["已終止的政權必須有存續結束年"];
        if ((req.PredecessorRegimeId is null) != (req.OriginTransitionType is null))
            errors["originTransitionType"] = ["predecessorRegimeId 與 originTransitionType 必須同時提供（分裂／禪讓而來）或同時省略（獨立建國）"];
        if (req.OriginTransitionType is not null && !OriginTypes.Contains(req.OriginTransitionType))
            errors["originTransitionType"] = ["originTransitionType 必須是 split 或 abdication"];
        if ((status == RegimeStatus.Destroyed) != (req.DestroyedByRegimeId is not null))
            errors["destroyedByRegimeId"] = ["只有 status = destroyed 時必須且只能提供消滅方政權（憲法 §4）"];
        ValidateAliases(req.Aliases, errors);

        var refs = new[] { req.PredecessorRegimeId, req.DestroyedByRegimeId }
            .Concat(req.Aliases?.Select(a => a.ObserverRegimeId) ?? [])
            .Where(x => x is not null).Select(x => x!.Value).Distinct().ToList();
        var found = await db.Regimes.Where(r => refs.Contains(r.Id)).Select(r => r.Id).ToListAsync(ct);
        foreach (var missing in refs.Except(found)) errors[$"regime:{missing}"] = ["參照的政權不存在"];

        if (errors.Count > 0) return Results.ValidationProblem(errors, title: "政權資料驗證失敗");

        var regime = new Regime
        {
            SelfName = req.SelfName!.Trim(),
            ExistencePeriod = Ranges.From(req.ExistenceFrom!.Value, req.ExistenceTo),
            Status = status,
            PredecessorRegimeId = req.PredecessorRegimeId,
            OriginTransitionType = req.OriginTransitionType,
            DestroyedByRegimeId = req.DestroyedByRegimeId,
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
            errors["status"] = [$"憲法 §4：不合法的狀態轉換 {regime.Status} → {req.Status}（只允許 existing → split / abdicated / destroyed）"];

        var newDestroyedBy = newStatus == RegimeStatus.Destroyed ? req.DestroyedByRegimeId ?? regime.DestroyedByRegimeId : null;
        if (newStatus == RegimeStatus.Destroyed && newDestroyedBy is null)
            errors["destroyedByRegimeId"] = ["被滅亡必須記錄消滅方政權（憲法 §4）"];
        if (newStatus != RegimeStatus.Destroyed && req.DestroyedByRegimeId is not null)
            errors["destroyedByRegimeId"] = ["只有 status = destroyed 時可指定消滅方"];
        if (newDestroyedBy == id) errors["destroyedByRegimeId"] = ["政權不可被自己消滅"];
        if (newDestroyedBy is not null && !await db.Regimes.AnyAsync(r => r.Id == newDestroyedBy, ct))
            errors["destroyedByRegimeId"] = ["消滅方政權不存在"];

        var from = req.ExistenceFrom ?? Ranges.Lower(regime.ExistencePeriod);
        var to = req.ExistenceTo ?? Ranges.UpperInclusive(regime.ExistencePeriod);
        if (to is not null && to < from) errors["existenceTo"] = ["結束年不可早於起始年"];
        if (newStatus != RegimeStatus.Existing && to is null) errors["existenceTo"] = ["已終止的政權必須有存續結束年"];

        if (errors.Count > 0) return Results.ValidationProblem(errors, title: "政權更新驗證失敗");
        if (req.Version != regime.Version)
            return Results.Problem(title: "版本衝突", detail: $"目前版本為 {regime.Version}，請重新讀取後再送出。", statusCode: 409);

        db.Entry(regime).Property(r => r.Version).OriginalValue = req.Version!.Value;
        if (req.SelfName is not null) regime.SelfName = req.SelfName.Trim();
        regime.Status = newStatus;
        regime.DestroyedByRegimeId = newDestroyedBy;
        regime.ExistencePeriod = Ranges.From(from, to);

        db.ChangeReason = req.ChangeReason!.Trim();
        await db.SaveChangesAsync(ct);
        return Results.Ok(await LoadDetailAsync(db, id, null, ct));
    }

    private static void ValidateAliases(List<AliasInput>? aliases, Dictionary<string, string[]> errors)
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
