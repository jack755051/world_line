using Microsoft.EntityFrameworkCore;
using WorldLine.Api.Common;
using WorldLine.Api.Domain;
using WorldLine.Api.Infrastructure;
using WorldLine.Contracts;

namespace WorldLine.Api.Features;

/// <summary>
/// 持續關係（PRD §6.3 regime_relations、§7.1 interactions、§7.2 POST /regime-relations）。
/// 扶植關係「兩者並存」（Tai 2026-10-28，§12 Q7）：控制紀錄版本上的 patron_regime_id 給地圖用，
/// 這裡的 patron_puppet 給聚焦面板與政權詳情用；兩者不互相推導、也不強制一致。
/// </summary>
public static class RegimeRelationsEndpoints
{
    public static void Map(RouteGroupBuilder read, RouteGroupBuilder write)
    {
        write.MapPost("/regime-relations", Create).WithTags("Regimes").WithName("CreateRegimeRelation")
            .RequiresApiKey().Created<RegimeRelationDto>().Errors(400, 401);
        read.MapGet("/regimes/{id:guid}/interactions", Interactions).WithTags("Regimes").WithName("GetRegimeInteractions")
            .Ok<RegimeInteractionsDto>().Errors(400, 404);
    }

    public static async Task<IResult> Create(CreateRegimeRelationRequest req, WorldLineDbContext db, CancellationToken ct)
    {
        var type = Mapping.RequireOneOf(req.RelationType, RelationTypes.All, "relationType");
        if (req.ValidPeriod?.Start is null)
            throw ApiError.BadRequest(ErrorCodes.PeriodRequired, "validPeriod.start 為必填（I1）；迄日未知可留空。", "validPeriod");
        var period = Mapping.Optional(req.ValidPeriod, "validPeriod")!.Value;
        if (req.RegimeAId is not { } a || req.RegimeBId is not { } b)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "regimeAId 與 regimeBId 為必填。", req.RegimeAId is null ? "regimeAId" : "regimeBId");
        if (a == b)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "關係雙方不可是同一政權。", "regimeBId");
        var found = await db.Regimes.CountAsync(x => (x.Id == a || x.Id == b) && x.RetractedAt == null, ct);
        if (found != 2)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "regimeAId 或 regimeBId 指向的政權不存在。", "regimeAId");

        var r = new RegimeRelation
        {
            Id = Guid.CreateVersion7(),
            RegimeAId = a,
            RegimeBId = b,
            RelationType = type,
            ValidPeriod = period,
            StartUncertainty = Mapping.Optional(req.StartUncertainty, "startUncertainty"),
            EndUncertainty = Mapping.Optional(req.EndUncertainty, "endUncertainty"),
            Note = Mapping.OptionalLocalized(req.Note, "note"),
        };
        db.RegimeRelations.Add(r);
        await db.SaveChangesAsync(ct);
        return ApiResults.Created($"/api/v1/regime-relations/{r.Id}", ToDto(r));
    }

    public static async Task<IResult> Interactions(Guid id, DateOnly? date, WorldLineDbContext db, CancellationToken ct)
    {
        if (date is not { } d)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "date 為必填（YYYY-MM-DD）。", "date");
        if (!await db.Regimes.AnyAsync(x => x.Id == id && x.RetractedAt == null, ct))
            throw ApiError.NotFound("政權");

        var rows = await db.RegimeRelations.AsNoTracking()
            .Where(r => r.RetractedAt == null && (r.RegimeAId == id || r.RegimeBId == id) && r.ValidPeriod.Contains(d))
            .OrderBy(r => r.RelationType).ThenBy(r => r.Id)
            .ToListAsync(ct);

        var items = rows.Select(r =>
        {
            var isA = r.RegimeAId == id;
            var role = r.RelationType == RelationTypes.PatronPuppet ? (isA ? "patron" : "puppet") : "party";
            return new RegimeInteractionDto(isA ? r.RegimeBId : r.RegimeAId, role, ToDto(r));
        }).ToList();
        return ApiResults.Ok(new RegimeInteractionsDto(id, d, items));
    }

    public static RegimeRelationDto ToDto(RegimeRelation r) => new(
        r.Id, r.RegimeAId, r.RegimeBId, r.RelationType, Mapping.ToDto(r.ValidPeriod)!,
        Mapping.ToDto(r.StartUncertainty), Mapping.ToDto(r.EndUncertainty), Mapping.ReadLocalizedOrNull(r.Note));
}
