using Microsoft.EntityFrameworkCore;
using WorldLine.Api.Common;
using WorldLine.Api.Domain;
using WorldLine.Api.Infrastructure;
using WorldLine.Contracts;

namespace WorldLine.Api.Features;

/// <summary>來源（R7）。</summary>
public static class SourcesEndpoints
{
    public static void Map(RouteGroupBuilder read, RouteGroupBuilder write)
    {
        read.MapGet("/sources/{id:guid}", Get).WithTags("Sources").WithName("GetSource").Ok<SourceDto>().Errors(404);
        write.MapPost("/sources", Create).WithTags("Sources").WithName("CreateSource").RequiresApiKey().Created<SourceDto>().Errors(400, 401);
    }

    public static async Task<IResult> Get(Guid id, WorldLineDbContext db, CancellationToken ct)
    {
        var s = await db.Sources.AsNoTracking().FirstOrDefaultAsync(x => x.Id == id, ct) ?? throw ApiError.NotFound("來源");
        return ApiResults.Ok(ToDto(s));
    }

    public static async Task<IResult> Create(CreateSourceRequest req, WorldLineDbContext db, CancellationToken ct)
    {
        var kind = Mapping.RequireOneOf(req.SourceKind, SourceKinds.All, "sourceKind");
        var title = Mapping.RequireText(req.Title, "title");
        if (string.IsNullOrWhiteSpace(req.Publisher))
            throw ApiError.BadRequest(ErrorCodes.SourceNotQualified, "來源必須有明確的出版者（R7）。", "publisher");
        if (CitationPolicy.IsSelfMadePublisher(req.Publisher))
            throw ApiError.BadRequest(ErrorCodes.SourceNotQualified, "只標「自製」的來源不採用（R7）。", "publisher");

        // 來源等級（docs/source-rules.md §2）：可不填（尚未評等）；填了就要寫依據。X 與禁用網域不收。
        var grade = string.IsNullOrWhiteSpace(req.Grade) ? null : Mapping.RequireOneOf(req.Grade, SourceGrades.All, "grade");
        if (grade == "X")
            throw ApiError.BadRequest(ErrorCodes.SourceNotQualified, "X 級來源不收（docs/source-rules.md §2）。", "grade");
        if (grade is not null && string.IsNullOrWhiteSpace(req.GradeBasis))
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, "填了來源等級就要寫評等依據。", "gradeBasis");
        if (BioSourcePolicy.IsExcludedUrl(req.Url) || BioSourcePolicy.IsExcludedUrl(req.ArchiveUrl))
            throw ApiError.BadRequest(ErrorCodes.SourceNotQualified, "來源網址屬禁用網域（data/source-policy.json）。", "url");

        var s = new Source
        {
            Id = Guid.CreateVersion7(),
            SourceKind = kind,
            Title = title,
            Publisher = req.Publisher.Trim(),
            Authors = req.Authors,
            PublishedText = req.PublishedText,
            LicenseCode = string.IsNullOrWhiteSpace(req.LicenseCode) ? null : Mapping.RequireText(req.LicenseCode, "licenseCode", 32),
            LicenseEvidenceUrl = req.LicenseEvidenceUrl,
            Url = req.Url,
            ArchiveUrl = req.ArchiveUrl,
            LocalCopyPath = req.LocalCopyPath,
            CatalogId = req.CatalogId,
            Note = req.Note,
            Grade = grade,
            GradeBasis = grade is null ? null : req.GradeBasis!.Trim(),
            Family = string.IsNullOrWhiteSpace(req.Family) ? null : Mapping.RequireText(req.Family, "family", 64),
        };
        db.Sources.Add(s);
        await db.SaveChangesAsync(ct);
        return ApiResults.Created($"/api/v1/sources/{s.Id}", ToDto(s));
    }

    public static SourceDto ToDto(Source s) => new(
        s.Id, s.SourceKind, s.Title, s.Publisher, s.Authors, s.PublishedText, s.LicenseCode, s.LicenseEvidenceUrl,
        s.Url, s.ArchiveUrl, s.LocalCopyPath, s.CatalogId, s.Note, s.Grade, s.GradeBasis, s.Family);
}
