namespace WorldLine.Api.Data.Entities;

/// <summary>`lineage_presets.preset_name`/`description` 的其他語言版本（憲法 R4，PRD §6）。</summary>
public class LineagePresetTranslation
{
    public Guid Id { get; set; }
    public Guid LineagePresetId { get; set; }
    public string Locale { get; set; } = null!;
    public string PresetName { get; set; } = null!;
    public string? Description { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
}
