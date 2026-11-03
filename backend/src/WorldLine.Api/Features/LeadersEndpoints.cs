using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using NpgsqlTypes;
using WorldLine.Api.Common;
using WorldLine.Api.Domain;
using WorldLine.Api.Infrastructure;
using WorldLine.Contracts;

namespace WorldLine.Api.Features;

/// <summary>
/// 領導人圖層（leader_records；2026-11-03 試驗，AI 提案・待拍板）。
/// - 每筆附出處文字（source）；查不到標「待查證」（verified=false）。
/// - 修正走軟撤回（I5），不硬刪。
/// - leader_bios：一人一筆生平（name、birth/death、summary 等），多任期共用，PersonId FK 指向此表。
/// </summary>
public static class LeadersEndpoints
{
    public static void Map(RouteGroupBuilder read, RouteGroupBuilder write)
    {
        read.MapGet("/leaders", GetOnDate).WithTags("Leaders").WithName("GetLeaders")
            .Ok<LeaderMapDto>().Errors(400);
        read.MapGet("/leader-bios/{id:guid}", GetBio).WithTags("Leaders").WithName("GetLeaderBio")
            .Ok<LeaderBioDto>().Errors(404);
        write.MapPost("/leader-records", Create).WithTags("Leaders").WithName("CreateLeaderRecord")
            .RequiresApiKey().Created<LeaderRecordDto>().Errors(400, 401);
        write.MapPost("/leader-bios", CreateBio).WithTags("Leaders").WithName("CreateLeaderBio")
            .RequiresApiKey().Created<LeaderBioDto>().Errors(400, 401);
        write.MapPatch("/leader-records/{id:guid}/person", LinkPerson).WithTags("Leaders").WithName("LinkLeaderPerson")
            .RequiresApiKey().Ok<LeaderRecordDto>().Errors(400, 401, 404);
    }

    // ── 任期紀錄 ──

    public static async Task<IResult> Create(CreateLeaderRecordRequest req, WorldLineDbContext db, CancellationToken ct)
    {
        if (req.RegimeId is not { } regimeId || !await db.Regimes.AnyAsync(x => x.Id == regimeId && x.RetractedAt == null, ct))
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "regimeId 指向的政權不存在。", "regimeId");

        if (req.PersonId is { } pid && !await db.LeaderBios.AnyAsync(x => x.Id == pid && x.RetractedAt == null, ct))
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "personId 指向的生平紀錄不存在或已撤回。", "personId");

        var name = Mapping.RequireText(req.Name, "name");
        var role = Mapping.RequireOneOf(req.Role, LeaderRoles.All, "role");
        var source = Mapping.RequireText(req.Source, "source");

        if (req.ValidFrom is null || !DateOnly.TryParse(req.ValidFrom, out var start))
            throw ApiError.BadRequest(ErrorCodes.PeriodRequired, "validFrom（YYYY-MM-DD）為必填。", "validFrom");

        DateOnly? endDate = null;
        if (req.ValidTo is not null)
        {
            if (!DateOnly.TryParse(req.ValidTo, out var e))
                throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "validTo 格式必須是 YYYY-MM-DD。", "validTo");
            if (e <= start)
                throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "validTo 必須晚於 validFrom。", "validTo");
            endDate = e;
        }
        var period = new NpgsqlRange<DateOnly>(start, true, false, endDate ?? default, false, endDate is null);

        var r = new LeaderRecord
        {
            Id = Guid.CreateVersion7(),
            RegimeId = regimeId,
            PersonId = req.PersonId,
            Name = name,
            NameZh = string.IsNullOrWhiteSpace(req.NameZh) ? null : req.NameZh.Trim(),
            Role = role,
            Title = string.IsNullOrWhiteSpace(req.Title) ? null : req.Title.Trim(),
            ValidPeriod = period,
            Source = source,
            SourceUrl = string.IsNullOrWhiteSpace(req.SourceUrl) ? null : req.SourceUrl.Trim(),
            Verified = req.Verified,
        };
        db.LeaderRecords.Add(r);
        await db.SaveChangesAsync(ct);
        return ApiResults.Created($"/api/v1/leader-records/{r.Id}", ToRecordDto(r));
    }

    /// <summary>PATCH /leader-records/{id}/person — 連結（或解除連結）任期紀錄與生平紀錄。</summary>
    public static async Task<IResult> LinkPerson(Guid id, LinkLeaderPersonRequest req, WorldLineDbContext db, CancellationToken ct)
    {
        if (req.PersonId is { } pid && !await db.LeaderBios.AnyAsync(x => x.Id == pid && x.RetractedAt == null, ct))
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "personId 指向的生平紀錄不存在或已撤回。", "personId");

        var row = await db.LeaderRecords.FirstOrDefaultAsync(x => x.Id == id && x.RetractedAt == null, ct)
            ?? throw ApiError.NotFound("領導人任期紀錄");

        row.PersonId = req.PersonId;
        await db.SaveChangesAsync(ct);
        return ApiResults.Ok(ToRecordDto(row));
    }

    /// <summary>GET /leaders?date=YYYY-MM-DD[&amp;regime={slug}] — 回傳指定日期所有在任領導人（retracted_at IS NULL 且 valid_period @> date）。</summary>
    public static async Task<IResult> GetOnDate(DateOnly? date, string? regime, WorldLineDbContext db, CancellationToken ct)
    {
        if (date is not { } d)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "date 為必填（YYYY-MM-DD）。", "date");

        var features = await BuildOnDateAsync(d, regime, db, ct);
        return ApiResults.Ok(new LeaderMapDto(d, features));
    }

    internal static async Task<List<LeaderFeature>> BuildOnDateAsync(DateOnly d, string? regimeSlug, WorldLineDbContext db, CancellationToken ct)
    {
        var rows = await (
                from l in db.LeaderRecords.AsNoTracking()
                join r in db.Regimes on l.RegimeId equals r.Id
                join b in db.LeaderBios on l.PersonId equals b.Id into bioJoin
                from bio in bioJoin.Where(bx => bx.RetractedAt == null).DefaultIfEmpty()
                where l.RetractedAt == null && l.ValidPeriod.Contains(d)
                    && (regimeSlug == null || r.Slug == regimeSlug)
                orderby l.RegimeId, l.Role, l.Id
                select new { l, r.Slug, bio })
            .ToListAsync(ct);

        return rows.Select(x => new LeaderFeature(
            x.l.Id,
            x.l.RegimeId,
            x.Slug,
            x.l.Name,
            x.l.NameZh,
            x.l.Role,
            x.l.Title,
            Mapping.ToDto(x.l.ValidPeriod)!,
            x.l.Source,
            x.l.SourceUrl,
            x.l.Verified,
            x.l.PersonId,
            x.bio == null ? null : ToBioSummaryDto(x.bio))).ToList();
    }

    // ── 生平 ──

    public static async Task<IResult> CreateBio(CreateLeaderBioRequest req, WorldLineDbContext db, CancellationToken ct)
    {
        var name = Mapping.RequireText(req.Name, "name");

        DateOnly? birthDate = null;
        if (req.BirthDate is not null)
        {
            if (!DateOnly.TryParse(req.BirthDate, out var bd))
                throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "birthDate 格式必須是 YYYY-MM-DD。", "birthDate");
            birthDate = bd;
        }

        if (req.BirthDatePrecision is not null &&
            !DatePrecisions.All.Contains(req.BirthDatePrecision))
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed,
                $"birthDatePrecision 必須是 {string.Join(" | ", DatePrecisions.All)} 之一。", "birthDatePrecision");

        DateOnly? deathDate = null;
        if (req.DeathDate is not null)
        {
            if (!DateOnly.TryParse(req.DeathDate, out var dd))
                throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "deathDate 格式必須是 YYYY-MM-DD。", "deathDate");
            deathDate = dd;
        }

        var fieldSourcesJson = req.FieldSources is { ValueKind: not JsonValueKind.Null } fs
            ? JsonSerializer.Serialize(fs)
            : null;

        var bio = new LeaderBio
        {
            Id = Guid.CreateVersion7(),
            Name = name,
            NameZh = string.IsNullOrWhiteSpace(req.NameZh) ? null : req.NameZh.Trim(),
            BirthDate = birthDate,
            BirthDatePrecision = req.BirthDatePrecision,
            DeathDate = deathDate,
            BirthPlace = Mapping.OptionalLocalized(req.BirthPlace, "birthPlace"),
            Party = Mapping.OptionalLocalized(req.Party, "party"),
            Summary = Mapping.OptionalLocalized(req.Summary, "summary"),
            FieldSources = fieldSourcesJson,
            IsTest = req.IsTest,
        };
        db.LeaderBios.Add(bio);
        await db.SaveChangesAsync(ct);
        return ApiResults.Created($"/api/v1/leader-bios/{bio.Id}", ToBioDto(bio));
    }

    /// <summary>GET /leader-bios/{id} — 完整生平（含 fieldSources）。</summary>
    public static async Task<IResult> GetBio(Guid id, WorldLineDbContext db, CancellationToken ct)
    {
        var bio = await db.LeaderBios.AsNoTracking().FirstOrDefaultAsync(x => x.Id == id, ct)
            ?? throw ApiError.NotFound("領導人生平紀錄");
        return ApiResults.Ok(ToBioDto(bio));
    }

    // ── Mapping helpers ──

    private static LeaderRecordDto ToRecordDto(LeaderRecord r) =>
        new(r.Id, r.RegimeId, r.Name, r.NameZh, r.Role, r.Title,
            Mapping.ToDto(r.ValidPeriod)!, r.Source, r.SourceUrl, r.Verified, r.PersonId);

    private static LeaderBioSummaryDto ToBioSummaryDto(LeaderBio b) =>
        new(b.Id, b.Name, b.NameZh,
            b.BirthDate?.ToString("yyyy-MM-dd"), b.BirthDatePrecision,
            b.DeathDate?.ToString("yyyy-MM-dd"),
            b.Summary == null ? null : Mapping.ReadLocalized(b.Summary));

    private static LeaderBioDto ToBioDto(LeaderBio b) =>
        new(b.Id, b.Name, b.NameZh,
            b.BirthDate?.ToString("yyyy-MM-dd"), b.BirthDatePrecision,
            b.DeathDate?.ToString("yyyy-MM-dd"),
            b.BirthPlace == null ? null : Mapping.ReadLocalized(b.BirthPlace),
            b.Party == null ? null : Mapping.ReadLocalized(b.Party),
            b.Summary == null ? null : Mapping.ReadLocalized(b.Summary),
            b.FieldSources == null ? null : JsonSerializer.Deserialize<JsonElement>(b.FieldSources),
            b.IsTest, b.RetractedAt, b.CreatedAt);
}
