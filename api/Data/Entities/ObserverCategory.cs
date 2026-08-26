namespace WorldLine.Api.Data.Entities;

/// <summary>
/// Controlled vocabulary for non-regime perspective holders (e.g. "國際第三者（當代旁觀）"、
/// "後世史學界（事後回顧）") — replaces free text so the same concept doesn't get spelled
/// differently across rows.
/// </summary>
public class ObserverCategory
{
    public int Id { get; set; }
    public string CategoryName { get; set; } = null!;
}
