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
    public DateTimeOffset CreatedAt { get; set; }
}
