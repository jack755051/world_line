using Microsoft.EntityFrameworkCore;
using WorldLine.Api.Common;
using WorldLine.Api.Domain;
using WorldLine.Api.Infrastructure;
using WorldLine.Contracts;

namespace WorldLine.Api.Features;

/// <summary>戰區與史料快照（§9：快照日期由來源決定；Q4：來源明文確立整段期間時允許 interval）。</summary>
public static class TheatersEndpoints
{
    public static void Map(RouteGroupBuilder write)
    {
        write.MapPost("/theaters", CreateTheater).WithTags("Theaters").WithName("CreateTheater").RequiresApiKey().Created<TheaterDto>().Errors(400, 401, 409);
        write.MapPost("/control-snapshots", CreateSnapshot).WithTags("Theaters").WithName("CreateControlSnapshot").RequiresApiKey().Created<ControlSnapshotDto>().Errors(400, 401, 409);
    }

    public static async Task<IResult> CreateTheater(CreateTheaterRequest req, WorldLineDbContext db, CancellationToken ct)
    {
        var code = Mapping.RequireText(req.Code, "code", 40);
        var t = new Theater
        {
            Id = Guid.CreateVersion7(),
            Code = code,
            Name = Mapping.RequireLocalized(req.Name, "name"),
            Extent = req.Extent is null ? null : Mapping.RequireMultiPolygon(req.Extent, "extent"),
        };
        if (await db.Theaters.AnyAsync(x => x.Code == code, ct))
            throw new ApiError(StatusCodes.Status409Conflict, ErrorCodes.Conflict, $"戰區代碼「{code}」已存在。");
        db.Theaters.Add(t);
        await db.SaveChangesAsync(ct);
        return ApiResults.Created($"/api/v1/theaters/{t.Id}", new TheaterDto(t.Id, t.Code, Mapping.ReadLocalized(t.Name)));
    }

    public static async Task<IResult> CreateSnapshot(CreateControlSnapshotRequest req, WorldLineDbContext db, CancellationToken ct)
    {
        if (req.TheaterId is not { } theaterId)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "theaterId 為必填。", "theaterId");
        if (req.AsOf is not { } asOf)
            throw ApiError.BadRequest(ErrorCodes.PeriodRequired, "asOf（來源地圖呈現的日期）為必填。", "asOf");
        var attestation = Mapping.RequireOneOf(req.Attestation ?? Attestations.Point, Attestations.All, "attestation");

        var attested = attestation == Attestations.Interval
            ? Mapping.RequireBounded(req.AttestedPeriod, "attestedPeriod")
            : (NpgsqlTypes.NpgsqlRange<DateOnly>?)null;
        if (attestation == Attestations.Point && req.AttestedPeriod is not null)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "attestation = point 時不可帶 attestedPeriod。", "attestedPeriod");

        if (!await db.Theaters.AnyAsync(x => x.Id == theaterId, ct))
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "theaterId 指向的戰區不存在。", "theaterId");
        if (await db.ControlSnapshots.AnyAsync(x => x.TheaterId == theaterId && x.AsOf == asOf, ct))
            throw new ApiError(StatusCodes.Status409Conflict, ErrorCodes.Conflict, $"該戰區在 {asOf:yyyy-MM-dd} 已有快照。");

        var s = new ControlSnapshot
        {
            Id = Guid.CreateVersion7(),
            TheaterId = theaterId,
            AsOf = asOf,
            Attestation = attestation,
            AttestedPeriod = attested,
            AsOfNote = Mapping.OptionalLocalized(req.AsOfNote, "asOfNote"),
            Title = Mapping.OptionalLocalized(req.Title, "title"),
        };
        db.ControlSnapshots.Add(s);
        await db.SaveChangesAsync(ct);
        return ApiResults.Created($"/api/v1/control-snapshots/{s.Id}", new ControlSnapshotDto(
            s.Id, s.TheaterId, s.AsOf, s.Attestation, Mapping.ToDto(s.AttestedPeriod),
            Mapping.ReadLocalizedOrNull(s.AsOfNote), Mapping.ReadLocalizedOrNull(s.Title)));
    }
}
