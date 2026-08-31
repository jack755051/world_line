namespace WorldLine.Api.Data.Entities;

/// <summary>`regime_territories` 逐筆可追溯來源（PRD §12「source/citation model」
/// TODO）——2026-08-31 吳（225年）pilot 是這張表第一筆真正的使用案例：`EvidenceNote`
/// 記錄「這塊疆域合併了 CHGIS 哪幾筆郡級記錄、用了什麼 GIS 方法、修補過哪些不合法
/// 幾何、還缺哪些郡沒資料」——`Source` 本身（例如「CHGIS v6」）可以被很多筆疆域快照
/// 共用，但每一筆的 `EvidenceNote` 都是獨立、具體的，不能共用同一份文字。</summary>
public class RegimeTerritoryCitation
{
    public Guid Id { get; set; }
    public Guid RegimeTerritoryId { get; set; }
    public Guid SourceId { get; set; }
    public string EvidenceNote { get; set; } = null!;
    public DateTimeOffset CreatedAt { get; set; }
}
