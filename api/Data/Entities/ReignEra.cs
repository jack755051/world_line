namespace WorldLine.Api.Data.Entities;

/// <summary>
/// Era-name lookup table (e.g. 貞觀/開元/昭和/民國) — a lookup problem, not a calendar-conversion
/// problem, so this is plain data rather than a library dependency (PRD §5 拍板).
/// </summary>
public class ReignEra
{
    public Guid Id { get; set; }
    public Guid RegimeId { get; set; }
    public string EraName { get; set; } = null!;
    public int StartYear { get; set; }
    public int? EndYear { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
}
