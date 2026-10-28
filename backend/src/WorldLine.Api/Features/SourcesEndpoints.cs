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
        read.MapGet("/sources/{id:guid}", Get).WithTags("Sources").WithName("GetSource");
        write.MapPost("/sources", Create).WithTags("Sources").WithName("CreateSource").RequiresApiKey();
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
        };
        db.Sources.Add(s);
        await db.SaveChangesAsync(ct);
        return ApiResults.Created($"/api/v1/sources/{s.Id}", ToDto(s));
    }

    public static SourceDto ToDto(Source s) => new(
        s.Id, s.SourceKind, s.Title, s.Publisher, s.Authors, s.PublishedText, s.LicenseCode, s.LicenseEvidenceUrl,
        s.Url, s.ArchiveUrl, s.LocalCopyPath, s.CatalogId, s.Note);
}
