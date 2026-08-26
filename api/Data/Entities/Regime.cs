namespace WorldLine.Api.Data.Entities;

/// <summary>
/// Status is one of: 存續 / 分裂 / 被取代(禪讓) / 被滅亡 (憲法 §4 狀態機).
/// Transition edges (PredecessorRegimeId/OriginTransitionType/DestroyedByRegimeId) are the
/// objective fact layer only — "which lineage is orthodox" lives in LineagePreset instead (PRD §6 方案 D).
/// </summary>
public class Regime
{
    public Guid Id { get; set; }
    public string SelfName { get; set; } = null!;
    public string Status { get; set; } = null!;

    public Guid? PredecessorRegimeId { get; set; }
    public string? OriginTransitionType { get; set; } // '分裂' | '被取代禪讓' | null
    public Guid? DestroyedByRegimeId { get; set; }

    public DateTimeOffset CreatedAt { get; set; }
    public DateTimeOffset UpdatedAt { get; set; }
    public int Version { get; set; }
}
