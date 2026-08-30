namespace WorldLine.Api.Contracts;

/// <summary>`GET /api/v1/lineage-presets` 的回應形狀（task 2.8）。</summary>
public class LineagePresetResponse
{
    public required Guid Id { get; init; }
    public required string PresetName { get; init; }
    public required string? Description { get; init; }
    /// <summary>PRD Story 4 AC#3：使用者未指定特定史觀時，UI 該顯示哪一個 preset 當
    /// 主線——見 `LineagePreset.IsDefault` 的類別註解，這裡直接透傳。</summary>
    public required bool IsDefault { get; init; }
}
