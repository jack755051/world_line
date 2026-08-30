namespace WorldLine.Api.Data.Entities;

/// <summary>
/// A named historiographical viewpoint (e.g. "傳統教科書史觀") pointing at a sequence of regimes.
/// Keeps "which lineage is orthodox" out of the neutral Regime graph (PRD §6 方案 D).
/// </summary>
public class LineagePreset
{
    public Guid Id { get; set; }
    public string PresetName { get; set; } = null!;
    public string? Description { get; set; }

    /// <summary>task 2.8：PRD Story 4 AC#3 要求「使用者未指定特定史觀時，依 lineage_
    /// presets 中的預設 preset 顯示主線」，但原本 schema 完全沒有欄位可以回答「哪一個
    /// 是預設」——不是靠插入順序或名稱字串猜（那樣之後新增/調整 preset 順序會意外改變
    /// 預設值，是隱性行為，跟這個專案一貫「不讓資料的巧合順序承載真正的商業語意」的原則
    /// 相反），2026-08-30 新增這個欄位明確標記。應用層目前不強制「最多一筆為 true」
    /// （task 2.8 範圍只有唯讀端點，沒有寫入端點，不會有人透過 API 改出兩個預設），
    /// 種子資料本身只標一筆。</summary>
    public bool IsDefault { get; set; }

    public DateTimeOffset CreatedAt { get; set; }
}
