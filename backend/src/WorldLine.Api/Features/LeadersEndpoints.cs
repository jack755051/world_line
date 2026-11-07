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
        write.MapPost("/leader-bios/{id:guid}/field-citations", AddFieldCitation).WithTags("Leaders").WithName("AddLeaderBioFieldCitation")
            .RequiresApiKey().Created<LeaderBioFieldCitationDto>().Errors(400, 401, 404, 409);
        write.MapPost("/leader-bio-field-citations/{id:guid}/retraction", RetractFieldCitation).WithTags("Leaders").WithName("RetractLeaderBioFieldCitation")
            .RequiresApiKey().Ok<RetractionDto>().Errors(400, 401, 404, 409);
        write.MapPost("/leader-bios/{id:guid}/revisions", Revise).WithTags("Leaders").WithName("ReviseLeaderBio")
            .RequiresApiKey().Created<LeaderBioDto>().Errors(400, 401, 404, 409);
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
        var bio = BuildBio(req);
        var citations = await BuildCitationsAsync(bio.Id, req.Citations, db, ct);
        db.LeaderBios.Add(bio);
        db.LeaderBioFieldCitations.AddRange(citations);
        await db.SaveChangesAsync(ct);
        return ApiResults.Created($"/api/v1/leader-bios/{bio.Id}", await LoadBioDtoAsync(bio.Id, db, ct));
    }

    /// <summary>從請求建立生平實體（只驗證，不寫入）。</summary>
    private static LeaderBio BuildBio(CreateLeaderBioRequest req)
    {
        var name = Mapping.RequireText(req.Name, "name");
        var birthDate = OptionalDate(req.BirthDate, "birthDate");
        var deathDate = OptionalDate(req.DeathDate, "deathDate");
        var birthPrec = OptionalPrecision(req.BirthDatePrecision, "birthDatePrecision");
        var deathPrec = OptionalPrecision(req.DeathDatePrecision, "deathDatePrecision");
        if (birthDate is not null && deathDate is not null && deathDate < birthDate)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "deathDate 不可早於 birthDate。", "deathDate");

        string? qid = null;
        if (!string.IsNullOrWhiteSpace(req.WikidataQid))
        {
            qid = req.WikidataQid.Trim();
            if (!System.Text.RegularExpressions.Regex.IsMatch(qid, "^Q[1-9][0-9]*$"))
                throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "wikidataQid 格式必須是 Q 加數字。", "wikidataQid");
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
            BirthDatePrecision = birthPrec,
            DeathDate = deathDate,
            DeathDatePrecision = deathPrec,
            BirthPlace = Mapping.OptionalLocalized(req.BirthPlace, "birthPlace"),
            Party = Mapping.OptionalLocalized(req.Party, "party"),
            Summary = Mapping.OptionalLocalized(req.Summary, "summary"),
            FieldSources = fieldSourcesJson,
            IsTest = req.IsTest,
            WikidataQid = qid,
        };
        if (req.Portrait is { } p) ApplyPortrait(bio, p);
        return bio;
    }

    private static DateOnly? OptionalDate(string? value, string field)
    {
        if (value is null) return null;
        if (!DateOnly.TryParse(value, out var d))
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, $"{field} 格式必須是 YYYY-MM-DD。", field);
        return d;
    }

    private static string? OptionalPrecision(string? value, string field)
    {
        if (value is null) return null;
        if (!DatePrecisions.All.Contains(value))
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed,
                $"{field} 必須是 {string.Join(" | ", DatePrecisions.All)} 之一。", field);
        return value;
    }

    private static string RequireHttpsUrl(string? value, string field)
    {
        var v = Mapping.RequireText(value, field);
        if (!Uri.TryCreate(v, UriKind.Absolute, out var u) || u.Scheme != Uri.UriSchemeHttps)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, $"{field} 必須是 https 網址。", field);
        return v;
    }

    /// <summary>照片：授權必須在允許清單，出處頁、署名、查證日期必填（R7 精神；不收受限或來源不明的圖）。</summary>
    private static void ApplyPortrait(LeaderBio bio, CreateLeaderPortraitRequest p)
    {
        var license = Mapping.RequireText(p.LicenseCode, "portrait.licenseCode", 32);
        if (!CitationPolicy.PrimaryLicenseAllowlist.Contains(license))
            throw ApiError.BadRequest(ErrorCodes.SourceNotQualified,
                $"照片授權（{license}）不在允許清單（{string.Join(", ", CitationPolicy.PrimaryLicenseAllowlist)}）。", "portrait.licenseCode");
        bio.PortraitUrl = RequireHttpsUrl(p.Url, "portrait.url");
        bio.PortraitSourceUrl = RequireHttpsUrl(p.SourceUrl, "portrait.sourceUrl");
        bio.PortraitAuthor = string.IsNullOrWhiteSpace(p.Author) ? null : p.Author.Trim();
        bio.PortraitLicenseCode = license;
        bio.PortraitLicenseUrl = string.IsNullOrWhiteSpace(p.LicenseUrl) ? null : RequireHttpsUrl(p.LicenseUrl, "portrait.licenseUrl");
        bio.PortraitAttribution = Mapping.RequireText(p.Attribution, "portrait.attribution");
        bio.PortraitRetrievedOn = OptionalDate(p.RetrievedOn, "portrait.retrievedOn")
            ?? throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "portrait.retrievedOn（查證授權日期）為必填。", "portrait.retrievedOn");
    }

    private static async Task<List<LeaderBioFieldCitation>> BuildCitationsAsync(
        Guid bioId, IReadOnlyList<CreateLeaderBioFieldCitationRequest>? reqs, WorldLineDbContext db, CancellationToken ct)
    {
        var list = new List<LeaderBioFieldCitation>();
        if (reqs is null) return list;
        for (var i = 0; i < reqs.Count; i++)
            list.Add(await BuildCitationAsync(bioId, reqs[i], db, ct, $"citations[{i}]."));
        return list;
    }

    private static async Task<LeaderBioFieldCitation> BuildCitationAsync(
        Guid bioId, CreateLeaderBioFieldCitationRequest r, WorldLineDbContext db, CancellationToken ct, string prefix = "")
    {
        var field = Mapping.RequireOneOf(r.Field, LeaderBioFields.All, prefix + "field");
        if (r.SourceId is not { } sid || !await db.Sources.AnyAsync(x => x.Id == sid, ct))
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "sourceId 指向的來源不存在。", prefix + "sourceId");
        var locator = Mapping.RequireText(r.Locator, prefix + "locator");
        var accessed = OptionalDate(r.AccessedOn, prefix + "accessedOn")
            ?? throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "accessedOn（查證日期）為必填。", prefix + "accessedOn");
        return new LeaderBioFieldCitation
        {
            Id = Guid.CreateVersion7(),
            BioId = bioId,
            Field = field,
            SourceId = sid,
            Locator = locator,
            EvidenceNote = string.IsNullOrWhiteSpace(r.EvidenceNote) ? null : r.EvidenceNote.Trim(),
            AccessedOn = accessed,
        };
    }

    /// <summary>POST /leader-bios/{id}/field-citations — 為現有生平的某欄位加一筆引用（不改生平本身）。</summary>
    public static async Task<IResult> AddFieldCitation(Guid id, CreateLeaderBioFieldCitationRequest req, WorldLineDbContext db, CancellationToken ct)
    {
        var bio = await db.LeaderBios.AsNoTracking().Select(x => new { x.Id, x.RetractedAt }).FirstOrDefaultAsync(x => x.Id == id, ct)
            ?? throw ApiError.NotFound("領導人生平紀錄");
        if (bio.RetractedAt is not null)
            throw new ApiError(StatusCodes.Status409Conflict, ErrorCodes.ConflictingOfficialVersion, $"生平 {id} 已撤回，不可再加引用。");
        var c = await BuildCitationAsync(id, req, db, ct);
        db.LeaderBioFieldCitations.Add(c);
        await db.SaveChangesAsync(ct);
        var src = await db.Sources.AsNoTracking().FirstAsync(x => x.Id == c.SourceId, ct);
        return ApiResults.Created($"/api/v1/leader-bios/{id}", ToCitationDto(c, src));
    }

    /// <summary>撤回一筆欄位引用（I5：只寫一次 retracted_at＋原因，不刪除）。</summary>
    public static async Task<IResult> RetractFieldCitation(Guid id, RetractionRequest req, WorldLineDbContext db, CancellationToken ct)
    {
        var reason = Mapping.RequireText(req.Reason, "reason");
        var row = await db.LeaderBioFieldCitations.AsNoTracking().Select(x => new { x.Id, x.RetractedAt })
            .FirstOrDefaultAsync(x => x.Id == id, ct) ?? throw ApiError.NotFound("生平欄位引用");
        if (row.RetractedAt is not null)
            throw new ApiError(StatusCodes.Status409Conflict, ErrorCodes.ConflictingOfficialVersion, $"引用 {id} 已於 {row.RetractedAt:O} 撤回。");
        var now = DateTimeOffset.UtcNow;
        var n = await db.LeaderBioFieldCitations.Where(x => x.Id == id && x.RetractedAt == null)
            .ExecuteUpdateAsync(u => u.SetProperty(x => x.RetractedAt, now).SetProperty(x => x.RetractionReason, reason), ct);
        if (n != 1)
            throw new ApiError(StatusCodes.Status409Conflict, ErrorCodes.ConflictingOfficialVersion, $"引用 {id} 已被撤回。");
        return ApiResults.Ok(new RetractionDto(id, now, reason));
    }

    /// <summary>
    /// POST /leader-bios/{id}/revisions — 撤回重寫（I5）：同一交易內撤回舊生平（記原因、superseded_by 指向新筆）、
    /// 建立新生平、把連到舊筆的有效任期改連新筆、複製舊筆未撤回的欄位引用。舊筆內容完整保留。
    /// </summary>
    public static async Task<IResult> Revise(Guid id, ReviseLeaderBioRequest req, WorldLineDbContext db, CancellationToken ct)
    {
        var reason = Mapping.RequireText(req.Reason, "reason");
        if (req.Bio is null)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "bio 為必填（新版生平的完整內容）。", "bio");

        await using var tx = await db.Database.BeginTransactionAsync(ct);
        var old = await db.LeaderBios.FirstOrDefaultAsync(x => x.Id == id, ct) ?? throw ApiError.NotFound("領導人生平紀錄");
        if (old.RetractedAt is not null)
            throw new ApiError(StatusCodes.Status409Conflict, ErrorCodes.ConflictingOfficialVersion, $"生平 {id} 已於 {old.RetractedAt:O} 撤回。");

        var bio = BuildBio(req.Bio);
        if (req.Bio.FieldSources is null) bio.FieldSources = old.FieldSources; // 舊格式出處備註沿用
        var newCitations = await BuildCitationsAsync(bio.Id, req.Bio.Citations, db, ct);
        var carried = await db.LeaderBioFieldCitations.AsNoTracking()
            .Where(x => x.BioId == id && x.RetractedAt == null).ToListAsync(ct);

        db.LeaderBios.Add(bio);
        await db.SaveChangesAsync(ct);
        db.LeaderBioFieldCitations.AddRange(newCitations);
        db.LeaderBioFieldCitations.AddRange(carried.Select(c => new LeaderBioFieldCitation
        {
            Id = Guid.CreateVersion7(), BioId = bio.Id, Field = c.Field, SourceId = c.SourceId,
            Locator = c.Locator, EvidenceNote = c.EvidenceNote, AccessedOn = c.AccessedOn,
        }));
        old.RetractedAt = DateTimeOffset.UtcNow;
        old.RetractionReason = reason;
        old.SupersededBy = bio.Id;
        await db.SaveChangesAsync(ct);
        await db.LeaderRecords.Where(x => x.PersonId == id && x.RetractedAt == null)
            .ExecuteUpdateAsync(u => u.SetProperty(x => x.PersonId, bio.Id), ct);
        await tx.CommitAsync(ct);
        return ApiResults.Created($"/api/v1/leader-bios/{bio.Id}", await LoadBioDtoAsync(bio.Id, db, ct));
    }

    /// <summary>GET /leader-bios/{id} — 完整生平（含 fieldSources、欄位引用、照片、全部有效任期）。已撤回者仍回傳（附 retractedAt、supersededBy）。</summary>
    public static async Task<IResult> GetBio(Guid id, WorldLineDbContext db, CancellationToken ct) =>
        ApiResults.Ok(await LoadBioDtoAsync(id, db, ct));

    private static async Task<LeaderBioDto> LoadBioDtoAsync(Guid id, WorldLineDbContext db, CancellationToken ct)
    {
        var bio = await db.LeaderBios.AsNoTracking().FirstOrDefaultAsync(x => x.Id == id, ct)
            ?? throw ApiError.NotFound("領導人生平紀錄");

        var citations = await (
                from c in db.LeaderBioFieldCitations.AsNoTracking()
                join s in db.Sources.AsNoTracking() on c.SourceId equals s.Id
                where c.BioId == id && c.RetractedAt == null
                orderby c.Field, c.CreatedAt
                select new { c, s })
            .ToListAsync(ct);

        var terms = await (
                from l in db.LeaderRecords.AsNoTracking()
                join r in db.Regimes.AsNoTracking() on l.RegimeId equals r.Id
                where l.PersonId == id && l.RetractedAt == null
                select new { l, r.Slug })
            .ToListAsync(ct);
        var regimeIds = terms.Select(t => t.l.RegimeId).Distinct().ToList();
        var names = (await db.RegimeNames.AsNoTracking()
                .Where(n => regimeIds.Contains(n.RegimeId) && n.NameKind == NameKinds.Self && n.RetractedAt == null)
                .OrderByDescending(n => n.IsPrimary).ThenBy(n => n.CreatedAt)
                .Select(n => new { n.RegimeId, n.Display })
                .ToListAsync(ct))
            .GroupBy(n => n.RegimeId)
            .ToDictionary(g => g.Key, g => Mapping.ReadLocalizedOrNull(g.First().Display));

        return new LeaderBioDto(bio.Id, bio.Name, bio.NameZh,
            bio.BirthDate?.ToString("yyyy-MM-dd"), bio.BirthDatePrecision,
            bio.DeathDate?.ToString("yyyy-MM-dd"),
            Mapping.ReadLocalizedOrNull(bio.BirthPlace),
            Mapping.ReadLocalizedOrNull(bio.Party),
            Mapping.ReadLocalizedOrNull(bio.Summary),
            bio.FieldSources == null ? null : JsonSerializer.Deserialize<JsonElement>(bio.FieldSources),
            bio.IsTest, bio.RetractedAt, bio.RetractionReason, bio.CreatedAt,
            bio.DeathDatePrecision, bio.WikidataQid, ToPortraitDto(bio), bio.SupersededBy,
            citations.Select(x => ToCitationDto(x.c, x.s)).ToList(),
            terms.OrderBy(t => t.l.ValidPeriod.LowerBound).ThenBy(t => t.l.Role)
                .Select(t => new LeaderTermDto(t.l.Id, t.l.RegimeId, t.Slug, names.GetValueOrDefault(t.l.RegimeId),
                    t.l.Role, t.l.Title, Mapping.ToDto(t.l.ValidPeriod)!, t.l.Source, t.l.SourceUrl))
                .ToList());
    }

    // ── Mapping helpers ──

    private static LeaderRecordDto ToRecordDto(LeaderRecord r) =>
        new(r.Id, r.RegimeId, r.Name, r.NameZh, r.Role, r.Title,
            Mapping.ToDto(r.ValidPeriod)!, r.Source, r.SourceUrl, r.Verified, r.PersonId);

    private static LeaderPortraitDto? ToPortraitDto(LeaderBio b) =>
        b.PortraitUrl is null ? null
            : new(b.PortraitUrl, b.PortraitSourceUrl!, b.PortraitAuthor, b.PortraitLicenseCode!, b.PortraitLicenseUrl,
                b.PortraitAttribution!, b.PortraitRetrievedOn!.Value.ToString("yyyy-MM-dd"));

    private static LeaderBioFieldCitationDto ToCitationDto(LeaderBioFieldCitation c, Source s) =>
        new(c.Id, c.Field, c.Locator, c.EvidenceNote, c.AccessedOn.ToString("yyyy-MM-dd"), SourcesEndpoints.ToDto(s));

    private static LeaderBioSummaryDto ToBioSummaryDto(LeaderBio b) =>
        new(b.Id, b.Name, b.NameZh,
            b.BirthDate?.ToString("yyyy-MM-dd"), b.BirthDatePrecision,
            b.DeathDate?.ToString("yyyy-MM-dd"),
            b.Summary == null ? null : Mapping.ReadLocalized(b.Summary),
            b.DeathDatePrecision, ToPortraitDto(b));
}
