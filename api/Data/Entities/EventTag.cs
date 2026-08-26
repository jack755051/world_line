namespace WorldLine.Api.Data.Entities;

/// <summary>Controlled vocabulary of event categories (war/trade/reform/...), many-to-many with events.</summary>
public class EventTag
{
    public int Id { get; set; }
    public string TagName { get; set; } = null!;
}
