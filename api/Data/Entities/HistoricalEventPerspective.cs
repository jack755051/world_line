namespace WorldLine.Api.Data.Entities;

/// <summary>
/// One party's subjective narrative of an event. RegimeId is for regime perspectives;
/// ObserverCategoryId is for non-regime observers. Application layer must enforce that at
/// least one of the two is set (Phase 2 concern, not a DB constraint here — PRD §6).
/// </summary>
public class HistoricalEventPerspective
{
    public Guid Id { get; set; }
    public string? EventId { get; set; }
    public Guid? RegimeId { get; set; }
    public int? ObserverCategoryId { get; set; }

    public string LocalName { get; set; } = null!;
    public string NarrativeSummary { get; set; } = null!;
    public string? OfficialJustification { get; set; }

    /// <summary>Raw JSON text, e.g. [{ "title": "...", "author": "...", "year": 1937 }].</summary>
    public string? PrimarySources { get; set; }

    /// <summary>Raw JSON text, e.g. { "own_loss": "...", "enemy_loss": "..." }.</summary>
    public string? ClaimedCasualties { get; set; }
}
