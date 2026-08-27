namespace WorldLine.Api.Data.Entities;

/// <summary>
/// Join row linking a regime's transition edge to the historical_events row(s) that caused it.
/// A single Regime row can carry both edges at once (e.g. 蜀漢: predecessor=漢 via 分裂, later
/// destroyed_by=曹魏), so TransitionKind disambiguates which edge ("origin" vs "destruction")
/// an event applies to. Many-to-many: one transition can have multiple contributing events
/// (a campaign of battles), and one event can trigger multiple regimes' transitions at once.
/// </summary>
public class RegimeTransitionEvent
{
    public Guid RegimeId { get; set; }
    public string EventId { get; set; } = null!;
    public string TransitionKind { get; set; } = null!; // 'origin' | 'destruction'
}
