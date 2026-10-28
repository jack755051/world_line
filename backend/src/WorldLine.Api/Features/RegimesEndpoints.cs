using System.Text.RegularExpressions;
using Microsoft.EntityFrameworkCore;
using WorldLine.Api.Common;
using WorldLine.Api.Domain;
using WorldLine.Api.Infrastructure;
using WorldLine.Contracts;

namespace WorldLine.Api.Features;

/// <summary>政權（I2 自稱必填、I4 代稱不孤兒、R4 雙語）。M0 只做建立與讀取；修正（PATCH＋revision_log）留待 M1。</summary>
public static partial class RegimesEndpoints
{
    [GeneratedRegex("^[a-z0-9]+(-[a-z0-9]+)*$")]
    private static partial Regex SlugPattern();

    public static void Map(RouteGroupBuilder read, RouteGroupBuilder write)
    {
        read.MapGet("/regimes/{id:guid}", Get).WithTags("Regimes").WithName("GetRegime").Ok<RegimeDto>().Errors(404);
        write.MapPost("/regimes", Create).WithTags("Regimes").WithName("CreateRegime").RequiresApiKey().Created<RegimeDto>().Errors(400, 401, 409);
    }

    public static async Task<IResult> Get(Guid id, WorldLineDbContext db, CancellationToken ct)
    {
        var r = await db.Regimes.AsNoTracking().Include(x => x.Names)
                    .FirstOrDefaultAsync(x => x.Id == id && x.RetractedAt == null, ct)
                ?? throw ApiError.NotFound("政權");
        return ApiResults.Ok(ToDto(r));
    }

    public static async Task<IResult> Create(CreateRegimeRequest req, WorldLineDbContext db, CancellationToken ct)
    {
        var slug = Mapping.RequireText(req.Slug, "slug", 80);
        if (!SlugPattern().IsMatch(slug))
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "slug 只能用小寫英數與連字號（例：french-state-vichy）。", "slug");

        var names = req.Names ?? [];
        // I2：建立政權時必須同時帶 ≥1 筆自稱（同一 transaction）
        if (!names.Any(n => n.NameKind == NameKinds.Self))
            throw ApiError.BadRequest(ErrorCodes.SelfNameRequired, "建立政權時必須同時帶至少一筆自稱（nameKind = self，I2）。", "names");

        var regime = new Regime
        {
            Id = Guid.CreateVersion7(),
            Slug = slug,
            WikidataQid = string.IsNullOrWhiteSpace(req.WikidataQid) ? null : Mapping.RequireText(req.WikidataQid, "wikidataQid", 20),
        };

        for (var i = 0; i < names.Count; i++)
        {
            var n = names[i];
            var f = $"names[{i}]";
            var kind = Mapping.RequireOneOf(n.NameKind, NameKinds.All, $"{f}.nameKind");
            if (kind == NameKinds.Exonym)
            {
                // I4＋PRD §6.3 AI 提案：代稱必須標出是哪個政權的視角
                if (n.ObserverRegimeId is not { } observer)
                    throw ApiError.BadRequest(ErrorCodes.OrphanExonym, "代稱必須帶 observerRegimeId（哪個政權的視角使用此稱呼）。", $"{f}.observerRegimeId");
                if (!await db.Regimes.AnyAsync(x => x.Id == observer, ct))
                    throw ApiError.BadRequest(ErrorCodes.OrphanExonym, "observerRegimeId 指向的政權不存在。", $"{f}.observerRegimeId");
            }
            regime.Names.Add(new RegimeName
            {
                Id = Guid.CreateVersion7(),
                NameKind = kind,
                OriginalText = Mapping.RequireText(n.OriginalText, $"{f}.originalText"),
                OriginalLang = Mapping.RequireText(n.OriginalLang, $"{f}.originalLang", 16),
                Display = Mapping.RequireLocalized(n.Display, $"{f}.display"),
                ObserverRegimeId = kind == NameKinds.Exonym ? n.ObserverRegimeId : null,
                ValidPeriod = Mapping.Optional(n.ValidPeriod, $"{f}.validPeriod"),
                IsPrimary = n.IsPrimary,
            });
        }

        if (await db.Regimes.AnyAsync(x => x.Slug == slug, ct))
            throw new ApiError(StatusCodes.Status409Conflict, ErrorCodes.Conflict, $"slug「{slug}」已存在。");

        db.Regimes.Add(regime);
        await db.SaveChangesAsync(ct);
        return ApiResults.Created($"/api/v1/regimes/{regime.Id}", ToDto(regime));
    }

    public static RegimeDto ToDto(Regime r) => new(
        r.Id, r.Slug, r.WikidataQid,
        r.Names.Where(n => n.RetractedAt == null)
            .OrderBy(n => n.NameKind == NameKinds.Self ? 0 : 1).ThenByDescending(n => n.IsPrimary)
            .Select(n => new RegimeNameDto(n.Id, n.NameKind, n.OriginalText, n.OriginalLang, Mapping.ReadLocalized(n.Display),
                n.ObserverRegimeId, Mapping.ToDto(n.ValidPeriod), n.IsPrimary))
            .ToList());
}
