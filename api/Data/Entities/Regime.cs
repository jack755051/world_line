namespace WorldLine.Api.Data.Entities;

/// <summary>
/// Status is one of: 'active' | 'split' | 'succeeded' | 'conquered' — culture-neutral codes for
/// 憲法 §4 狀態機's 存續／分裂／被取代(禪讓)／被滅亡. The constitution's Chinese vocabulary is the
/// authoritative business definition; these are just its storage encoding (2026-08-28 changed from
/// literal Chinese strings, which had already drifted — status used "被取代(禪讓)" while
/// OriginTransitionType used "被取代禪讓" for the same concept — and don't generalize cleanly to
/// non-Chinese regimes planned for M4 世界史, e.g. European personal-union mergers).
/// Transition edges (PredecessorRegimeId/OriginTransitionType/DestroyedByRegimeId) are the
/// objective fact layer only — "which lineage is orthodox" lives in LineagePreset instead (PRD §6 方案 D).
/// </summary>
public class Regime
{
    public Guid Id { get; set; }
    public string SelfName { get; set; } = null!;
    public string Status { get; set; } = null!;

    public Guid? PredecessorRegimeId { get; set; }
    public string? OriginTransitionType { get; set; } // 'split' | 'succeeded' | null
    public Guid? DestroyedByRegimeId { get; set; }

    public DateTimeOffset CreatedAt { get; set; }
    public DateTimeOffset UpdatedAt { get; set; }
    public int Version { get; set; }
}
