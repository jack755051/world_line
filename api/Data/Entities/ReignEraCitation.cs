namespace WorldLine.Api.Data.Entities;

/// <summary>`reign_eras` 逐筆可追溯來源（PRD §12「source/citation model」TODO）。見
/// `Source`/`RegimeTerritoryCitation` 類別文件說明。</summary>
public class ReignEraCitation
{
    public Guid Id { get; set; }
    public Guid ReignEraId { get; set; }
    public Guid SourceId { get; set; }
    public string EvidenceNote { get; set; } = null!;
    public DateTimeOffset CreatedAt { get; set; }
}
