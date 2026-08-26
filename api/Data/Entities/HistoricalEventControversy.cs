namespace WorldLine.Api.Data.Entities;

/// <summary>A specific point of unresolved historiographical dispute about an event (notes §十.2).</summary>
public class HistoricalEventControversy
{
    public Guid Id { get; set; }
    public string? EventId { get; set; }
    public string Topic { get; set; } = null!;
    public string NeutralDescription { get; set; } = null!;

    /// <summary>Raw JSON text — list of competing scholarly viewpoints/evidence.</summary>
    public string? Viewpoints { get; set; }
}
