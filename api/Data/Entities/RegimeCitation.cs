namespace WorldLine.Api.Data.Entities;

/// <summary>`regimes` 逐筆可追溯來源（PRD §12「source/citation model」TODO）——同一個
/// 政權可以有多筆引用（例如自稱名稱一個來源、存續起訖另一個來源）。`EvidenceNote` 見
/// `Source` 類別文件說明：這裡才是「此來源具體支持這個政權的哪個結論」的地方。</summary>
public class RegimeCitation
{
    public Guid Id { get; set; }
    public Guid RegimeId { get; set; }
    public Guid SourceId { get; set; }
    public string EvidenceNote { get; set; } = null!;
    public DateTimeOffset CreatedAt { get; set; }
}
